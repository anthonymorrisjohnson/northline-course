"""Build slides/follow-along.html from slides/follow-along.body.html and the deck engine in slides/present.html.

The engine (styles, presenter view, timer, keyboard handling) lives in one place, present.html.
This script borrows it so the follow-along deck stays a single self-contained file.

    uv run python scripts/build_follow_along.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "slides" / "present.html"
BODY = ROOT / "slides" / "follow-along.body.html"
OUT = ROOT / "slides" / "follow-along.html"
TITLE = "Northline Follow Along"


def build() -> Path:
    engine = ENGINE.read_text(encoding="utf-8")
    body = BODY.read_text(encoding="utf-8")
    links = "\n".join(re.findall(r"<link[^>]+>", engine))
    style = re.search(r"<style>.*?</style>", engine, re.S).group(0)
    extra = re.search(r"<style>.*?</style>", body, re.S).group(0)
    slides = body.replace(extra, "").strip()
    tail = engine[engine.index("</main>") + len("</main>"):]          # presenter panel, notes bar, toast, script
    tail = tail.replace("'northline-deck'", "'northline-follow'").replace("'nl-deck-state'", "'nl-follow-state'")
    tail = tail.replace("'northline-presenter'", "'northline-follow-presenter'")
    page = f"<title>{TITLE}</title>\n{links}\n{style}\n{extra}\n\n<main id=\"deck\" aria-live=\"polite\">\n\n{slides}\n\n</main>{tail}"
    OUT.write_text(page, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"wrote {out} ({out.read_text(encoding='utf-8').count('<section class=')} slides)")
