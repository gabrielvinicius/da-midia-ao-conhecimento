import os

import pytest

from main import create_app


@pytest.mark.smoke
@pytest.mark.anyio("asyncio")
async def test_admin_bootstrap_lightweight(anyio_backend_name):
    if anyio_backend_name != "asyncio":
        pytest.skip("Only asyncio backend supported in lightweight bootstrap")
    os.environ.setdefault("LIGHTWEIGHT_BOOTSTRAP", "1")
    app = create_app()
    async with app.router.lifespan_context(app):
        assert hasattr(app.state, "event_bus")
        assert hasattr(app.state, "providers_read_service")

        # Confirma que o router admin foi incluído. Usa o OpenAPI em vez de
        # app.routes: versões recentes do FastAPI agrupam os routers incluídos
        # em objetos sem atributo "path".
        paths = app.openapi()["paths"]
        assert any(path.startswith("/admin") for path in paths)
