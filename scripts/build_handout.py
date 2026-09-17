"""Render docs/exhibits.md to docs/exhibits.pdf, the paper handout.

Author-only. Needs Google Chrome (or Edge or Chromium) and the markdown package:

    uv run --with markdown python scripts/build_handout.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from export_deck import find_browser  # noqa: E402

SOURCE = ROOT / "docs" / "exhibits.md"
OUT = ROOT / "docs" / "exhibits.pdf"

CSS = """
@page { size: A4; margin: 18mm 17mm; }
body { font: 10.5pt/1.45 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: #14212b; }
h1 { font-size: 20pt; margin: 0 0 6pt; }
h2 { font-size: 13.5pt; margin: 20pt 0 6pt; padding-top: 8pt; border-top: 1.5pt solid #0b6e8a;
     break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; break-after: avoid; }
p, li { margin: 0 0 6pt; }
ul { padding-left: 16pt; }
blockquote { margin: 8pt 0; padding: 10pt 14pt; background: #f1f5f8; border-left: 3pt solid #0b6e8a;
             break-inside: avoid; }
blockquote p:last-child { margin-bottom: 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9.8pt; }
th, td { border: 0.5pt solid #b8c4cc; padding: 4pt 7pt; text-align: left; vertical-align: top; }
th { background: #14212b; color: #fff; }
tr { break-inside: avoid; }
td:nth-child(2) { white-space: nowrap; }
code { font: 9pt ui-monospace, Menlo, Consolas, monospace; background: #f1f5f8; padding: 0 2pt; }
.pagebreak { break-after: page; }
"""


def to_html(source: str) -> str:
    import markdown

    body = markdown.markdown(source, extensions=["tables"])
    return f'<!doctype html><meta charset="utf-8"><title>Northline Care exhibits</title><style>{CSS}</style>{body}'


def main() -> Path:
    html = to_html(SOURCE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "exhibits.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT}", page.as_uri()],
                       check=True, capture_output=True, timeout=120)
    print(f"wrote {OUT}")
    return OUT


if __name__ == "__main__":
    main()
