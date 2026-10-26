"""Auth microservice: register, login (JWT), token verification."""
import datetime
import os
import sqlite3

import jwt
from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash


def create_app(db_path=None, secret=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", "auth.db")
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

    with app.app_context():
        get_db().execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )"""
        )
        get_db().commit()

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="auth-service")

    @app.post("/register")
    def register():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        if len(username) < 3:
            return jsonify(error="Username must be at least 3 characters"), 400
        if len(password) < 6:
            return jsonify(error="Password must be at least 6 characters"), 400
        try:
            get_db().execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return jsonify(error="Username already taken"), 409
        return jsonify(message="User registered", username=username), 201

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        row = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row is None or not check_password_hash(row["password_hash"], password):
            return jsonify(error="Invalid username or password"), 401
        payload = {
            "sub": row["username"],
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2),
        }
        token = jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")
        return jsonify(token=token, username=row["username"])

    @app.get("/me")
    def me():
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Missing token"), 401
        try:
            claims = jwt.decode(header[7:], app.config["JWT_SECRET"], algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify(error="Invalid or expired token"), 401
        return jsonify(username=claims["sub"])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
