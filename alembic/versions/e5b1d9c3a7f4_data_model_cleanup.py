"""Limpeza do modelo de dados.

- transcriptions: a coluna JSON "result" guardava a saída bruta do Whisper,
  que repetia o texto e os segmentos já gravados, junto com a duração e o
  contexto visual. Esses dois ganham colunas próprias e "result" sai. A
  confiança, que ficava sempre em 0, é calculada a partir dos segmentos.
- Datas com fuso (UTC) em todas as tabelas: media, text_analysis_results e
  processing_stats gravavam sem fuso, e o código convertia nas comparações.
- text_analysis_results.id/document_id e analysis_feedback.analysis_id viram
  UUID, como os demais ids; a avaliação ganha chave estrangeira para a
  análise, e a análise para a mídia (como transcrições e trechos indexados).
  Ids que não sejam UUID recebem um UUID determinístico (md5), o mesmo nas
  duas tabelas. Análises de mídias que já não existem são removidas.
- Enums nativos do PostgreSQL viram texto (VARCHAR), validados pela
  aplicação: incluir ou remover um valor não exige mais migração.

Revision ID: e5b1d9c3a7f4
Revises: d7a3c5e1f9b2
Create Date: 2026-10-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5b1d9c3a7f4"
down_revision: Union[str, None] = "d7a3c5e1f9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID_RE = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

_ENUMS = {
    # (tabela, coluna): (tipo nativo, valores)
    ("users", "role"): ("userrole", ("ADMIN", "USER")),
    ("media", "media_type"): ("mediatype", ("AUDIO", "VIDEO", "TEXT")),
    ("media", "status"): ("mediastatus", ("UPLOADED", "PROCESSING", "COMPLETED", "FAILED")),
    ("transcriptions", "status"): ("transcriptionstatus", ("PENDING", "PROCESSING", "COMPLETED", "FAILED")),
    ("notifications", "type"): ("notificationtype", ("EMAIL", "SMS", "PUSH", "WEBSOCKET")),
    ("notifications", "priority"): ("notificationpriority", ("LOW", "NORMAL", "HIGH", "CRITICAL")),
    ("notifications", "status"): ("notificationstatus", ("PENDING", "SENT", "DELIVERED", "READ", "FAILED")),
}

_TIMESTAMPS = (
    ("media", "created_at"),
    ("media", "updated_at"),
    ("text_analysis_results", "created_at"),
    ("text_analysis_results", "updated_at"),
    ("processing_stats", "created_at"),
)


def _as_uuid(column: str) -> str:
    return f"CASE WHEN {column} ~ '{_UUID_RE}' THEN {column}::uuid ELSE md5({column})::uuid END"


def upgrade() -> None:
    # Transcrições: colunas tipadas no lugar do JSON "result".
    op.add_column("transcriptions", sa.Column("media_duration_seconds", sa.Float(), nullable=True))
    op.add_column("transcriptions", sa.Column("visual_context", sa.JSON(), nullable=True))
    op.execute(
        "UPDATE transcriptions SET "
        "media_duration_seconds = (result::jsonb ->> 'media_duration_seconds')::float, "
        "visual_context = (result::jsonb -> 'visual_context')::json "
        "WHERE result IS NOT NULL"
    )
    op.drop_column("transcriptions", "result")
    op.execute(
        """
        UPDATE transcriptions t SET confidence_score = c.value FROM (
            SELECT t2.id, round((
                sum(least(1.0, exp((s ->> 'confidence')::float)) * w.weight) / sum(w.weight)
            )::numeric, 3)::float AS value
            FROM transcriptions t2,
                 json_array_elements(t2.segments) AS s,
                 LATERAL (SELECT CASE
                     WHEN (s ->> 'end')::float > (s ->> 'start')::float
                     THEN (s ->> 'end')::float - (s ->> 'start')::float ELSE 1.0 END AS weight) w
            WHERE json_typeof(t2.segments) = 'array' AND (s ->> 'confidence') IS NOT NULL
            GROUP BY t2.id
        ) c WHERE t.id = c.id
        """
    )
    op.execute("UPDATE transcriptions SET confidence_score = NULL WHERE confidence_score = 0")

    # Datas com fuso: os valores gravados já estavam em UTC.
    for table, column in _TIMESTAMPS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )
    op.create_index(op.f("ix_processing_stats_created_at"), "processing_stats", ["created_at"], unique=False)

    # Análises e avaliações com UUID e chaves estrangeiras.
    op.execute("DELETE FROM analysis_feedback WHERE analysis_id IN ("
               "SELECT id FROM text_analysis_results WHERE media_id IS NOT NULL "
               "AND media_id NOT IN (SELECT id FROM media))")
    op.execute("DELETE FROM text_analysis_results WHERE media_id IS NOT NULL "
               "AND media_id NOT IN (SELECT id FROM media)")
    op.execute("DELETE FROM analysis_feedback WHERE analysis_id NOT IN (SELECT id FROM text_analysis_results)")
    op.execute(f"ALTER TABLE text_analysis_results ALTER COLUMN id TYPE UUID USING {_as_uuid('id')}")
    op.execute(f"ALTER TABLE text_analysis_results ALTER COLUMN document_id TYPE UUID USING {_as_uuid('document_id')}")
    op.execute(f"ALTER TABLE analysis_feedback ALTER COLUMN analysis_id TYPE UUID USING {_as_uuid('analysis_id')}")
    op.create_foreign_key(
        "analysis_feedback_analysis_id_fkey", "analysis_feedback", "text_analysis_results",
        ["analysis_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "text_analysis_results_media_id_fkey", "text_analysis_results", "media", ["media_id"], ["id"]
    )

    # Enums como texto.
    for (table, column), (type_name, _) in _ENUMS.items():
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(32) USING {column}::text")
    for type_name, _ in set(_ENUMS.values()):
        op.execute(f"DROP TYPE IF EXISTS {type_name}")


def downgrade() -> None:
    for type_name, values in set(_ENUMS.values()):
        quoted = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {type_name} AS ENUM ({quoted})")
    for (table, column), (type_name, _) in _ENUMS.items():
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {type_name} USING {column}::{type_name}")

    op.drop_constraint("text_analysis_results_media_id_fkey", "text_analysis_results", type_="foreignkey")
    op.drop_constraint("analysis_feedback_analysis_id_fkey", "analysis_feedback", type_="foreignkey")
    op.execute("ALTER TABLE analysis_feedback ALTER COLUMN analysis_id TYPE VARCHAR USING analysis_id::text")
    op.execute("ALTER TABLE text_analysis_results ALTER COLUMN document_id TYPE VARCHAR USING document_id::text")
    op.execute("ALTER TABLE text_analysis_results ALTER COLUMN id TYPE VARCHAR USING id::text")

    op.drop_index(op.f("ix_processing_stats_created_at"), table_name="processing_stats")
    for table, column in _TIMESTAMPS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )

    op.add_column("transcriptions", sa.Column("result", sa.JSON(), nullable=True))
    op.execute(
        "UPDATE transcriptions SET result = json_build_object("
        "'media_duration_seconds', media_duration_seconds, 'visual_context', visual_context)"
    )
    op.drop_column("transcriptions", "visual_context")
    op.drop_column("transcriptions", "media_duration_seconds")
