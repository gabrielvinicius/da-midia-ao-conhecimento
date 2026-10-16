"""Converte docs/ nas páginas da Wiki do GitHub.

A documentação continua em docs/: muda no mesmo PR que o código, passa pela
revisão e gera o site (zensical.toml). A Wiki é um espelho, escrito pelo
workflow .github/workflows/wiki.yml a cada mudança na main; editada à mão,
ela seria sobrescrita.

O que muda na conversão:
  - cada página vira um arquivo com o título do menu (nav do zensical.toml),
    porque a Wiki não tem pastas; docs/README.md vira a Home;
  - os links entre páginas (../guias/x.md#ancora) passam a apontar para o
    nome da página na Wiki, com a mesma âncora;
  - o título (# ...) sai do conteúdo, porque a Wiki já o mostra;
  - _Sidebar.md repete o menu do site, e _Footer.md avisa onde editar.

Uso, na raiz do repositório:
  python scripts/docs/publicar_wiki.py <pasta de saída>
"""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CONFIG = ROOT / "zensical.toml"
HOME = "Home"
REPOSITORY = "https://github.com/gabrielvinicius/da-midia-ao-conhecimento"
SITE = "https://docs.gabrielvinicius.dev"

# [texto](destino) e [texto](destino "título"); imagens incluídas.
LINK = re.compile(r"(\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
TITLE = re.compile(r"\A# .*\n+")


def menu() -> list[tuple[str, list[tuple[str, str]]]]:
    """Seções do menu do site, cada uma com (título, caminho em docs/)."""
    nav = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["project"]["nav"]
    sections: list[tuple[str, list[tuple[str, str]]]] = []
    for entry in nav:
        ((title, target),) = entry.items()
        if isinstance(target, str):
            sections.append((title, [(title, target)]))
        else:
            sections.append((title, [next(iter(item.items())) for item in target]))
    return sections


def page_names() -> dict[str, str]:
    """Caminho em docs/ -> nome da página na Wiki."""
    names: dict[str, str] = {}
    for _, pages in menu():
        for title, path in pages:
            names[path] = HOME if path == "README.md" else title.replace(" ", "-")
    if len(set(names.values())) != len(names):
        raise SystemExit("Dois itens do menu viram a mesma página na Wiki.")
    return names


def wiki_link(name: str, fragment: str = "") -> str:
    return quote(name, safe="-") + (f"#{fragment}" if fragment else "")


def convert(path: str, text: str, names: dict[str, str]) -> str:
    """Conteúdo de docs/<path> no formato da Wiki."""
    folder = posixpath.dirname(path)

    def rewrite(match: re.Match[str]) -> str:
        target = match.group(2)
        if re.match(r"[a-z][a-z0-9+.-]*:|#", target):
            return match.group(0)
        file, _, fragment = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(folder, file))
        if resolved not in names:
            raise SystemExit(f"{path}: link para {target}, que não está no menu do site.")
        return f"{match.group(1)}{wiki_link(names[resolved], fragment)}{match.group(3)}"

    return LINK.sub(rewrite, TITLE.sub("", text, count=1))


def sidebar(names: dict[str, str]) -> str:
    lines = [f"**[Início]({HOME})**", ""]
    for section, pages in menu():
        if pages == [(section, "README.md")]:
            continue
        lines += [f"**{section}**", ""]
        lines += [f"- [{title}]({wiki_link(names[path])})" for title, path in pages]
        lines.append("")
    return "\n".join(lines)


FOOTER = (
    f"Espelho de [`docs/`]({REPOSITORY}/tree/main/docs), atualizado a cada "
    f"mudança na `main`. Para corrigir uma página, edite o arquivo em `docs/` "
    f"num PR: mudanças feitas aqui são sobrescritas. Também em [{SITE.removeprefix('https://')}]({SITE}).\n"
)


def export() -> dict[str, str]:
    """Nome do arquivo na Wiki -> conteúdo."""
    names = page_names()
    found = {p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*.md")}
    missing = sorted(found - names.keys())
    if missing:
        raise SystemExit(f"Páginas fora do menu do site (nav do zensical.toml): {', '.join(missing)}")
    pages = {
        f"{name}.md": convert(path, (DOCS / path).read_text(encoding="utf-8"), names)
        for path, name in names.items()
    }
    pages["_Sidebar.md"] = sidebar(names)
    pages["_Footer.md"] = FOOTER
    return pages


def main_cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("saida", type=Path, help="pasta da Wiki (o clone de <repositório>.wiki.git)")
    out = parser.parse_args().saida
    for old in out.glob("*.md"):
        old.unlink()
    for name, content in export().items():
        (out / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"{len(export())} arquivos escritos em {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
