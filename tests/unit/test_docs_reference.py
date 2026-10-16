"""A referência da documentação (docs/referencia/{api,configuracao,eventos-e-filas}.md)
é gerada a partir do código. Escrita à mão, ela se afastava do código sem
ninguém notar; este teste falha quando ela fica para trás."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _generator():
    spec = importlib.util.spec_from_file_location(
        "gerar_referencia", ROOT / "scripts" / "docs" / "gerar_referencia.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_reference_matches_the_code():
    stale = [
        path.relative_to(ROOT).as_posix()
        for path, content in _generator().generate().items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    assert not stale, (
        f"Referência desatualizada: {', '.join(stale)}. "
        "Rode: python scripts/docs/gerar_referencia.py"
    )
