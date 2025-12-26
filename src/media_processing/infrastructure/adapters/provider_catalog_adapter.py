from __future__ import annotations

from typing import Dict, List

from src.shared.application.ports import PipelineProviderCatalogPort
from src.shared.application.provider_catalog import ProviderOption

from src.media_processing.infrastructure.dependencies import providers as registry


class MediaProcessingProvidersCatalogAdapter(PipelineProviderCatalogPort):
    """Expõe apenas providers do pipeline de media_processing."""

    def list_pipeline_providers(self) -> Dict[str, List[ProviderOption]]:
        def _build(stage: str, names: list[str], meta_fn):
            providers: List[ProviderOption] = []
            for name in names:
                meta = meta_fn(name)
                label = meta.get("label") or name.replace("_", " ").title()
                providers.append(
                    ProviderOption(
                        name=name,
                        label=label,
                        description=meta.get("description"),
                        capabilities=meta.get("capabilities", {}),
                    )
                )
            return providers

        transcribers = registry.list_speech_recognizers(public_only=True)
        text_extractors = registry.list_text_extractors(public_only=True)
        ocr_providers = registry.list_ocr_providers(public_only=True)

        stages: Dict[str, List[ProviderOption]] = {
            "transcription": _build("transcription", transcribers, registry.speech_recognizer_meta),
            "text_extraction": _build("text_extraction", text_extractors, registry.text_extractor_meta),
            "ocr": _build("ocr", ocr_providers, registry.ocr_provider_meta),
        }

        audio_extractors = registry.list_audio_extractors()
        if audio_extractors:
            stages["audio_extraction"] = _build(
                "audio_extraction",
                audio_extractors,
                registry.audio_extractor_meta,
            )

        return stages


__all__ = ["MediaProcessingProvidersCatalogAdapter"]
