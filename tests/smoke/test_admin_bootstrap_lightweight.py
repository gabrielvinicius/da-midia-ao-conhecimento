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

        # Confirma que o router admin foi incluído (sem depender de overrides).
        paths = {getattr(route, "path", None) for route in app.routes}
        assert any(path and path.startswith("/admin") for path in paths)
