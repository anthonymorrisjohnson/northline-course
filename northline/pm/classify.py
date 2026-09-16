"""Step 2 of the loop: one structured record per conversation or tool-log session."""
import json
from collections import defaultdict
from pathlib import Path
from . import claude_json

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT = HERE / "out"
TAXONOMY = (HERE / "taxonomy.md").read_text()
TIERS = ["urgent_clinical", "non_urgent_clinical", "non_clinical", "none"]
RECORD_SCHEMA = {"type": "object", "properties": {
    "id": {"type": "string"}, "persona": {"type": "string"}, "intent": {"type": "string"},
    "tier": {"type": "string", "enum": TIERS}, "outcome": {"type": "string", "enum": ["resolved", "partial", "failed", "escalated"]},
    "tools_used": {"type": "array", "items": {"type": "string"}}, "unmet_need": {"type": "boolean"},
    "unmet_need_description": {"type": "string"}, "proposed_tool": {"type": "string"}, "evidence_quote": {"type": "string"}},
    "required": ["id", "persona", "intent", "tier", "outcome", "tools_used", "unmet_need", "unmet_need_description", "proposed_tool", "evidence_quote"]}
BATCH_SCHEMA = {"type": "object", "properties": {"records": {"type": "array", "items": RECORD_SCHEMA}}, "required": ["records"]}
EMPTY = {"intent": "unclassified", "tier": "none", "outcome": "failed", "tools_used": [], "unmet_need": False,
         "unmet_need_description": "", "proposed_tool": "", "evidence_quote": ""}


def _transcript_text(doc):
    return "\n".join(f"{m['role']}: {m['content']}" for m in doc["messages"]) + \
        "\ntools used: " + ", ".join(t["name"] for t in doc.get("tool_uses", []))


def _calls_text(calls):
    return "\n".join(f"{c['tool']}({json.dumps(c['args'])}) -> {c['status']}" + (f" [{c['error']}]" if c.get("error") else "") for c in calls)


def load_items(corpus_dir: Path, log_dir: Path) -> list[dict]:
    items = []
    for p in sorted((corpus_dir / "patient").glob("*.json")):
        items.append({"id": p.stem, "persona": "patient", "text": _transcript_text(json.loads(p.read_text()))})
    for p in sorted((log_dir / "transcripts").glob("*.json")) if (log_dir / "transcripts").exists() else []:
        items.append({"id": f"live-{p.stem}", "persona": "patient", "text": _transcript_text(json.loads(p.read_text()))})
    for p in sorted((corpus_dir / "plan").glob("*.jsonl")):
        items.append({"id": p.stem, "persona": "plan", "text": _calls_text([json.loads(l) for l in p.read_text().splitlines() if l.strip()])})
    live = log_dir / "tool_calls.jsonl"
    if live.exists():
        groups = defaultdict(list)
        for l in live.read_text().splitlines():
            if l.strip():
                c = json.loads(l); groups[c["session_id"]].append(c)
        for sid, calls in groups.items():
            items.append({"id": f"live-{sid}", "persona": calls[0]["persona"], "text": _calls_text(calls)})
    return items


def _prompt(batch):
    body = "\n\n".join(f"### item {i['id']} (persona={i['persona']})\n{i['text']}" for i in batch)
    return f"{TAXONOMY}\n\nClassify each item. Return exactly {len(batch)} records in order, copying each id and persona.\n\n{body}"


def classify_items(items, *, batch_size=8, model="haiku", ask=claude_json.ask_json_many) -> list[dict]:
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    outs = ask([(_prompt(b), BATCH_SCHEMA) for b in batches], model=model)
    records = []
    for batch, out in zip(batches, outs):
        recs = out["records"] + [None] * (len(batch) - len(out["records"]))
        for item, rec in zip(batch, recs):
            rec = dict(rec or EMPTY); rec.update(id=item["id"], persona=item["persona"]); records.append(rec)
    return records


def main() -> None:
    items = load_items(REPO_ROOT / "corpus", REPO_ROOT / "northline" / "logs")
    print(f"classifying {len(items)} items")
    OUT.mkdir(exist_ok=True)
    with (OUT / "classified.jsonl").open("w") as f:
        for r in classify_items(items):
            f.write(json.dumps(r) + "\n")
    print(f"wrote {OUT / 'classified.jsonl'}")


if __name__ == "__main__":
    main()
