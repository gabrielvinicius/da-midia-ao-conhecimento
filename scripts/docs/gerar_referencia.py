"""Gera a referência da documentação a partir do código.

Escreve em docs/referencia/:
  api.md              rotas da API (OpenAPI do FastAPI)
  configuracao.md     variáveis de ambiente (classes de configuração e os
                      comentários acima de cada campo)
  eventos-e-filas.md  eventos de integração (quem publica, quem reage, campos),
                      tarefas e filas do Celery

Uso, na raiz do repositório:
  python scripts/docs/gerar_referencia.py           # reescreve os arquivos
  python scripts/docs/gerar_referencia.py --check   # falha se estiverem desatualizados

Escrita à mão, a referência se afastava do código sem ninguém notar; gerada,
um teste (tests/unit/test_docs_reference.py) falha quando ela fica para trás.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import inspect
import os
import sys
import textwrap
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "referencia"
HEADER = (
    "<!-- Gerado por scripts/docs/gerar_referencia.py a partir do código. "
    "Não edite à mão: rode o script. -->\n\n"
)

# Importar main.py não deve depender da máquina: sem banco nem Redis no ar.
for name, value in {
    "APP_ENV": "development",
    "SECRET_KEY": "documentacao",
    "LIGHTWEIGHT_BOOTSTRAP": "true",
    # O motor é criado ao importar, mas não conecta.
    "DATABASE_URL": "postgresql+asyncpg://documentacao@localhost:5432/documentacao",
}.items():
    os.environ.setdefault(name, value)
sys.path.insert(0, str(ROOT))


def _cell(text: str) -> str:
    """Texto numa célula de tabela: uma linha, sem quebrar a tabela."""
    return " ".join(str(text).split()).replace("|", "\\|")


# ---------------------------------------------------------------- API

TAGS = {
    "Authentication": "Autenticação e conta",
    "Media": "Mídias",
    "Transcriptions": "Transcrições",
    "text-analysis": "Análise, estudo e busca",
    "Notifications": "Avisos",
    "Providers": "Opções do processamento",
    "monitoring": "Monitoramento",
    "Admin": "Administração",
    "Health": "Saúde",
}


def _access(path: str, operation: dict) -> str:
    if path.startswith("/admin"):
        return "administrador"
    return "com sessão" if operation.get("security") else "público"


def _summary(operation: dict) -> str:
    description = (operation.get("description") or "").strip()
    first = description.split("\n\n")[0] if description else operation.get("summary", "")
    return _cell(first)


def render_api() -> str:
    import main

    spec = main.app.openapi()
    groups: dict[str, list[tuple[str, str, dict]]] = {}
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            tag = (operation.get("tags") or ["Outros"])[0]
            groups.setdefault(tag, []).append((path, method.upper(), operation))

    lines = [
        HEADER,
        "# Referência da API\n\n",
        f"API REST do sistema (FastAPI, versão `{spec['info'].get('version', '')}`), com "
        f"{sum(len(v) for v in groups.values())} operações. Na instalação com o Compose, "
        "ela fica atrás do Nginx do frontend, no prefixo `/api` (por exemplo, "
        "`POST /api/auth/token`). A especificação completa, com os esquemas, sai em "
        "`/docs` e `/openapi.json` no ambiente de desenvolvimento.\n\n",
        "- **público**: sem login.\n",
        "- **com sessão**: cabeçalho `Authorization: Bearer <token de acesso>` "
        "(`POST /auth/token`); o token de renovação vai num cookie `httpOnly`.\n",
        "- **administrador**: com sessão e papel `ADMIN`.\n\n",
        "Dono ou administrador: uma mídia de outra pessoa responde 404, e não 403 "
        "(veja [Segurança](../explicacao/seguranca.md)).\n\n",
    ]
    order = list(TAGS) + sorted(set(groups) - set(TAGS))
    for tag in order:
        if tag not in groups:
            continue
        lines.append(f"## {TAGS.get(tag, tag)}\n\n| Método | Caminho | Acesso | O que faz |\n|---|---|---|---|\n")
        for path, method, operation in sorted(groups[tag], key=lambda item: (item[0], item[1])):
            lines.append(f"| `{method}` | `{path}` | {_access(path, operation)} | {_summary(operation)} |\n")
        lines.append("\n")
    return "".join(lines)


# ------------------------------------------------------- configuração

SETTINGS = [
    ("src.shared.infrastructure.config.settings", "Settings", "Gerais (API, workers, modelos)"),
    ("src.media_management.config.settings", "MediaSettings", "Mídias e envios"),
    ("src.media_processing.config.settings", "MediaProcessingSettings", "Processamento"),
    ("src.storage.config.settings", "StorageSettings", "Armazenamento"),
    ("src.user_management.config.settings", "UserSettings", "Usuários, sessão e e-mail"),
]


def _field_comments(cls: type) -> dict[str, str]:
    """Comentário logo acima de cada campo, no código da classe."""
    source_lines, start = inspect.getsourcelines(cls)
    tree = ast.parse(textwrap.dedent("".join(source_lines)))
    comments: dict[str, str] = {}
    for node in tree.body[0].body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            block = []
            index = node.lineno - 2
            while index >= 0 and source_lines[index].strip().startswith("#"):
                block.insert(0, source_lines[index].strip().lstrip("#").strip())
                index -= 1
            comments[node.target.id] = " ".join(block)
    return comments


def _default(field) -> str:
    if field.default_factory is not None:
        value = field.default_factory()
    else:
        value = field.default
    if value is None or value == "":
        return "(vazio)"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    if isinstance(value, (list, tuple, set)):
        return "`" + ",".join(str(v) for v in value) + "`" if value else "(vazio)"
    return f"`{value}`"


def _env_names(cls: type, name: str, field) -> list[str]:
    prefix = (cls.model_config.get("env_prefix") or "").upper()
    names = [str(choice).upper() for choice in getattr(field.validation_alias, "choices", []) or []]
    return names or [prefix + name.upper()]


def _read_elsewhere() -> list[str]:
    """Variáveis lidas fora das classes (Compose, scripts), do teste de implantação."""
    tree = ast.parse((ROOT / "tests" / "unit" / "test_deployment_config.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "READ_ELSEWHERE":
            return sorted(ast.literal_eval(node.value))
    return []


def _example_var(line: str) -> str:
    """Nome da variável numa linha "VAR=..." ou "# VAR=..." do .env.example."""
    candidate = line.lstrip("# ").split("=", 1)[0]
    if "=" in line and candidate.isupper() and candidate.replace("_", "").isalnum():
        return candidate
    return ""


def _example_descriptions() -> dict[str, str]:
    """Variável do .env.example -> comentário logo acima dela (o bloco pode valer
    para várias variáveis seguidas)."""
    descriptions: dict[str, str] = {}
    block: list[str] = []
    after_var = False
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        name = _example_var(line)
        if name:
            descriptions[name] = " ".join(text for text in block if text)
            after_var = True
        elif line.startswith(("# ---", "# ===")) or not line.strip():
            block, after_var = [], False
        elif line.startswith("#"):
            if after_var:  # comentário depois de variáveis: começa outro bloco
                block, after_var = [], False
            block.append(line.lstrip("#").strip())
    return descriptions


def _description(own: str, example: str) -> str:
    """O comentário do código; se for só um rótulo ("Database"), o do .env.example."""
    if len(own.split()) >= 4 or not example:
        return own
    return example


def render_config() -> str:
    import importlib

    examples = _example_descriptions()
    lines = [
        HEADER,
        "# Referência da configuração\n\n",
        "Variáveis de ambiente lidas pelo sistema, com o valor padrão do código. Na "
        "instalação com o Compose, elas vêm do `.env` (copie o `.env.example`); o "
        "`docker-compose.yml` sobrescreve os endereços dos serviços (banco, Redis, "
        "Ollama, Jaeger) e `APP_ENV=production`. Um teste confere que toda variável "
        "do `.env.example` é lida por alguma configuração.\n\n",
        "A coluna **.env.example** marca as que aparecem lá, com explicação; as demais "
        "têm um padrão adequado e raramente mudam. Para trocar modelos e etapas, veja "
        "[Trocar modelos e etapas da análise](../guias/modelos-e-etapas.md).\n\n",
    ]
    for module_name, class_name, title in SETTINGS:
        cls = getattr(importlib.import_module(module_name), class_name)
        comments = _field_comments(cls)
        lines.append(f"## {title}\n\n`{class_name}` em `{module_name.replace('.', '/')}.py`.\n\n")
        lines.append("| Variável | Padrão | .env.example | Descrição |\n|---|---|---|---|\n")
        for name, field in cls.model_fields.items():
            env = _env_names(cls, name, field)
            in_example = [e for e in env if e in examples]
            mark = "sim" if in_example else ""
            example = examples.get(in_example[0], "") if in_example else ""
            lines.append(
                f"| {' / '.join(f'`{e}`' for e in env)} | {_cell(_default(field))} | {mark} | "
                f"{_cell(_description(comments.get(name, ''), example))} |\n"
            )
        lines.append("\n")
    lines.append(
        "## Lidas fora das classes de configuração\n\n"
        "Usadas pelo Compose, pelos scripts de operação ou por bibliotecas (lista em "
        "`READ_ELSEWHERE`, `tests/unit/test_deployment_config.py`):\n\n"
    )
    lines.append("".join(f"- `{name}`\n" for name in _read_elsewhere()))
    return "".join(lines)


# --------------------------------------------------- eventos e filas


class _RecordingBus:
    """Barramento falso: só anota quem se inscreve em quê."""

    def __init__(self) -> None:
        self.subscriptions: dict[str, list[str]] = {}
        self.current = ""

    def subscribe(self, event_type, handler) -> None:
        module = self.current
        subscribers = self.subscriptions.setdefault(event_type.__name__, [])
        if module not in subscribers:
            subscribers.append(module)

    def unsubscribe(self, event_type, handler) -> None:  # pragma: no cover
        pass

    async def publish(self, event) -> None:  # pragma: no cover
        pass


def _type_name(annotation) -> str:
    text = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", str(annotation))
    return text.replace("typing.", "").replace("Optional[", "").rstrip("]") if "Optional" in text else text


def render_events() -> str:
    from src.shared.domain import events as events_module
    from src.shared.events import integration_events as queues
    from src.worker_process import WORKER_SUBSCRIBERS

    bus = _RecordingBus()
    for bind in WORKER_SUBSCRIBERS:
        bus.current = bind.__module__.split(".")[1]
        bind(bus)

    base_fields = {f.name for f in dataclasses.fields(events_module.DomainEvent)}
    event_classes = [
        cls
        for _, cls in inspect.getmembers(events_module, inspect.isclass)
        if issubclass(cls, events_module.DomainEvent) and cls is not events_module.DomainEvent
        and cls.__module__ == events_module.__name__
    ]
    event_classes.sort(key=lambda cls: inspect.getsourcelines(cls)[1])

    lines = [
        HEADER,
        "# Referência dos eventos e das filas\n\n",
        "Os módulos conversam por **eventos de integração** (`src/shared/domain/events.py`). "
        "Cada evento tem um único módulo que o publica; os demais só reagem a ele. "
        "Dentro de um processo, o barramento em memória entrega o evento às reações "
        "inscritas; entre a API e os workers, o trabalho segue pelas **filas** do "
        "Celery (Redis). Veja [Arquitetura](../explicacao/arquitetura.md) e "
        "[Pipeline de processamento](../explicacao/pipeline.md).\n\n",
        "Todo evento carrega também `event_id`, `occurred_at` e `correlation_id` "
        "(o identificador da requisição que o originou, presente em todos os logs).\n\n",
        "## Eventos\n\n| Evento | Publicado por | Reações nos workers | Campos |\n|---|---|---|---|\n",
    ]
    for cls in event_classes:
        hints = typing.get_type_hints(cls)
        fields = [
            f"`{f.name}`" for f in dataclasses.fields(cls) if f.name not in base_fields
        ]
        reactions = ", ".join(f"`{m}`" for m in bus.subscriptions.get(cls.__name__, [])) or "—"
        # Sem docstring, a dataclass mostra a própria assinatura; não é descrição.
        doc = cls.__dict__.get("__doc__") or ""
        own_doc = "" if doc.startswith(cls.__name__ + "(") else inspect.cleandoc(doc)
        title = f"`{cls.__name__}`" + (f"<br>{_cell(own_doc.split(chr(10) + chr(10))[0])}" if own_doc else "")
        del hints
        lines.append(f"| {title} | `{cls.published_by}` | {reactions} | {', '.join(fields) or '—'} |\n")

    lines.append(
        "\n## Tarefas do Celery\n\n"
        "Nomes em `src/shared/events/integration_events.py`; quem agenda uma tarefa "
        "usa o nome, sem importar o módulo que a executa.\n\n| Constante | Tarefa |\n|---|---|\n"
    )
    for name, value in vars(queues).items():
        if name.startswith("TASK_"):
            lines.append(f"| `{name}` | `{value}` |\n")
    lines.append(
        "\n## Filas\n\n"
        "O `-Q` de cada worker no `docker-compose.yml` repete estas listas, e um teste "
        "(`tests/unit/test_queue_names.py`) confere que as duas não se afastam.\n\n"
        "| Worker | Filas, em ordem de prioridade |\n|---|---|\n"
        f"| `worker-heavy` (GPU, uma tarefa por vez) | {', '.join(f'`{q}`' for q in queues.HEAVY_WORKER_QUEUES)} |\n"
        f"| `worker-light` (verificações periódicas) | {', '.join(f'`{q}`' for q in queues.LIGHT_WORKER_QUEUES)} |\n"
    )
    return "".join(lines)


# ------------------------------------------------------------- saída

PAGES = {
    "api.md": render_api,
    "configuracao.md": render_config,
    "eventos-e-filas.md": render_events,
}


def generate() -> dict[Path, str]:
    # Uma única quebra de linha no fim (o markdownlint recusa linhas em branco a mais).
    return {OUT / name: render().rstrip() + "\n" for name, render in PAGES.items()}


def main_cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="falha se algum arquivo estiver desatualizado")
    args = parser.parse_args()
    stale = []
    for path, content in generate().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        if args.check:
            stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"escrito: {path.relative_to(ROOT).as_posix()}")
    if stale:
        print("Referência desatualizada: " + ", ".join(stale))
        print("Rode: python scripts/docs/gerar_referencia.py")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
