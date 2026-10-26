"""Student microservice: CRUD API protected by JWT issued by auth-service."""
import os
import sqlite3
from functools import wraps

import jwt
from flask import Flask, g, jsonify, request


def create_app(db_path=None, secret=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", "students.db")
    app.config["JWT_SECRET"] = secret or os.environ.get("JWT_SECRET", "dev-secret-change-me")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def require_auth(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return jsonify(error="Authentication required"), 401
            try:
                claims = jwt.decode(header[7:], app.config["JWT_SECRET"], algorithms=["HS256"])
            except jwt.InvalidTokenError:
                return jsonify(error="Invalid or expired token"), 401
            g.user = claims["sub"]
            return fn(*args, **kwargs)
        return wrapper

    with app.app_context():
        get_db().execute(
            """CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                course TEXT NOT NULL
            )"""
        )
        get_db().commit()

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="student-service")

    @app.get("/api/students")
    @require_auth
    def list_students():
        rows = get_db().execute("SELECT * FROM students ORDER BY id").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/students/<int:sid>")
    @require_auth
    def get_student(sid):
        row = get_db().execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
        if row is None:
            return jsonify(error="Student not found"), 404
        return jsonify(dict(row))

    @app.post("/api/students")
    @require_auth
    def create_student():
        data = request.get_json(silent=True) or {}
        if not all(data.get(k) for k in ("name", "email", "course")):
            return jsonify(error="name, email and course are required"), 400
        try:
            cur = get_db().execute(
                "INSERT INTO students (name, email, course) VALUES (?, ?, ?)",
                (data["name"], data["email"], data["course"]),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return jsonify(error="Email already exists"), 409
        return jsonify(id=cur.lastrowid, **{k: data[k] for k in ("name", "email", "course")}), 201

    @app.put("/api/students/<int:sid>")
    @require_auth
    def update_student(sid):
        data = request.get_json(silent=True) or {}
        row = get_db().execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
        if row is None:
            return jsonify(error="Student not found"), 404
        name = data.get("name", row["name"])
        email = data.get("email", row["email"])
        course = data.get("course", row["course"])
        get_db().execute(
            "UPDATE students SET name=?, email=?, course=? WHERE id=?",
            (name, email, course, sid),
        )
        get_db().commit()
        return jsonify(id=sid, name=name, email=email, course=course)

    @app.delete("/api/students/<int:sid>")
    @require_auth
    def delete_student(sid):
        cur = get_db().execute("DELETE FROM students WHERE id = ?", (sid,))
        get_db().commit()
        if cur.rowcount == 0:
            return jsonify(error="Student not found"), 404
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5002)))
