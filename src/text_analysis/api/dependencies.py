from typing import Annotated

from fastapi import Depends

from src.text_analysis.bootstrap import TextAnalysisModule


def get_text_analysis_dependencies() -> TextAnalysisModule:
    ...


T_TextAnalysisDeps = Annotated[
    TextAnalysisModule, Depends(get_text_analysis_dependencies)
]
