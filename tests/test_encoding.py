"""Every text file read or written by the course must name its encoding.

Attendees run this on Windows laptops where the default is cp1252; a transcript
with a curly quote in it would otherwise crash the loop.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOTS = ["northline", "scripts"]
CALL = re.compile(r"(?:\.read_text|\.write_text|\.open|(?<![\w.])open)\(")
BINARY = re.compile(r'"(?:rb|wb|ab|r\+b|w\+b)"')


def _sources():
    for root in ROOTS:
        yield from sorted((REPO_ROOT / root).rglob("*.py"))


def _closing(text: str, open_paren: int) -> int:
    depth, i, quote = 0, open_paren, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _offenders(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    bad = []
    for m in CALL.finditer(src):
        open_paren = m.end() - 1
        close = _closing(src, open_paren)
        if close < 0:
            continue
        args = src[open_paren + 1 : close]
        if "encoding=" in args or BINARY.search(args):
            continue
        line = src.count("\n", 0, m.start()) + 1
        bad.append(f"{path.name}:{line}: {src[m.start():close + 1][:80]}")
    return bad


@pytest.mark.parametrize("path", list(_sources()), ids=lambda p: str(p.name))
def test_text_file_calls_declare_encoding(path):
    offenders = _offenders(path)
    assert not offenders, "text file access without encoding=:\n" + "\n".join(offenders)


def test_the_check_actually_catches_a_bare_call(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text('x = (tmp / "a.txt").read_text()\n', encoding="utf-8")
    assert _offenders(p)
    p.write_text('x = (tmp / "a.zip").open("rb")\n', encoding="utf-8")
    assert not _offenders(p)
