"""Identifica o gênero do conteúdo para orientar o resumo.

Uma chamada curta ao modelo de linguagem, com trechos do início, do meio e
do fim e os sinais que a análise já tem (gravação ou documento, duração, o
que aparecia na tela, temas). Sem resposta válida, o gênero fica vazio e o
resumo usa as instruções gerais.
"""
from __future__ import annotations

from typing import Optional

import structlog

from src.text_analysis.application.pipeline.base import AnalysisStep
from src.text_analysis.application.ports import TextGenerationPort
from src.text_analysis.domain import Analysis, ContentGenre
from src.text_analysis.domain.content_genre import parse_genre

logger = structlog.get_logger(__name__)

SAMPLE_CHARS = 1200  # de cada parte: início, meio e fim

GENRE_OPTIONS = (
    "- aula: explicação didática e neutra de um conteúdo, para ensinar (conceitos, exemplos, exercícios);\n"
    "- palestra: apresentação para um público, com uma tese e argumentos;\n"
    "- opiniao: ensaio, crítica ou comentário em que quem fala defende uma posição pessoal, mesmo que "
    "conte uma história ou explique conceitos para sustentá-la;\n"
    "- reuniao: várias pessoas discutindo, decidindo e combinando tarefas;\n"
    "- entrevista: perguntas e respostas entre pessoas, podcast ou debate;\n"
    "- tutorial: passo a passo prático de como fazer algo;\n"
    "- documento: texto escrito (apostila, artigo, lei, contrato, relatório);\n"
    "- outro: nenhum dos anteriores.\n"
)

# O que o resumo de cada gênero precisa trazer (entra no prompt da síntese).
GENRE_FOCUS = {
    ContentGenre.LECTURE: (
        "É uma aula: explique os conceitos na ordem em que são ensinados, com as definições, "
        "os exemplos e os exercícios ou aplicações propostos."
    ),
    ContentGenre.TALK: (
        "É uma palestra: apresente a tese central, os argumentos e exemplos usados e as conclusões, "
        "atribuídos a quem fala."
    ),
    ContentGenre.OPINION: (
        "É um conteúdo opinativo: apresente a tese e os argumentos como posições de quem fala "
        "(\"o apresentador argumenta que…\"), separe os fatos e dados citados das opiniões e termine "
        "com a conclusão ou o apelo final."
    ),
    ContentGenre.MEETING: (
        "É uma reunião: organize por assunto da pauta, com as decisões tomadas, as tarefas e os "
        "responsáveis (quando ditos) e o que ficou pendente."
    ),
    ContentGenre.INTERVIEW: (
        "É uma entrevista ou conversa: identifique os participantes pelo papel (entrevistador, "
        "convidado), atribua as falas e destaque as perguntas centrais e as respostas."
    ),
    ContentGenre.TUTORIAL: (
        "É um tutorial: descreva os passos na ordem, com as ferramentas, comandos e cuidados mencionados."
    ),
    ContentGenre.DOCUMENT: (
        "É um documento escrito: siga a estrutura dele (seções, capítulos, artigos), com definições, "
        "obrigações, prazos e valores exatamente como estão no texto."
    ),
}


def genre_focus(genre: Optional[ContentGenre]) -> Optional[str]:
    return GENRE_FOCUS.get(genre) if genre else None


class ContentGenreStep(AnalysisStep):
    """Gênero do conteúdo (aula, reunião, documento...), antes do resumo."""

    def __init__(self, text_generation: TextGenerationPort):
        self.text_generation = text_generation

    @property
    def name(self) -> str:
        return "content_genre"

    async def process(self, analysis: Analysis) -> Analysis:
        text = (analysis.document.text or "").strip() if analysis.document else ""
        if not text:
            return analysis
        # Sem modelo, o erro chega ao pipeline, que registra a etapa como falha
        # (antes ela saía "ok" e o resumo perdia a orientação sem aviso).
        answer = await self.text_generation.summarize_topic(
            "Gênero do conteúdo", self.build_prompt(analysis, text), [], "pt", max_tokens=10
        )
        analysis.genre = parse_genre(answer)
        logger.info("content_genre.identified", genre=analysis.genre.value if analysis.genre else None)
        return analysis

    def build_prompt(self, analysis: Analysis, text: str) -> str:
        return (
            "<<<SYSTEM>>>\nVocê classifica conteúdos para escolher como resumi-los.\n<<<END_SYSTEM>>>\n"
            "Classifique o material em UM destes gêneros:\n" + GENRE_OPTIONS + "\n"
            "Sinais da análise:\n" + "\n".join(f"- {s}" for s in self.signals(analysis)) + "\n\n"
            + self.samples(text)
            + "\nSe quem fala critica, alerta ou defende uma posição ao longo do material, é opiniao ou "
            "palestra, e não aula. Responda só com o gênero, em uma palavra, sem explicação."
        )

    @staticmethod
    def signals(analysis: Analysis) -> list[str]:
        starts = [c.end or c.start for c in analysis.chunks or [] if (c.end or c.start) is not None]
        if starts:
            signals = [f"gravação de cerca de {max(1, round(max(starts) / 60))} min"]
        else:
            signals = ["documento escrito (sem áudio)"]
        if analysis.visual_context:
            signals.append("na tela: " + " | ".join(v.split("] ", 1)[-1][:160] for v in analysis.visual_context[:4]))
        titles = [t.title for t in analysis.main_topics if t.title][:6]
        if titles:
            signals.append("temas: " + "; ".join(titles))
        return signals

    @staticmethod
    def samples(text: str) -> str:
        if len(text) <= SAMPLE_CHARS * 3:
            return "<trecho>\n" + text + "\n</trecho>\n"
        middle = len(text) // 2 - SAMPLE_CHARS // 2
        parts = {"início": text[:SAMPLE_CHARS], "meio": text[middle:middle + SAMPLE_CHARS], "fim": text[-SAMPLE_CHARS:]}
        return "".join(f"<trecho parte='{k}'>\n{v}\n</trecho>\n" for k, v in parts.items())


__all__ = ["ContentGenreStep", "GENRE_FOCUS", "genre_focus"]
