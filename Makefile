.PHONY: test-unit test-smoke test-integration

VENV?=. .venv/bin/activate &&

test-unit:
	$(VENV) pytest tests/unit

test-smoke:
	$(VENV) pytest -m smoke tests/smoke

test-integration:
	$(VENV) pytest -m integration tests/integration
