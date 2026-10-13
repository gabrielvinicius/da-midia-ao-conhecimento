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


def test_new_analysis_preserves_a_reviewed_result_in_the_real_database(client):
    import asyncio

    from src.shared.infrastructure.database.db import AsyncSessionLocal
    from src.text_analysis.domain import Analysis, Document
    from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import SqlAlchemyAnalysisRepository

    headers = _account(client, "reviewed")
    response = client.post(
        "/media/", headers=headers, files={"file": ("revisao.txt", b"Texto da aula.", "text/plain")},
    )
    assert response.status_code == 201, response.text
    media = response.json()

    async def seed_review():
        async with AsyncSessionLocal() as session:
            repository = SqlAlchemyAnalysisRepository(session)
            analysis = Analysis.new(
                Document.from_payload("Texto da aula."), media_id=uuid.UUID(media["id"]),
                user_id=uuid.UUID(media["user_id"]),
            )
            analysis.summary = "Resumo original."
            await repository.save(analysis)
            await repository.update_summary(str(analysis.id), "Resumo revisado pelo usuário.")

    asyncio.run(seed_review())
    response = client.post("/text-analysis/analyze", headers=headers, json={"media_id": media["id"]})
    assert response.status_code == 409, response.text
    stored = client.get(f"/text-analysis/media/{media['id']}", headers=headers)
    assert stored.status_code == 200, stored.text
    assert stored.json()["summary"] == "Resumo revisado pelo usuário."
    assert stored.json()["diagnostics"]["original_ai_summary"] == "Resumo original."


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

    # Sem duração lida nem histórico, não há estimativa (e não um número inventado).
    r = client.get(f"/transcriptions/media/{media_id}/estimate", headers=alice)
    assert r.status_code == 200, r.text
    assert r.json()["estimated_seconds"] is None
    assert client.get(f"/transcriptions/media/{media_id}/estimate", headers=bob).status_code == 404

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

    for path in (
        "/admin/stats", "/admin/stats/health", "/admin/stats/media-processing", "/admin/users", "/admin/queue",
        "/admin/quality", "/admin/server", "/text-analysis/study-deck", "/text-analysis/notebook",
        "/text-analysis/topics-overview",
    ):
        response = client.get(path, headers=admin)
        assert response.status_code == 200, (path, response.text)
    assert client.get("/admin/stats", headers=admin).json()["total_users"] >= 1
    users = client.get("/admin/users", headers=admin).json()
    assert users["total"] >= 1
    user_id = users["items"][0]["id"]
    activity = client.get(f"/admin/users/{user_id}/activity", headers=admin)
    assert activity.status_code == 200, activity.text
    assert activity.json()["user_id"] == user_id
    media = client.get("/admin/media", headers=admin)
    assert media.status_code == 200
    assert all("owner_email" in item for item in media.json()["items"])
    queue = client.get("/admin/queue", headers=admin).json()
    assert set(queue["counts"]) == {"uploaded", "processing", "analyzing"}


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


def test_stalled_media_is_marked_failed_and_can_be_retried(client):
    """Worker morto no meio da tarefa: sem a verificação periódica, a mídia
    ficava "em processamento" para sempre e não podia ser reprocessada."""
    import asyncio

    from sqlalchemy import text

    from src.media_management.worker import bind_media_subscribers
    from src.media_processing.worker import MediaWorkerApp
    from src.media_processing.infrastructure.dependencies.builders import (
        build_stalled_processing_monitor,
    )
    from src.shared.infrastructure.database.db import AsyncSessionLocal, engine_sync
    from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus

    alice = _account(client, "erica")
    r = client.post(
        "/media/",
        headers=alice,
        files={"file": ("apostila.txt", "O limite descreve o comportamento da função.".encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    media_id = r.json()["id"]

    # O registro da extração é criado logo após a resposta do envio.
    import time

    for _ in range(50):
        with engine_sync.connect() as conn:
            if conn.execute(text("SELECT 1 FROM transcriptions WHERE media_id = :id"), {"id": media_id}).first():
                break
        time.sleep(0.1)

    # Simula a extração iniciada há 2 h por um worker que morreu (documento:
    # sem duração, prazo padrão de 1 h).
    with engine_sync.begin() as conn:
        conn.execute(text("UPDATE media SET status = 'PROCESSING' WHERE id = :id"), {"id": media_id})
        updated = conn.execute(
            text(
                "UPDATE transcriptions SET status = 'PROCESSING', "
                "updated_at = now() - interval '2 hours' WHERE media_id = :id"
            ),
            {"id": media_id},
        )
        assert updated.rowcount == 1

    async def sweep():
        bus = get_event_bus()
        MediaWorkerApp(event_bus=bus).subscribe()  # como no worker
        bind_media_subscribers(bus)
        async with AsyncSessionLocal() as session:
            return await build_stalled_processing_monitor(session, bus).sweep()

    assert media_id in asyncio.run(sweep())

    media = client.get(f"/media/{media_id}", headers=alice).json()
    assert media["status"].lower() == "failed"
    assert "tempo esperado" in media["error_message"]
    # E agora o usuário pode tentar de novo.
    assert client.post(f"/media/{media_id}/reprocess", headers=alice).status_code == 200


def test_upload_without_processing_record_is_requeued_then_failed(client):
    """API caiu entre gravar a mídia e criar o registro do processamento: a
    mídia ficava "enviada" para sempre, invisível ao monitor de prazos."""
    import asyncio
    import time

    from sqlalchemy import text

    from src.media_management.worker import bind_media_subscribers
    from src.media_processing.worker import MediaWorkerApp
    from src.media_management.infrastructure.dependencies.recovery import build_unstarted_media_recovery
    from src.shared.infrastructure.database.db import AsyncSessionLocal, engine_sync
    from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus

    alice = _account(client, "fabia")
    r = client.post(
        "/media/",
        headers=alice,
        files={"file": ("notas.txt", "A derivada mede a taxa de variação.".encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    media_id = r.json()["id"]

    def has_record():
        with engine_sync.connect() as conn:
            return conn.execute(
                text("SELECT 1 FROM transcriptions WHERE media_id = :id"), {"id": media_id}
            ).first() is not None

    for _ in range(50):
        if has_record():
            break
        time.sleep(0.1)

    def lose_record(minutes_ago):
        with engine_sync.begin() as conn:
            conn.execute(text("DELETE FROM transcriptions WHERE media_id = :id"), {"id": media_id})
            conn.execute(
                text(
                    "UPDATE media SET status = 'UPLOADED', "
                    "created_at = (now() at time zone 'utc') - make_interval(mins => :m) "
                    "WHERE id = :id"
                ),
                {"id": media_id, "m": minutes_ago},
            )

    async def recover():
        bus = get_event_bus()
        MediaWorkerApp(event_bus=bus).subscribe()  # como no worker
        bind_media_subscribers(bus)
        async with AsyncSessionLocal() as session:
            return await build_unstarted_media_recovery(session, bus).sweep()

    # Perdida há 20 min: volta para a fila.
    lose_record(20)
    result = asyncio.run(recover())
    assert media_id in result.requeued
    assert has_record()

    # Perdida há 2 h (reenfileirar não adiantou): falha, e o usuário pode tentar de novo.
    lose_record(120)
    result = asyncio.run(recover())
    assert media_id in result.failed
    media = client.get(f"/media/{media_id}", headers=alice).json()
    assert media["status"].lower() == "failed"
    assert "não chegou a começar" in media["error_message"]
    assert client.post(f"/media/{media_id}/reprocess", headers=alice).status_code == 200


def test_a_failed_or_stuck_analysis_can_be_reprocessed(client):
    """A mídia ficava "concluída" sem resumo quando a análise falhava, e o
    reprocessamento (só para mídias com falha) era recusado."""
    import asyncio

    from sqlalchemy import text

    from src.media_management.infrastructure.dependencies.recovery import build_unfinished_analysis_recovery
    from src.media_management.worker import bind_media_subscribers
    from src.shared.domain.events import AnalysisFailed
    from src.shared.infrastructure.database.db import AsyncSessionLocal, engine_sync
    from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus

    alice = _account(client, "gilda")

    def analyzing_media(hours_ago=0):
        r = client.post(
            "/media/", headers=alice,
            files={"file": ("resumo.txt", "A integral mede a área sob a curva.".encode(), "text/plain")},
        )
        assert r.status_code == 201, r.text
        media_id = r.json()["id"]
        with engine_sync.begin() as conn:
            conn.execute(
                text(
                    "UPDATE media SET status = 'ANALYZING', "
                    "updated_at = (now() at time zone 'utc') - make_interval(hours => :h) WHERE id = :id"
                ),
                {"id": media_id, "h": hours_ago},
            )
        return media_id

    async def fail_analysis(media_id):
        bus = get_event_bus()
        bind_media_subscribers(bus)
        await bus.publish(AnalysisFailed(media_id=media_id, error_message="CUDA out of memory"))

    async def sweep():
        async with AsyncSessionLocal() as session:
            return await build_unfinished_analysis_recovery(session, get_event_bus()).sweep()

    failed = analyzing_media()
    asyncio.run(fail_analysis(failed))
    stuck = analyzing_media(hours_ago=4)
    assert stuck in asyncio.run(sweep())

    for media_id, reason in ((failed, "análise do conteúdo falhou"), (stuck, "não terminou no prazo")):
        media = client.get(f"/media/{media_id}", headers=alice).json()
        assert media["status"].lower() == "failed" and reason in media["error_message"]
        assert client.post(f"/media/{media_id}/reprocess", headers=alice).status_code == 200


def test_deleting_analyzed_media_leaves_nothing_behind(client):
    """RNF06. A rota da API montava a exclusão sem a análise: os trechos
    indexados barravam a exclusão (chave estrangeira) depois de a transcrição
    já ter sido apagada, e análises e avaliações ficavam órfãs."""
    import time
    import uuid as _uuid

    from sqlalchemy import text

    from src.shared.infrastructure.database.db import engine_sync

    alice = _account(client, "gabi")
    r = client.post(
        "/media/",
        headers=alice,
        files={"file": ("aula.txt", "A regra da cadeia deriva funções compostas.".encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    media_id = r.json()["id"]

    tables = {
        "transcriptions": "media_id = :id",
        "text_analysis_results": "media_id = :id",
        "knowledge_chunks": "media_id = :id",
        "analysis_feedback": "analysis_id IN (SELECT id FROM text_analysis_results WHERE media_id = :id) OR analysis_id = :aid",
    }
    analysis_id = str(_uuid.uuid4())

    def counts():
        with engine_sync.connect() as conn:
            return {
                t: conn.execute(text(f"SELECT count(*) FROM {t} WHERE {where}"), {"id": media_id, "aid": analysis_id}).scalar()
                for t, where in tables.items()
            }

    for _ in range(50):
        if counts()["transcriptions"]:
            break
        time.sleep(0.1)

    # Simula o que o worker gravaria: análise, trecho indexado e uma avaliação.
    with engine_sync.begin() as conn:
        user_id = conn.execute(text("SELECT user_id FROM media WHERE id = :id"), {"id": media_id}).scalar()
        conn.execute(
            text("INSERT INTO text_analysis_results (id, document_id, media_id, user_id, payload) "
                 "VALUES (:aid, :aid, :id, :uid, '{}'::jsonb)"),
            {"aid": analysis_id, "id": media_id, "uid": user_id},
        )
        conn.execute(
            text("INSERT INTO knowledge_chunks (id, media_id, content, embedding) "
                 "VALUES (:cid, :id, 'regra da cadeia', array_fill(0.1, ARRAY[384])::vector)"),
            {"cid": str(_uuid.uuid4()), "id": media_id},
        )
        conn.execute(
            text("INSERT INTO analysis_feedback (id, analysis_id, user_id, score, aspect) "
                 "VALUES (:fid, :aid, :uid, 1, 'summary')"),
            {"fid": str(_uuid.uuid4()), "aid": analysis_id, "uid": user_id},
        )
    assert all(counts().values())

    from src.storage.infrastructure.dependencies import StorageServiceFactory

    with engine_sync.connect() as conn:
        stored = conn.execute(text("SELECT original_file_path FROM media WHERE id = :id"), {"id": media_id}).scalar()
    stored_file = StorageServiceFactory().get_provider_root("local") / stored
    assert stored_file.exists()

    assert client.delete(f"/media/{media_id}", headers=alice).status_code == 204
    assert client.get(f"/media/{media_id}", headers=alice).status_code == 404
    assert counts() == {t: 0 for t in tables}
    # O arquivo enviado também sai do disco (antes ficava: a pasta não era apagada).
    assert not stored_file.exists()


def test_failed_deletion_keeps_everything(client, monkeypatch):
    """Unidade de trabalho: se o arquivo não puder ser apagado, nenhum dado
    derivado sai do banco (antes, transcrição e análise já tinham sido
    apagadas quando a falha acontecia) e a exclusão pode ser repetida."""
    import time
    import uuid as _uuid

    from sqlalchemy import text

    from src.shared.infrastructure.database.db import engine_sync
    from src.storage.infrastructure.persistence.local_storage_repository import LocalStorageService

    alice = _account(client, "hele")
    r = client.post(
        "/media/",
        headers=alice,
        files={"file": ("aula.txt", "A integral acumula a variação.".encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    media_id = r.json()["id"]

    def count(table):
        with engine_sync.connect() as conn:
            return conn.execute(text(f"SELECT count(*) FROM {table} WHERE media_id = :id"), {"id": media_id}).scalar()

    for _ in range(50):
        if count("transcriptions"):
            break
        time.sleep(0.1)
    with engine_sync.begin() as conn:
        conn.execute(
            text("INSERT INTO text_analysis_results (id, document_id, media_id, payload) "
                 "VALUES (:aid, :aid, :id, '{}'::jsonb)"),
            {"aid": str(_uuid.uuid4()), "id": media_id},
        )

    async def broken_remove_folder(self, folder_path):
        raise OSError("disco somente leitura")

    monkeypatch.setattr(LocalStorageService, "remove_folder", broken_remove_folder)
    r = client.delete(f"/media/{media_id}", headers=alice)
    assert r.status_code == 503, r.text
    assert count("transcriptions") == 1
    assert count("text_analysis_results") == 1
    assert client.get(f"/media/{media_id}", headers=alice).status_code == 200

    monkeypatch.undo()
    assert client.delete(f"/media/{media_id}", headers=alice).status_code == 204
    assert count("transcriptions") == 0 and count("text_analysis_results") == 0


def test_semantic_search_only_returns_the_owners_chunks(client):
    """A busca filtra pelo dono gravado no próprio trecho (antes, consultava a
    tabela de mídias, que é de outro módulo)."""
    import asyncio
    import time

    from sqlalchemy import text

    from src.shared.infrastructure.database.db import AsyncSessionLocal, engine_sync
    from src.text_analysis.infrastructure.repositories.vector_repository import VectorRepository

    owners = {}
    for name in ("iara", "joao"):
        headers = _account(client, name)
        r = client.post(
            "/media/",
            headers=headers,
            files={"file": (f"{name}.txt", "A derivada mede a variação.".encode(), "text/plain")},
        )
        assert r.status_code == 201, r.text
        media_id = r.json()["id"]
        with engine_sync.connect() as conn:
            owners[name] = (media_id, conn.execute(
                text("SELECT user_id FROM media WHERE id = :id"), {"id": media_id}
            ).scalar())

    vector = [0.1] * 384

    async def index_and_search():
        async with AsyncSessionLocal() as session:
            repo = VectorRepository(session)
            for name, (media_id, user_id) in owners.items():
                await repo.save_chunks(
                    media_id, [{"text": f"trecho de {name}", "embedding": vector}], user_id=user_id
                )
            rows = await repo.semantic_search(vector, limit=10, user_id=owners["iara"][1])
            return [row.content for row, _ in rows]

    time.sleep(0.2)
    assert asyncio.run(index_and_search()) == ["trecho de iara"]


def test_existing_users_can_be_updated(client):
    """Troca de senha e mudança de perfil gravam um usuário que já existe."""
    email = f"lia-{uuid.uuid4().hex[:8]}@teste.com"
    assert client.post("/auth/register", json={"email": email, "password": "Senha123"}).status_code == 201
    token = client.post("/auth/token", data={"username": email, "password": "Senha123"}).json()["access_token"]
    me = {"Authorization": f"Bearer {token}"}

    r = client.put("/auth/me/password", headers=me, json={"old_password": "Senha123", "new_password": "Nova12345"})
    assert r.status_code == 204, r.text
    assert client.post("/auth/token", data={"username": email, "password": "Nova12345"}).status_code == 200

    admin_email, admin_password = os.environ.get("DEFAULT_ADMIN_EMAIL"), os.environ.get("DEFAULT_ADMIN_PASSWORD")
    if not (admin_email and admin_password):
        return
    admin_token = client.post("/auth/token", data={"username": admin_email, "password": admin_password}).json()["access_token"]
    admin = {"Authorization": f"Bearer {admin_token}"}
    user_id = client.get("/auth/me", headers=me).json()["id"]
    r = client.put(f"/admin/users/{user_id}", headers=admin, json={"role": "ADMIN"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "ADMIN"


def test_logout_ends_the_session_and_refresh_rotates(client):
    """O logout só apagava o cookie: uma cópia do token de renovação seguia
    renovando a sessão por 7 dias, e ele também valia como token de acesso."""
    email = f"sara-{uuid.uuid4().hex[:8]}@teste.com"
    assert client.post("/auth/register", json={"email": email, "password": "Senha123"}).status_code == 201
    first = client.post("/auth/token", data={"username": email, "password": "Senha123"}).cookies["refresh_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {first}"}).status_code == 401

    client.cookies.set("refresh_token", first)
    second = client.post("/auth/refresh")
    assert second.status_code == 200
    client.cookies.set("refresh_token", first)
    assert client.post("/auth/refresh").status_code == 401  # usado uma vez

    copy = second.cookies["refresh_token"]
    client.cookies.set("refresh_token", copy)
    assert client.post("/auth/logout").status_code == 200
    client.cookies.set("refresh_token", copy)
    assert client.post("/auth/refresh").status_code == 401
    client.cookies.clear()


def test_deactivated_user_loses_access(client):
    """Desativar uma conta no painel não bloqueava nada: o login, o token já
    emitido e a renovação continuavam funcionando."""
    admin_email, admin_password = os.environ.get("DEFAULT_ADMIN_EMAIL"), os.environ.get("DEFAULT_ADMIN_PASSWORD")
    if not (admin_email and admin_password):
        pytest.skip("sem administrador padrão")
    email = f"rui-{uuid.uuid4().hex[:8]}@teste.com"
    assert client.post("/auth/register", json={"email": email, "password": "Senha123"}).status_code == 201
    login = client.post("/auth/token", data={"username": email, "password": "Senha123"})
    me = {"Authorization": f"Bearer {login.json()['access_token']}"}
    refresh_cookie = login.cookies["refresh_token"]
    user_id = client.get("/auth/me", headers=me).json()["id"]

    admin_token = client.post("/auth/token", data={"username": admin_email, "password": admin_password}).json()["access_token"]
    admin = {"Authorization": f"Bearer {admin_token}"}
    r = client.post(f"/admin/users/{user_id}/deactivate", headers=admin)
    assert r.status_code == 200, r.text

    assert client.get("/auth/me", headers=me).status_code == 401
    client.cookies.set("refresh_token", refresh_cookie)
    assert client.post("/auth/refresh").status_code == 401
    r = client.post("/auth/token", data={"username": email, "password": "Senha123"})
    assert r.status_code == 401 and "desativada" in r.json()["detail"]


def test_notifications_survive_a_closed_page(client):
    """Os avisos eram gravados, mas a interface só via os que chegavam pelo
    WebSocket com a página aberta, e "lido" se perdia ao recarregar."""
    import asyncio

    from src.notifications.domain import Notification, NotificationType
    from src.notifications.infrastructure.repositories.notification_repository import (
        NotificationRepository,
    )
    from src.shared.infrastructure.database.db import AsyncSessionLocal

    alice = _account(client, "nina")
    alice_id = client.get("/auth/me", headers=alice).json()["id"]
    bob = _account(client, "otto")

    async def store(text):
        async with AsyncSessionLocal() as session:
            saved = await NotificationRepository(db=session).save(
                Notification(user_id=uuid.UUID(alice_id), type=NotificationType.WEBSOCKET, content=text)
            )
            return str(saved.id)

    first = asyncio.run(store("Transcrição concluída"))
    asyncio.run(store("Análise concluída"))

    items = client.get("/notifications/", headers=alice).json()
    assert [n["content"] for n in items] == ["Análise concluída", "Transcrição concluída"]
    assert not any(n["read"] for n in items)
    assert client.get("/notifications/", headers=bob).json() == []

    assert client.post(f"/notifications/{first}/read", headers=bob).status_code == 404
    assert client.post(f"/notifications/{first}/read", headers=alice).status_code == 204
    read = {n["id"]: n["read"] for n in client.get("/notifications/", headers=alice).json()}
    assert read[first] is True and list(read.values()).count(False) == 1
    # O filtro de não lidos vem antes do limite: o único não lido aparece
    # mesmo pedindo um só aviso (antes, a lista filtrava depois do limite).
    asyncio.run(store("Aviso mais novo"))
    client.post(f"/notifications/{client.get('/notifications/?limit=1', headers=alice).json()[0]['id']}/read", headers=alice)
    [unread] = client.get("/notifications/?unread=true&limit=1", headers=alice).json()
    assert unread["content"] == "Análise concluída"

    assert client.post("/notifications/read-all", headers=alice).status_code == 204
    assert all(n["read"] for n in client.get("/notifications/", headers=alice).json())


def test_websocket_delivers_what_arrived_with_the_page_closed(client):
    """A conexão fechava logo após abrir (método inexistente na consulta dos
    pendentes), e os pendentes saíam num formato que a interface ignorava."""
    import asyncio

    import pytest
    from starlette.websockets import WebSocketDisconnect

    from src.notifications.domain import Notification
    from src.notifications.infrastructure.repositories.notification_repository import (
        NotificationRepository,
    )
    from src.shared.infrastructure.database.db import AsyncSessionLocal

    headers = _account(client, "paula")
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    token = client.post("/auth/scoped-token", headers=headers, json={"purpose": "notifications"}).json()["token"]

    async def store():
        async with AsyncSessionLocal() as session:
            await NotificationRepository(db=session).save(
                Notification(user_id=uuid.UUID(user_id), content="Análise concluída")
            )

    asyncio.run(store())
    import time

    with client.websocket_connect(f"/ws/notifications?token={token}") as ws:
        message = ws.receive_json()
        # Marcado como entregue logo depois do envio, com a conexão aberta.
        for _ in range(50):
            [item] = client.get("/notifications/", headers=headers).json()
            if item["status"] == "delivered":
                break
            time.sleep(0.05)
    assert message["kind"] == "new_notification"
    assert message["payload"]["content"] == "Análise concluída"
    assert item["status"] == "delivered"

    # Já entregue: uma nova conexão não o repete. Sem token, a conexão é recusada.
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/notifications") as ws:
            ws.receive_json()


def test_admin_manages_own_media_and_owner_is_reported(client):
    """O painel barrava o admin nas próprias mídias (regra feita para contas),
    e a resposta da mídia não dizia o dono, então o dono não via "Reprocessar"."""
    admin_email, admin_password = os.environ.get("DEFAULT_ADMIN_EMAIL"), os.environ.get("DEFAULT_ADMIN_PASSWORD")
    if not (admin_email and admin_password):
        pytest.skip("sem administrador padrão")
    token = client.post("/auth/token", data={"username": admin_email, "password": admin_password}).json()["access_token"]
    admin = {"Authorization": f"Bearer {token}"}
    admin_id = client.get("/auth/me", headers=admin).json()["id"]

    r = client.post("/media/", headers=admin, files={"file": ("pauta.txt", b"Reuniao de pauta.", "text/plain")})
    assert r.status_code == 201, r.text
    assert r.json()["user_id"] == admin_id

    assert client.delete(f"/admin/media/{r.json()['id']}", headers=admin).status_code == 204


def test_s3_storage_keeps_files_in_the_bucket(client):
    """A opção "s3" gravava no disco local. Roda quando há um bucket configurado
    (STORAGE_S3_BUCKET), por exemplo com um MinIO ou o servidor do moto."""
    from src.storage.config.settings import storage_settings

    if not storage_settings.s3_configured:
        pytest.skip("sem S3 configurado")
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=storage_settings.s3_endpoint_url,
        aws_access_key_id=storage_settings.s3_access_key,
        aws_secret_access_key=storage_settings.s3_secret_key,
        region_name=storage_settings.s3_region,
    )
    me = _account(client, "sara")
    r = client.post(
        "/media/?storage_provider=s3",
        headers=me,
        files={"file": ("ata.txt", "Ata da reunião.".encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    media = r.json()
    assert media["storage_provider"] == "s3"

    keys = [o["Key"] for o in s3.list_objects_v2(Bucket=storage_settings.s3_bucket).get("Contents", [])]
    assert any(media["id"] in key for key in keys)

    # O token de acesso não vai mais na URL; o de reprodução só abre esta mídia.
    access = me["Authorization"].split()[1]
    assert client.get(f"/media/{media['id']}/stream?token={access}").status_code == 401
    token = client.post(
        "/auth/scoped-token", headers=me, json={"purpose": "media_stream", "resource": media["id"]}
    ).json()["token"]
    stream = client.get(f"/media/{media['id']}/stream?token={token}")
    assert stream.status_code == 200 and stream.content == "Ata da reunião.".encode()
    # O reprodutor pede trechos: só o intervalo pedido volta (lido em partes).
    part = client.get(f"/media/{media['id']}/stream?token={token}", headers={"Range": "bytes=0-2"})
    assert part.status_code == 206 and part.content == b"Ata"
    assert part.headers["content-range"].startswith("bytes 0-2/")

    assert client.delete(f"/media/{media['id']}", headers=me).status_code == 204
    keys = [o["Key"] for o in s3.list_objects_v2(Bucket=storage_settings.s3_bucket).get("Contents", [])]
    assert not any(media["id"] in key for key in keys)


def test_deleting_a_user_removes_their_media_and_notifications(client):
    """Excluir quem já tinha enviado algo dava 500: as chaves estrangeiras das
    mídias e dos avisos barravam a exclusão, e a resposta expunha o erro do banco."""
    import asyncio

    from sqlalchemy import text as sql

    from src.notifications.domain import Notification, NotificationType
    from src.notifications.infrastructure.repositories.notification_repository import (
        NotificationRepository,
    )
    from src.shared.infrastructure.database.db import AsyncSessionLocal, engine_sync

    admin_email, admin_password = os.environ.get("DEFAULT_ADMIN_EMAIL"), os.environ.get("DEFAULT_ADMIN_PASSWORD")
    if not (admin_email and admin_password):
        pytest.skip("sem administrador padrão")
    me = _account(client, "lia")
    user_id = client.get("/auth/me", headers=me).json()["id"]
    media_id = client.post(
        "/media/", headers=me, files={"file": ("ata.txt", "Ata da reunião.".encode(), "text/plain")}
    ).json()["id"]

    async def notify():
        async with AsyncSessionLocal() as session:
            await NotificationRepository(db=session).save(
                Notification(user_id=uuid.UUID(user_id), type=NotificationType.WEBSOCKET, content="Pronto")
            )

    asyncio.run(notify())
    admin_token = client.post("/auth/token", data={"username": admin_email, "password": admin_password}).json()["access_token"]

    r = client.delete(f"/admin/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 204, r.text

    with engine_sync.connect() as conn:
        for table, column, value in (("users", "id", user_id), ("media", "id", media_id), ("notifications", "user_id", user_id)):
            count = conn.execute(sql(f"SELECT count(*) FROM {table} WHERE {column} = :v"), {"v": value}).scalar()
            assert count == 0, table
