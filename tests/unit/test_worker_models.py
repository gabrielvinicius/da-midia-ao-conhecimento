"""O processo do worker carrega todas as tabelas que as suas chaves estrangeiras citam.

O worker importa só ``src.worker_process`` (``include`` do Celery). As tabelas
media e notifications apontam para users, cujo modelo não era carregado ali: ao
gravar o estado da mídia, o SQLAlchemy falhava com "could not find table
'users'", e a mídia ficava parada em "uploaded" depois da transcrição. Os
testes de unidade não pegavam porque o processo do pytest já importou tudo;
por isso a verificação roda num interpretador novo.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_CHECK = """
import src.worker_process  # noqa: F401  (o que o worker carrega)
from src.shared.infrastructure.database import Base

missing = []
for table in Base.metadata.tables.values():
    for fk in table.foreign_keys:
        try:
            fk.column
        except Exception as exc:
            missing.append(f"{table.name}.{fk.parent.name}: {exc}")
print("\\n".join(missing))
"""


def test_every_foreign_key_resolves_in_the_worker_process():
    result = subprocess.run(
        [sys.executable, "-c", _CHECK],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
