"""Installation guidance must use verified release assets, not index names."""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX_INSTALL = re.compile(
    r"\b(?:pip(?:3)?|pipx|uv\s+(?:tool|pip))\s+install\b"
    r"[^\n`;&|]*?(?<![\w./-])(?:wallet[-_]exit[-_]kit|exitkit)"
    r"(?=$|[\s`'\"\[<>=!~])",
    re.IGNORECASE,
)


def test_docs_do_not_install_by_index_name():
    paths = [*ROOT.glob("*.md")]
    for folder in ("skills", "docs", "templates"):
        paths.extend(path for path in (ROOT / folder).rglob("*")
                     if path.suffix in (".md", ".rst", ".txt"))
    for path in paths:
        assert not INDEX_INSTALL.search(path.read_text(encoding="utf-8")), path


@pytest.mark.parametrize("command", [
    "pip install wallet-exit-kit",
    "python3 -m pip install wallet-exit-kit==0.1.0",
    "pipx install exitkit",
    "uv tool install wallet-exit-kit",
    "uv pip install --upgrade exitkit",
])
def test_index_install_guard_detects_package_names(command):
    assert INDEX_INSTALL.search(command)


def test_onchain_skill_requires_verified_release_install():
    text = (ROOT / "skills/onchain-exit-assist/SKILL.md").read_text(encoding="utf-8")
    assert "SHA256SUMS" in text
    assert "https://gitlab.com/aa22396584/wallet-exit-kit/-/releases" in text
    assert "禁止從 PyPI 安裝 `wallet-exit-kit` 或 `exitkit`" in text
