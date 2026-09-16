# Moving the Bottleneck, Live: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A zip-distributed course folder where Northline Care's check-in agent, the Prairie MCP server, a company simulator with a dashboard, a PM loop that finds the nurse bottleneck from raw logs, and a `/deploy triage` flow all run on Claude Code alone.

**Architecture:** Plain Python tools over JSON data in one registry with deployment gating. Front door 1 is an MCP stdio server registered by `.mcp.json`. Front door 2 is a FastAPI page that runs headless Claude Code per turn. A weekly simulator produces Exhibit B and feeds both the corpus and the dashboard. The PM loop is Python scripts calling `claude -p --json-schema` for judgment. Skills wrap the scripts and hold the thinking gates.

**Tech Stack:** Python >=3.12, `uv`, `mcp` 2.x (`from mcp.server import MCPServer`), FastAPI, uvicorn, pytest, httpx (tests), Claude Code 2.1.x headless mode. No API key. No git for attendees.

**Spec:** `docs/superpowers/specs/2026-09-16-northline-course-design.md`

## Global Constraints

- Every LLM call goes through `claude -p`. Never import `anthropic` or read `ANTHROPIC_API_KEY`.
- No attendee-facing skill or script runs `git`. Authors commit; attendees never see a repo.
- Python `>=3.12` via `uv`. Runtime deps: `mcp>=2.2`, `fastapi`, `uvicorn`. Dev: `pytest`, `httpx`.
- Tool functions never raise. They return a dict with `status` in `ok`, `not_found`, `error`.
- Personas: `patient`, `plan`, `triage`. MCP server name `northline`; tools appear as `mcp__northline__<tool>`.
- Tiers: `urgent_clinical`, `non_urgent_clinical`, `non_clinical`. Routes: `nurse_urgent`, `nurse_routine`, `admin`, `auto_reply`.
- Weeks: the sim runs weeks 1 to 39 (nine months). Prairie projection is weeks 40 to 52.
- Paths in `.mcp.json` use `${CLAUDE_PROJECT_DIR}`.
- Verified headless flags on Claude Code 2.1.86: `--system-prompt`, `--mcp-config <json>`, `--strict-mcp-config`, `--tools ""`, `--allowedTools`, `--permission-mode dontAsk`, `--output-format stream-json --verbose`, `--output-format json --json-schema <json>` (result in `structured_output`; never pass `--max-turns 1` with a schema), `--resume <id>`, `--no-session-persistence`, `--model haiku|sonnet`.
- Tests never call `claude`. Every module that shells out takes an injectable `runner`.
- Commit after every task with a message ending `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## File Map

```
pyproject.toml  .gitignore  .mcp.json  README.md
northline/__init__.py
northline/tools/{__init__,store,calllog,patient,plan,triage,registry}.py
northline/data/{patients,plans,nurses,deployments}.json
northline/mcp_server.py
northline/agent/{__init__,claude_runner,prompt,transcripts,server}.py  brief.md  static/{index,dashboard}.html
northline/sim/{__init__,model,run}.py  out/
northline/pm/{__init__,claude_json,classify,aggregate,diagnose,propose,generate_corpus}.py  taxonomy.md  out/
northline/agents/triage/{__init__,render,acceptance}.py  exhibit_e.json  nurse_key.json  decisions.json  prompt.md  out/
northline/logs/.gitkeep
corpus/patient/*.json  corpus/plan/*.jsonl  corpus/queue.jsonl
templates/{use-case-brief,tool-spec,agent-brief,taxonomy,expansion-proposal,deployment-proposal}.md
.claude/skills/{setup,pm-run,deploy,expand,brief,tools,agent,new-experience,generate-corpus}/SKILL.md
scripts/{__init__,check,package,new_experience}.py
docs/0[0-5]-*.md  exercises/*.md  slides/outline.md  slides/deck.pptx
tests/
```

---

## Phase 1: Tool layer and MCP front door

### Task 1: Scaffold

**Files:** `pyproject.toml`, `.gitignore`, `northline/__init__.py`, `northline/tools/__init__.py`, `northline/logs/.gitkeep`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: pyproject.toml**

```toml
[project]
name = "northline-course"
version = "0.1.0"
description = "Moving the bottleneck, live: Northline Care on Claude Code"
requires-python = ">=3.12"
dependencies = ["mcp>=2.2", "fastapi>=0.110", "uvicorn>=0.29"]

[dependency-groups]
dev = ["pytest>=8", "httpx>=0.27"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["northline"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: .gitignore**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
northline/logs/*
!northline/logs/.gitkeep
northline/agents/triage/decisions.json
northline/agents/triage/prompt.md
northline/agents/triage/out/
briefs/
dist/
```

- [ ] **Step 3: tests/conftest.py**

```python
import shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    dst = tmp_path / "data"
    shutil.copytree(ROOT / "northline" / "data", dst)
    monkeypatch.setenv("NORTHLINE_DATA_DIR", str(dst))
    return dst


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    d = tmp_path / "logs"
    d.mkdir()
    monkeypatch.setenv("NORTHLINE_LOG_DIR", str(d))
    return d


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 4: create package files, sync, run**

Run: `touch northline/__init__.py northline/tools/__init__.py tests/__init__.py northline/logs/.gitkeep && mkdir -p northline/data && uv sync && uv run pytest -q`
Expected: `no tests ran`

- [ ] **Step 5: Commit** `git add -A && git commit -m "Scaffold the Northline course project"`

### Task 2: Store and seed data

**Files:** `northline/tools/store.py`, `northline/data/patients.json`, `northline/data/plans.json`, `northline/data/nurses.json`, `northline/data/deployments.json`, `tests/test_store.py`

**Interfaces:** `store.load(name) -> list[dict]` (missing file is `[]`), `store.save(name, rows)`, `store.append(name, row) -> dict`, `store.data_dir() -> Path` honouring `NORTHLINE_DATA_DIR`. For `deployments`, `load` returns a list of `{"name", "live_from_week", "effects": dict}`.

- [ ] **Step 1: Test**

```python
# tests/test_store.py
from northline.tools import store


def test_missing_is_empty(data_dir):
    assert store.load("nope") == []


def test_roundtrip_and_append(data_dir):
    store.save("t", [{"id": 1}])
    store.append("t", {"id": 2})
    assert [r["id"] for r in store.load("t")] == [1, 2]
    assert store.data_dir() == data_dir


def test_seed_shapes(data_dir):
    assert {p["id"] for p in store.load("patients")} >= {"pt-1001", "pt-1002"}
    assert store.load("plans")[0]["id"] == "plan-prairie"
    assert store.load("deployments")[0]["name"] == "checkin_agent"
```

- [ ] **Step 2: store.py**

```python
import json, os
from pathlib import Path
_DEFAULT = Path(__file__).resolve().parents[1] / "data"

def data_dir() -> Path:
    return Path(os.environ.get("NORTHLINE_DATA_DIR", _DEFAULT))

def _p(name): return data_dir() / f"{name}.json"

def load(name: str) -> list[dict]:
    p = _p(name)
    return json.loads(p.read_text()) if p.exists() else []

def save(name: str, rows: list[dict]) -> None:
    _p(name).parent.mkdir(parents=True, exist_ok=True)
    _p(name).write_text(json.dumps(rows, indent=2))

def append(name: str, row: dict) -> dict:
    rows = load(name); rows.append(row); save(name, rows); return row
```

- [ ] **Step 3: Seed data.** `patients.json` has eight patients with `id` (pt-1001 to pt-1008), `name`, `phone`, `town` (Dickinson, Minot, Williston, Bismarck, Ward County), `conditions` (subset of `["hypertension", "type2_diabetes"]`), `nurse_id` (n-01 to n-03), `plan_id` (`plan-prairie` for two, `plan-dakota` for six), `medications` (e.g. lisinopril 10 mg, metformin 500 mg), `last_readings` (list of `{kind: "bp"|"glucose", value: "146/92"|"62", at: iso}`), `engaged: true|false`. Two patients have `engaged: false` with a note `"no response since unanswered escalation 2026-08-30"`. `plans.json` has `plan-dakota` (enrolled 38,000) and `plan-prairie` (enrolled 2,000, `prospective_members: 60000`). `nurses.json` has n-01 to n-03 with `name`, `region`, `patients`. `deployments.json`:

```json
[
  {"name": "checkin_agent", "live_from_week": 1,
   "effects": {"engaged_weekly": 0.78, "escalation_rate": 0.06, "inbound_rate": 0.0775, "readings_per_response": 0.89}}
]
```

- [ ] **Step 4: Run** `uv run pytest tests/test_store.py -q` → 3 passed. **Commit** `git add -A && git commit -m "Add JSON store and Northline seed data"`

### Task 3: Patient tools

**Files:** `northline/tools/patient.py`, `tests/test_patient_tools.py`

**Interfaces:**
- `log_reading(patient_id: str, kind: str, value: str) -> dict` kinds `bp` (value `"146/92"`) or `glucose` (value `"62"`); appends to patient `last_readings` and to `readings.json`; returns `{"status","reading_id","flag": "normal"|"high"|"low"}` using fixed thresholds bp >=160 systolic or >=100 diastolic -> `high`, glucose <70 -> `low`, >250 -> `high`.
- `log_medication(patient_id: str, taken: bool, note: str = "") -> dict`.
- `escalate_to_nurse(patient_id: str, reason: str, urgency: str = "routine") -> dict` appends `{"id": "esc-<n>", "patient_id", "reason", "urgency", "created_at": now iso, "answered_at": null, "tier": null, "route": null}` to `$NORTHLINE_LOG_DIR/queue.jsonl` (via `calllog.log_dir()` from Task 6; until then a local `_log_dir()` reading `NORTHLINE_LOG_DIR`) and returns `{"status","escalation_id","message": "A nurse will review this. Median response time is currently <h> hours."}` where `<h>` reads `sim/out/summary.json` if present else `31`.
- `next_checkin(patient_id: str) -> dict` returns next Monday 09:00 from today as iso.

- [ ] **Step 1: Tests**

```python
# tests/test_patient_tools.py
import json
from northline.tools import patient as p, store


def test_log_reading_flags_high_bp(data_dir, log_dir):
    r = p.log_reading(patient_id="pt-1001", kind="bp", value="184/112")
    assert r["status"] == "ok" and r["flag"] == "high"
    assert store.load("readings")[-1]["value"] == "184/112"


def test_log_reading_low_glucose(data_dir, log_dir):
    assert p.log_reading(patient_id="pt-1001", kind="glucose", value="62")["flag"] == "low"


def test_log_reading_unknown_patient(data_dir, log_dir):
    assert p.log_reading(patient_id="zz", kind="bp", value="120/80")["status"] == "not_found"


def test_log_medication(data_dir, log_dir):
    assert p.log_medication(patient_id="pt-1002", taken=False, note="upsets stomach")["status"] == "ok"


def test_escalate_writes_queue(data_dir, log_dir):
    r = p.escalate_to_nurse(patient_id="pt-1001", reason="BP 184/112 with headache", urgency="urgent")
    assert r["status"] == "ok" and r["escalation_id"] == "esc-1"
    row = json.loads((log_dir / "queue.jsonl").read_text().strip())
    assert row["answered_at"] is None and row["urgency"] == "urgent"
    assert "hours" in r["message"]


def test_next_checkin(data_dir, log_dir):
    assert p.next_checkin(patient_id="pt-1001")["next"].endswith("T09:00")
```

- [ ] **Step 2: Implementation**

```python
# northline/tools/patient.py
"""Patient-facing tools for the weekly check-in agent. Administrative only."""
import json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import store

_ROOT = Path(__file__).resolve().parents[1]


def _log_dir() -> Path:
    return Path(os.environ.get("NORTHLINE_LOG_DIR", _ROOT / "logs"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _patient(pid):
    return next((x for x in store.load("patients") if x["id"] == pid), None)


def _flag(kind: str, value: str) -> str:
    try:
        if kind == "bp":
            s, d = (int(x) for x in value.split("/"))
            return "high" if s >= 160 or d >= 100 else "normal"
        g = float(value)
        return "low" if g < 70 else "high" if g > 250 else "normal"
    except ValueError:
        return "normal"


def log_reading(patient_id: str, kind: str, value: str) -> dict:
    """Log a blood pressure (kind 'bp', value like '146/92') or glucose (kind 'glucose', value like '62') reading."""
    pts = store.load("patients")
    pt = next((x for x in pts if x["id"] == patient_id), None)
    if pt is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    if kind not in ("bp", "glucose"):
        return {"status": "error", "message": "kind must be bp or glucose"}
    row = store.append("readings", {"id": f"rd-{len(store.load('readings')) + 1}", "patient_id": patient_id,
                                    "kind": kind, "value": value, "at": _now(), "flag": _flag(kind, value)})
    pt.setdefault("last_readings", []).append({"kind": kind, "value": value, "at": row["at"]})
    store.save("patients", pts)
    return {"status": "ok", "reading_id": row["id"], "flag": row["flag"]}


def log_medication(patient_id: str, taken: bool, note: str = "") -> dict:
    """Record whether the patient took their medication this week, with an optional note."""
    if _patient(patient_id) is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    store.append("medication_log", {"patient_id": patient_id, "taken": taken, "note": note, "at": _now()})
    return {"status": "ok"}


def _median_hours() -> float:
    p = _ROOT / "sim" / "out" / "summary.json"
    if p.exists():
        try:
            return round(json.loads(p.read_text())["now"]["nurse_response_median_h"], 1)
        except (KeyError, ValueError):
            pass
    return 31.0


def escalate_to_nurse(patient_id: str, reason: str, urgency: str = "routine") -> dict:
    """Hand a concerning reading or symptom to a nurse. urgency is 'routine' or 'urgent'. Use for any clinical question."""
    if _patient(patient_id) is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    d = _log_dir(); d.mkdir(parents=True, exist_ok=True)
    q = d / "queue.jsonl"
    n = sum(1 for _ in q.open()) + 1 if q.exists() else 1
    row = {"id": f"esc-{n}", "patient_id": patient_id, "reason": reason, "urgency": urgency,
           "created_at": _now(), "answered_at": None, "tier": None, "route": None}
    with q.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return {"status": "ok", "escalation_id": row["id"],
            "message": f"A nurse will review this. Median response time is currently {_median_hours()} hours."}


def next_checkin(patient_id: str) -> dict:
    """When the patient's next weekly check-in is due."""
    if _patient(patient_id) is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    today = datetime.now().date()
    nxt = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    return {"status": "ok", "next": f"{nxt.isoformat()}T09:00"}
```

- [ ] **Step 3: Run** `uv run pytest tests/test_patient_tools.py -q` → 6 passed. **Commit** `git add -A && git commit -m "Add patient check-in tools"`

### Task 4: Plan tools

**Files:** `northline/tools/plan.py`, `tests/test_plan_tools.py`

**Interfaces:** All read `sim/out/summary.json` when present (Task 11) and fall back to the case's last-quarter numbers otherwise, so the MCP demo works before the sim exists.
- `member_engagement(plan_id: str) -> dict` -> `{"status","plan","enrolled","weekly_response_rate","readings_per_month"}`.
- `outcome_evidence(plan_id: str, metric: str) -> dict` metrics `bp_control`, `readings`, `satisfaction`, `escalations`; returns `{"status","metric","value","period":"last quarter","note"}`. `bp_control` returns `0.58` with note "share of hypertensive members with last reading under 140/90". `escalations` returns the weekly count and note "clinical flags surfaced by the agent"; this is the number Prairie never asks about.
- `enrollment_status(member_id: str) -> dict`.
- `enroll_members(plan_id: str, count: int) -> dict` increments `enrolled` in `plans.json`, returns new total.

- [ ] **Step 1: Tests**

```python
# tests/test_plan_tools.py
from northline.tools import plan as pl, store


def test_engagement_fallback(data_dir, log_dir):
    r = pl.member_engagement(plan_id="plan-prairie")
    assert r["status"] == "ok" and r["weekly_response_rate"] == 0.78 and r["enrolled"] == 2000


def test_outcome_metrics(data_dir, log_dir):
    assert pl.outcome_evidence(plan_id="plan-prairie", metric="satisfaction")["value"] == 72
    assert pl.outcome_evidence(plan_id="plan-prairie", metric="escalations")["value"] == 2400
    assert pl.outcome_evidence(plan_id="plan-prairie", metric="nope")["status"] == "error"


def test_enrollment(data_dir, log_dir):
    assert pl.enrollment_status(member_id="pt-1001")["status"] == "ok"
    assert pl.enroll_members(plan_id="plan-prairie", count=100)["enrolled"] == 2100
    assert next(p for p in store.load("plans") if p["id"] == "plan-prairie")["enrolled"] == 2100
```

- [ ] **Step 2: Implementation**

```python
# northline/tools/plan.py
"""Tools Northline publishes to health plans over MCP. Their agent, our data."""
import json
from pathlib import Path
from . import store

_SUMMARY = Path(__file__).resolve().parents[1] / "sim" / "out" / "summary.json"
FALLBACK = {"engaged_weekly": 0.78, "readings_per_month": 120000, "escalations_per_week": 2400, "satisfaction": 72,
            "nurse_response_median_h": 31.0}


def _now() -> dict:
    if _SUMMARY.exists():
        try:
            return {**FALLBACK, **json.loads(_SUMMARY.read_text())["now"]}
        except (KeyError, ValueError):
            pass
    return FALLBACK


def _plan(pid):
    return next((p for p in store.load("plans") if p["id"] == pid), None)


def member_engagement(plan_id: str) -> dict:
    """Engagement figures for a plan's enrolled members: weekly response rate and readings logged."""
    p = _plan(plan_id)
    if p is None:
        return {"status": "not_found", "message": f"no plan {plan_id}"}
    n = _now()
    return {"status": "ok", "plan": p["name"], "enrolled": p["enrolled"], "weekly_response_rate": n["engaged_weekly"],
            "readings_per_month": int(n["readings_per_month"] * p["enrolled"] / 40000)}


def outcome_evidence(plan_id: str, metric: str) -> dict:
    """Outcome evidence for a plan. metric: bp_control, readings, satisfaction, escalations."""
    if _plan(plan_id) is None:
        return {"status": "not_found", "message": f"no plan {plan_id}"}
    n = _now()
    table = {"bp_control": (0.58, "share of hypertensive members with last reading under 140/90"),
             "readings": (n["readings_per_month"], "readings logged per month, all members"),
             "satisfaction": (n["satisfaction"], "patient satisfaction score, 0 to 100"),
             "escalations": (n["escalations_per_week"], "clinical flags surfaced by the agent per week, all members")}
    if metric not in table:
        return {"status": "error", "message": f"metric must be one of {sorted(table)}"}
    v, note = table[metric]
    return {"status": "ok", "metric": metric, "value": v, "period": "last quarter", "note": note}


def enrollment_status(member_id: str) -> dict:
    """Whether a member is enrolled and engaged with the check-in program."""
    pt = next((x for x in store.load("patients") if x["id"] == member_id), None)
    if pt is None:
        return {"status": "not_found", "message": f"no member {member_id}"}
    return {"status": "ok", "member_id": member_id, "plan_id": pt["plan_id"], "engaged": pt["engaged"]}


def enroll_members(plan_id: str, count: int) -> dict:
    """Enroll additional members from a plan into the program."""
    plans = store.load("plans")
    p = next((x for x in plans if x["id"] == plan_id), None)
    if p is None:
        return {"status": "not_found", "message": f"no plan {plan_id}"}
    p["enrolled"] += int(count)
    store.save("plans", plans)
    return {"status": "ok", "plan": p["name"], "enrolled": p["enrolled"]}
```

- [ ] **Step 3: Run** `uv run pytest tests/test_plan_tools.py -q` → 3 passed. **Commit** `git add -A && git commit -m "Add health-plan tools for the MCP front door"`

### Task 5: Triage tools and the gated registry

**Files:** `northline/tools/triage.py`, `northline/tools/registry.py`, `tests/test_triage_tools.py`, `tests/test_registry.py`

**Interfaces:**
- `triage.pending_messages(limit: int = 20) -> dict` reads `queue.jsonl` (same `_log_dir` rule as Task 3) and returns rows with `answered_at` null and `route` null, oldest first.
- `triage.tier_message(message_id: str, tier: str, rationale: str) -> dict` sets `tier` on the row; tier must be one of the three tiers.
- `triage.route_message(message_id: str, to: str, draft_reply: str = "") -> dict` sets `route` (one of the four routes) and `draft_reply`; if `to` is `admin` or `auto_reply` it also sets `answered_at` to now, because those leave the nurse queue.
- Queue rows are rewritten in place: read all, modify, write all.
- `registry.ToolSpec(name, fn, personas: frozenset, requires: str | None)`, `registry.TOOLS`, `registry.live_deployments() -> set[str]` from `store.load("deployments")`, `registry.select(persona: str) -> list[ToolSpec]` returning tools whose persona matches (`"all"` matches everything) and whose `requires` is `None` or in `live_deployments()`.

- [ ] **Step 1: Tests**

```python
# tests/test_triage_tools.py
import json
from northline.tools import patient as p, triage as t


def _seed(data_dir, log_dir):
    p.escalate_to_nurse(patient_id="pt-1001", reason="BP 184/112 headache", urgency="urgent")
    p.escalate_to_nurse(patient_id="pt-1002", reason="insurance denied strips", urgency="routine")


def test_pending_lists_unrouted(data_dir, log_dir):
    _seed(data_dir, log_dir)
    r = t.pending_messages(limit=10)
    assert [m["id"] for m in r["messages"]] == ["esc-1", "esc-2"]


def test_tier_and_route(data_dir, log_dir):
    _seed(data_dir, log_dir)
    assert t.tier_message(message_id="esc-2", tier="non_clinical", rationale="benefits question")["status"] == "ok"
    assert t.tier_message(message_id="esc-2", tier="silly", rationale="")["status"] == "error"
    r = t.route_message(message_id="esc-2", to="admin", draft_reply="Our benefits team will call you tomorrow.")
    assert r["status"] == "ok"
    rows = [json.loads(l) for l in (log_dir / "queue.jsonl").read_text().splitlines()]
    assert rows[1]["route"] == "admin" and rows[1]["answered_at"] is not None and rows[0]["answered_at"] is None
    assert [m["id"] for m in t.pending_messages()["messages"]] == ["esc-1"]


def test_route_unknown(data_dir, log_dir):
    assert t.route_message(message_id="esc-9", to="admin")["status"] == "not_found"
```

```python
# tests/test_registry.py
from northline.tools import registry as r, store


def test_docstrings_and_unique_names():
    names = [t.name for t in r.TOOLS]
    assert len(names) == len(set(names))
    assert all(t.fn.__doc__ for t in r.TOOLS)


def test_persona_selection(data_dir):
    assert {t.name for t in r.select("patient")} == {"log_reading", "log_medication", "escalate_to_nurse", "next_checkin"}
    assert {t.name for t in r.select("plan")} == {"member_engagement", "outcome_evidence", "enrollment_status", "enroll_members"}


def test_triage_tools_gated_by_deployment(data_dir):
    assert r.select("triage") == []
    store.append("deployments", {"name": "triage", "live_from_week": 40, "effects": {}})
    assert {t.name for t in r.select("triage")} == {"pending_messages", "tier_message", "route_message"}
```

- [ ] **Step 2: triage.py**

```python
# northline/tools/triage.py
"""Tools the triage agent uses on the nurse queue. Exposed only once triage is deployed."""
import json
from datetime import datetime, timezone
from .patient import _log_dir

TIERS = {"urgent_clinical", "non_urgent_clinical", "non_clinical"}
ROUTES = {"nurse_urgent", "nurse_routine", "admin", "auto_reply"}


def _rows() -> list[dict]:
    q = _log_dir() / "queue.jsonl"
    return [json.loads(l) for l in q.read_text().splitlines() if l.strip()] if q.exists() else []


def _write(rows: list[dict]) -> None:
    (_log_dir() / "queue.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def _update(message_id: str, **fields) -> dict:
    rows = _rows()
    row = next((r for r in rows if r["id"] == message_id), None)
    if row is None:
        return {"status": "not_found", "message": f"no message {message_id}"}
    row.update(fields); _write(rows)
    return {"status": "ok", "message_id": message_id}


def pending_messages(limit: int = 20) -> dict:
    """Oldest unrouted messages in the nurse queue: id, patient_id, reason, urgency, created_at."""
    rows = [r for r in _rows() if r["answered_at"] is None and r.get("route") is None]
    return {"status": "ok" if rows else "not_found", "messages": rows[:limit]}


def tier_message(message_id: str, tier: str, rationale: str) -> dict:
    """Assign a tier: urgent_clinical, non_urgent_clinical, or non_clinical, with a one-line rationale."""
    if tier not in TIERS:
        return {"status": "error", "message": f"tier must be one of {sorted(TIERS)}"}
    return _update(message_id, tier=tier, rationale=rationale)


def route_message(message_id: str, to: str, draft_reply: str = "") -> dict:
    """Route a message: nurse_urgent, nurse_routine, admin, or auto_reply. Include a draft reply for a nurse to review."""
    if to not in ROUTES:
        return {"status": "error", "message": f"to must be one of {sorted(ROUTES)}"}
    fields = {"route": to, "draft_reply": draft_reply}
    if to in ("admin", "auto_reply"):
        fields["answered_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return _update(message_id, **fields)
```

- [ ] **Step 3: registry.py**

```python
# northline/tools/registry.py
"""The single list of Northline tools. Both front doors and the triage agent read this.

Adding a tool is one function with a docstring plus one line here. A tool with `requires`
appears only once that deployment is live in data/deployments.json; that is how /deploy
changes what agents can do without editing Python on stage.
"""
from dataclasses import dataclass
from typing import Callable
from . import patient as p, plan as pl, triage as t, store


@dataclass(frozen=True)
class ToolSpec:
    name: str
    fn: Callable
    personas: frozenset[str]
    requires: str | None = None


def _t(fn, personas, requires=None):
    return ToolSpec(fn.__name__, fn, frozenset(personas), requires)


TOOLS: list[ToolSpec] = [
    _t(p.log_reading, {"patient"}), _t(p.log_medication, {"patient"}),
    _t(p.escalate_to_nurse, {"patient"}), _t(p.next_checkin, {"patient"}),
    _t(pl.member_engagement, {"plan"}), _t(pl.outcome_evidence, {"plan"}),
    _t(pl.enrollment_status, {"plan"}), _t(pl.enroll_members, {"plan"}),
    _t(t.pending_messages, {"triage"}, "triage"), _t(t.tier_message, {"triage"}, "triage"),
    _t(t.route_message, {"triage"}, "triage"),
]


def live_deployments() -> set[str]:
    return {d["name"] for d in store.load("deployments")}


def select(persona: str) -> list[ToolSpec]:
    live = live_deployments()
    return [x for x in TOOLS if (persona == "all" or persona in x.personas) and (x.requires is None or x.requires in live)]
```

- [ ] **Step 4: Run** `uv run pytest -q` → all pass. **Commit** `git add -A && git commit -m "Add triage tools and the deployment-gated registry"`

### Task 6: Call log, MCP server, project registration

**Files:** `northline/tools/calllog.py`, `northline/mcp_server.py`, `.mcp.json`, `tests/test_calllog.py`, `tests/test_mcp_server.py`
- Modify: `northline/tools/patient.py` so `_log_dir` is imported from `calllog` (`from .calllog import log_dir as _log_dir`) and the local definition is removed.

**Interfaces:** `calllog.log_dir() -> Path` (env `NORTHLINE_LOG_DIR`, default `northline/logs`), `calllog.log_call(tool, args, result, *, persona, session_id)`, `calllog.wrap(fn, *, persona, session_id)` preserving signature and docstring via `functools.wraps`. Log line: `{"ts","session_id","persona","tool","args","status","error"}` to `tool_calls.jsonl`. `mcp_server.build_server(persona: str, session_id: str) -> MCPServer` named `northline`.

- [ ] **Step 1: Tests**

```python
# tests/test_calllog.py
import inspect, json
from northline.tools import calllog


def test_wrap_logs_and_preserves(log_dir):
    def add(a: int, b: int = 1) -> dict:
        """Add."""
        return {"status": "ok", "sum": a + b}
    w = calllog.wrap(add, persona="plan", session_id="s1")
    assert w(a=2)["sum"] == 3 and list(inspect.signature(w).parameters) == ["a", "b"] and w.__doc__ == "Add."
    line = json.loads((log_dir / "tool_calls.jsonl").read_text().strip())
    assert line["tool"] == "add" and line["args"] == {"a": 2} and line["persona"] == "plan" and line["session_id"] == "s1"


def test_wrap_records_error(log_dir):
    def bad() -> dict:
        """Bad."""
        return {"status": "error", "message": "nope"}
    calllog.wrap(bad, persona="plan", session_id="s2")()
    assert json.loads((log_dir / "tool_calls.jsonl").read_text().strip())["error"] == "nope"
```

```python
# tests/test_mcp_server.py
import json, pytest
from mcp import Client
from northline.mcp_server import build_server


@pytest.mark.anyio
async def test_plan_server_lists_plan_tools(data_dir, log_dir):
    async with Client(build_server(persona="plan", session_id="t1")) as c:
        names = {t.name for t in (await c.list_tools()).tools}
    assert names == {"member_engagement", "outcome_evidence", "enrollment_status", "enroll_members"}


@pytest.mark.anyio
async def test_call_logs(data_dir, log_dir):
    async with Client(build_server(persona="plan", session_id="t2")) as c:
        r = await c.call_tool("outcome_evidence", {"plan_id": "plan-prairie", "metric": "escalations"})
    assert r.structured_content["value"] == 2400
    assert json.loads((log_dir / "tool_calls.jsonl").read_text().strip())["session_id"] == "t2"
```

- [ ] **Step 2: calllog.py**

```python
# northline/tools/calllog.py
"""Append-only log of every tool call. This is the only product signal the MCP path gives you."""
import functools, json, os
from datetime import datetime, timezone
from pathlib import Path
_DEFAULT = Path(__file__).resolve().parents[1] / "logs"


def log_dir() -> Path:
    return Path(os.environ.get("NORTHLINE_LOG_DIR", _DEFAULT))


def log_call(tool: str, args: dict, result: dict, *, persona: str, session_id: str) -> None:
    d = log_dir(); d.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session_id": session_id, "persona": persona,
            "tool": tool, "args": args, "status": result.get("status", "unknown"),
            "error": result.get("message") if result.get("status") != "ok" else None}
    with (d / "tool_calls.jsonl").open("a") as f:
        f.write(json.dumps(line) + "\n")


def wrap(fn, *, persona: str, session_id: str):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        result = fn(*args, **kwargs)
        log_call(fn.__name__, kwargs, result, persona=persona, session_id=session_id)
        return result
    return inner
```

- [ ] **Step 3: mcp_server.py**

```python
# northline/mcp_server.py
"""Front door 1: Northline's tools over MCP. Persona from NORTHLINE_PERSONA: patient, plan, or triage."""
import os, uuid
from mcp.server import MCPServer
from northline.tools import calllog, registry


def build_server(persona: str, session_id: str) -> MCPServer:
    server = MCPServer("northline")
    for spec in registry.select(persona):
        server.add_tool(calllog.wrap(spec.fn, persona=persona, session_id=session_id),
                        name=spec.name, description=spec.fn.__doc__.strip())
    return server


if __name__ == "__main__":
    build_server(os.environ.get("NORTHLINE_PERSONA", "plan"),
                 os.environ.get("NORTHLINE_SESSION_ID") or uuid.uuid4().hex[:8]).run()
```

- [ ] **Step 4: .mcp.json**

```json
{
  "mcpServers": {
    "northline": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${CLAUDE_PROJECT_DIR}", "python", "-m", "northline.mcp_server"],
      "env": {
        "NORTHLINE_PERSONA": "${NORTHLINE_PERSONA:-plan}",
        "NORTHLINE_LOG_DIR": "${CLAUDE_PROJECT_DIR}/northline/logs",
        "NORTHLINE_DATA_DIR": "${CLAUDE_PROJECT_DIR}/northline/data"
      }
    }
  }
}
```

- [ ] **Step 5: Run** `uv run pytest -q` → all pass. Then the real check: `claude -p "You are Prairie Health Plan's analyst. Using the northline tools, report engagement and outcome evidence for plan-prairie in four lines." --output-format json --tools "" --model haiku | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])"`. Expected: four lines quoting 78% and 72, and `northline/logs/tool_calls.jsonl` gains lines. **Commit** `git add -A && git commit -m "Add call logging, the MCP server, and project registration"`

### Task 7: Setup, check, package, README

**Files:** `scripts/__init__.py`, `scripts/check.py`, `scripts/package.py`, `.claude/skills/setup/SKILL.md`, `README.md`, `tests/test_package.py`

- [ ] **Step 1: scripts/check.py**

```python
"""Pre-flight. Run: uv run python scripts/check.py"""
import shutil, subprocess, sys
from northline.tools import registry


def main() -> int:
    ok = True
    print(f"python {sys.version.split()[0]}")
    try:
        import mcp  # noqa: F401
        print("mcp ok")
    except ImportError as e:
        print(f"mcp FAILED: {e}"); ok = False
    for persona in ("patient", "plan", "triage"):
        print(f"tools {persona}: {len(registry.select(persona))}")
    if shutil.which("claude"):
        print("claude " + subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    else:
        print("claude not found on PATH"); ok = False
    print("\nREADY" if ok else "\nNOT READY, see above")
    print("Check-in agent + dashboard: uv run python -m northline.agent.server  ->  http://127.0.0.1:8765 and /dashboard")
    print("Prairie's analyst (MCP): this Claude Code session already has the northline tools.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: scripts/package.py and its test**

```python
"""Build dist/northline-course.zip for attendees. No git, no venv, no logs, no generated triage files."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "dist", "briefs"}
EXCLUDE_FILES = {"northline/agents/triage/decisions.json", "northline/agents/triage/prompt.md"}
EXCLUDE_PREFIX = ("northline/logs/", "northline/agents/triage/out/")


def build(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out or root / "dist" / "northline-course.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root).as_posix()
            if p.is_dir() or any(part in EXCLUDE_DIRS for part in p.parts) or rel in EXCLUDE_FILES:
                continue
            if rel.startswith(EXCLUDE_PREFIX) and not rel.endswith(".gitkeep"):
                continue
            z.write(p, f"northline-course/{rel}")
    return out


if __name__ == "__main__":
    print(build())
```

```python
# tests/test_package.py
import zipfile
from scripts.package import build


def test_zip_has_no_git_venv_or_logs(tmp_path):
    out = build(out=tmp_path / "z.zip")
    names = zipfile.ZipFile(out).namelist()
    assert any(n.endswith("pyproject.toml") for n in names)
    assert not any("/.git/" in n or "/.venv/" in n or "/__pycache__/" in n for n in names)
    assert not any("northline/logs/" in n and not n.endswith(".gitkeep") for n in names)
    assert all(n.startswith("northline-course/") for n in names)
```

- [ ] **Step 3: The /setup skill**

```markdown
---
name: setup
description: Prepare this laptop for the Northline session. Installs uv if missing, syncs dependencies, runs the checks, confirms the MCP server, and prints what to open. Works on macOS, Linux, and Windows.
disable-model-invocation: true
---

You are preparing an attendee's laptop. Do these in order. Stop with a plain-language message if a step fails; do not try workarounds that install other tools.

1. Detect the OS. Run `uv --version`. If missing:
   - macOS or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   Then re-run `uv --version`. If it is still not found, tell the user to close and reopen their terminal or Claude Code, then run /setup again.
2. Run `uv sync`.
3. Run `uv run pytest -q` and report the count.
4. Run `uv run python scripts/check.py`. If the last line is not READY, show the output and stop.
5. Run `claude mcp list`. If `northline` is missing or shows as needing approval, tell the user: start a new Claude Code session in this folder and accept the project MCP server when asked, then come back.
6. Finish with exactly this, filled in:
   READY: <OS>, <python version>, <claude version>, northline tools: patient <n> plan <n>
   Ask them to paste that line into the workshop group chat.
   Then two lines: "In the room you will type /pm-run and /deploy triage. Nothing else."

Never run git. Never modify files. Never install anything other than uv.
```

- [ ] **Step 4: README.md** under 60 lines: the thesis line, pre-work in five steps (download the zip, unzip into your home folder, open Claude Code in the folder, type `/setup`, paste the READY line), what happens in the room, the three surfaces (check-in agent, dashboard, Prairie's analyst), the take-home skills, and a pointer to `docs/00-session-plan.md`. No mention of git or GitHub anywhere.

- [ ] **Step 5: Run** `uv run pytest -q && uv run python scripts/check.py && uv run python scripts/package.py` → tests pass, READY, zip path printed. Unzip the zip into a temp folder, run `uv sync && uv run pytest -q` there, delete it. **Commit** `git add -A && git commit -m "Add setup skill, pre-flight check, packaging, and README"`

**Phase 1 checkpoint:** unzip, `/setup`, and Prairie's analyst works from the attendee's Claude Code.

---

## Phase 2: The check-in agent

### Task 8: Headless turn runner

**Files:** `northline/agent/__init__.py`, `northline/agent/claude_runner.py`, `tests/test_claude_runner.py`

**Interfaces:** `TurnResult(reply, session_id, tool_uses: list[{name,input,result,is_error}], cost_usd, is_error)` with the `mcp__northline__` prefix stripped from names. `build_command(message, *, system_prompt, mcp_config: dict, session_id, model, cwd) -> list[str]`. `parse_stream(lines) -> TurnResult`. `run_turn(message, *, system_prompt, mcp_config, session_id=None, model=None, cwd=REPO_ROOT, runner=subprocess.run) -> TurnResult`.

- [ ] **Step 1: Tests**

```python
# tests/test_claude_runner.py
import json
from types import SimpleNamespace
from northline.agent import claude_runner as cr

STREAM = [
    {"type": "system", "subtype": "init", "session_id": "sess-1"},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "tu1", "name": "mcp__northline__log_reading",
                                                    "input": {"patient_id": "pt-1001", "kind": "bp", "value": "146/92"}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "tu1",
                                               "content": [{"type": "text", "text": "{\"status\": \"ok\"}"}], "is_error": False}]}},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "Logged. Thanks!"}]}},
    {"type": "result", "subtype": "success", "is_error": False, "result": "Logged. Thanks!", "session_id": "sess-1", "total_cost_usd": 0.01},
]


def test_parse_stream():
    r = cr.parse_stream(json.dumps(l) for l in STREAM)
    assert r.reply == "Logged. Thanks!" and r.session_id == "sess-1" and r.cost_usd == 0.01
    assert r.tool_uses == [{"name": "log_reading", "input": {"patient_id": "pt-1001", "kind": "bp", "value": "146/92"},
                            "result": '{"status": "ok"}', "is_error": False}]


def test_build_command_lockdown(tmp_path):
    cmd = cr.build_command("hi", system_prompt="SP", mcp_config={"mcpServers": {}}, session_id=None, model=None, cwd=tmp_path)
    assert cmd[:3] == ["claude", "-p", "hi"]
    assert cmd[cmd.index("--tools") + 1] == "" and cmd[cmd.index("--allowedTools") + 1] == "mcp__northline__*"
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk" and "--strict-mcp-config" in cmd and "--resume" not in cmd


def test_build_command_resume(tmp_path):
    cmd = cr.build_command("hi", system_prompt="SP", mcp_config={}, session_id="abc", model="sonnet", cwd=tmp_path)
    assert cmd[cmd.index("--resume") + 1] == "abc" and cmd[cmd.index("--model") + 1] == "sonnet"


def test_run_turn_injected_runner(tmp_path):
    def fake(cmd, **kw):
        return SimpleNamespace(stdout="\n".join(json.dumps(l) for l in STREAM), returncode=0, stderr="")
    assert cr.run_turn("hi", system_prompt="SP", mcp_config={}, cwd=tmp_path, runner=fake).session_id == "sess-1"


def test_run_turn_error(tmp_path):
    def fake(cmd, **kw):
        return SimpleNamespace(stdout="", returncode=1, stderr="boom")
    r = cr.run_turn("hi", system_prompt="SP", mcp_config={}, cwd=tmp_path, runner=fake)
    assert r.is_error and "boom" in r.reply
```

- [ ] **Step 2: Implementation**

```python
# northline/agent/claude_runner.py
"""One conversational turn through headless Claude Code. The controlled agent is *our* Claude Code
configuration: locked system prompt, only the Northline MCP tools, no built-ins."""
import json, subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
PREFIX = "mcp__northline__"


@dataclass
class TurnResult:
    reply: str
    session_id: str
    tool_uses: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    is_error: bool = False


def build_command(message, *, system_prompt, mcp_config, session_id, model, cwd) -> list[str]:
    cmd = ["claude", "-p", message, "--output-format", "stream-json", "--verbose",
           "--system-prompt", system_prompt, "--mcp-config", json.dumps(mcp_config), "--strict-mcp-config",
           "--tools", "", "--allowedTools", PREFIX + "*", "--permission-mode", "dontAsk", "--max-turns", "10"]
    if session_id:
        cmd += ["--resume", session_id]
    if model:
        cmd += ["--model", model]
    return cmd


def parse_stream(lines: Iterable[str]) -> TurnResult:
    pending, tool_uses = {}, []
    reply = session_id = ""
    cost, is_error = 0.0, False
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "assistant":
            for b in d["message"]["content"]:
                if b.get("type") == "tool_use":
                    rec = {"name": b["name"].removeprefix(PREFIX), "input": b.get("input", {}), "result": "", "is_error": False}
                    pending[b["id"]] = rec; tool_uses.append(rec)
        elif t == "user":
            for b in d["message"]["content"]:
                if b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                    c = b.get("content")
                    if isinstance(c, list):
                        c = "".join(x.get("text", "") for x in c if isinstance(x, dict))
                    pending[b["tool_use_id"]].update(result=str(c or ""), is_error=bool(b.get("is_error")))
        elif t == "result":
            reply, session_id = d.get("result") or "", d.get("session_id", "")
            cost, is_error = float(d.get("total_cost_usd") or 0), bool(d.get("is_error"))
        elif t == "system" and d.get("subtype") == "init" and not session_id:
            session_id = d.get("session_id", "")
    return TurnResult(reply, session_id, tool_uses, cost, is_error)


def run_turn(message, *, system_prompt, mcp_config, session_id=None, model=None, cwd=REPO_ROOT, runner=subprocess.run) -> TurnResult:
    cmd = build_command(message, system_prompt=system_prompt, mcp_config=mcp_config, session_id=session_id, model=model, cwd=cwd)
    proc = runner(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 and not proc.stdout.strip():
        return TurnResult(f"agent error: {getattr(proc, 'stderr', '')}".strip(), session_id or "", is_error=True)
    return parse_stream(proc.stdout.splitlines())
```

- [ ] **Step 3: Run** `uv run pytest tests/test_claude_runner.py -q` → 5 passed. **Commit** `git add -A && git commit -m "Add headless Claude Code turn runner"`

### Task 9: Check-in brief and prompt assembly

**Files:** `northline/agent/brief.md`, `northline/agent/prompt.py`, `tests/test_prompt.py`

**Interfaces:** `prompt.system_prompt() -> str` (brief text plus a line with today's date), `prompt.mcp_config(session_id: str) -> dict` for persona `patient`, with `NORTHLINE_SESSION_ID`, `NORTHLINE_LOG_DIR`, `NORTHLINE_DATA_DIR` set from the environment or repo defaults.

- [ ] **Step 1: brief.md** (the filled `templates/agent-brief.md`)

```markdown
# Northline check-in agent

## Role
You are Northline Care's weekly check-in assistant, texting patients with hypertension or type 2 diabetes in rural North Dakota, South Dakota, and Montana. Each week you ask for a blood pressure or glucose reading, whether they took their medication, and how they are feeling. You log what they tell you and hand anything clinical to a nurse. That is the whole job.

## Hard rules
- You do not diagnose, interpret readings, adjust medication, or give dietary or treatment advice. Not even "that's probably fine".
- Any symptom, side effect, missed or doubled dose, reading flagged high or low, or "should I worry": call `escalate_to_nurse`. Use urgency `urgent` for chest pain or pressure, arm or jaw pain, trouble breathing, confusion, slurred speech, a glucose under 70 or over 300, or a blood pressure at or above 180/110. For those, also tell the patient to call 911 if it is happening now.
- If a patient asks for something you have no tool for (a refill, insurance, the pharmacy drive, diet questions, device errors), say plainly that you cannot do that yet, say what you can do, and offer to note it for a nurse. Do not invent a process.
- Never promise a call-back time other than what `escalate_to_nurse` returns.
- Ask for the patient id (looks like pt-1001) once, then reuse it.

## Style
- Short texts, one question at a time, plain words. Many patients are older and on small phones.
- Warm but not chatty. Thank them for readings.
- If a patient says STOP, confirm you will stop and end the conversation.

## Logging
Every conversation is stored with the tools you used and whether you escalated. The product team reads them weekly. Be explicit about what you could not do; that is how the next tool gets built.
```

- [ ] **Step 2: Tests**

```python
# tests/test_prompt.py
from northline.agent import prompt


def test_system_prompt_has_rules_and_date():
    sp = prompt.system_prompt()
    assert "## Hard rules" in sp and "escalate_to_nurse" in sp and "Today is" in sp


def test_mcp_config_patient(monkeypatch, tmp_path):
    monkeypatch.setenv("NORTHLINE_LOG_DIR", str(tmp_path))
    cfg = prompt.mcp_config("s-1")["mcpServers"]["northline"]
    assert cfg["env"]["NORTHLINE_PERSONA"] == "patient" and cfg["env"]["NORTHLINE_SESSION_ID"] == "s-1"
    assert cfg["env"]["NORTHLINE_LOG_DIR"] == str(tmp_path) and cfg["args"][-2:] == ["-m", "northline.mcp_server"]
```

- [ ] **Step 3: prompt.py**

```python
# northline/agent/prompt.py
import os
from datetime import date
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def system_prompt() -> str:
    return (HERE / "brief.md").read_text().rstrip() + f"\n\nToday is {date.today().isoformat()}."


def mcp_config(session_id: str) -> dict:
    return {"mcpServers": {"northline": {
        "type": "stdio", "command": "uv",
        "args": ["run", "--directory", str(REPO_ROOT), "python", "-m", "northline.mcp_server"],
        "env": {"NORTHLINE_PERSONA": "patient", "NORTHLINE_SESSION_ID": session_id,
                "NORTHLINE_LOG_DIR": os.environ.get("NORTHLINE_LOG_DIR", str(REPO_ROOT / "northline" / "logs")),
                "NORTHLINE_DATA_DIR": os.environ.get("NORTHLINE_DATA_DIR", str(REPO_ROOT / "northline" / "data"))}}}}
```

- [ ] **Step 4: Run** `uv run pytest tests/test_prompt.py -q` → 2 passed. **Commit** `git add -A && git commit -m "Add the check-in agent brief and prompt assembly"`

### Task 10: Transcripts and the SMS page

**Files:** `northline/agent/transcripts.py`, `northline/agent/server.py`, `northline/agent/static/index.html`, `tests/test_transcripts.py`, `tests/test_server.py`

**Interfaces:**
- `transcripts.record_turn(session_id, user, result: TurnResult) -> Path` writes `log_dir()/transcripts/<session_id>.json`: `{"session_id","persona":"patient","started","messages":[{"role","content","ts"}],"tool_uses":[...],"escalated": bool,"cost_usd"}`. `transcripts.load_all(dir) -> list[dict]`.
- `server.app`: `GET /` page; `POST /chat` body `{"message", "session_id": str|null}` -> `{"reply","session_id","tool_uses","is_error"}`. Session id is `uuid4().hex[:12]` generated before the first call so the MCP env carries it; Claude's session id kept in a module dict for `--resume`. `server.run_turn_fn` is a module attribute tests replace. `/dashboard` and `/api/sim` are added in Task 12.
- `python -m northline.agent.server` serves `127.0.0.1:8765`.

- [ ] **Step 1: Tests**

```python
# tests/test_transcripts.py
import json
from northline.agent import transcripts as tr
from northline.agent.claude_runner import TurnResult


def test_record_and_load(log_dir):
    path = tr.record_turn("s1", "hi", TurnResult("hello", "c1", [], 0.01))
    tr.record_turn("s1", "chest tight", TurnResult("call 911", "c1", [{"name": "escalate_to_nurse", "input": {}, "result": "", "is_error": False}], 0.02))
    d = json.loads(path.read_text())
    assert len(d["messages"]) == 4 and d["escalated"] is True and abs(d["cost_usd"] - 0.03) < 1e-9
    assert tr.load_all(log_dir / "transcripts")[0]["session_id"] == "s1"
```

```python
# tests/test_server.py
import json
from fastapi.testclient import TestClient
from northline.agent import server
from northline.agent.claude_runner import TurnResult


def test_chat_roundtrip(log_dir, data_dir, monkeypatch):
    seen = {}
    def fake(message, *, system_prompt, mcp_config, session_id=None, model=None, **kw):
        seen.update(cfg=mcp_config, resume=session_id)
        return TurnResult("Hi Thandi", "claude-abc", [], 0.0)
    monkeypatch.setattr(server, "run_turn_fn", fake)
    c = TestClient(server.app)
    r = c.post("/chat", json={"message": "hi", "session_id": None}).json()
    assert r["reply"] == "Hi Thandi" and len(r["session_id"]) == 12 and seen["resume"] is None
    assert seen["cfg"]["mcpServers"]["northline"]["env"]["NORTHLINE_SESSION_ID"] == r["session_id"]
    c.post("/chat", json={"message": "146/92", "session_id": r["session_id"]})
    assert seen["resume"] == "claude-abc"
    assert len(json.loads((log_dir / "transcripts" / f"{r['session_id']}.json").read_text())["messages"]) == 4


def test_index(log_dir):
    assert TestClient(server.app).get("/").status_code == 200
```

- [ ] **Step 2: transcripts.py**

```python
# northline/agent/transcripts.py
"""One JSON file per check-in conversation. This is the product signal the controlled agent gives you."""
import json
from datetime import datetime, timezone
from pathlib import Path
from northline.tools.calllog import log_dir
from .claude_runner import TurnResult


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_turn(session_id: str, user: str, result: TurnResult) -> Path:
    d = log_dir() / "transcripts"; d.mkdir(parents=True, exist_ok=True)
    path = d / f"{session_id}.json"
    doc = json.loads(path.read_text()) if path.exists() else {
        "session_id": session_id, "persona": "patient", "started": _now(), "messages": [], "tool_uses": [],
        "escalated": False, "cost_usd": 0.0}
    doc["messages"] += [{"role": "user", "content": user, "ts": _now()}, {"role": "assistant", "content": result.reply, "ts": _now()}]
    doc["tool_uses"] += result.tool_uses
    doc["escalated"] = doc["escalated"] or any(t["name"] == "escalate_to_nurse" for t in result.tool_uses)
    doc["cost_usd"] = round(doc["cost_usd"] + result.cost_usd, 6)
    path.write_text(json.dumps(doc, indent=2))
    return path


def load_all(directory: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(directory).glob("*.json"))]
```

- [ ] **Step 3: server.py**

```python
# northline/agent/server.py
"""Front door 2: the check-in agent as an SMS-style page. The dashboard is served here too."""
import os, uuid
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from . import claude_runner, prompt, transcripts

app = FastAPI(title="Northline check-in agent")
STATIC = Path(__file__).resolve().parent / "static"
run_turn_fn = claude_runner.run_turn
_claude_sessions: dict[str, str] = {}


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/chat")
def chat(body: ChatIn):
    sid = body.session_id or uuid.uuid4().hex[:12]
    r = run_turn_fn(body.message, system_prompt=prompt.system_prompt(), mcp_config=prompt.mcp_config(sid),
                    session_id=_claude_sessions.get(sid), model=os.environ.get("NORTHLINE_MODEL"))
    if r.session_id:
        _claude_sessions[sid] = r.session_id
    transcripts.record_turn(sid, body.message, r)
    return {"reply": r.reply, "session_id": sid, "tool_uses": r.tool_uses, "is_error": r.is_error}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("NORTHLINE_PORT", "8765")))
```

- [ ] **Step 4: static/index.html.** One file, no external assets, under 150 lines. A phone-shaped SMS thread on a plain background, header "Northline Care" with a small "weekly check-in" subtitle, the first bubble pre-filled from the agent's side: "Hi, it's your Northline check-in. What was your blood pressure this week?" (rendered client-side, not sent). Input with placeholder "Text back…", disabled with "…" while waiting. Under each assistant bubble a grey line listing tool names used, and a red "escalated to nurse" tag if `escalate_to_nurse` appears. "New conversation" link resets the session. A small link to `/dashboard` in the footer. Fetch `POST /chat`.

- [ ] **Step 5: Run** `uv run pytest -q` → all pass. Real smoke: start `uv run python -m northline.agent.server`, then `curl -s -X POST localhost:8765/chat -H 'content-type: application/json' -d '{"message":"pt-1001 here. BP was 184/112 this morning, bit of a headache, probably nothing"}'`. Expected: reply escalates with urgency urgent and mentions 911; `northline/logs/queue.jsonl` gains a row; a transcript file appears. Then open the page and have one ordinary check-in conversation. **Commit** `git add -A && git commit -m "Add the check-in agent page with transcripts"`

**Phase 2 checkpoint:** both front doors work and each leaves its own kind of log.

---

## Phase 3: Company simulator and dashboard

### Task 11: Weekly company model

**Files:** `northline/sim/__init__.py`, `northline/sim/model.py`, `northline/sim/run.py`, `tests/test_sim.py`

**Interfaces:**
- `model.BASE: dict` the no-agent parameters. `model.State(week, patients, nurses, resign_accum, inactive_total)`.
- `model.step(state: State, params: dict) -> tuple[State, dict]` returns the next state and a metrics row: `week, patients, nurses, readings_per_month, escalations_per_week, inbound_per_week, after_hours_share, nurse_items_per_week, load, nurse_response_median_h, urgent_response_h, overtime_hours_per_month, resignations, inactive_after_escalation, missed_urgent_per_week, satisfaction, revenue_month, nurse_cost_month`.
- `model.params_for(week: int, deployments: list[dict]) -> dict` merges `BASE` with the `effects` of every deployment whose `live_from_week <= week`, in list order.
- `model.run(weeks: range, deployments, start: State | None = None, patients: int | None = None) -> list[dict]`.
- `model.average(rows) -> dict` mean of numeric fields, `inactive_after_escalation` and `resignations` summed instead of averaged.
- `run.main()` writes `sim/out/weekly.json` (`{"history": rows 1-39 with deployments live by week 39 filtered to checkin_agent, "next_quarter": rows 40-52 all deployments, "prairie": rows 40-52 all deployments at 100000 patients, "prairie_without": rows 40-52 checkin only at 100000}`) and `sim/out/summary.json` with `before` (week 0 metrics, no deployments), `last_quarter` (average of history weeks 27-39), `next_quarter`, `prairie`, `prairie_without`, `now` (= `next_quarter` if any deployment other than `checkin_agent` is live, else `last_quarter`), and `deployments` (the list).

Calibration targets from the case, asserted within 10% unless noted: before column readings 12,000, escalations 300, median 4h, overtime 180, satisfaction 41; last quarter readings 120,000, escalations 2,400, inbound 3,100, after-hours 0.46, median 31h, overtime 1,150, nurses 22 (±1), resignations in the last 13 weeks 3 (±1), inactive 340, satisfaction 72.

- [ ] **Step 1: Tests**

```python
# tests/test_sim.py
from northline.sim import model as m

CHECKIN = [{"name": "checkin_agent", "live_from_week": 1,
            "effects": {"engaged_weekly": 0.78, "escalation_rate": 0.06, "inbound_rate": 0.0775, "readings_per_response": 0.89}}]


def close(a, b, tol=0.10):
    return abs(a - b) <= tol * b


def test_before_column():
    _, r = m.step(m.State(0, 40000, 25, 0.0, 0), m.params_for(0, []))
    assert close(r["readings_per_month"], 12000) and close(r["escalations_per_week"], 300)
    assert r["nurse_response_median_h"] == 4.0 and close(r["overtime_hours_per_month"], 180, 0.2) and close(r["satisfaction"], 41, 0.05)


def test_last_quarter_column():
    rows = m.run(range(1, 40), CHECKIN)
    lq = m.average(rows[26:])
    assert close(lq["readings_per_month"], 120000) and close(lq["escalations_per_week"], 2400)
    assert close(lq["inbound_per_week"], 3100) and lq["after_hours_share"] == 0.46
    assert close(lq["nurse_response_median_h"], 31) and close(lq["overtime_hours_per_month"], 1150)
    assert 21 <= rows[-1]["nurses"] <= 23 and 2 <= lq["resignations"] <= 4
    assert close(lq["inactive_after_escalation"], 340, 0.15) and close(lq["satisfaction"], 72, 0.05)


def test_triage_effects_lower_response_time():
    hist = m.run(range(1, 40), CHECKIN)
    start = m.State(39, 40000, hist[-1]["nurses"], 0.0, 0)
    triage = CHECKIN + [{"name": "triage", "live_from_week": 40,
                         "effects": {"inbound_to_nurse_share": 0.25, "routine_time_factor": 0.6, "urgent_recall": 0.8}}]
    with_t = m.average(m.run(range(40, 53), triage, start=start))
    without = m.average(m.run(range(40, 53), CHECKIN, start=start))
    assert with_t["nurse_response_median_h"] < without["nurse_response_median_h"] / 2
    assert with_t["missed_urgent_per_week"] > 0 and without["missed_urgent_per_week"] == 0


def test_prairie_projection_without_triage_is_worse():
    hist = m.run(range(1, 40), CHECKIN)
    start = m.State(39, 40000, hist[-1]["nurses"], 0.0, 0)
    p = m.average(m.run(range(40, 53), CHECKIN, start=start, patients=100000))
    assert p["nurse_response_median_h"] > 60
```

- [ ] **Step 2: model.py**

```python
# northline/sim/model.py
"""A weekly model of Northline Care. Small enough to read, calibrated to the case's two columns.

Deployments override parameters. That is the whole mechanism: deploy an agent, the company changes.
"""
import math
from dataclasses import dataclass, replace

BASE = {
    "nurse_capacity_items_per_week": 150, "hours_per_item": 0.28, "nurse_cost_month": 9000, "overtime_rate": 45, "fee": 25,
    "monthly_reach": 0.60, "readings_per_reach": 0.5,          # before: 40000 * 0.6 * 0.5 = 12,000 readings a month
    "engaged_weekly": 0.0, "readings_per_response": 0.89,      # agent: 40000 * 0.78 * 4.33 * 0.89 = 120,000
    "escalation_rate": 0.0075, "inbound_rate": 0.0, "after_hours_share": 0.46,
    "urgent_share_of_escalations": 0.15, "inbound_to_nurse_share": 0.60, "routine_time_factor": 1.0,
    "urgent_recall": 1.0, "response_curve": 4.2, "resignation_rate": 0.016, "disengage_rate": 0.021,
}


@dataclass(frozen=True)
class State:
    week: int
    patients: int
    nurses: int
    resign_accum: float
    inactive_total: int


def params_for(week: int, deployments: list[dict]) -> dict:
    p = dict(BASE)
    for d in deployments:
        if d.get("live_from_week", 1) <= week:
            p.update(d.get("effects", {}))
    return p


def step(s: State, p: dict) -> tuple[State, dict]:
    P, N = s.patients, s.nurses
    if p["engaged_weekly"] > 0:
        readings = P * p["engaged_weekly"] * 4.33 * p["readings_per_response"]
    else:
        readings = P * p["monthly_reach"] * p["readings_per_reach"]
    esc = P * p["escalation_rate"]
    inbound = P * p["inbound_rate"]
    urgent = esc * p["urgent_share_of_escalations"]
    items = urgent + (esc - urgent) * p["routine_time_factor"] + inbound * p["inbound_to_nurse_share"]
    capacity = N * p["nurse_capacity_items_per_week"]
    load = items / capacity if capacity else 99.0
    median_h = round(4.0 * math.exp(p["response_curve"] * max(0.0, load - 0.8)), 1)
    urgent_h = 4.0 if p["routine_time_factor"] < 1.0 else median_h   # a triage layer sees urgent items first
    overtime = max(0.0, items - capacity) * p["hours_per_item"] * 4.33
    accum = s.resign_accum + N * p["resignation_rate"] * max(0.0, load - 1.0)
    resigned = int(accum); accum -= resigned
    unanswered_share = min(0.9, max(0.0, (median_h - 4.0) / (median_h + 20.0)))
    inactive_new = int(round(esc * unanswered_share * p["disengage_rate"]))
    missed_urgent = urgent * (1.0 - p["urgent_recall"])
    satisfaction = round(41 + 36 * (1 if p["engaged_weekly"] > 0 else 0) - 9 * min(1.0, (median_h - 4.0) / 48.0), 1)
    row = {"week": s.week, "patients": P, "nurses": N, "readings_per_month": round(readings), "escalations_per_week": round(esc),
           "inbound_per_week": round(inbound), "after_hours_share": p["after_hours_share"] if inbound else 0.0,
           "nurse_items_per_week": round(items), "load": round(load, 3), "nurse_response_median_h": median_h,
           "urgent_response_h": urgent_h, "overtime_hours_per_month": round(overtime), "resignations": resigned,
           "inactive_after_escalation": inactive_new, "missed_urgent_per_week": round(missed_urgent, 1),
           "satisfaction": satisfaction, "revenue_month": P * p["fee"],
           "nurse_cost_month": round(N * p["nurse_cost_month"] + overtime * p["overtime_rate"])}
    return State(s.week + 1, P, N - resigned, accum, s.inactive_total + inactive_new), row


def run(weeks: range, deployments: list[dict], start: State | None = None, patients: int | None = None) -> list[dict]:
    s = start or State(weeks.start, 40000, 25, 0.0, 0)
    s = replace(s, week=weeks.start, patients=patients or s.patients)
    rows = []
    for w in weeks:
        s, row = step(s, params_for(w, deployments)); rows.append(row)
    return rows


SUMMED = {"resignations", "inactive_after_escalation"}


def average(rows: list[dict]) -> dict:
    out = {}
    for k in rows[0]:
        vals = [r[k] for r in rows]
        out[k] = sum(vals) if k in SUMMED else round(sum(vals) / len(vals), 2)
    out["week"] = rows[-1]["week"]
    return out
```

If a calibration assertion fails by a small margin, adjust the single named constant that drives it (`readings_per_response`, `hours_per_item`, `resignation_rate`, `disengage_rate`, `response_curve`) and re-run; do not loosen the test tolerances.

- [ ] **Step 3: run.py**

```python
# northline/sim/run.py
"""Run the model for every scenario the dashboard shows and write sim/out/*.json."""
import json
from pathlib import Path
from northline.tools import store
from . import model as m

OUT = Path(__file__).resolve().parent / "out"


def main() -> dict:
    deps = store.load("deployments")
    checkin = [d for d in deps if d["name"] == "checkin_agent"]
    history = m.run(range(1, 40), checkin)
    start = m.State(39, 40000, history[-1]["nurses"], 0.0, 0)
    nxt = m.run(range(40, 53), deps, start=start)
    prairie = m.run(range(40, 53), deps, start=start, patients=100000)
    prairie_wo = m.run(range(40, 53), checkin, start=start, patients=100000)
    _, before = m.step(m.State(0, 40000, 25, 0.0, 0), m.params_for(0, []))
    last_q, next_q = m.average(history[26:]), m.average(nxt)
    new_live = any(d["name"] != "checkin_agent" for d in deps)
    summary = {"before": before, "last_quarter": last_q, "next_quarter": next_q, "prairie": m.average(prairie),
               "prairie_without": m.average(prairie_wo), "now": next_q if new_live else last_q, "deployments": deps}
    OUT.mkdir(exist_ok=True)
    (OUT / "weekly.json").write_text(json.dumps({"history": history, "next_quarter": nxt, "prairie": prairie, "prairie_without": prairie_wo}))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    s = main()
    print(f"last quarter: median {s['last_quarter']['nurse_response_median_h']}h, nurses {s['last_quarter']['nurses']}, "
          f"overtime {s['last_quarter']['overtime_hours_per_month']}h; prairie without new deployments: {s['prairie_without']['nurse_response_median_h']}h")
```

- [ ] **Step 4: Run** `uv run pytest tests/test_sim.py -q && uv run python -m northline.sim.run` → 4 passed and a line with median near 31h. Then `uv run pytest -q` (plan tools now read the summary; values must still match). Commit the `sim/out/*.json` files. **Commit** `git add -A && git commit -m "Add the weekly company model calibrated to the case"`

### Task 12: Dashboard

**Files:** `northline/agent/static/dashboard.html`, `tests/test_dashboard_api.py`
- Modify: `northline/agent/server.py` to add `GET /dashboard` (serves the file), `GET /api/sim` (returns `sim/out/summary.json` plus `weekly.json` under one object, running `sim.run.main()` first if `summary.json` is missing), and `GET /api/live` (counts from `log_dir()`: transcripts, escalations in `queue.jsonl`, unanswered escalations, tool calls).

**Interfaces:** `/api/sim` -> `{"summary": {...}, "weekly": {...}}`. `/api/live` -> `{"transcripts": int, "escalations": int, "unanswered": int, "tool_calls": int}`.

Before writing the page, load the `dataviz` skill and follow its procedure. The decisions it leads to for this page:
- **Forms.** The Exhibit B block is a table, not charts: rows are the metrics, columns are Before, Last quarter, Next quarter, and the two Prairie projections. Cells whose Next quarter value is better than Last quarter get a small up or down glyph plus the word "better" or "worse", never colour alone. The time series are four separate single-series line charts (escalations per week, nurse response median hours, overtime hours, patients inactive), weeks 1 to 52, with a vertical rule and label at each deployment's `live_from_week`. The Prairie block is one line chart with two series, with and without new deployments, legend present and both lines direct-labelled at the right end. No dual axes anywhere.
- **Colour.** Use the reference palette from the skill's `references/palette.md`: one sequential hue for single-series charts, the first two categorical hues for the Prairie pair, status colours only for the "urgent cases missed" tile, which also carries an icon and a label. Run `node <skill dir>/scripts/validate_palette.js` on the pair in light and dark mode and record the pass in a comment at the top of the file.
- **Marks and hover.** 2px lines, 8px markers on hover only, crosshair tooltip on each line chart showing week and value, a 2px surface gap where the deployment rule crosses a line.
- **Layout.** Header "Northline Care, operations" with the current week and a "Deployments live" list. A "Sign Prairie" toggle switches the Prairie block on. A "Live in this room" strip with the four counts from `/api/live`. The page polls `/api/sim` every ten seconds and redraws when the JSON changes. Dark mode via `prefers-color-scheme` with colours redefined for the dark surface. No external scripts or fonts. Under 400 lines.

- [ ] **Step 1: Test the API**

```python
# tests/test_dashboard_api.py
import json
from fastapi.testclient import TestClient
from northline.agent import server


def test_api_sim_and_dashboard(log_dir, data_dir):
    c = TestClient(server.app)
    d = c.get("/api/sim").json()
    assert "last_quarter" in d["summary"] and len(d["weekly"]["history"]) == 39
    assert c.get("/dashboard").status_code == 200


def test_api_live_counts(log_dir, data_dir):
    (log_dir / "queue.jsonl").write_text(json.dumps({"id": "esc-1", "answered_at": None}) + "\n" + json.dumps({"id": "esc-2", "answered_at": "x"}) + "\n")
    d = TestClient(server.app).get("/api/live").json()
    assert d["escalations"] == 2 and d["unanswered"] == 1 and d["transcripts"] == 0
```

- [ ] **Step 2: Server additions**

```python
# add to northline/agent/server.py
import json
from fastapi.responses import JSONResponse
from northline.tools.calllog import log_dir
from northline.sim import run as sim_run

SIM_OUT = sim_run.OUT


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC / "dashboard.html")


@app.get("/api/sim")
def api_sim():
    if not (SIM_OUT / "summary.json").exists():
        sim_run.main()
    return JSONResponse({"summary": json.loads((SIM_OUT / "summary.json").read_text()),
                         "weekly": json.loads((SIM_OUT / "weekly.json").read_text())})


@app.get("/api/live")
def api_live():
    d = log_dir()
    q = [json.loads(l) for l in (d / "queue.jsonl").read_text().splitlines() if l.strip()] if (d / "queue.jsonl").exists() else []
    calls = sum(1 for l in (d / "tool_calls.jsonl").read_text().splitlines() if l.strip()) if (d / "tool_calls.jsonl").exists() else 0
    return {"transcripts": len(list((d / "transcripts").glob("*.json"))) if (d / "transcripts").exists() else 0,
            "escalations": len(q), "unanswered": sum(1 for r in q if r.get("answered_at") is None), "tool_calls": calls}
```

- [ ] **Step 3: Write dashboard.html** to the decisions above.

- [ ] **Step 4: Run** `uv run pytest -q` → all pass. Start the server, open `/dashboard`, check: the table shows Before and Last quarter matching the case within 10%; four line charts render with a "checkin_agent" rule at week 1; toggling Sign Prairie shows the two-line chart; the live strip shows the counts from the smoke test in Task 10. Take a screenshot for the slides later. **Commit** `git add -A && git commit -m "Add the operations dashboard and its API"`

**Phase 3 checkpoint:** the dashboard shows the company from the model, and any change to `deployments.json` followed by a sim run changes it.

---

## Phase 4: The PM loop

### Task 13: Structured calls through headless Claude Code

**Files:** `northline/pm/__init__.py`, `northline/pm/claude_json.py`, `tests/test_claude_json.py`

**Interfaces:** `ask_json(prompt, schema, *, model="haiku", runner=subprocess.run, cwd=REPO_ROOT) -> dict` runs `claude -p <prompt> --output-format json --json-schema <schema> --tools "" --strict-mcp-config --no-session-persistence --model <model>` and returns `structured_output`; raises `RuntimeError` on `is_error` or missing output. `ask_json_many(jobs: list[tuple[str, dict]], *, workers=4, **kw) -> list[dict]` in order.

- [ ] **Step 1: Tests**

```python
# tests/test_claude_json.py
import json, pytest
from types import SimpleNamespace
from northline.pm import claude_json as cj
S = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}


def test_ask_json():
    def fake(cmd, **kw):
        assert "--json-schema" in cmd and cmd[cmd.index("--tools") + 1] == ""
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": 3}}), returncode=0, stderr="")
    assert cj.ask_json("p", S, runner=fake) == {"x": 3}


def test_ask_json_error():
    def fake(cmd, **kw):
        return SimpleNamespace(stdout=json.dumps({"is_error": True, "result": "rate limited"}), returncode=0, stderr="")
    with pytest.raises(RuntimeError, match="rate limited"):
        cj.ask_json("p", S, runner=fake)


def test_many_in_order():
    def fake(cmd, **kw):
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": int(cmd[2])}}), returncode=0, stderr="")
    assert [o["x"] for o in cj.ask_json_many([(str(i), S) for i in range(6)], workers=3, runner=fake)] == list(range(6))
```

- [ ] **Step 2: Implementation**

```python
# northline/pm/claude_json.py
"""LLM judgment as a function call, through headless Claude Code. No API key, no SDK."""
import json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]


def ask_json(prompt: str, schema: dict, *, model: str = "haiku", runner=subprocess.run, cwd: Path = REPO_ROOT) -> dict:
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(schema),
           "--tools", "", "--strict-mcp-config", "--no-session-persistence", "--model", model]
    proc = runner(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)
    if not proc.stdout.strip():
        raise RuntimeError(f"claude produced no output: {getattr(proc, 'stderr', '')}")
    d = json.loads(proc.stdout)
    if d.get("is_error") or d.get("structured_output") is None:
        raise RuntimeError(f"claude failed: {d.get('result') or d.get('subtype')}")
    return d["structured_output"]


def ask_json_many(jobs, *, workers: int = 4, **kw) -> list[dict]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda j: ask_json(j[0], j[1], **kw), jobs))
```

- [ ] **Step 3: Run** `uv run pytest tests/test_claude_json.py -q` → 3 passed; then one real call: `uv run python -c "from northline.pm.claude_json import ask_json; print(ask_json('Is 184/112 a high blood pressure? boolean field high.', {'type':'object','properties':{'high':{'type':'boolean'}},'required':['high']}))"` → `{'high': True}`. **Commit** `git add -A && git commit -m "Add structured JSON calls through headless Claude Code"`

### Task 14: Taxonomy and classifier

**Files:** `northline/pm/taxonomy.md`, `northline/pm/classify.py`, `tests/test_classify.py`, `tests/fixtures/transcript.json`, `tests/fixtures/plan_session.jsonl`

**Interfaces:**
- `classify.load_items(corpus_dir, log_dir) -> list[dict]` items `{"id","persona","text"}`. Patient items from `corpus/patient/*.json` and `log_dir/transcripts/*.json` (id `live-<stem>`), text as `user:`/`assistant:` lines plus `tools used:`. Plan items from `corpus/plan/*.jsonl` and `log_dir/tool_calls.jsonl` grouped by session (id `live-<session>`), text one call per line `tool(args) -> status [error]`. The queue log is not classified; it is aggregated in Task 15.
- `classify.RECORD_SCHEMA`, `classify.BATCH_SCHEMA`. Record: `id, persona, intent, tier (urgent_clinical|non_urgent_clinical|non_clinical|none), outcome (resolved|partial|failed|escalated), tools_used, unmet_need (bool), unmet_need_description, proposed_tool, evidence_quote`.
- `classify.classify_items(items, *, batch_size=8, ask=claude_json.ask_json_many) -> list[dict]` copies `id` and `persona` from the item. `classify.main()` writes `pm/out/classified.jsonl`.

- [ ] **Step 1: taxonomy.md** (also the filled `templates/taxonomy.md`)

```markdown
# Northline conversation taxonomy

Classify each check-in conversation or plan tool-log session into one record.

- **intent**: what the user wanted, five words or fewer. Examples: weekly reading, refill request, insurance denial, diet question, device error, social contact, opt out, pull outcome evidence.
- **tier**: for patient conversations, the clinical tier of what they raised: `urgent_clinical` (chest pain, possible stroke, glucose under 70 or over 300, BP at or above 180/110, double dose with symptoms), `non_urgent_clinical` (routine readings, mild symptoms, stopped a medication, a wound, diet, refills), `non_clinical` (insurance, scheduling, logistics, device support, social contact, opt-out). Plan sessions are `none`.
- **outcome**: `resolved`, `partial`, `failed` (nothing useful and no handoff), `escalated` (handed to a nurse).
- **tools_used**: tool names that appear.
- **unmet_need**: true when the user asked for something no available tool could do, even if the assistant declined gracefully. A polite "I can't do that yet" is still an unmet need.
- **unmet_need_description**: one sentence.
- **proposed_tool**: snake_case, reused across conversations for the same need: `request_refill`, `insurance_question`, `pharmacy_logistics`, `diet_content`, `device_support`, `social_checkin`, `opt_out`, `lookup_member_by_phone`, `bulk_outcome_export`. Empty when none.
- **evidence_quote**: the single user line that best shows the need, verbatim.

Rules: a clinical question that was escalated is `escalated`, not an unmet need. Never propose a tool that would give clinical advice; if a patient wanted advice, set unmet_need true and proposed_tool empty so the count shows the demand without a tool.
```

- [ ] **Step 2: Fixtures**

`tests/fixtures/transcript.json`:
```json
{"session_id": "fx-1", "persona": "patient", "started": "2026-09-01T21:14:00+00:00",
 "messages": [{"role": "user", "content": "Pharmacy in Dickinson says my lisinopril refill needs a new script. Can someone call it in? I run out Thursday.", "ts": ""},
              {"role": "assistant", "content": "I can't request refills yet. I've noted it for a nurse.", "ts": ""}],
 "tool_uses": [{"name": "escalate_to_nurse", "input": {}, "result": "", "is_error": false}], "escalated": true, "cost_usd": 0.01}
```
`tests/fixtures/plan_session.jsonl`:
```
{"ts": "2026-09-01T10:00:00+00:00", "session_id": "fx-p1", "persona": "plan", "tool": "outcome_evidence", "args": {"plan_id": "plan-prairie", "metric": "bp_control"}, "status": "ok", "error": null}
{"ts": "2026-09-01T10:00:05+00:00", "session_id": "fx-p1", "persona": "plan", "tool": "enrollment_status", "args": {"member_id": "701-555-0101"}, "status": "not_found", "error": "no member 701-555-0101"}
```

- [ ] **Step 3: Tests**

```python
# tests/test_classify.py
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
```

- [ ] **Step 4: classify.py**

```python
# northline/pm/classify.py
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


def classify_items(items, *, batch_size=8, ask=claude_json.ask_json_many) -> list[dict]:
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    outs = ask([(_prompt(b), BATCH_SCHEMA) for b in batches])
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
```

- [ ] **Step 5: Run** `uv run pytest tests/test_classify.py -q` → 2 passed. **Commit** `git add -A && git commit -m "Add the taxonomy and classifier"`

### Task 15: Aggregation with queue metrics

**Files:** `northline/pm/aggregate.py`, `tests/test_aggregate.py`, `tests/fixtures/classified.jsonl`, `tests/fixtures/queue.jsonl`

**Interfaces:**
- `aggregate.load_queue(corpus_dir, log_dir) -> list[dict]` concatenates `corpus/queue.jsonl` and `log_dir/queue.jsonl`.
- `aggregate.queue_metrics(rows, weeks: float = 13.0) -> dict`: `escalations_per_week` (len/weeks), `answered_share`, `nurse_response_median_h` and `nurse_response_p90_h` over answered rows (hours between `created_at` and `answered_at`), `after_hours_share` (created between 18:00 and 07:59 local-as-given, or Saturday/Sunday), `non_clinical_share_of_queue` (rows whose `tier` is `non_clinical`), `unanswered_over_24h` (unanswered rows older than 24h relative to the newest `created_at`), `patients_inactive_after_escalation` (distinct `patient_id` among unanswered rows), `urgent_median_h` over rows with `urgency == "urgent"`.
- `aggregate.candidates(records) -> list[dict]` grouped by `(persona, proposed_tool)` for records with `unmet_need` and a tool: `count, share` (of that persona's records), `quotes` (max 3), `nearest_tools` (top 2 `tools_used`), `description`, `tier_mix` (Counter of tiers as dict). Sorted by count desc.
- `aggregate.report(records, cands, qm, summary: dict | None) -> str` markdown: an Exhibit B style table with columns Board deck (from `summary["last_quarter"]` if given, else the case constants) and From logs (from `qm` and records); an outcome table per persona; a tier mix of what reaches the nurse queue; the candidate table; and a closing line "Unanswered escalations: <n>, from <m> patients."
- `aggregate.main()` reads `out/classified.jsonl`, the queue, and `sim/out/summary.json` if present; writes `out/report.md`, `out/candidates.json`, `out/queue_metrics.json`.

- [ ] **Step 1: Fixtures.** `tests/fixtures/queue.jsonl`, eight rows, all with `created_at` in the week of 2026-09-07, chosen so: median answered response is 30h exactly (answered deltas 6h, 20h, 30h, 30h, 48h, 70h), two unanswered rows from two patients older than 24h, three rows after hours (one at 21:14, one at 01:48, one on Sunday 14:00), three rows `tier: "non_clinical"`, one row `urgency: "urgent"` answered in 40h. `tests/fixtures/classified.jsonl`, six lines like the earlier MediBridge fixture but with Northline fields: two `request_refill` (patient, quotes "Can someone call it in?" and "I run out Thursday"), one `insurance_question`, one escalated urgent, one resolved weekly reading, one plan record with `lookup_member_by_phone`.

- [ ] **Step 2: Tests**

```python
# tests/test_aggregate.py
import json
from pathlib import Path
from northline.pm import aggregate as ag
FX = Path(__file__).parent / "fixtures"
RECS = [json.loads(l) for l in (FX / "classified.jsonl").read_text().splitlines()]
Q = [json.loads(l) for l in (FX / "queue.jsonl").read_text().splitlines()]


def test_queue_metrics():
    m = ag.queue_metrics(Q, weeks=1.0)
    assert m["escalations_per_week"] == 8 and m["nurse_response_median_h"] == 30.0
    assert m["after_hours_share"] == 0.38 and m["non_clinical_share_of_queue"] == 0.38
    assert m["unanswered_over_24h"] == 2 and m["patients_inactive_after_escalation"] == 2 and m["urgent_median_h"] == 40.0


def test_candidates():
    c = ag.candidates(RECS)
    assert c[0]["proposed_tool"] == "request_refill" and c[0]["count"] == 2 and c[0]["share"] == 0.4
    assert c[0]["quotes"] == ["Can someone call it in?", "I run out Thursday"]


def test_report_mentions_both_columns():
    r = ag.report(RECS, ag.candidates(RECS), ag.queue_metrics(Q, weeks=1.0), None)
    assert "Board deck" in r and "From logs" in r and "request_refill" in r and "Unanswered escalations: 2, from 2 patients." in r
```

- [ ] **Step 3: aggregate.py**

```python
# northline/pm/aggregate.py
"""Step 3 of the loop: arithmetic only. Unmet needs from the records, the bottleneck from the queue timestamps."""
import json, statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT = HERE / "out"
CASE = {"escalations_per_week": 2400, "nurse_response_median_h": 31, "after_hours_share": 0.46,
        "inbound_per_week": 3100, "overtime_hours_per_month": 1150, "inactive_after_escalation": 340}


def _dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_queue(corpus_dir: Path, log_dir: Path) -> list[dict]:
    rows = []
    for p in (corpus_dir / "queue.jsonl", log_dir / "queue.jsonl"):
        if p.exists():
            rows += [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return rows


def queue_metrics(rows: list[dict], weeks: float = 13.0) -> dict:
    if not rows:
        return {k: 0 for k in ("escalations_per_week", "answered_share", "nurse_response_median_h", "nurse_response_p90_h",
                               "after_hours_share", "non_clinical_share_of_queue", "unanswered_over_24h",
                               "patients_inactive_after_escalation", "urgent_median_h")}
    answered = [(_dt(r["answered_at"]) - _dt(r["created_at"])).total_seconds() / 3600 for r in rows if r.get("answered_at")]
    urgent = [(_dt(r["answered_at"]) - _dt(r["created_at"])).total_seconds() / 3600 for r in rows if r.get("answered_at") and r.get("urgency") == "urgent"]
    newest = max(_dt(r["created_at"]) for r in rows)
    unanswered = [r for r in rows if not r.get("answered_at") and (newest - _dt(r["created_at"])).total_seconds() > 86400]
    after = [r for r in rows if _dt(r["created_at"]).weekday() >= 5 or not 8 <= _dt(r["created_at"]).hour < 18]
    p90 = sorted(answered)[int(0.9 * (len(answered) - 1))] if answered else 0
    return {"escalations_per_week": round(len(rows) / weeks), "answered_share": round(len(answered) / len(rows), 2),
            "nurse_response_median_h": round(statistics.median(answered), 1) if answered else 0, "nurse_response_p90_h": round(p90, 1),
            "after_hours_share": round(len(after) / len(rows), 2),
            "non_clinical_share_of_queue": round(sum(1 for r in rows if r.get("tier") == "non_clinical") / len(rows), 2),
            "unanswered_over_24h": len(unanswered), "patients_inactive_after_escalation": len({r["patient_id"] for r in unanswered}),
            "urgent_median_h": round(statistics.median(urgent), 1) if urgent else 0}


def candidates(records: list[dict]) -> list[dict]:
    totals = Counter(r["persona"] for r in records)
    groups = defaultdict(list)
    for r in records:
        if r.get("unmet_need") and r.get("proposed_tool"):
            groups[(r["persona"], r["proposed_tool"])].append(r)
    out = []
    for (persona, tool), rs in groups.items():
        near = Counter(t for r in rs for t in r.get("tools_used", []))
        desc = Counter(r["unmet_need_description"] for r in rs if r.get("unmet_need_description"))
        out.append({"persona": persona, "proposed_tool": tool, "count": len(rs), "share": round(len(rs) / totals[persona], 2),
                    "quotes": [r["evidence_quote"] for r in rs if r.get("evidence_quote")][:3],
                    "nearest_tools": [t for t, _ in near.most_common(2)], "description": desc.most_common(1)[0][0] if desc else "",
                    "tier_mix": dict(Counter(r.get("tier", "none") for r in rs))})
    return sorted(out, key=lambda c: (-c["count"], c["proposed_tool"]))


def report(records, cands, qm, summary) -> str:
    board = {**CASE, **(summary or {}).get("last_quarter", {})} if summary else CASE
    L = ["# Northline PM loop report", "", f"{len(records)} conversations and sessions classified; {qm['escalations_per_week']} escalations a week in the queue log.", "",
         "## The board's numbers next to the logs", "", "| metric | Board deck | From logs |", "|---|---|---|",
         f"| Escalations per week | {board['escalations_per_week']} | {qm['escalations_per_week']} |",
         f"| Median nurse response (h) | {board['nurse_response_median_h']} | {qm['nurse_response_median_h']} (p90 {qm['nurse_response_p90_h']}) |",
         f"| Urgent escalations, median response (h) | not reported | {qm['urgent_median_h']} |",
         f"| After-hours share | {board['after_hours_share']} | {qm['after_hours_share']} |",
         f"| Non-clinical share of the nurse queue | not reported | {qm['non_clinical_share_of_queue']} |",
         f"| Patients inactive after an escalation | {board['inactive_after_escalation']} | {qm['patients_inactive_after_escalation']} |", ""]
    for persona in ("patient", "plan"):
        rs = [r for r in records if r["persona"] == persona]
        if rs:
            c = Counter(r["outcome"] for r in rs)
            L += [f"## Outcomes, {persona}", "", "| resolved | partial | failed | escalated |", "|---|---|---|---|",
                  f"| {c['resolved']} | {c['partial']} | {c['failed']} | {c['escalated']} |", ""]
    tiers = Counter(r["tier"] for r in records if r["persona"] == "patient")
    L += ["## What patients raise, by tier", "", "| urgent clinical | non-urgent clinical | non-clinical |", "|---|---|---|",
          f"| {tiers['urgent_clinical']} | {tiers['non_urgent_clinical']} | {tiers['non_clinical']} |", "",
          "## Candidate expansions", "", "| tool | persona | count | share | nearest existing | example |", "|---|---|---|---|---|---|"]
    for c in cands:
        L.append(f"| `{c['proposed_tool']}` | {c['persona']} | {c['count']} | {int(c['share'] * 100)}% | {', '.join(c['nearest_tools']) or '-'} | {(c['quotes'] or [c['description']])[0]} |")
    L += ["", f"Unanswered escalations: {qm['unanswered_over_24h']}, from {qm['patients_inactive_after_escalation']} patients.", ""]
    return "\n".join(L)


def main() -> None:
    records = [json.loads(l) for l in (OUT / "classified.jsonl").read_text().splitlines() if l.strip()]
    qm = queue_metrics(load_queue(REPO_ROOT / "corpus", REPO_ROOT / "northline" / "logs"))
    sp = REPO_ROOT / "northline" / "sim" / "out" / "summary.json"
    summary = json.loads(sp.read_text()) if sp.exists() else None
    cands = candidates(records)
    (OUT / "report.md").write_text(report(records, cands, qm, summary))
    (OUT / "candidates.json").write_text(json.dumps(cands, indent=2))
    (OUT / "queue_metrics.json").write_text(json.dumps(qm, indent=2))
    print(f"{len(cands)} candidates; median response {qm['nurse_response_median_h']}h -> {OUT / 'report.md'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run** `uv run pytest tests/test_aggregate.py -q` → 3 passed. **Commit** `git add -A && git commit -m "Add aggregation with queue metrics and the two-column report"`

### Task 16: Diagnosis and proposals of two kinds

**Files:** `northline/pm/diagnose.py`, `northline/pm/propose.py`, `templates/expansion-proposal.md`, `templates/deployment-proposal.md`, `tests/test_propose.py`

**Interfaces:**
- `diagnose.DIAG_SCHEMA` `{headline: str, what_the_board_sees: str, what_the_logs_show: str, the_bottleneck: str, why_signing_prairie_makes_it_worse: str, the_one_metric_to_watch: str}`. `diagnose.prompt(report_md, qm, summary) -> str`. `diagnose.main(ask=claude_json.ask_json)` writes `out/diagnosis.md` with those six sections as headers, model `sonnet`.
- `propose.PROPOSAL_SCHEMA` for tools: `tool_name, description, input_schema (object), backend_needed, safety_notes, personas (list)`. `propose.DEPLOY_SCHEMA` for agents: `agent_name, placement, purpose, tools_needed (list), decisions_for_humans (list of str), acceptance_test, metrics_it_should_move (list), risks`.
- `propose.render_tool(cand, out) -> str` fills `templates/expansion-proposal.md` by `{placeholder}` substitution. `propose.render_deploy(qm, out) -> str` fills `templates/deployment-proposal.md`.
- `propose.main(top=4, ask=claude_json.ask_json_many)` writes `out/proposals/tool-<name>.md` for the top candidates and always `out/proposals/agent-triage.md`, which is rendered from the queue metrics whether or not any candidate mentions triage; the triage proposal's `decisions_for_humans` must be exactly the four from the spec, so `propose.py` supplies them verbatim rather than asking the model.

- [ ] **Step 1: Templates**

`templates/expansion-proposal.md`:
```markdown
# Expansion proposal: `{tool_name}`

**Kind:** tool  **Persona(s):** {personas}  **Evidence:** {count} conversations ({share}% of {persona} conversations)

## What users asked for
{description}

Example quotes:
{quotes}

## Proposed tool
**Docstring (what the model reads):** {tool_description}

**Input schema:**
```json
{input_schema}
```

**Nearest existing tool(s):** {nearest_tools}

## What the backend needs
{backend_needed}

## Safety notes
{safety_notes}

## Decision
- [ ] Approve: `/expand {file_stem}`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
```

`templates/deployment-proposal.md`:
```markdown
# Deployment proposal: `{agent_name}`

**Kind:** agent  **Placement:** {placement}

## Why
{purpose}

Evidence from the queue log: {escalations_per_week} escalations a week, median nurse response {median_h} hours (p90 {p90_h}), {non_clinical_pct}% of the nurse queue is non-clinical, {unanswered} escalations unanswered over 24 hours from {inactive} patients.

## Tools it needs
{tools_needed}

## Decisions a human must make before it goes live
{decisions}

## Acceptance test
{acceptance_test}

## Metrics it should move
{metrics}

## Risks
{risks}

## Decision
- [ ] Approve: `/deploy {agent_name}`
- [ ] Reject, reason:
```

- [ ] **Step 2: Test**

```python
# tests/test_propose.py
from northline.pm import propose as pr

CAND = {"persona": "patient", "proposed_tool": "request_refill", "count": 14, "share": 0.12, "quotes": ["Can someone call it in?"],
        "nearest_tools": ["escalate_to_nurse"], "description": "Refill needs a new script", "tier_mix": {"non_urgent_clinical": 14}}
OUT = {"tool_name": "request_refill", "description": "Request a prescription refill.", "input_schema": {"type": "object"},
       "backend_needed": "e-prescribing", "safety_notes": "Nurse approves.", "personas": ["patient"]}
QM = {"escalations_per_week": 2400, "nurse_response_median_h": 31.0, "nurse_response_p90_h": 70.0, "non_clinical_share_of_queue": 0.41,
      "unanswered_over_24h": 300, "patients_inactive_after_escalation": 280}


def test_render_tool():
    t = pr.render_tool(CAND, OUT)
    assert "`request_refill`" in t and "12%" in t and "/expand tool-request_refill" in t and "{" not in t.split("```json")[0]


def test_render_deploy_has_four_decisions():
    t = pr.render_deploy(QM, {"agent_name": "triage", "placement": "between escalation and the nurse queue", "purpose": "p",
                              "tools_needed": ["pending_messages"], "decisions_for_humans": [], "acceptance_test": "Exhibit E",
                              "metrics_it_should_move": ["median response"], "risks": "downgrading"})
    assert t.count("\n1. ") == 1 and "4. " in t and "Urgent thresholds" in t and "/deploy triage" in t and "41%" in t
```

- [ ] **Step 3: diagnose.py**

```python
# northline/pm/diagnose.py
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
```

- [ ] **Step 4: propose.py**

```python
# northline/pm/propose.py
"""Step 5 of the loop: draft specs. Tools for unmet needs; an agent deployment for the queue. Humans approve."""
import json
from pathlib import Path
from . import claude_json

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT = HERE / "out"
T = REPO_ROOT / "templates"
PROPOSAL_SCHEMA = {"type": "object", "properties": {"tool_name": {"type": "string"}, "description": {"type": "string"},
                   "input_schema": {"type": "object"}, "backend_needed": {"type": "string"}, "safety_notes": {"type": "string"},
                   "personas": {"type": "array", "items": {"type": "string"}}},
                   "required": ["tool_name", "description", "input_schema", "backend_needed", "safety_notes", "personas"]}
DEPLOY_SCHEMA = {"type": "object", "properties": {"agent_name": {"type": "string"}, "placement": {"type": "string"}, "purpose": {"type": "string"},
                 "tools_needed": {"type": "array", "items": {"type": "string"}}, "decisions_for_humans": {"type": "array", "items": {"type": "string"}},
                 "acceptance_test": {"type": "string"}, "metrics_it_should_move": {"type": "array", "items": {"type": "string"}}, "risks": {"type": "string"}},
                 "required": ["agent_name", "placement", "purpose", "tools_needed", "decisions_for_humans", "acceptance_test", "metrics_it_should_move", "risks"]}
TRIAGE_DECISIONS = [
    "Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.",
    "Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.",
    "After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.",
    "Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.",
]


def _fill(template: str, fill: dict) -> str:
    for k, v in fill.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def render_tool(c: dict, o: dict) -> str:
    stem = f"tool-{c['proposed_tool']}"
    return _fill((T / "expansion-proposal.md").read_text(), {
        "tool_name": o["tool_name"], "personas": ", ".join(o["personas"]), "count": c["count"], "share": int(c["share"] * 100),
        "persona": c["persona"], "description": c["description"], "quotes": "\n".join(f'- "{q}"' for q in c["quotes"]) or "- (none)",
        "tool_description": o["description"], "input_schema": json.dumps(o["input_schema"], indent=2),
        "nearest_tools": ", ".join(c["nearest_tools"]) or "-", "backend_needed": o["backend_needed"], "safety_notes": o["safety_notes"], "file_stem": stem})


def render_deploy(qm: dict, o: dict) -> str:
    decisions = TRIAGE_DECISIONS if o["agent_name"] == "triage" else o["decisions_for_humans"]
    return _fill((T / "deployment-proposal.md").read_text(), {
        "agent_name": o["agent_name"], "placement": o["placement"], "purpose": o["purpose"],
        "escalations_per_week": qm["escalations_per_week"], "median_h": qm["nurse_response_median_h"], "p90_h": qm["nurse_response_p90_h"],
        "non_clinical_pct": int(qm["non_clinical_share_of_queue"] * 100), "unanswered": qm["unanswered_over_24h"], "inactive": qm["patients_inactive_after_escalation"],
        "tools_needed": "\n".join(f"- `{t}`" for t in o["tools_needed"]), "decisions": "\n".join(f"{i + 1}. {d}" for i, d in enumerate(decisions)),
        "acceptance_test": o["acceptance_test"], "metrics": "\n".join(f"- {m}" for m in o["metrics_it_should_move"]), "risks": o["risks"]})


def _tool_prompt(c):
    return (f"You are the product manager at Northline Care, a rural chronic-care company with an SMS check-in agent. Patients asked {c['count']} times "
            f"for something no tool can do: {c['description']}. Quotes: {c['quotes']}. Nearest tools: {c['nearest_tools']}. Draft a tool named "
            f"{c['proposed_tool']}: a one-sentence docstring, a JSON input schema with snake_case fields including patient_id, the backend it needs, "
            f"and safety notes. Patients never receive clinical advice through a tool; if this request is clinical, design the tool to route to a nurse with the right context.")


def _deploy_prompt(qm):
    return (f"You are the product manager at Northline Care. The nurse queue shows {qm['escalations_per_week']} escalations a week, median response "
            f"{qm['nurse_response_median_h']}h, {int(qm['non_clinical_share_of_queue'] * 100)}% non-clinical items, {qm['unanswered_over_24h']} unanswered over 24h. "
            f"Draft a deployment proposal for an agent named triage that sits between the check-in agent's escalations and the nurse queue. It has tools "
            f"pending_messages, tier_message, route_message. Describe placement, purpose, the acceptance test (the fifteen night texts in Exhibit E scored against "
            f"a nurse's key), the metrics it should move, and the risks, especially downgrading an urgent case. Leave decisions_for_humans empty; they are fixed.")


def main(top: int = 4, ask=claude_json.ask_json_many) -> None:
    cands = json.loads((OUT / "candidates.json").read_text())[:top]
    qm = json.loads((OUT / "queue_metrics.json").read_text())
    outs = ask([(_tool_prompt(c), PROPOSAL_SCHEMA) for c in cands] + [(_deploy_prompt(qm), DEPLOY_SCHEMA)], model="sonnet")
    (OUT / "proposals").mkdir(exist_ok=True)
    for c, o in zip(cands, outs[:-1]):
        (OUT / "proposals" / f"tool-{c['proposed_tool']}.md").write_text(render_tool(c, o))
    d = outs[-1]; d["agent_name"] = "triage"
    (OUT / "proposals" / "agent-triage.md").write_text(render_deploy(qm, d))
    print(f"wrote {len(cands)} tool proposals and agent-triage.md")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run** `uv run pytest tests/test_propose.py -q` → 2 passed. **Commit** `git add -A && git commit -m "Add diagnosis and tool and deployment proposals"`

### Task 17: Corpus from the model, with Exhibit E seeded

**Files:** `northline/pm/generate_corpus.py`, `northline/agents/triage/exhibit_e.json`, `northline/agents/triage/nurse_key.json`, `tests/test_generate_corpus.py`, `corpus/patient/*.json`, `corpus/plan/*.jsonl`, `corpus/queue.jsonl`

**Interfaces:**
- `exhibit_e.json`: list of fifteen `{"n", "time", "text"}` copied verbatim from the case (9:14 pm to 7:05 am, texts 1 to 15). `nurse_key.json`: fifteen `{"n", "tier", "route", "note"}` from the answer key: tiers `non_urgent_clinical` for 1, 6, 7, 9, 13; `non_clinical` for 2, 3, 8, 11, 14, 15; `urgent_clinical` for 4, 5, 10, 12; routes `nurse_urgent` for urgent, `nurse_routine` for non-urgent clinical, `admin` for 2, 8, 11, 14, 15 and `nurse_routine` for 3 (social contact, daytime follow-up). Notes are the "why, and the trap" column, shortened, and the file carries `"draft": true, "note": "Illustrative, from the case document; a clinician should review before use."`.
- `generate_corpus.THEMES: list[tuple[str, int, str]]` (theme, weight, tier) with the case's night-text themes plus routine check-ins; `plan(n, seed) -> list[tuple[str, str]]`; `TRANSCRIPT_SCHEMA`; `PLAN_SCHEMA`; `transcript_prompt(theme, tier, idx)`; `plan_prompt(idx)`; `to_transcript(idx, theme, out) -> dict` (session id `corpus-p-<idx:03d>`, `started` a timestamp in the last quarter with hour drawn so 46% are after hours); `queue_rows(summary_last_quarter: dict, n: int, seed: int) -> list[dict]` producing `n` rows over 13 weeks with `created_at` hours drawn so 46% fall after hours, `tier` drawn 15% urgent, 45% non-urgent, 40% non-clinical, `urgency` `urgent` for urgent tier, `answered_at` = created + lognormal hours with median 31 and sigma 0.7 for 88% of rows and null for 12%, `patient_id` from a pool of 1,500 ids `pt-<n>`; `seed_exhibit_e(rows) -> None` appends fifteen queue rows whose `reason` is each Exhibit E text at its time on 2026-09-08/09, unanswered.
- `main(n_transcripts=120, n_plan=40, n_queue=2000, ask=...)`.

- [ ] **Step 1: Write exhibit_e.json and nurse_key.json** from the case text above, verbatim messages.

- [ ] **Step 2: Tests**

```python
# tests/test_generate_corpus.py
import json, statistics
from datetime import datetime
from northline.pm import generate_corpus as g


def test_plan_deterministic_and_has_refills():
    p = g.plan(60, seed=1)
    assert p == g.plan(60, seed=1) and sum("refill" in t for t, _ in p) >= 4 and sum(t == "routine weekly check-in" for t, _ in p) >= 15


def test_queue_rows_shape():
    rows = g.queue_rows({"escalations_per_week": 2400, "nurse_response_median_h": 31.0}, n=2000, seed=2)
    assert len(rows) == 2000 and all(r["id"].startswith("corpus-esc-") for r in rows)
    answered = [(datetime.fromisoformat(r["answered_at"]) - datetime.fromisoformat(r["created_at"])).total_seconds() / 3600 for r in rows if r["answered_at"]]
    assert 0.85 <= len(answered) / 2000 <= 0.91 and 26 <= statistics.median(answered) <= 36
    after = sum(1 for r in rows if datetime.fromisoformat(r["created_at"]).weekday() >= 5 or not 8 <= datetime.fromisoformat(r["created_at"]).hour < 18)
    assert 0.42 <= after / 2000 <= 0.50


def test_exhibit_files():
    e = json.loads(open("northline/agents/triage/exhibit_e.json").read()); k = json.loads(open("northline/agents/triage/nurse_key.json").read())
    assert len(e) == 15 and e[11]["text"].startswith("BP was 184/112") and len(k["key"]) == 15 and k["key"][11]["tier"] == "urgent_clinical"
```

- [ ] **Step 3: generate_corpus.py**

```python
# northline/pm/generate_corpus.py
"""Author the corpus once from the model's numbers, commit it. Attendees never run this."""
import json, math, random
from datetime import datetime, timedelta
from pathlib import Path
from . import claude_json

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "corpus"
TRIAGE = REPO_ROOT / "northline" / "agents" / "triage"
Q_START = datetime(2026, 6, 8, 0, 0)   # 13 weeks ending 2026-09-06

THEMES = [
    ("routine weekly check-in, reading logged, nothing else", 30, "non_urgent_clinical"),
    ("reading flagged high and escalated to a nurse", 12, "non_urgent_clinical"),
    ("urgent symptom (chest tightness, very high BP with headache, low glucose at night) escalated", 8, "urgent_clinical"),
    ("prescription refill needs a new script, pharmacy is far away", 12, "non_urgent_clinical"),
    ("insurance denied test strips or a claim question", 8, "non_clinical"),
    ("the long drive to the pharmacy or clinic, transport", 5, "non_clinical"),
    ("diet question, what to eat instead of bread", 6, "non_urgent_clinical"),
    ("blood pressure cuff shows ERR, device support", 5, "non_clinical"),
    ("lonely, just wanted to talk, nobody has been by since the snow", 5, "non_clinical"),
    ("stopped a medication because of side effects, asks not to tell the doctor", 4, "non_urgent_clinical"),
    ("wants to opt out, sends STOP after a slow reply", 4, "non_clinical"),
    ("asks how long a nurse will take to call back, frustrated after 30 hours", 6, "non_urgent_clinical"),
]
TRANSCRIPT_SCHEMA = {"type": "object", "properties": {
    "messages": {"type": "array", "items": {"type": "object", "properties": {"role": {"type": "string", "enum": ["user", "assistant"]}, "content": {"type": "string"}}, "required": ["role", "content"]}},
    "tools_used": {"type": "array", "items": {"type": "string"}}, "escalated": {"type": "boolean"}}, "required": ["messages", "tools_used", "escalated"]}
PLAN_SCHEMA = {"type": "object", "properties": {"calls": {"type": "array", "items": {"type": "object", "properties": {
    "tool": {"type": "string"}, "args": {"type": "object"}, "status": {"type": "string", "enum": ["ok", "not_found", "error"]}, "error": {"type": "string"}},
    "required": ["tool", "args", "status"]}}}, "required": ["calls"]}
TOOLS = ("Tools the agent has: log_reading, log_medication, escalate_to_nurse (returns 'median response time is currently 31 hours'), next_checkin. "
         "It cannot do refills, insurance, transport, diet advice, device support, or reply to loneliness beyond kindness; it says so plainly.")


def plan(n: int, seed: int) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    pool = [(t, tier) for t, w, tier in THEMES for _ in range(w)]
    return [rng.choice(pool) for _ in range(n)]


def _hour(rng: random.Random) -> int:
    return rng.choice([21, 22, 23, 0, 1, 5, 6, 7, 19, 20]) if rng.random() < 0.46 else rng.randint(8, 17)


def _stamp(rng: random.Random) -> datetime:
    return Q_START + timedelta(days=rng.randint(0, 90), hours=_hour(rng), minutes=rng.randint(0, 59))


def transcript_prompt(theme: str, tier: str, idx: int) -> str:
    return (f"Write a realistic SMS conversation, 4 to 8 short texts, between a patient in rural North Dakota with hypertension or type 2 diabetes "
            f"and Northline Care's weekly check-in agent. Situation: {theme}. {TOOLS} The agent never gives clinical advice, escalates anything clinical, "
            f"and says plainly what it cannot do. Patient id pt-{1000 + idx % 8 + 1}. Vary tone and wording; conversation number {idx}. "
            f"tools_used lists the tools the agent would call; escalated is true if escalate_to_nurse is among them.")


def plan_prompt(idx: int) -> str:
    return (f"Write the tool-call log of a health-plan analyst using Northline's MCP tools through their own AI assistant. Tools: member_engagement(plan_id), "
            f"outcome_evidence(plan_id, metric in bp_control|readings|satisfaction|escalations), enrollment_status(member_id like pt-1001), enroll_members(plan_id, count). "
            f"Plan id plan-prairie. 2 to 5 calls. Session {idx}. Some sessions try a phone number or name as member_id and get not_found; almost none ask for escalations.")


def to_transcript(idx: int, theme: str, out: dict, rng: random.Random) -> dict:
    return {"session_id": f"corpus-p-{idx:03d}", "persona": "patient", "started": _stamp(rng).isoformat(timespec="seconds"),
            "messages": [{**m, "ts": ""} for m in out["messages"]],
            "tool_uses": [{"name": t, "input": {}, "result": "", "is_error": False} for t in out["tools_used"]],
            "escalated": out["escalated"], "cost_usd": 0.0, "theme": theme}


def queue_rows(last_q: dict, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    median = last_q["nurse_response_median_h"]
    rows = []
    for i in range(n):
        created = _stamp(rng)
        tier = rng.choices(["urgent_clinical", "non_urgent_clinical", "non_clinical"], [15, 45, 40])[0]
        answered = None
        if rng.random() < 0.88:
            hours = math.exp(math.log(median) + rng.gauss(0, 0.7))
            answered = (created + timedelta(hours=hours)).isoformat(timespec="seconds")
        rows.append({"id": f"corpus-esc-{i:04d}", "patient_id": f"pt-{rng.randint(1, 1500)}", "reason": tier.replace("_", " "),
                     "urgency": "urgent" if tier == "urgent_clinical" else "routine", "created_at": created.isoformat(timespec="seconds"),
                     "answered_at": answered, "tier": tier, "route": None})
    return rows


def seed_exhibit_e(rows: list[dict]) -> None:
    for e in json.loads((TRIAGE / "exhibit_e.json").read_text()):
        t = datetime.strptime(e["time"], "%I:%M %p")
        day = datetime(2026, 9, 8) if t.hour >= 12 else datetime(2026, 9, 9)
        rows.append({"id": f"exhibit-e-{e['n']:02d}", "patient_id": f"pt-e{e['n']:02d}", "reason": e["text"], "urgency": "routine",
                     "created_at": day.replace(hour=t.hour, minute=t.minute).isoformat(timespec="seconds"), "answered_at": None, "tier": None, "route": None})


def main(n_transcripts: int = 120, n_plan: int = 40, n_queue: int = 2000, ask=claude_json.ask_json_many) -> None:
    rng = random.Random(7)
    (CORPUS / "patient").mkdir(parents=True, exist_ok=True); (CORPUS / "plan").mkdir(exist_ok=True)
    themes = plan(n_transcripts, seed=1)
    outs = ask([(transcript_prompt(t, tier, i), TRANSCRIPT_SCHEMA) for i, (t, tier) in enumerate(themes)], workers=6)
    for i, ((t, _), o) in enumerate(zip(themes, outs)):
        (CORPUS / "patient" / f"p-{i:03d}.json").write_text(json.dumps(to_transcript(i, t, o, rng), indent=2))
    outs = ask([(plan_prompt(i), PLAN_SCHEMA) for i in range(n_plan)], workers=6)
    for i, o in enumerate(outs):
        lines = [json.dumps({"ts": _stamp(rng).isoformat(timespec="seconds"), "session_id": f"corpus-s-{i:03d}", "persona": "plan",
                             "tool": c["tool"], "args": c["args"], "status": c["status"], "error": c.get("error") or None}) for c in o["calls"]]
        (CORPUS / "plan" / f"s-{i:03d}.jsonl").write_text("\n".join(lines) + "\n")
    summary = json.loads((REPO_ROOT / "northline" / "sim" / "out" / "summary.json").read_text())["last_quarter"]
    rows = queue_rows(summary, n_queue, seed=2); seed_exhibit_e(rows)
    (CORPUS / "queue.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{n_transcripts} transcripts, {n_plan} plan sessions, {len(rows)} queue rows")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run** `uv run pytest tests/test_generate_corpus.py -q` → 3 passed. Then `uv run python -m northline.pm.generate_corpus` (160 headless calls, several minutes). Read five transcripts: refills, insurance, and loneliness should appear; at least three escalations. Then `uv run python -c "from northline.pm.aggregate import *; print(queue_metrics(load_queue(REPO_ROOT/'corpus', REPO_ROOT/'northline'/'logs')))"` → median near 31, after-hours near 0.46, non-clinical near 0.40. **Commit** `git add -A && git commit -m "Add the corpus generator, Exhibit E, the nurse key, and the committed corpus"`

### Task 18: The /pm-run skill and committed outputs

**Files:** `.claude/skills/pm-run/SKILL.md`, `northline/pm/out/{classified.jsonl,report.md,candidates.json,queue_metrics.json,diagnosis.md,proposals/*.md}`

- [ ] **Step 1: Write the skill**

```markdown
---
name: pm-run
description: Run the product-management loop over Northline's conversations and nurse queue: classify, aggregate, diagnose, propose. Shows the numbers first, asks what the board doesn't see, then reveals the diagnosis and the proposals.
---

You are running the loop with the attendee. The judgment steps call headless Claude Code; the counting is Python. Narrate briefly; do not paste whole files.

1. Say how many items will be classified: `uv run python -c "from northline.pm.classify import load_items, REPO_ROOT; print(len(load_items(REPO_ROOT/'corpus', REPO_ROOT/'northline'/'logs')))"`. Tell them this takes about two minutes.
2. Run `uv run python -m northline.pm.classify`. On a RuntimeError, run it once more.
3. Run `uv run python -m northline.pm.aggregate`, then `uv run python -m northline.pm.diagnose`, then `uv run python -m northline.pm.propose`. Do not show diagnosis.md yet.
4. Show, from `northline/pm/out/report.md`: the "board's numbers next to the logs" table, the tier table, and the top five candidate expansions. If any ids in `classified.jsonl` start with `live-`, find them and say which candidate the attendee's own conversation landed in, quoting their line.
5. **Gate.** Ask exactly: "In one sentence, what is the problem the board doesn't see?" Wait for the answer. Do not proceed without one. Acknowledge it in one line, without grading it.
6. Now show `northline/pm/out/diagnosis.md` in full. Then list the proposal files in `northline/pm/out/proposals/`, one line each with the metric each would move.
7. Ask: "Which proposal do you want to pursue, and why?" If they pick a tool proposal, reply once: "<tool> is <share>% of conversations. The queue metrics say the median nurse response is <h> hours. Which metric does <tool> move?" and ask again. Accept whatever they choose the second time.
8. End with the one command to run next: `/deploy triage` or `/expand <file stem>`.

Never run git. Never edit tool code here. Never skip the aggregate step even if classification looks off; the report is how you see that it is off.
```

- [ ] **Step 2: Run the loop for real** `uv run python -m northline.pm.classify && uv run python -m northline.pm.aggregate && uv run python -m northline.pm.diagnose && uv run python -m northline.pm.propose`. Check `report.md`: From-logs median within 15% of 31h, top candidates include `request_refill` and `insurance_question`, `agent-triage.md` exists with the four decisions. Read `diagnosis.md`; it should name nurses and capacity, not "the AI". If it does not, tighten `diagnose.prompt` and re-run.

- [ ] **Step 3: Commit the outputs** `git add -A && git commit -m "Add the /pm-run skill and the committed loop outputs"`

**Phase 4 checkpoint:** `/pm-run` reproduces Exhibit B from raw logs, withholds the diagnosis until the gate question is answered, and proposes triage.

---

## Phase 5: The triage deployment

### Task 19: Decisions, prompt rendering, and the acceptance scorer

**Files:** `northline/agents/__init__.py`, `northline/agents/triage/__init__.py`, `northline/agents/triage/render.py`, `northline/agents/triage/acceptance.py`, `northline/agents/triage/prompt_template.md`, `tests/test_triage_agent.py`, `tests/fixtures/decisions.json`

**Interfaces:**
- `decisions.json` shape: `{"urgent": {"systolic": 180, "diastolic": 110, "glucose_low": 70, "glucose_high": 300, "always_urgent_words": ["chest", "arm heavy", "can't breathe", "slurred", "confused", "stroke"]}, "non_clinical_handling": "admin"|"auto_reply"|"hold_for_morning", "after_hours_urgent": "tell_911_and_page_on_call"|"tell_911_only"|"queue_for_morning", "honour_dont_tell": true|false, "chosen_by": "attendee"|"northline_default"}`. `render.DEFAULTS` is that dict with the values shown, `chosen_by` `northline_default`.
- `render.render(decisions: dict) -> str` fills `prompt_template.md` and writes nothing. `render.write(decisions) -> Path` writes `decisions.json` and `prompt.md`.
- `acceptance.ITEM_SCHEMA` `{tier, route, rationale, draft_reply}` with enums. `acceptance.classify_exhibit(prompt_md, exhibit, *, ask=claude_json.ask_json_many) -> list[dict]` one headless call per message, model `sonnet`, prompt = the rendered triage prompt plus "Message received at <time>: <text>". `acceptance.score(results, key) -> dict`: per-message rows `{n, text, expected_tier, got_tier, expected_route, got_route, hit: bool, trap: bool}` (traps are 5, 9, 12, 13), `accuracy`, `urgent_recall` (urgent in key found urgent), `urgent_precision`, `routed_from_nurses` (share of key non-clinical messages the agent routed to `admin` or `auto_reply`), `missed_urgent: list[int]`. `acceptance.effects(score) -> dict` = `{"inbound_to_nurse_share": round(0.60 * (1 - routed_from_nurses), 2), "routine_time_factor": 0.6, "urgent_recall": urgent_recall}`. `acceptance.table(score) -> str` markdown with misses marked `MISS` and traps marked `trap`. `acceptance.main()` reads `prompt.md`, runs, writes `out/acceptance.json` and `out/acceptance.md`, prints the table.

- [ ] **Step 1: prompt_template.md**

```markdown
# Northline triage agent

You sort messages from Northline patients before a nurse sees them. You do not talk to patients. You tier, route, and draft.

## Tiers
- `urgent_clinical`: blood pressure at or above {systolic}/{diastolic}, glucose under {glucose_low} or over {glucose_high}, a possible double dose with symptoms, or any of these words: {always_urgent_words}. A patient saying "probably nothing" does not lower the tier. A patient who already acted (had juice) does not lower the tier if the reading was dangerous.
- `non_urgent_clinical`: routine readings, mild symptoms, refills, diet questions, a stopped medication, a wound that is not healing. A diabetic foot wound that "doesn't hurt" is a warning sign, not reassurance.
- `non_clinical`: insurance, scheduling, logistics, device support, social contact, opt-outs.

## Routes
- `urgent_clinical` -> `nurse_urgent`. After hours: {after_hours_rule}
- `non_urgent_clinical` -> `nurse_routine`, with a draft reply the nurse can send or edit.
- `non_clinical` -> {non_clinical_rule}
- A STOP message: route `admin` and note whether the patient had an unanswered escalation.

## Consent
{consent_rule}

## Output
For each message give tier, route, a one-line rationale, and a draft reply in plain words a nurse could send. Never diagnose in the draft.

Decisions in this prompt were chosen by: {chosen_by}.
```

- [ ] **Step 2: Tests**

```python
# tests/test_triage_agent.py
import json
from pathlib import Path
from northline.agents.triage import render, acceptance as ac

KEY = json.loads(Path("northline/agents/triage/nurse_key.json").read_text())["key"]


def test_render_fills_all_placeholders():
    p = render.render(render.DEFAULTS)
    assert "{" not in p and "180/110" in p and "northline_default" in p


def test_render_strict_threshold_changes_prompt():
    d = json.loads(json.dumps(render.DEFAULTS)); d["urgent"]["systolic"] = 190; d["chosen_by"] = "attendee"
    assert "190/110" in render.render(d)


def _results(overrides: dict) -> list[dict]:
    out = []
    for k in KEY:
        r = {"n": k["n"], "tier": k["tier"], "route": k["route"], "rationale": "", "draft_reply": ""}
        r.update(overrides.get(k["n"], {})); out.append(r)
    return out


def test_score_perfect():
    s = ac.score(_results({}), KEY)
    assert s["accuracy"] == 1.0 and s["urgent_recall"] == 1.0 and s["missed_urgent"] == [] and s["routed_from_nurses"] == 1.0


def test_score_downgrades_message_12():
    s = ac.score(_results({12: {"tier": "non_urgent_clinical", "route": "nurse_routine"}}), KEY)
    assert s["missed_urgent"] == [12] and s["urgent_recall"] == 0.75
    row = next(r for r in s["rows"] if r["n"] == 12)
    assert row["hit"] is False and row["trap"] is True and "MISS" in ac.table(s)


def test_effects_from_score():
    s = ac.score(_results({2: {"route": "nurse_routine"}}), KEY)
    e = ac.effects(s)
    assert e["urgent_recall"] == 1.0 and e["routine_time_factor"] == 0.6 and 0.6 * (1 - s["routed_from_nurses"]) - 0.01 < e["inbound_to_nurse_share"] < 0.6
```

- [ ] **Step 3: render.py**

```python
# northline/agents/triage/render.py
"""Turn four human decisions into the triage agent's prompt."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
DEFAULTS = {"urgent": {"systolic": 180, "diastolic": 110, "glucose_low": 70, "glucose_high": 300,
                       "always_urgent_words": ["chest", "arm heavy", "can't breathe", "slurred", "confused", "stroke"]},
            "non_clinical_handling": "admin", "after_hours_urgent": "tell_911_and_page_on_call", "honour_dont_tell": False,
            "chosen_by": "northline_default"}
NON_CLINICAL = {"admin": "`admin`, with a draft reply saying the benefits or support team will call the next working day.",
                "auto_reply": "`auto_reply` from approved content where one exists, otherwise `admin`.",
                "hold_for_morning": "`nurse_routine`, held for the morning. Note: this keeps non-clinical work in the nurse queue."}
AFTER_HOURS = {"tell_911_and_page_on_call": "draft a reply telling the patient to call 911 now if it is happening now, and page the on-call nurse.",
               "tell_911_only": "draft a reply telling the patient to call 911 now. No nurse is paged overnight.",
               "queue_for_morning": "route `nurse_urgent` and leave it for the first nurse in the morning. Note: this is the 40-hour path."}
CONSENT = {True: "If a patient asks you not to tell the doctor, honour it: route to `nurse_routine` with the draft addressed to the patient only, and say in the rationale that consent limits what the nurse may share.",
           False: "If a patient asks you not to tell the doctor, do not promise that. Route to `nurse_routine` and draft a reply saying a nurse will talk it through with them first."}


def render(d: dict) -> str:
    u = d["urgent"]
    fill = {"systolic": u["systolic"], "diastolic": u["diastolic"], "glucose_low": u["glucose_low"], "glucose_high": u["glucose_high"],
            "always_urgent_words": ", ".join(u["always_urgent_words"]), "after_hours_rule": AFTER_HOURS[d["after_hours_urgent"]],
            "non_clinical_rule": NON_CLINICAL[d["non_clinical_handling"]], "consent_rule": CONSENT[bool(d["honour_dont_tell"])], "chosen_by": d["chosen_by"]}
    t = (HERE / "prompt_template.md").read_text()
    for k, v in fill.items():
        t = t.replace("{" + k + "}", str(v))
    return t


def write(d: dict) -> Path:
    (HERE / "decisions.json").write_text(json.dumps(d, indent=2))
    (HERE / "prompt.md").write_text(render(d))
    return HERE / "prompt.md"
```

- [ ] **Step 4: acceptance.py**

```python
# northline/agents/triage/acceptance.py
"""Score the triage prompt on Exhibit E against the nurse's key. This is the test a clinical decision deserves."""
import json
from pathlib import Path
from northline.pm import claude_json

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TRAPS = {5, 9, 12, 13}
ITEM_SCHEMA = {"type": "object", "properties": {
    "tier": {"type": "string", "enum": ["urgent_clinical", "non_urgent_clinical", "non_clinical"]},
    "route": {"type": "string", "enum": ["nurse_urgent", "nurse_routine", "admin", "auto_reply"]},
    "rationale": {"type": "string"}, "draft_reply": {"type": "string"}}, "required": ["tier", "route", "rationale", "draft_reply"]}


def classify_exhibit(prompt_md: str, exhibit: list[dict], *, ask=claude_json.ask_json_many) -> list[dict]:
    jobs = [(f"{prompt_md}\n\nMessage received at {e['time']}: {e['text']}", ITEM_SCHEMA) for e in exhibit]
    return [{"n": e["n"], **o} for e, o in zip(exhibit, ask(jobs, model="sonnet", workers=5))]


def score(results: list[dict], key: list[dict]) -> dict:
    by = {r["n"]: r for r in results}
    rows, tp, fn, fp = [], 0, 0, 0
    nc_total = nc_routed = 0
    for k in key:
        r = by[k["n"]]
        hit = r["tier"] == k["tier"]
        rows.append({"n": k["n"], "text": k.get("text", ""), "expected_tier": k["tier"], "got_tier": r["tier"], "expected_route": k["route"],
                     "got_route": r["route"], "hit": hit, "trap": k["n"] in TRAPS, "rationale": r.get("rationale", "")})
        if k["tier"] == "urgent_clinical":
            tp += hit; fn += (not hit)
        elif r["tier"] == "urgent_clinical":
            fp += 1
        if k["tier"] == "non_clinical":
            nc_total += 1; nc_routed += r["route"] in ("admin", "auto_reply")
    return {"rows": rows, "accuracy": round(sum(r["hit"] for r in rows) / len(rows), 2),
            "urgent_recall": round(tp / (tp + fn), 2) if tp + fn else 1.0, "urgent_precision": round(tp / (tp + fp), 2) if tp + fp else 1.0,
            "routed_from_nurses": round(nc_routed / nc_total, 2) if nc_total else 0.0,
            "missed_urgent": [r["n"] for r in rows if r["expected_tier"] == "urgent_clinical" and not r["hit"]]}


def effects(s: dict) -> dict:
    return {"inbound_to_nurse_share": round(0.60 * (1 - s["routed_from_nurses"]), 2), "routine_time_factor": 0.6, "urgent_recall": s["urgent_recall"]}


def table(s: dict) -> str:
    L = ["| # | expected | got | route | |", "|---|---|---|---|---|"]
    for r in s["rows"]:
        mark = ("" if r["hit"] else "MISS") + (" trap" if r["trap"] else "")
        L.append(f"| {r['n']} | {r['expected_tier']} | {r['got_tier']} | {r['got_route']} | {mark.strip()} |")
    L += ["", f"Accuracy {int(s['accuracy'] * 100)}%. Urgent recall {s['urgent_recall']}. Missed urgent: {s['missed_urgent'] or 'none'}. "
              f"Non-clinical routed away from nurses: {int(s['routed_from_nurses'] * 100)}%."]
    return "\n".join(L)


def main(ask=claude_json.ask_json_many) -> dict:
    exhibit = json.loads((HERE / "exhibit_e.json").read_text())
    key = json.loads((HERE / "nurse_key.json").read_text())["key"]
    for k in key:
        k["text"] = next(e["text"] for e in exhibit if e["n"] == k["n"])
    results = classify_exhibit((HERE / "prompt.md").read_text(), exhibit, ask=ask)
    s = score(results, key); s["effects"] = effects(s); s["results"] = results
    OUT.mkdir(exist_ok=True)
    (OUT / "acceptance.json").write_text(json.dumps(s, indent=2)); (OUT / "acceptance.md").write_text(table(s))
    print(table(s))
    return s


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run** `uv run pytest tests/test_triage_agent.py -q` → 5 passed. Then a real run with defaults: `uv run python -c "from northline.agents.triage import render; render.write(render.DEFAULTS)" && uv run python -m northline.agents.triage.acceptance`. Expected: a fifteen-row table; with defaults, message 12 is urgent and message 10 is urgent; note which traps miss. Then a strict run with systolic 190 to confirm message 12 flips to MISS. Do not commit `decisions.json`, `prompt.md`, or `out/` (gitignored). **Commit** `git add -A && git commit -m "Add triage decisions, prompt rendering, and the Exhibit E acceptance scorer"`

### Task 20: The /deploy skill

**Files:** `.claude/skills/deploy/SKILL.md`, `northline/agents/triage/deploy.py`, `tests/test_deploy.py`

**Interfaces:** `deploy.register(name: str, effects: dict, live_from_week: int = 40) -> list[dict]` appends or replaces the deployment in `data/deployments.json`, then runs `sim.run.main()` and returns the deployments list. `deploy.main()` reads `out/acceptance.json` and registers `triage` with its `effects`.

- [ ] **Step 1: Test**

```python
# tests/test_deploy.py
import json
from northline.agents.triage import deploy
from northline.tools import store


def test_register_replaces_and_reruns_sim(data_dir, monkeypatch, tmp_path):
    from northline.sim import run as sim_run
    monkeypatch.setattr(sim_run, "OUT", tmp_path)
    deploy.register("triage", {"inbound_to_nurse_share": 0.3, "routine_time_factor": 0.6, "urgent_recall": 0.9})
    deploy.register("triage", {"inbound_to_nurse_share": 0.25, "routine_time_factor": 0.6, "urgent_recall": 1.0})
    deps = store.load("deployments")
    assert [d["name"] for d in deps] == ["checkin_agent", "triage"] and deps[1]["effects"]["urgent_recall"] == 1.0
    s = json.loads((tmp_path / "summary.json").read_text())
    assert s["now"]["nurse_response_median_h"] < s["last_quarter"]["nurse_response_median_h"]
```

- [ ] **Step 2: deploy.py**

```python
# northline/agents/triage/deploy.py
"""Register a deployment and re-run the company model. The dashboard picks it up on its next refresh."""
import json
from pathlib import Path
from northline.tools import store
from northline.sim import run as sim_run
HERE = Path(__file__).resolve().parent


def register(name: str, effects: dict, live_from_week: int = 40) -> list[dict]:
    deps = [d for d in store.load("deployments") if d["name"] != name]
    deps.append({"name": name, "live_from_week": live_from_week, "effects": effects})
    store.save("deployments", deps)
    sim_run.main()
    return deps


def main() -> None:
    s = json.loads((HERE / "out" / "acceptance.json").read_text())
    deps = register("triage", s["effects"])
    print(f"triage live; deployments: {[d['name'] for d in deps]}; effects {s['effects']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: The skill**

```markdown
---
name: deploy
description: Deploy an agent from an approved deployment proposal. For triage, interview the user on the four clinical-risk decisions, render the prompt, run the Exhibit E acceptance test against the nurse's key, show the misses, register the deployment, and re-run the company model. Usage /deploy triage
arguments: [agent]
---

Deploy `$agent`. Today only `triage` has a proposal (`northline/pm/out/proposals/agent-triage.md`); read it first and say in two lines where the agent sits and what it must not do.

**Decisions first. Do not write a prompt until all four are answered.** Ask one at a time. For each, offer the Northline default and say it is what Northline's product team chose; taking it is a decision and is recorded as such. Accept short answers.

1. Urgent thresholds. Default: BP at or above 180/110, glucose under 70 or over 300, always-urgent words chest, arm heavy, can't breathe, slurred, confused, stroke. Ask for their numbers and any words to add or remove.
2. Non-clinical handling. Options: `admin` (route to admin staff, default), `auto_reply` (approved content), `hold_for_morning` (stays in the nurse queue).
3. After-hours urgent rule. Options: `tell_911_and_page_on_call` (default), `tell_911_only`, `queue_for_morning`.
4. Consent. Honour "don't tell the doctor"? Default no.

Then:
5. Write `northline/agents/triage/decisions.json` in the shape `render.DEFAULTS` uses, with `chosen_by` set to `attendee` if any value differs from the default, else `northline_default`. Run `uv run python -c "import json; from northline.agents.triage import render; render.write(json.load(open('northline/agents/triage/decisions.json')))"`.
6. Say: "Testing it on the fifteen night texts against the nurse's key. About a minute." Run `uv run python -m northline.agents.triage.acceptance`. Show the table it prints, unchanged.
7. Point at every MISS. For each trap message that missed (5, 9, 12, 13), quote the message and the nurse's note from `northline/agents/triage/nurse_key.json`. Then ask: "Do you deploy it as is, or change a decision and re-test?" If they change a decision, go back to step 5 for that decision only. Do not loop more than twice; a third time, deploy as is and say why.
8. Run `uv run python -m northline.agents.triage.deploy`. Then say: open http://127.0.0.1:8765/dashboard (start the server with `uv run python -m northline.agent.server` if it is not running). Tell them what to look at: the Next quarter column, the nurse response line after week 40, the "urgent cases missed" tile, and the Sign Prairie toggle.
9. Close with two lines: what their decisions did to the numbers, and the one question the board chair will ask them: "What did your triage do with 184/112?"

Never run git. Never edit Python. Never soften a MISS.
```

- [ ] **Step 4: End-to-end.** In an interactive Claude Code session: `/deploy triage`, take defaults except systolic 190, confirm message 12 is a MISS, change back to 180, re-test, deploy. Open the dashboard: Next quarter median should be well under Last quarter's 31h, the triage rule at week 40, the missed-urgent tile non-zero if recall < 1. Then restore the repo state: `git checkout northline/data/deployments.json northline/sim/out/` so the committed tree has only the check-in agent live. **Commit** `git add -A && git commit -m "Add the /deploy skill and deployment registration"`

### Task 21: The /expand skill and tool spec template

**Files:** `templates/tool-spec.md`, `.claude/skills/expand/SKILL.md`, `northline/tools/specs/.gitkeep`

- [ ] **Step 1: templates/tool-spec.md**

```markdown
# Tool: `{tool_name}`

**Module:** northline/tools/{module}.py  **Personas:** {personas}  **Requires deployment:** {requires}

## Docstring (what the model reads)
{description}

## Signature
```python
def {tool_name}({signature}) -> dict:
```

## Returns
`{"status": "ok" | "not_found" | "error", ...}` with fields: {return_fields}

## Data it reads or writes
{data}

## Failure modes
{failure_modes}

## Safety
{safety}

## Test cases
{tests}
```

- [ ] **Step 2: The skill**

```markdown
---
name: expand
description: Implement one approved tool proposal end to end: spec, failing tests, function, registry line, tests green, and how to see it in both front doors. Usage /expand tool-request_refill
arguments: [proposal]
---

Implement `northline/pm/out/proposals/$proposal.md`. Read it. Then follow the repo's one procedure for adding a tool; the point is that it is short.

1. **Spec.** Copy `templates/tool-spec.md` to `northline/tools/specs/$proposal.md`, filling every placeholder from the proposal. Module: `patient.py` if the persona is patient, `plan.py` if plan. Keyword arguments, typed. `requires` is `none` unless the proposal says the tool belongs to an agent. Three test cases minimum: happy path, `not_found`, `error`.
2. **Tests first.** Add them to `tests/test_patient_tools.py` or `tests/test_plan_tools.py` in the existing style, using the `data_dir` and `log_dir` fixtures. Run `uv run pytest -q` and confirm they fail.
3. **Function.** Add it with the docstring from the spec. Never raise; return `status`. Use `store.load`, `store.save`, `store.append`. New data file: `northline/data/<name>.json` with three realistic seed rows.
4. **Register.** One `_t(...)` line in `northline/tools/registry.py`. Run `uv run pytest -q`; all green, including `test_registry`.
5. **Guardrail.** If the proposal would give a patient clinical advice or a result interpretation, the function returns `{"status": "error", "message": "..."}` explaining a nurse handles that, and you say so.
6. **Show it.** Three lines: restart the agent server and ask for the new capability on the check-in page; start a new Claude Code session so front door 1 picks up the tool; re-run `/pm-run` later to watch the candidate shrink.

Never run git. Do not change existing signatures. Do not edit `brief.md` unless the proposal's safety notes require a new rule, and show the diff first.
```

- [ ] **Step 3: Verify** on the committed `tool-request_refill.md` in an interactive session, then discard the changes with `git checkout -- . && git clean -fd northline/tools/specs northline/data` so the demo can run it live. **Commit** `git add -A && git commit -m "Add the /expand skill and tool spec template"`

**Phase 5 checkpoint:** `/deploy triage` turns four decisions into a tested agent and a changed company; `/expand` turns a proposal into a tool.

---

## Phase 6: Course material

### Task 22: Templates, take-home skills, and new-experience

**Files:** `templates/use-case-brief.md`, `templates/agent-brief.md`, `templates/taxonomy.md`, `.claude/skills/brief/SKILL.md`, `.claude/skills/tools/SKILL.md`, `.claude/skills/agent/SKILL.md`, `.claude/skills/new-experience/SKILL.md`, `.claude/skills/generate-corpus/SKILL.md`, `scripts/new_experience.py`, `tests/test_new_experience.py`, `briefs/.gitkeep`

- [ ] **Step 1: templates/use-case-brief.md**

```markdown
# Use-case brief: {experience name}

## 1. Who talks to it
- Personas, one line each: who they are, what they are trying to get done.
- Where each persona already lives: their own AI assistant, a portal, SMS or WhatsApp, a phone line.

## 2. The jobs, ranked
The five things users will ask for most, in order, each with the tool it needs and whether that tool exists today.

## 3. Front-door decision, per persona
| Persona | Front door | Why | What you give up |
|---|---|---|---|
| | MCP to their agent / controlled agent | | |

## 4. Product signal you need
- Do you need the user's words, or are tool calls enough?
- Who reads them, how often, and what do they do with what they find?

## 5. Where the bottleneck will move
When the agent works, whose queue grows? What is the metric that shows it first? Who watches that metric weekly?

## 6. Guardrails that are non-negotiable
Three to five rules the assistant must never break, and what it does instead.

## 7. First release
The three tools you ship first, and the one metric that would make you pause rollout.
```

- [ ] **Step 2: templates/agent-brief.md** as a blank of `northline/agent/brief.md`: headings `Role`, `Hard rules`, `Style`, `Logging`, each with one-line prompts. Under `Hard rules`: "what it must never state", "what triggers a hand-off and how", "what to say when no tool fits". Under `Logging`: "what is stored, who reads it, what they look for".

- [ ] **Step 3: templates/taxonomy.md** as a blank of `northline/pm/taxonomy.md`: same fields; intent examples replaced by "{three intent examples from your brief}", proposed tool names by "{tool names you expect; reuse them}", tiers replaced by "{your severity levels, or delete this field}". Keep both closing rules, generalised.

- [ ] **Step 4: The `/brief` skill**

```markdown
---
name: brief
description: Interview the user about one AI experience from their own company and fill templates/use-case-brief.md, ending in a front-door decision and a guess at where the bottleneck will move. Usage /brief <short_name>
arguments: [name]
---

Fill `templates/use-case-brief.md` for "$name". One question at a time, two or three concrete options each, short answers accepted. Under ten questions; infer the rest and say what you inferred.

Order: personas and where they live (1); the top three jobs, then propose two more (2); the signal question (4); where the bottleneck will move (5), and push on it: "when this works, whose queue grows?"; guardrails (6), propose five and ask which to keep.

Write section 3 yourself with this rule of thumb, reasoning in the Why column:
- Users already live in their own AI assistant or a partner platform, and tool calls are enough signal -> MCP to their agent.
- Users come to you, the domain is regulated or high-stakes, you need their words as signal, or the channel is SMS or WhatsApp -> controlled agent.
- One persona each -> both, and name the shared tools.

Write section 7 last. Save to `briefs/$name.md`. Read back the front-door table and section 5 in three sentences and ask whether it matches their instinct. If it does not, ask what the table missed.
```

- [ ] **Step 5: The `/tools` and `/agent` skills**, as in the MediBridge plan but for this repo: `/tools <name>` reads `briefs/$name.md` and runs the `/expand` procedure for each missing tool (spec, failing tests, function, registry line, tests green), stops at five, never runs git. `/agent <name>` writes `briefs/$name-agent-brief.md` from `templates/agent-brief.md` with the hard rules from section 6, the mandatory "no tool fits" rule, under 60 lines, and offers to install it over `northline/agent/brief.md`.

- [ ] **Step 6: scripts/new_experience.py and its test.** `create(name, dest, repo_root) -> Path` makes `dest/<name>/` with: `templates/` copied; `.claude/skills/{setup,brief,tools,agent,pm-run,expand,deploy}` copied with `northline` replaced by `<name>`; `.mcp.json` rewritten; `pyproject.toml` with the name and package changed; `<name>/tools/{store,calllog}.py`, an empty registry (`TOOLS = []` plus `select` and `live_deployments`), empty `patient.py`, `mcp_server.py`, `agent/*` (brief from the template), `sim/model.py` and `run.py` (the model with `BASE` left as is and a comment "recalibrate to your company"), `pm/{claude_json,classify,aggregate,diagnose,propose}.py` with `taxonomy.md` from the template, `agents/` empty, `data/deployments.json` as `[]`, `logs/.gitkeep`, `scripts/check.py`, `tests/conftest.py`, a README saying "Start with /brief <name>". Excludes `corpus/`, `pm/out/`, `sim/out/`, `docs/`, `exercises/`, `slides/`, `tests/test_*`. Test asserts the registry is empty, no `northline` string remains in `.py` or `.mcp.json`, no corpus copied, and `uv sync && uv run python scripts/check.py` succeeds in the new folder (run in the test via `subprocess`, skipped if `uv` is missing).

- [ ] **Step 7: `/new-experience` skill** runs `uv run python scripts/new_experience.py $name` (creates `../$name`), then `cd ../$name && uv sync && uv run python scripts/check.py`, reports the path, and says: open Claude Code there and run `/brief $name`. No corpus on purpose; the loop runs on the first real conversations. No git.

- [ ] **Step 8: `/generate-corpus` skill** for authors: warns it overwrites `corpus/` and takes several minutes, asks to confirm, runs `uv run python -m northline.pm.generate_corpus`, reads three transcripts, reports whether refills, insurance, and loneliness appear.

- [ ] **Step 9: Run** `uv run pytest -q`. Dry-run `/brief` on a made-up pharmacy chain in an interactive session; confirm seven sections and under ten questions; do not commit the brief. **Commit** `git add -A && git commit -m "Add templates, take-home skills, and new-experience scaffolding"`

### Task 23: Docs

**Files:** `docs/00-session-plan.md`, `docs/01-front-doors.md`, `docs/02-the-loop.md`, `docs/03-triage-decisions.md`, `docs/04-operating.md`, `docs/05-case-crosswalk.md`

- [ ] **Step 1: `docs/01-front-doors.md`.** Thesis line, then this table verbatim, then one paragraph per row with a Northline example, then "The hybrid" (build once, consume from your own agent, publish the same server), then "Where each front door sits at Northline": patients on the controlled agent because the channel is SMS and every word is signal; plans on MCP because Prairie already has an analyst agent and only needs the tools.

```markdown
| Dimension | MCP given to the customer | Controlled agent you host |
|---|---|---|
| Who runs the loop | Their agent, their prompt, their model | You |
| Distribution | Wherever they already work | They have to come to you |
| What you see | Tool calls: name, arguments, status | Every word, including what you could not do |
| Guardrails | You can refuse inside a tool; you cannot shape what is said around it | Yours, end to end |
| Who pays for tokens | They do | You do |
| Liability when it misspeaks | Shared and unclear | Yours, and clear |
| Build cost | The tool layer only | Tool layer plus prompt, UI, hosting, logging |
| Time to first user | Days if they already have an agent | Weeks |
| What Prairie saw | 78% engagement, tenfold readings | Nothing; they never asked for escalations |
```

- [ ] **Step 2: `docs/02-the-loop.md`.** The six stages, one section each naming the file. The diagram:

```
transcripts/*.json ─┐
tool_calls.jsonl   ─┼─ classify.py ─► classified.jsonl ─┐
queue.jsonl        ─┘   (claude -p)                     ├─ aggregate.py ─► report.md ─► diagnose.py ─► diagnosis.md
                        queue timestamps ───────────────┘   (python)                    (claude -p)
                                                                 └─► candidates.json ─► propose.py ─► proposals/{tool-*, agent-triage}.md ─► /expand | /deploy
```

Then "What each front door lets you see" with one real transcript excerpt (a refill request) and one plan tool-log excerpt (a phone-number lookup miss) from the committed corpus. Then "Why the queue log is the one that matters here": the unmet needs are real, but the timestamps are where the bottleneck shows. Then "Judgment and arithmetic" on the split. Then "Reading the committed report" with the two-column table copied from `pm/out/report.md`.

- [ ] **Step 3: `docs/03-triage-decisions.md`.** The four decisions, each with: why it is a strategy decision and not a parameter, the Northline default and what it trades, and which Exhibit E message exposes it (thresholds: 12 and 5; non-clinical: 2, 11, 14; after hours: 10; consent: 13). Then the acceptance test explained, with the nurse key table and its "draft, clinician to review" note. Then "What the dashboard shows after you deploy" and how the effects map to the model.

- [ ] **Step 4: `docs/04-operating.md`.** Backlog owner reads `report.md` weekly; the decision box on every proposal; generated agents get an acceptance test before they are live and a human signs the decisions file; cost per conversation read from the committed transcripts' `cost_usd` and the classification run's cost, real numbers, no estimates; the metric that pauses rollout (median nurse response over 8 hours, or any missed urgent); the business-model note that a flat fee does not pay for surfaced demand.

- [ ] **Step 5: `docs/05-case-crosswalk.md`.** A table mapping every part of the case document to the thing in this repo: Exhibit A to the plan tools over MCP, Exhibit B to the dashboard's Last quarter column and `report.md`, Exhibit C to slide 2, Exhibit D to `diagnosis.md`, Exhibit E to `agents/triage/exhibit_e.json`, the nurse key to `nurse_key.json`, the role cards and board template to "unchanged, on paper", the threshold trap to decision 1, the 40-hour path to the after-hours rule, the disengaged cohort to `patients_inactive_after_escalation`, the math table to the Prairie toggle.

- [ ] **Step 6: `docs/00-session-plan.md`.** The 75-minute table from the spec with a Presenter notes column: for each block the command or prompt to type, the file to have open, and the sentence to land. Pre-work section (three days ahead: the zip link, unzip into your home folder, open Claude Code in it, `/setup`, paste READY). Room and Screen roles. The seven interactive questions in order. Fallbacks: wifi dies (everything local except Claude; committed outputs allow a read-through), a laptop falls behind (watch the screen; the file names are on the slide), the acceptance run fails (re-run once; if still failing, show `docs/03-triage-decisions.md`'s example table).

- [ ] **Step 7: Commit** `git add -A && git commit -m "Add the session plan, front doors, loop, triage, operating, and crosswalk docs"`

### Task 24: Exercises

**Files:** `exercises/README.md`, `exercises/01-pharmacy-chain.md`, `exercises/02-health-insurer.md`, `exercises/03-telemedicine-startup.md`

- [ ] **Step 1:** Each exercise: a one-paragraph business; two personas; a "where will the bottleneck move" prompt; a Read track with three questions whose answers are the front-door table, the first three tools, and the bottleneck metric; a Build track that is `/new-experience <name>`, `/brief`, `/tools`, `/agent`, five conversations, `/pm-run`; and an Answer sketch giving one defensible answer with a sentence of why. The three must land differently: pharmacy on MCP for the app persona and a controlled agent for the counter; insurer on a controlled agent for members and MCP for employer HR; telemedicine on the hybrid with the bottleneck moving to clinicians exactly as at Northline. `README.md` explains the tracks and that answer sketches are one defensible answer, not the answer.

- [ ] **Step 2: Commit** `git add -A && git commit -m "Add three take-home exercises"`

### Task 25: Slides

**Files:** `slides/outline.md`, `slides/deck.pptx`

- [ ] **Step 1: `slides/outline.md`**, one `## Slide N: title` section each with bullets and a `Speaker:` line:

1. Moving the bottleneck, live. Speaker: what the room will do in 75 minutes.
2. The Monday email, full text, nothing else.
3. Two front doors, one tool layer: a diagram with patients on the left into "our agent", Prairie's analyst on the right into "their agent", both into the Northline tools. Speaker: this is how Prairie got impressed.
4. The loop: the diagram from `docs/02-the-loop.md`.
5. Four decisions, blank boxes: thresholds, non-clinical, after hours, consent. Filled live.
6. Pushback questions, one per click: day 91; which patients no longer get a call; the growth story if we decline; what did your triage do with 184/112; who pays for the extra care.
7. You didn't automate the bottleneck, you moved it. Dashboard screenshot: Before and Last quarter.
8. Tuning parameters are strategy decisions in disguise. The acceptance table with message 12 marked.
9. AI lets you pivot fast. Dashboard screenshot: Next quarter after triage.
10. A fast fix still needs testing. The nurse key's four traps.
11. Business model matters. The Prairie toggle, with and without.
12. Where each front door belongs. The table from `docs/01-front-doors.md`, last row highlighted.
13. Case one in one slide: build-versus-buy is a go-to-market question; good enough is relative to the market.
14. Take it home: unzip, `/setup`, `/new-experience`, the three exercises, and "where is this bottleneck hiding in your market?"

- [ ] **Step 2: Build** with the `anthropic-skills:pptx` skill from the outline. Screenshots for 7, 9, and 11 come from the running dashboard; the table for 8 from a real acceptance run with systolic 190. Dark title slide, white content slides, one table or one image per slide, no clip art.

- [ ] **Step 3: Check** by rendering to images and confirming legibility. Rebuild the zip with `uv run python scripts/package.py` (the deck is excluded from the zip; attendees do not need it). **Commit** `git add -A && git commit -m "Add the presenter deck and outline"`

**Phase 6 checkpoint:** a fresh attendee can unzip, `/setup`, and follow `docs/00-session-plan.md`; a reader can follow every step from the docs and committed outputs; the presenters have a deck. Matches spec section 10.

---

## Self-review against the spec

- Spec 2 lessons: 1 and 2 in Tasks 6, 10, docs 01, slide 3; 3 in Tasks 15, 16, 18; 4 in Tasks 19, 20; 5 in Task 19's scorer and doc 03; 6 in Task 11's Prairie scenarios, Task 12's toggle, slide 11.
- Spec 3 domain: numbers in Task 11 calibration tests; personas in Task 5 registry; no regions anywhere.
- Spec 4 constraints: no API key (global constraints, Tasks 8, 13); no git for attendees (every skill says "Never run git"; Task 7 packages a zip; Task 22's scaffold makes a plain folder); Windows in Task 7's skill; two commands in the room (Tasks 18, 20); committed outputs (Tasks 17, 18); nurse key marked draft (Task 17).
- Spec 5.1 to 5.10: Tasks 2 to 6 (tools, gating, MCP), 8 to 10 (agent), 11 (sim), 17 (corpus), 13 to 16 and 18 (loop), 19 to 20 (triage), 12 (dashboard), 7, 18, 20, 21, 22 (skills), 7 (distribution).
- Spec 6 run of show and spec 7 gates: Task 18 steps 5 and 7; Task 20 steps 1 to 4 and 7; Task 23 session plan.
- Spec 8 slides: Task 25. Spec 9 testing: every task; Task 7 tests the zip. Spec 10 criteria: phase checkpoints.
- Type consistency: `TurnResult` identical in Tasks 8 and 10; queue row shape identical in Tasks 3, 5, 15, 17; deployment entry shape identical in Tasks 2, 5, 11, 20; `effects` keys identical in Tasks 11, 19, 20; candidate dict identical in Tasks 15, 16; summary keys (`before`, `last_quarter`, `next_quarter`, `prairie`, `prairie_without`, `now`) identical in Tasks 4, 11, 12, 16, 20.
- Placeholder scan: none of TBD, TODO, "implement later", "similar to Task N".
