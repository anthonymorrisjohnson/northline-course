"""Step 4 of the loop: say in plain words what the numbers mean. Withheld by /pm-run until the gate question is answered."""
import json
from pathlib import Path
from . import claude_json

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DIAG_SCHEMA = {"type": "object", "properties": {k: {"type": "string"} for k in
               ["headline", "what_the_board_sees", "what_the_logs_show", "the_bottleneck", "why_signing_prairie_makes_it_worse", "the_one_metric_to_watch"]},
               "required": ["headline", "what_the_board_sees", "what_the_logs_show", "the_bottleneck", "why_signing_prairie_makes_it_worse", "the_one_metric_to_watch"]}
TITLES = {"headline": "Headline", "what_the_board_sees": "What the board sees", "what_the_logs_show": "What the logs show",
          "the_bottleneck": "The bottleneck", "why_signing_prairie_makes_it_worse": "Why signing Prairie makes it worse",
          "the_one_metric_to_watch": "The one metric to watch"}


def prompt(report_md: str, qm: dict, summary: dict | None) -> str:
    proj = summary["prairie_without"]["nurse_response_median_h"] if summary else "unknown"
    return (f"You are the head of product at Northline Care, a rural chronic-care company whose AI check-in agent has been live nine months. "
            f"Read this report and write a one-page diagnosis for the CEO in plain words, no jargon, each section two to four sentences. "
            f"The company is about to sign a contract taking it from 40,000 to 100,000 patients with the same 22 nurses; the model projects "
            f"median nurse response of {proj} hours after signing. Name the bottleneck as people and capacity, not technology. "
            f"Do not recommend a fix; that comes next.\n\n{report_md}\n\nQueue metrics: {json.dumps(qm)}")


def main(ask=claude_json.ask_json) -> None:
    from .aggregate import REPO_ROOT
    qm = json.loads((OUT / "queue_metrics.json").read_text())
    sp = REPO_ROOT / "northline" / "sim" / "out" / "summary.json"
    summary = json.loads(sp.read_text()) if sp.exists() else None
    d = ask(prompt((OUT / "report.md").read_text(), qm, summary), DIAG_SCHEMA, model="sonnet")
    (OUT / "diagnosis.md").write_text("# Diagnosis\n\n" + "\n\n".join(f"## {TITLES[k]}\n\n{d[k]}" for k in TITLES) + "\n")
    print(f"wrote {OUT / 'diagnosis.md'}: {d['headline']}")


if __name__ == "__main__":
    main()
