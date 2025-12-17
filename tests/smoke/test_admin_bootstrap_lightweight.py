import os

import pytest

from main import create_app
from src.admin.api.dependencies import AdminDependencies, get_admin_dependencies
from src.admin.application.services.admin_service import AdminService
from src.media_processing import MediaProcessingService
from src.shared.application.service_registry import DomainServiceRegistry


@pytest.mark.smoke
@pytest.mark.anyio("asyncio")
async def test_admin_bootstrap_lightweight(anyio_backend_name):
    if anyio_backend_name != "asyncio":
        pytest.skip("Only asyncio backend supported in lightweight bootstrap")
    os.environ.setdefault("LIGHTWEIGHT_BOOTSTRAP", "1")
    app = create_app()
    async with app.router.lifespan_context(app):
        dependencies_factory = app.dependency_overrides[get_admin_dependencies]
        admin_deps = dependencies_factory()
        assert isinstance(admin_deps, AdminDependencies)
        assert isinstance(admin_deps.service, AdminService)

        # Admin module remains powered by admin services during Stage A.
        assert admin_deps.user_service.__class__.__module__.startswith("src.admin")
        assert admin_deps.media_service.__class__.__module__.startswith("src.admin")
        assert admin_deps.audit_service.__class__.__module__.startswith("src.admin")

        registry = app.state.domain_services
        assert isinstance(registry, DomainServiceRegistry)
        assert registry.user_management.module is not None
        assert registry.media_management.module is not None

        # Facade instances are attached for future refactors.
        assert isinstance(registry.media_processing.facade, MediaProcessingService)
        # In lightweight mode, text_analysis is skipped, facade is None
        assert registry.text_analysis.facade is None
