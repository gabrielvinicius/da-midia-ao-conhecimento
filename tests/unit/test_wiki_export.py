"""A Wiki é gerada de docs/ (scripts/docs/publicar_wiki.py): toda página do
site vira uma página da Wiki, e nenhum link entre páginas fica quebrado."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("publicar_wiki", ROOT / "scripts" / "docs" / "publicar_wiki.py")
publicar_wiki = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(publicar_wiki)

LINK_TARGET = re.compile(r"\]\(([^)\s]+)")


def test_every_docs_page_becomes_a_wiki_page():
    pages = publicar_wiki.export()
    docs = list((ROOT / "docs").rglob("*.md"))
    assert len(pages) == len(docs) + 2  # mais _Sidebar e _Footer
    assert "Home.md" in pages


def test_links_between_pages_point_to_existing_wiki_pages():
    pages = publicar_wiki.export()
    names = {name.removesuffix(".md") for name in pages}
    for name, content in pages.items():
        for target in LINK_TARGET.findall(content):
            if re.match(r"[a-z][a-z0-9+.-]*:|#", target):
                continue
            page = unquote(target.partition("#")[0])
            assert page in names, f"{name}: link para {target}"
            assert not page.endswith(".md"), f"{name}: link ainda aponta para o arquivo ({target})"


def test_the_title_is_left_to_the_wiki():
    pages = publicar_wiki.export()
    assert not any(content.startswith("# ") for content in pages.values())
