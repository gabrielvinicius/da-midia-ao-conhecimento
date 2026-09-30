"""Fluxo do usuário pela API, com banco e fila reais."""
import os
import uuid

import pytest


@pytest.fixture(scope="module")
def client():
    os.environ["LIGHTWEIGHT_BOOTSTRAP"] = "0"
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as c:
        yield c


def _account(client, prefix):
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@teste.com"
    r = client.post("/auth/register", json={"email": email, "password": "Senha123"})
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "USER"
    r = client.post("/auth/token", data={"username": email, "password": "Senha123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_upload_list_isolation_and_delete(client):
    alice = _account(client, "alice")
    bob = _account(client, "bob")

    r = client.post(
        "/media/",
        headers=alice,
        files={"file": ("aula.txt", "A derivada mede a taxa de variação.".encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    media = r.json()
    assert media["media_type"].lower() == "text"
    media_id = media["id"]

    items = client.get("/media/", headers=alice).json()["items"]
    assert [m["id"] for m in items] == [media_id]

    # Outro usuário não vê nem apaga a mídia
    assert client.get("/media/", headers=bob).json()["items"] == []
    assert client.get(f"/media/{media_id}", headers=bob).status_code == 404
    assert client.delete(f"/media/{media_id}", headers=bob).status_code == 404

    assert client.delete(f"/media/{media_id}", headers=alice).status_code == 204
    assert client.get(f"/media/{media_id}", headers=alice).status_code == 404


def test_login_is_blocked_after_repeated_failures(client):
    email = f"carol-{uuid.uuid4().hex[:8]}@teste.com"
    client.post("/auth/register", json={"email": email, "password": "Senha123"})
    codes = [
        client.post("/auth/token", data={"username": email, "password": "errada"}).status_code
        for _ in range(6)
    ]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
    # Bloqueado mesmo com a senha certa, até o prazo acabar
    r = client.post("/auth/token", data={"username": email, "password": "Senha123"})
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_requests_without_token_are_rejected(client):
    assert client.get("/media/").status_code == 401
    assert client.get("/text-analysis/search", params={"q": "derivada"}).status_code == 401
