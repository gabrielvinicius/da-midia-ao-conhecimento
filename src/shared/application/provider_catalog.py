from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field


class ProviderOption(BaseModel):
    """Provider exposto para seleção no pipeline.

    Importante: este contrato não expõe detalhes internos de adapters (classes,
    bibliotecas, endpoints). É apenas o que o usuário pode selecionar no upload.
    """

    name: str
    label: str
    description: Optional[str] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class ProvidersResponse(BaseModel):
    """Response do endpoint `GET /providers`."""

    stages: Dict[str, List[ProviderOption]] = Field(default_factory=dict)


def merge_provider_stages(
    *sources: Mapping[str, List[ProviderOption]],
) -> Dict[str, List[ProviderOption]]:
    """Merge determinístico de providers por stage.

    - Deduplica por (stage, name) preservando a primeira ocorrência.
    - Ordena por stage e por `name` para estabilidade.
    """

    merged: Dict[str, Dict[str, ProviderOption]] = {}
    for source in sources:
        for stage, providers in source.items():
            stage_map = merged.setdefault(stage, {})
            for provider in providers:
                if provider.name not in stage_map:
                    stage_map[provider.name] = provider

    ordered: Dict[str, List[ProviderOption]] = {}
    for stage in sorted(merged.keys()):
        ordered[stage] = [merged[stage][name] for name in sorted(merged[stage].keys())]
    return ordered


__all__ = [
    "ProviderOption",
    "ProvidersResponse",
    "merge_provider_stages",
]

