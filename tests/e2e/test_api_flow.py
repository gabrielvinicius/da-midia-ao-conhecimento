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


def _set_status(media_id, status):
    """Simula o resultado do worker, que não roda nos testes de ponta a ponta."""
    from sqlalchemy import text

    from src.shared.infrastructure.database.db import engine_sync

    with engine_sync.begin() as conn:
        conn.execute(
            text("UPDATE media SET status = :status, error_message = :error WHERE id = :id"),
            {"status": status, "error": "falha simulada" if status == "FAILED" else None, "id": media_id},
        )


def test_owner_retries_only_failed_media(client):
    alice = _account(client, "alice")
    bob = _account(client, "bob")
    r = client.post(
        "/media/",
        headers=alice,
        files={"file": ("aula.txt", "A integral acumula a variação.".encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    media_id = r.json()["id"]

    # Concluída: reprocessar apagaria o resumo corrigido e as avaliações.
    _set_status(media_id, "COMPLETED")
    r = client.post(f"/media/{media_id}/reprocess", headers=alice)
    assert r.status_code == 409, r.text

    _set_status(media_id, "FAILED")
    # Outro usuário não reprocessa (nem descobre que a mídia existe).
    assert client.post(f"/media/{media_id}/reprocess", headers=bob).status_code == 404

    r = client.post(f"/media/{media_id}/reprocess", headers=alice)
    assert r.status_code == 200, r.text
    media = client.get(f"/media/{media_id}", headers=alice).json()
    assert media["status"].lower() == "processing"
    assert not media.get("error_message")

    # Em processamento: um segundo clique não reinicia a mídia.
    assert client.post(f"/media/{media_id}/reprocess", headers=alice).status_code == 409


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
    assert client.get("/text-analysis/search", params={"query": "derivada"}).status_code == 401


def test_admin_dashboard_endpoints_answer(client):
    """O painel do administrador falhava com 500 (método inexistente no
    repositório de usuários); só aparece com o banco real."""
    email, password = os.environ.get("DEFAULT_ADMIN_EMAIL"), os.environ.get("DEFAULT_ADMIN_PASSWORD")
    if not (email and password):
        pytest.skip("defina DEFAULT_ADMIN_EMAIL e DEFAULT_ADMIN_PASSWORD")
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    admin = {"Authorization": f"Bearer {r.json()['access_token']}"}

    for path in ("/admin/stats", "/admin/stats/health", "/admin/stats/media-processing", "/admin/users"):
        response = client.get(path, headers=admin)
        assert response.status_code == 200, (path, response.text)
    assert client.get("/admin/stats", headers=admin).json()["total_users"] >= 1
    users = client.get("/admin/users", headers=admin).json()
    assert users["total"] >= 1
    user_id = users["items"][0]["id"]
    activity = client.get(f"/admin/users/{user_id}/activity", headers=admin)
    assert activity.status_code == 200, activity.text
    assert activity.json()["user_id"] == user_id
    assert client.get("/admin/media", headers=admin).status_code == 200


def test_concurrent_requests_each_get_their_own_session(client):
    """Antes, todos os módulos usavam uma única sessão criada na inicialização:
    requisições simultâneas falhavam com 500 ("concurrent operations are not
    permitted") e podiam misturar o estado de transação entre usuários."""
    import asyncio

    import httpx

    import main

    headers = _account(client, "dora")
    paths = ["/media/", "/media/stats", "/auth/me"] * 10

    async def burst():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            responses = await asyncio.gather(*(ac.get(p, headers=headers) for p in paths))
        return [r.status_code for r in responses]

    codes = asyncio.run(burst())
    assert codes == [200] * len(paths)
