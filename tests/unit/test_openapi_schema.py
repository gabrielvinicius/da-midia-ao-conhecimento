"""Garante que todos os modelos da API são resolvíveis.

Um tipo sem import (ex.: ``List`` numa anotação) deixa o modelo Pydantic
"não totalmente definido": a rota que o usa falha e o /openapi.json (Swagger)
de toda a aplicação quebra.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.text_analysis.api import routers as text_analysis_routers
from src.text_analysis.api.schemas import AnalyzeRequest


def test_analyze_request_model_is_fully_defined():
    request = AnalyzeRequest.model_validate(
        {"text": "oi", "segments": [{"start": 0, "end": 1, "text": "oi"}]}
    )
    assert request.segments[0].text == "oi"


def test_text_analysis_openapi_schema_builds():
    app = FastAPI()
    app.include_router(text_analysis_routers.router)
    response = TestClient(app).get("/openapi.json")
    assert response.status_code == 200
    assert "/text-analysis/analyze" in response.json()["paths"]
