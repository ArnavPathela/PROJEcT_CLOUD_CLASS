import jwt
import pytest

from app import create_app

SECRET = "test-secret"


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"), secret=SECRET)
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture()
def auth():
    token = jwt.encode({"sub": "tester"}, SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def sample(**kw):
    return {"name": "Asha", "email": "asha@example.com", "course": "CS", **kw}


def test_health(client):
    assert client.get("/health").get_json()["status"] == "ok"


def test_requires_auth(client):
    assert client.get("/api/students").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/students", headers=bad).status_code == 401


def test_rejects_token_signed_with_wrong_secret(client):
    token = jwt.encode({"sub": "evil"}, "other-secret", algorithm="HS256")
    r = client.get("/api/students", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_create_and_get(client, auth):
    r = client.post("/api/students", json=sample(), headers=auth)
    assert r.status_code == 201
    sid = r.get_json()["id"]
    assert client.get(f"/api/students/{sid}", headers=auth).get_json()["name"] == "Asha"


def test_list(client, auth):
    client.post("/api/students", json=sample(), headers=auth)
    client.post("/api/students", json=sample(email="b@example.com"), headers=auth)
    assert len(client.get("/api/students", headers=auth).get_json()) == 2


def test_validation(client, auth):
    assert client.post("/api/students", json={"name": "x"}, headers=auth).status_code == 400


def test_duplicate_email(client, auth):
    client.post("/api/students", json=sample(), headers=auth)
    assert client.post("/api/students", json=sample(), headers=auth).status_code == 409


def test_update(client, auth):
    sid = client.post("/api/students", json=sample(), headers=auth).get_json()["id"]
    r = client.put(f"/api/students/{sid}", json={"course": "AI"}, headers=auth)
    assert r.status_code == 200 and r.get_json()["course"] == "AI"


def test_delete(client, auth):
    sid = client.post("/api/students", json=sample(), headers=auth).get_json()["id"]
    assert client.delete(f"/api/students/{sid}", headers=auth).status_code == 204
    assert client.get(f"/api/students/{sid}", headers=auth).status_code == 404


def test_not_found(client, auth):
    assert client.get("/api/students/999", headers=auth).status_code == 404
    assert client.delete("/api/students/999", headers=auth).status_code == 404
