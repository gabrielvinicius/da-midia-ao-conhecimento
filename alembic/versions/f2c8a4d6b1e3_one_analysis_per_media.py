"""Uma análise por mídia.

Cada nova tentativa da tarefa de análise criava outra análise, com outro id,
e as gravações parciais da tentativa anterior ficavam no banco. Ficam as
análises mais recentes de cada mídia; as avaliações das demais passam para
ela; e media_id ganha índice único.

Revision ID: f2c8a4d6b1e3
Revises: e5b1d9c3a7f4
Create Date: 2026-10-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f2c8a4d6b1e3"
down_revision: Union[str, None] = "e5b1d9c3a7f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RANKED = """
    WITH ranked AS (
        SELECT id, media_id,
               row_number() OVER (PARTITION BY media_id ORDER BY updated_at DESC, created_at DESC, id) AS rn
        FROM text_analysis_results
        WHERE media_id IS NOT NULL
    ), keep AS (
        SELECT media_id, id AS keep_id FROM ranked WHERE rn = 1
    )
"""


def upgrade() -> None:
    op.execute(
        _RANKED
        + """
        UPDATE analysis_feedback AS f SET analysis_id = k.keep_id
        FROM ranked r JOIN keep k ON k.media_id = r.media_id
        WHERE f.analysis_id = r.id AND r.rn > 1
        """
    )
    op.execute(
        _RANKED
        + """
        DELETE FROM text_analysis_results AS t
        USING ranked r WHERE t.id = r.id AND r.rn > 1
        """
    )
    op.drop_index("ix_text_analysis_results_media_id", table_name="text_analysis_results")
    op.create_index("ix_text_analysis_results_media_id", "text_analysis_results", ["media_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_text_analysis_results_media_id", table_name="text_analysis_results")
    op.create_index("ix_text_analysis_results_media_id", "text_analysis_results", ["media_id"], unique=False)
