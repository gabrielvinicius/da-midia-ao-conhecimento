from typing import Annotated, TYPE_CHECKING

from fastapi import Depends

if TYPE_CHECKING:
    from src.text_analysis.bootstrap import TextAnalysisModule
else:
    TextAnalysisModule = object


def get_text_analysis_dependencies() -> "TextAnalysisModule":
    ...


T_TextAnalysisDeps = Annotated[
    TextAnalysisModule, Depends(get_text_analysis_dependencies)
]
