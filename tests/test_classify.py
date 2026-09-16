import shutil
from pathlib import Path
from northline.pm import classify as c
FX = Path(__file__).parent / "fixtures"


def test_load_items(tmp_path):
    (tmp_path / "corpus/patient").mkdir(parents=True); (tmp_path / "corpus/plan").mkdir(); (tmp_path / "logs").mkdir()
    shutil.copy(FX / "transcript.json", tmp_path / "corpus/patient/p-001.json")
    shutil.copy(FX / "plan_session.jsonl", tmp_path / "corpus/plan/s-001.jsonl")
    by = {i["id"]: i for i in c.load_items(tmp_path / "corpus", tmp_path / "logs")}
    assert "user: Pharmacy in Dickinson" in by["p-001"]["text"] and "tools used: escalate_to_nurse" in by["p-001"]["text"]
    assert by["s-001"]["persona"] == "plan" and "not_found" in by["s-001"]["text"]


def test_classify_batches_and_copies_ids():
    items = [{"id": f"i{n}", "persona": "patient", "text": "user: hi"} for n in range(10)]
    calls = []
    def fake(jobs, **kw):
        calls.append(len(jobs))
        return [{"records": [{"id": "x", "persona": "plan", "intent": "", "tier": "none", "outcome": "resolved", "tools_used": [],
                              "unmet_need": False, "unmet_need_description": "", "proposed_tool": "", "evidence_quote": ""}
                             for _ in range(p.count("### item"))]} for p, _ in jobs]
    recs = c.classify_items(items, batch_size=4, ask=fake)
    assert [r["id"] for r in recs] == [f"i{n}" for n in range(10)] and recs[0]["persona"] == "patient" and calls == [3]


def test_classify_pads_short_batches():
    items = [{"id": f"i{n}", "persona": "patient", "text": "user: hi"} for n in range(3)]
    rec = {"id": "x", "persona": "plan", "intent": "known", "tier": "none", "outcome": "resolved", "tools_used": [],
           "unmet_need": False, "unmet_need_description": "", "proposed_tool": "", "evidence_quote": ""}

    def fake(jobs, **kw):
        return [{"records": [dict(rec)]} for _ in jobs]

    recs = c.classify_items(items, batch_size=3, ask=fake)
    assert [r["id"] for r in recs] == ["i0", "i1", "i2"]
    assert recs[0]["intent"] == "known"
    assert recs[1]["intent"] == "unclassified" and recs[2]["intent"] == "unclassified"


def test_record_schema_constrains_proposed_tool():
    enum = c.RECORD_SCHEMA["properties"]["proposed_tool"]["enum"]
    assert enum == c.PROPOSED_TOOLS and "" in enum and "request_refill" in enum and "insurance_question" in enum


def test_classify_truncates_long_batches():
    items = [{"id": f"i{n}", "persona": "patient", "text": "user: hi"} for n in range(3)]
    rec = {"id": "x", "persona": "plan", "intent": "known", "tier": "none", "outcome": "resolved", "tools_used": [],
           "unmet_need": False, "unmet_need_description": "", "proposed_tool": "", "evidence_quote": ""}

    def fake(jobs, **kw):
        return [{"records": [dict(rec) for _ in range(5)]} for _ in jobs]

    recs = c.classify_items(items, batch_size=3, ask=fake)
    assert [r["id"] for r in recs] == ["i0", "i1", "i2"]
