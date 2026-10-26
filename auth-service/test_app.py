import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "auth.db"), secret="test-secret")
    app.config["TESTING"] = True
    return app.test_client()


def creds(**kw):
    return {"username": "asha", "password": "secret123", **kw}


def test_health(client):
    assert client.get("/health").get_json()["status"] == "ok"


def test_register_and_login(client):
    assert client.post("/register", json=creds()).status_code == 201
    r = client.post("/login", json=creds())
    assert r.status_code == 200 and "token" in r.get_json()


def test_duplicate_username(client):
    client.post("/register", json=creds())
    assert client.post("/register", json=creds()).status_code == 409


def test_register_validation(client):
    assert client.post("/register", json=creds(username="ab")).status_code == 400
    assert client.post("/register", json=creds(password="123")).status_code == 400


def test_wrong_password(client):
    client.post("/register", json=creds())
    assert client.post("/login", json=creds(password="wrongpass")).status_code == 401


def test_unknown_user(client):
    assert client.post("/login", json=creds(username="nobody")).status_code == 401


def test_me_with_token(client):
    client.post("/register", json=creds())
    token = client.post("/login", json=creds()).get_json()["token"]
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.get_json()["username"] == "asha"


def test_me_rejects_bad_token(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer junk"}).status_code == 401
