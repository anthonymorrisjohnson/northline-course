# One Tool Layer, Two Front Doors: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A cloneable course repo where the MediBridge tools are exposed both as an MCP server and inside a controlled web agent, a PM loop turns conversations into tool proposals, and repo skills let attendees run every step.

**Architecture:** Plain Python tool functions over JSON data, listed in one registry. Front door 1 is an MCP stdio server registered by `.mcp.json`. Front door 2 is a FastAPI page that runs headless Claude Code per turn with a locked system prompt and only the MediBridge MCP tools. The PM loop is Python scripts that call `claude -p --json-schema` for judgment and do arithmetic themselves, wrapped by skills.

**Tech Stack:** Python >=3.12, `uv`, `mcp` 2.x (`from mcp.server import MCPServer`), FastAPI, uvicorn, pytest, Claude Code 2.1.x headless mode. No Anthropic API key anywhere.

**Spec:** `docs/superpowers/specs/2026-09-16-agent-vs-mcp-course-design.md`

## Global Constraints

- Every LLM call goes through `claude -p`. Never import `anthropic` or read `ANTHROPIC_API_KEY`.
- Python `>=3.12`, managed by `uv`. Runtime deps: `mcp>=2.2`, `fastapi`, `uvicorn`. Dev deps: `pytest`, `pytest-anyio` is not needed; `mcp` ships `anyio`, use `@pytest.mark.anyio`.
- Tool functions never raise. They return a dict with a `status` key: `"ok"`, `"not_found"`, or `"error"`.
- Regions are `"A"` and `"B"`. Personas are `"patient"` and `"staff"`.
- MCP server name is `medibridge`, so tool names seen by Claude Code are `mcp__medibridge__<tool>`.
- Paths in `.mcp.json` use `${CLAUDE_PROJECT_DIR}`; never rely on the working directory.
- Headless flags verified on Claude Code 2.1.86: `--system-prompt`, `--mcp-config <json>`, `--strict-mcp-config`, `--tools ""`, `--allowedTools`, `--permission-mode dontAsk`, `--output-format stream-json --verbose`, `--output-format json --json-schema <json>` (result lands in `structured_output`; do not pass `--max-turns 1`, structured output needs two turns), `--resume <id>`, `--no-session-persistence`, `--model haiku`.
- Commit after every task with a descriptive message ending in `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Tests never call `claude`. Every module that shells out takes an injectable `runner` callable.

## File Map

```
pyproject.toml                       project metadata and deps
.gitignore
.mcp.json                            registers the medibridge MCP server
README.md
medibridge/__init__.py
medibridge/tools/__init__.py
medibridge/tools/store.py            JSON load/save with a configurable data dir
medibridge/tools/patient.py          patient-facing tool functions
medibridge/tools/staff.py            staff-facing and region-gated tool functions
medibridge/tools/registry.py         the single list of tools with persona and region tags
medibridge/data/*.json               seed data
medibridge/mcp_server.py             front door 1
medibridge/agent/claude_runner.py    builds and parses one headless turn
medibridge/agent/prompt.py           assembles system prompt from brief.md + region block
medibridge/agent/brief.md            the filled agent brief
medibridge/agent/transcripts.py      transcript file read/write
medibridge/agent/server.py           front door 2, FastAPI
medibridge/agent/static/index.html   the chat page
medibridge/logs/.gitkeep             tool_calls.jsonl and transcripts/ land here
medibridge/pm/claude_json.py         run claude -p with a JSON schema, return dict
medibridge/pm/taxonomy.md            the classification schema in prose
medibridge/pm/classify.py            transcripts + tool logs -> classified.jsonl
medibridge/pm/aggregate.py           classified.jsonl -> report.md + candidates.json
medibridge/pm/propose.py             candidates.json -> proposals/*.md
medibridge/pm/generate_corpus.py     region profiles -> corpus/
medibridge/pm/out/                   committed outputs
corpus/patient/{regionA,regionB}/*.json
corpus/staff/{regionA,regionB}/*.jsonl
templates/*.md                       clean templates
.claude/skills/<name>/SKILL.md       setup, brief, tools, agent, pm-run, expand, new-experience, generate-corpus
docs/0[0-4]-*.md
exercises/*.md
slides/outline.md, slides/deck.pptx
scripts/check.py                     used by /setup
tests/
```

---

## Phase 1: Tool layer and MCP front door

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `medibridge/__init__.py`, `medibridge/tools/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `medibridge/logs/.gitkeep`

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "medibridge-course"
version = "0.1.0"
description = "One tool layer, two front doors: MCP vs controlled agent course"
requires-python = ">=3.12"
dependencies = ["mcp>=2.2", "fastapi>=0.110", "uvicorn>=0.29"]

[dependency-groups]
dev = ["pytest>=8", "httpx>=0.27"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["medibridge"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write .gitignore**

```
.venv/
__pycache__/
*.pyc
medibridge/logs/tool_calls.jsonl
medibridge/logs/transcripts/
.pytest_cache/
```

- [ ] **Step 3: Write tests/conftest.py**

```python
import json
import shutil
from pathlib import Path

import pytest

DATA_SRC = Path(__file__).resolve().parents[1] / "medibridge" / "data"


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Copy seed data to a temp dir so tests can mutate it."""
    dst = tmp_path / "data"
    shutil.copytree(DATA_SRC, dst)
    monkeypatch.setenv("MEDIBRIDGE_DATA_DIR", str(dst))
    return dst


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    d = tmp_path / "logs"
    d.mkdir()
    monkeypatch.setenv("MEDIBRIDGE_LOG_DIR", str(d))
    return d


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 4: Create empty package files and sync**

Run: `touch medibridge/__init__.py medibridge/tools/__init__.py tests/__init__.py medibridge/logs/.gitkeep && uv sync && uv run pytest -q`
Expected: `no tests ran`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Scaffold uv project for the MediBridge course"
```

### Task 2: JSON store

**Files:**
- Create: `medibridge/tools/store.py`, `medibridge/data/clinics.json`, `tests/test_store.py`

**Interfaces:**
- Produces: `load(name: str) -> list[dict]`, `save(name: str, rows: list[dict]) -> None`, `append(name: str, row: dict) -> dict`, `data_dir() -> Path`. `name` is the file stem, e.g. `"clinics"`. Missing files load as `[]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
from medibridge.tools import store


def test_load_missing_returns_empty(data_dir):
    assert store.load("nothing_here") == []


def test_save_then_load_roundtrip(data_dir):
    store.save("things", [{"id": "t1"}])
    assert store.load("things") == [{"id": "t1"}]


def test_append_returns_row(data_dir):
    row = store.append("things", {"id": "t2"})
    assert row == {"id": "t2"}
    assert store.load("things") == [{"id": "t2"}]


def test_data_dir_env_override(data_dir):
    assert store.data_dir() == data_dir
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL with `ImportError` or `AttributeError`

- [ ] **Step 3: Write the implementation**

```python
# medibridge/tools/store.py
"""Tiny JSON-file store. One list of dicts per file. Good enough for a course."""
import json
import os
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[1] / "data"


def data_dir() -> Path:
    return Path(os.environ.get("MEDIBRIDGE_DATA_DIR", _DEFAULT))


def _path(name: str) -> Path:
    return data_dir() / f"{name}.json"


def load(name: str) -> list[dict]:
    p = _path(name)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def save(name: str, rows: list[dict]) -> None:
    p = _path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows, indent=2, ensure_ascii=False))


def append(name: str, row: dict) -> dict:
    rows = load(name)
    rows.append(row)
    save(name, rows)
    return row
```

- [ ] **Step 4: Write the seed clinics file** (needed so `copytree` in conftest has a directory)

```json
[
  {"id": "cl-a1", "region": "A", "name": "MediBridge Rosebank", "city": "Johannesburg", "address": "12 Oxford Rd, Rosebank", "services": ["general", "paediatrics", "lab", "physio"], "hours": "Mon-Fri 07:00-19:00, Sat 08:00-13:00", "phone": "+27 11 555 0101", "languages": ["en"]},
  {"id": "cl-a2", "region": "A", "name": "MediBridge Sea Point", "city": "Cape Town", "address": "8 Beach Rd, Sea Point", "services": ["general", "lab", "dermatology"], "hours": "Mon-Fri 08:00-18:00", "phone": "+27 21 555 0102", "languages": ["en"]},
  {"id": "cl-b1", "region": "B", "name": "Clinique MediBridge Plateau", "city": "Dakar", "address": "Av. Léopold Sédar Senghor, Plateau", "services": ["general", "maternity", "lab"], "hours": "Lun-Sam 08:00-18:00", "phone": "+221 33 555 0201", "languages": ["fr", "wo"]},
  {"id": "cl-b2", "region": "B", "name": "Clinique MediBridge Cocody", "city": "Abidjan", "address": "Rue des Jardins, Cocody", "services": ["general", "paediatrics", "lab"], "hours": "Lun-Ven 08:00-17:00", "phone": "+225 27 555 0202", "languages": ["fr"]}
]
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_store.py -q`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Add JSON store and seed clinics"
```

### Task 3: Seed data and patient tools

**Files:**
- Create: `medibridge/data/slots.json`, `medibridge/data/patients.json`, `medibridge/tools/patient.py`, `tests/test_patient_tools.py`

**Interfaces:**
- Consumes: `store.load/save/append`
- Produces, all keyword-only, all returning `dict` with `status`:
  - `find_clinic(region: str, city: str | None = None, service: str | None = None) -> dict` with `clinics: list`
  - `get_availability(clinic_id: str, service: str, date: str) -> dict` with `slots: list[{slot_id, start}]`
  - `book_appointment(patient_id: str, slot_id: str) -> dict` with `appointment_id, clinic, start`
  - `reschedule_or_cancel(appointment_id: str, new_slot_id: str | None = None) -> dict`
  - `results_status(patient_id: str) -> dict` with `results: list[{test, status, ready_at}]`, never values
  - `medication_schedule(patient_id: str) -> dict` with `prescriptions: list[{drug, dose, schedule, refills_left}]`
  - `escalate_to_human(patient_id: str | None, reason: str, urgency: str = "normal") -> dict` with `ticket_id, next_step`
- Appointment ids are `ap-<n>` where n is `len(appointments)+1`. Ticket ids are `esc-<n>`.

- [ ] **Step 1: Write seed slots** (`medibridge/data/slots.json`). Use 2026-09-21 to 2026-09-25 so dates look current during the course.

```json
[
  {"id": "sl-a1-01", "clinic_id": "cl-a1", "service": "general", "start": "2026-09-21T08:00", "booked_by": null},
  {"id": "sl-a1-02", "clinic_id": "cl-a1", "service": "general", "start": "2026-09-21T09:00", "booked_by": null},
  {"id": "sl-a1-03", "clinic_id": "cl-a1", "service": "paediatrics", "start": "2026-09-21T10:00", "booked_by": null},
  {"id": "sl-a1-04", "clinic_id": "cl-a1", "service": "physio", "start": "2026-09-22T14:00", "booked_by": null},
  {"id": "sl-a2-01", "clinic_id": "cl-a2", "service": "general", "start": "2026-09-21T11:00", "booked_by": null},
  {"id": "sl-a2-02", "clinic_id": "cl-a2", "service": "dermatology", "start": "2026-09-23T09:30", "booked_by": null},
  {"id": "sl-b1-01", "clinic_id": "cl-b1", "service": "general", "start": "2026-09-21T09:00", "booked_by": null},
  {"id": "sl-b1-02", "clinic_id": "cl-b1", "service": "general", "start": "2026-09-21T10:00", "booked_by": null},
  {"id": "sl-b1-03", "clinic_id": "cl-b1", "service": "maternity", "start": "2026-09-22T09:00", "booked_by": null},
  {"id": "sl-b2-01", "clinic_id": "cl-b2", "service": "paediatrics", "start": "2026-09-21T15:00", "booked_by": null},
  {"id": "sl-b2-02", "clinic_id": "cl-b2", "service": "general", "start": "2026-09-24T08:30", "booked_by": null}
]
```

- [ ] **Step 2: Write seed patients** (`medibridge/data/patients.json`)

```json
[
  {"id": "pt-a-001", "region": "A", "name": "Thandi Mokoena", "phone": "+27 82 555 1001", "preferred_language": "en", "scheme_member_no": "DHS-448812",
   "results": [{"test": "Full blood count", "status": "ready", "ready_at": "2026-09-15"}, {"test": "HbA1c", "status": "pending", "ready_at": "2026-09-19"}],
   "prescriptions": [{"drug": "Metformin", "dose": "500 mg", "schedule": "twice daily with meals", "refills_left": 1}]},
  {"id": "pt-a-002", "region": "A", "name": "Pieter van der Berg", "phone": "+27 83 555 1002", "preferred_language": "en", "scheme_member_no": "BON-102233",
   "results": [], "prescriptions": []},
  {"id": "pt-b-001", "region": "B", "name": "Aminata Diallo", "phone": "+221 77 555 2001", "preferred_language": "fr", "scheme_member_no": null,
   "results": [{"test": "Test de paludisme", "status": "ready", "ready_at": "2026-09-14"}],
   "prescriptions": [{"drug": "Amoxicilline", "dose": "500 mg", "schedule": "3 fois par jour pendant 7 jours", "refills_left": 0}]},
  {"id": "pt-b-002", "region": "B", "name": "Kouassi Yao", "phone": "+225 07 555 2002", "preferred_language": "fr", "scheme_member_no": null,
   "results": [{"test": "Glycémie", "status": "pending", "ready_at": "2026-09-20"}], "prescriptions": []}
]
```

- [ ] **Step 3: Write the failing tests**

```python
# tests/test_patient_tools.py
from medibridge.tools import patient as p, store


def test_find_clinic_filters_by_region_and_service(data_dir):
    r = p.find_clinic(region="B", service="maternity")
    assert r["status"] == "ok"
    assert [c["id"] for c in r["clinics"]] == ["cl-b1"]


def test_find_clinic_unknown_region_is_not_found(data_dir):
    assert p.find_clinic(region="Z")["status"] == "not_found"


def test_get_availability_lists_open_slots_for_date(data_dir):
    r = p.get_availability(clinic_id="cl-a1", service="general", date="2026-09-21")
    assert [s["slot_id"] for s in r["slots"]] == ["sl-a1-01", "sl-a1-02"]


def test_book_appointment_marks_slot_and_creates_record(data_dir):
    r = p.book_appointment(patient_id="pt-a-001", slot_id="sl-a1-01")
    assert r["status"] == "ok" and r["appointment_id"] == "ap-1"
    assert r["clinic"] == "MediBridge Rosebank"
    slot = next(s for s in store.load("slots") if s["id"] == "sl-a1-01")
    assert slot["booked_by"] == "pt-a-001"


def test_book_appointment_twice_is_error(data_dir):
    p.book_appointment(patient_id="pt-a-001", slot_id="sl-a1-01")
    r = p.book_appointment(patient_id="pt-a-002", slot_id="sl-a1-01")
    assert r["status"] == "error"


def test_reschedule_moves_booking(data_dir):
    ap = p.book_appointment(patient_id="pt-a-001", slot_id="sl-a1-01")["appointment_id"]
    r = p.reschedule_or_cancel(appointment_id=ap, new_slot_id="sl-a1-02")
    assert r["status"] == "ok" and r["start"] == "2026-09-21T09:00"
    slots = {s["id"]: s["booked_by"] for s in store.load("slots")}
    assert slots["sl-a1-01"] is None and slots["sl-a1-02"] == "pt-a-001"


def test_cancel_frees_slot(data_dir):
    ap = p.book_appointment(patient_id="pt-a-001", slot_id="sl-a1-01")["appointment_id"]
    r = p.reschedule_or_cancel(appointment_id=ap)
    assert r["status"] == "ok" and r["cancelled"] is True


def test_results_status_never_returns_values(data_dir):
    r = p.results_status(patient_id="pt-a-001")
    assert r["results"][0] == {"test": "Full blood count", "status": "ready", "ready_at": "2026-09-15"}
    assert "value" not in str(r)


def test_medication_schedule_from_own_record(data_dir):
    r = p.medication_schedule(patient_id="pt-b-001")
    assert r["prescriptions"][0]["drug"] == "Amoxicilline"


def test_escalate_creates_ticket(data_dir):
    r = p.escalate_to_human(patient_id="pt-b-002", reason="chest pain", urgency="high")
    assert r["status"] == "ok" and r["ticket_id"] == "esc-1"
    assert "urgent" in r["next_step"].lower() or "emergency" in r["next_step"].lower()
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_patient_tools.py -q`
Expected: FAIL with `ImportError: cannot import name 'patient'`

- [ ] **Step 5: Write the implementation**

```python
# medibridge/tools/patient.py
"""Patient-facing tools. Administrative and informational only. Never clinical advice."""
from . import store

EMERGENCY = {"A": "call 10177 (ambulance) or go to the nearest emergency room",
             "B": "appelez le 18 (SAMU) ou rendez-vous aux urgences les plus proches"}


def _clinic(clinic_id: str) -> dict | None:
    return next((c for c in store.load("clinics") if c["id"] == clinic_id), None)


def _patient(patient_id: str | None) -> dict | None:
    return next((p for p in store.load("patients") if p["id"] == patient_id), None)


def find_clinic(region: str, city: str | None = None, service: str | None = None) -> dict:
    """Find MediBridge clinics in a region, optionally filtered by city and service."""
    rows = [c for c in store.load("clinics") if c["region"] == region]
    if city:
        rows = [c for c in rows if c["city"].lower() == city.lower()]
    if service:
        rows = [c for c in rows if service.lower() in c["services"]]
    if not rows:
        return {"status": "not_found", "clinics": []}
    return {"status": "ok", "clinics": rows}


def get_availability(clinic_id: str, service: str, date: str) -> dict:
    """List open appointment slots at a clinic for a service on a date (YYYY-MM-DD)."""
    if not _clinic(clinic_id):
        return {"status": "not_found", "slots": []}
    slots = [{"slot_id": s["id"], "start": s["start"]}
             for s in store.load("slots")
             if s["clinic_id"] == clinic_id and s["service"] == service.lower()
             and s["start"].startswith(date) and s["booked_by"] is None]
    return {"status": "ok" if slots else "not_found", "slots": slots}


def book_appointment(patient_id: str, slot_id: str) -> dict:
    """Book an open slot for a patient. Returns the appointment id."""
    if not _patient(patient_id):
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    slots = store.load("slots")
    slot = next((s for s in slots if s["id"] == slot_id), None)
    if slot is None:
        return {"status": "not_found", "message": f"no slot {slot_id}"}
    if slot["booked_by"]:
        return {"status": "error", "message": "slot already booked"}
    slot["booked_by"] = patient_id
    store.save("slots", slots)
    clinic = _clinic(slot["clinic_id"])
    ap = store.append("appointments", {
        "id": f"ap-{len(store.load('appointments')) + 1}", "patient_id": patient_id,
        "slot_id": slot_id, "clinic_id": slot["clinic_id"], "service": slot["service"],
        "start": slot["start"], "status": "booked"})
    return {"status": "ok", "appointment_id": ap["id"], "clinic": clinic["name"], "start": slot["start"]}


def reschedule_or_cancel(appointment_id: str, new_slot_id: str | None = None) -> dict:
    """Move an appointment to a new slot, or cancel it when no new slot is given."""
    aps = store.load("appointments")
    ap = next((a for a in aps if a["id"] == appointment_id), None)
    if ap is None or ap["status"] == "cancelled":
        return {"status": "not_found", "message": f"no active appointment {appointment_id}"}
    slots = store.load("slots")
    old = next(s for s in slots if s["id"] == ap["slot_id"])
    if new_slot_id is None:
        old["booked_by"] = None
        ap["status"] = "cancelled"
        store.save("slots", slots); store.save("appointments", aps)
        return {"status": "ok", "cancelled": True}
    new = next((s for s in slots if s["id"] == new_slot_id), None)
    if new is None or new["booked_by"]:
        return {"status": "error", "message": "new slot unavailable"}
    old["booked_by"] = None
    new["booked_by"] = ap["patient_id"]
    ap.update(slot_id=new_slot_id, clinic_id=new["clinic_id"], start=new["start"])
    store.save("slots", slots); store.save("appointments", aps)
    return {"status": "ok", "cancelled": False, "start": new["start"]}


def results_status(patient_id: str) -> dict:
    """Say whether each of a patient's lab results is ready. Never returns result values."""
    pt = _patient(patient_id)
    if pt is None:
        return {"status": "not_found", "results": []}
    return {"status": "ok", "results": [{"test": r["test"], "status": r["status"], "ready_at": r["ready_at"]}
                                        for r in pt["results"]]}


def medication_schedule(patient_id: str) -> dict:
    """Return the dosing schedule from the patient's own prescription record."""
    pt = _patient(patient_id)
    if pt is None:
        return {"status": "not_found", "prescriptions": []}
    return {"status": "ok", "prescriptions": pt["prescriptions"]}


def escalate_to_human(patient_id: str | None, reason: str, urgency: str = "normal") -> dict:
    """Hand the conversation to a nurse line. Use for any symptom, clinical, or urgent question."""
    pt = _patient(patient_id)
    region = pt["region"] if pt else "A"
    ticket = store.append("escalations", {"id": f"esc-{len(store.load('escalations')) + 1}",
                                          "patient_id": patient_id, "reason": reason, "urgency": urgency})
    if urgency == "high":
        step = f"This is urgent: {EMERGENCY[region]}. A nurse has also been paged."
    else:
        step = "A nurse will call you back within two hours on your registered number."
    return {"status": "ok", "ticket_id": ticket["id"], "next_step": step}
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_patient_tools.py -q`
Expected: 10 passed

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "Add patient tools and seed slots and patients"
```

### Task 4: Staff and region-gated tools

**Files:**
- Create: `medibridge/data/stock.json`, `medibridge/data/schemes.json`, `medibridge/tools/staff.py`, `tests/test_staff_tools.py`

**Interfaces:**
- Produces:
  - `lookup_patient(patient_id: str) -> dict` with `patient: {id, name, phone, region, preferred_language}`. Deliberately takes an id, not a phone number: the corpus shows staff trying phone numbers, which becomes a proposal.
  - `todays_schedule(clinic_id: str, date: str) -> dict` with `appointments: list`
  - `drug_stock(clinic_id: str, item: str) -> dict` with `quantity, reorder_level, below_reorder`
  - `send_reminder(patient_id: str, appointment_id: str, channel: str = "sms") -> dict`. In region B only `whatsapp` works; `sms` returns `error` "sms gateway not configured for region B". In region A only `sms` works.
  - `check_scheme_eligibility(scheme_member_no: str, service: str) -> dict` with `eligible: bool, scheme`
  - `mobile_money_payment_link(patient_id: str, amount: int, provider: str) -> dict` with `link`

- [ ] **Step 1: Write seed stock and schemes**

`medibridge/data/stock.json`:
```json
[
  {"clinic_id": "cl-a1", "item": "amoxicillin 500mg", "quantity": 120, "reorder_level": 50},
  {"clinic_id": "cl-a1", "item": "metformin 500mg", "quantity": 30, "reorder_level": 40},
  {"clinic_id": "cl-b1", "item": "amoxicilline 500mg", "quantity": 15, "reorder_level": 40},
  {"clinic_id": "cl-b1", "item": "paracétamol 500mg", "quantity": 400, "reorder_level": 100},
  {"clinic_id": "cl-b2", "item": "TDR paludisme", "quantity": 8, "reorder_level": 25}
]
```

`medibridge/data/schemes.json`:
```json
[
  {"member_no": "DHS-448812", "scheme": "Discovery Health", "status": "active", "covered_services": ["general", "lab", "paediatrics", "physio"]},
  {"member_no": "BON-102233", "scheme": "Bonitas", "status": "lapsed", "covered_services": ["general"]}
]
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_staff_tools.py
from medibridge.tools import patient as p, staff as s


def test_lookup_patient_by_id(data_dir):
    r = s.lookup_patient(patient_id="pt-b-001")
    assert r["status"] == "ok" and r["patient"]["name"] == "Aminata Diallo"
    assert "results" not in r["patient"]


def test_lookup_patient_by_phone_is_not_found(data_dir):
    assert s.lookup_patient(patient_id="+221 77 555 2001")["status"] == "not_found"


def test_todays_schedule_lists_booked(data_dir):
    p.book_appointment(patient_id="pt-a-001", slot_id="sl-a1-01")
    r = s.todays_schedule(clinic_id="cl-a1", date="2026-09-21")
    assert [a["patient_id"] for a in r["appointments"]] == ["pt-a-001"]


def test_drug_stock_flags_reorder(data_dir):
    r = s.drug_stock(clinic_id="cl-b1", item="amoxicilline 500mg")
    assert r["status"] == "ok" and r["below_reorder"] is True


def test_drug_stock_unknown_item(data_dir):
    assert s.drug_stock(clinic_id="cl-b1", item="insulin")["status"] == "not_found"


def test_send_reminder_sms_fails_in_region_b(data_dir):
    ap = p.book_appointment(patient_id="pt-b-001", slot_id="sl-b1-01")["appointment_id"]
    r = s.send_reminder(patient_id="pt-b-001", appointment_id=ap, channel="sms")
    assert r["status"] == "error" and "region B" in r["message"]


def test_send_reminder_whatsapp_works_in_region_b(data_dir):
    ap = p.book_appointment(patient_id="pt-b-001", slot_id="sl-b1-01")["appointment_id"]
    r = s.send_reminder(patient_id="pt-b-001", appointment_id=ap, channel="whatsapp")
    assert r["status"] == "ok"


def test_scheme_eligibility(data_dir):
    assert s.check_scheme_eligibility(scheme_member_no="DHS-448812", service="physio")["eligible"] is True
    assert s.check_scheme_eligibility(scheme_member_no="BON-102233", service="general")["eligible"] is False


def test_mobile_money_link(data_dir):
    r = s.mobile_money_payment_link(patient_id="pt-b-001", amount=15000, provider="orange_money")
    assert r["status"] == "ok" and r["link"].startswith("https://pay.medibridge.example/")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_staff_tools.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Write the implementation**

```python
# medibridge/tools/staff.py
"""Staff-facing tools and region-gated tools."""
from . import store

CHANNELS = {"A": {"sms"}, "B": {"whatsapp"}}


def _patient(patient_id: str) -> dict | None:
    return next((p for p in store.load("patients") if p["id"] == patient_id), None)


def lookup_patient(patient_id: str) -> dict:
    """Look up a patient's contact record by MediBridge patient id (pt-...)."""
    pt = _patient(patient_id)
    if pt is None:
        return {"status": "not_found", "message": f"no patient with id {patient_id!r}; ids look like pt-a-001"}
    keys = ("id", "name", "phone", "region", "preferred_language")
    return {"status": "ok", "patient": {k: pt[k] for k in keys}}


def todays_schedule(clinic_id: str, date: str) -> dict:
    """List booked appointments at a clinic on a date (YYYY-MM-DD)."""
    aps = [a for a in store.load("appointments")
           if a["clinic_id"] == clinic_id and a["start"].startswith(date) and a["status"] == "booked"]
    return {"status": "ok" if aps else "not_found", "appointments": aps}


def drug_stock(clinic_id: str, item: str) -> dict:
    """Current stock of an item at a clinic, and whether it is below reorder level."""
    row = next((r for r in store.load("stock")
                if r["clinic_id"] == clinic_id and r["item"].lower() == item.lower()), None)
    if row is None:
        return {"status": "not_found", "message": f"{item!r} is not in the catalogue for {clinic_id}"}
    return {"status": "ok", "quantity": row["quantity"], "reorder_level": row["reorder_level"],
            "below_reorder": row["quantity"] < row["reorder_level"]}


def send_reminder(patient_id: str, appointment_id: str, channel: str = "sms") -> dict:
    """Send an appointment reminder. Channel must be configured for the patient's region."""
    pt = _patient(patient_id)
    if pt is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    if channel not in CHANNELS[pt["region"]]:
        return {"status": "error", "message": f"{channel} gateway not configured for region {pt['region']}"}
    store.append("reminders", {"patient_id": patient_id, "appointment_id": appointment_id, "channel": channel})
    return {"status": "ok", "channel": channel}


def check_scheme_eligibility(scheme_member_no: str, service: str) -> dict:
    """Region A only. Check whether a medical scheme member is covered for a service."""
    row = next((r for r in store.load("schemes") if r["member_no"] == scheme_member_no), None)
    if row is None:
        return {"status": "not_found", "eligible": False}
    ok = row["status"] == "active" and service in row["covered_services"]
    return {"status": "ok", "eligible": ok, "scheme": row["scheme"], "member_status": row["status"]}


def mobile_money_payment_link(patient_id: str, amount: int, provider: str) -> dict:
    """Region B only. Create a mobile money payment link (orange_money, wave, mtn)."""
    if _patient(patient_id) is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    if provider not in {"orange_money", "wave", "mtn"}:
        return {"status": "error", "message": "unknown provider"}
    row = store.append("payments", {"patient_id": patient_id, "amount": amount, "provider": provider})
    n = len(store.load("payments"))
    return {"status": "ok", "link": f"https://pay.medibridge.example/{provider}/{n}", "amount": amount}
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Add staff tools and region-gated tools with seed stock and schemes"
```

### Task 5: Tool registry

**Files:**
- Create: `medibridge/tools/registry.py`, `tests/test_registry.py`

**Interfaces:**
- Produces: `ToolSpec` dataclass `(name: str, fn: Callable, personas: frozenset[str], regions: frozenset[str])`, `TOOLS: list[ToolSpec]`, `select(persona: str, region: str) -> list[ToolSpec]`. `persona` and `region` accept `"all"`. Descriptions come from each function's docstring, so every tool function must have one.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
from medibridge.tools import registry as r


def test_every_tool_has_docstring_and_tags():
    for t in r.TOOLS:
        assert t.fn.__doc__, t.name
        assert t.personas and t.regions, t.name


def test_names_are_unique():
    names = [t.name for t in r.TOOLS]
    assert len(names) == len(set(names))


def test_select_patient_region_b_excludes_scheme_tool():
    names = {t.name for t in r.select("patient", "B")}
    assert "book_appointment" in names
    assert "mobile_money_payment_link" in names
    assert "check_scheme_eligibility" not in names
    assert "drug_stock" not in names


def test_select_staff_region_a():
    names = {t.name for t in r.select("staff", "A")}
    assert {"lookup_patient", "todays_schedule", "drug_stock", "send_reminder", "check_scheme_eligibility"} <= names
    assert "book_appointment" not in names


def test_select_all_returns_everything():
    assert len(r.select("all", "all")) == len(r.TOOLS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_registry.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write the implementation**

```python
# medibridge/tools/registry.py
"""The single list of MediBridge tools. Both front doors read this and nothing else.

To add a tool: write the function in patient.py or staff.py with a docstring,
then add one ToolSpec line below. That is the whole procedure. /expand does it for you.
"""
from dataclasses import dataclass
from typing import Callable

from . import patient as p, staff as s

ALL_REGIONS = frozenset({"A", "B"})


@dataclass(frozen=True)
class ToolSpec:
    name: str
    fn: Callable
    personas: frozenset[str]
    regions: frozenset[str]


def _t(fn, personas, regions=ALL_REGIONS) -> ToolSpec:
    return ToolSpec(fn.__name__, fn, frozenset(personas), frozenset(regions))


TOOLS: list[ToolSpec] = [
    _t(p.find_clinic, {"patient", "staff"}),
    _t(p.get_availability, {"patient", "staff"}),
    _t(p.book_appointment, {"patient", "staff"}),
    _t(p.reschedule_or_cancel, {"patient", "staff"}),
    _t(p.results_status, {"patient"}),
    _t(p.medication_schedule, {"patient"}),
    _t(p.escalate_to_human, {"patient"}),
    _t(s.lookup_patient, {"staff"}),
    _t(s.todays_schedule, {"staff"}),
    _t(s.drug_stock, {"staff"}),
    _t(s.send_reminder, {"staff"}),
    _t(s.check_scheme_eligibility, {"patient", "staff"}, {"A"}),
    _t(s.mobile_money_payment_link, {"patient", "staff"}, {"B"}),
]


def select(persona: str, region: str) -> list[ToolSpec]:
    return [t for t in TOOLS
            if (persona == "all" or persona in t.personas)
            and (region == "all" or region in t.regions)]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_registry.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add the tool registry with persona and region tags"
```

### Task 6: MCP server and project registration

**Files:**
- Create: `medibridge/mcp_server.py`, `medibridge/tools/calllog.py`, `.mcp.json`, `tests/test_mcp_server.py`, `tests/test_calllog.py`

**Interfaces:**
- Consumes: `registry.select`
- Produces: `calllog.log_call(tool: str, args: dict, result: dict, *, region: str, persona: str, session_id: str) -> None` appending one JSON line to `$MEDIBRIDGE_LOG_DIR/tool_calls.jsonl` (default `medibridge/logs`). `calllog.wrap(fn, region, persona, session_id) -> Callable` returns a function with the same signature that logs. `mcp_server.build_server(persona: str, region: str, session_id: str) -> MCPServer`.
- Log line shape: `{"ts": iso, "session_id": str, "persona": str, "region": str, "tool": str, "args": dict, "status": str, "error": str | null}`.

- [ ] **Step 1: Write the failing calllog test**

```python
# tests/test_calllog.py
import json
from medibridge.tools import calllog


def test_wrap_logs_call_and_preserves_signature(log_dir, data_dir):
    def add(a: int, b: int = 1) -> dict:
        """Add."""
        return {"status": "ok", "sum": a + b}
    w = calllog.wrap(add, region="B", persona="staff", session_id="s1")
    assert w(a=2) == {"status": "ok", "sum": 3}
    import inspect
    assert list(inspect.signature(w).parameters) == ["a", "b"]
    assert w.__doc__ == "Add."
    line = json.loads((log_dir / "tool_calls.jsonl").read_text().strip())
    assert line["tool"] == "add" and line["args"] == {"a": 2} and line["status"] == "ok"
    assert line["region"] == "B" and line["persona"] == "staff" and line["session_id"] == "s1"


def test_wrap_logs_error_status(log_dir, data_dir):
    def boom() -> dict:
        """Boom."""
        return {"status": "error", "message": "nope"}
    calllog.wrap(boom, region="A", persona="staff", session_id="s2")()
    line = json.loads((log_dir / "tool_calls.jsonl").read_text().strip())
    assert line["status"] == "error" and line["error"] == "nope"
```

- [ ] **Step 2: Write calllog**

```python
# medibridge/tools/calllog.py
"""Append-only log of every tool call. This is the only product signal the MCP path gives you."""
import functools
import json
import os
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[1] / "logs"


def log_dir() -> Path:
    return Path(os.environ.get("MEDIBRIDGE_LOG_DIR", _DEFAULT))


def log_call(tool: str, args: dict, result: dict, *, region: str, persona: str, session_id: str) -> None:
    d = log_dir()
    d.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session_id": session_id,
            "persona": persona, "region": region, "tool": tool, "args": args,
            "status": result.get("status", "unknown"), "error": result.get("message") if result.get("status") != "ok" else None}
    with (d / "tool_calls.jsonl").open("a") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def wrap(fn, *, region: str, persona: str, session_id: str):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        result = fn(*args, **kwargs)
        log_call(fn.__name__, kwargs, result, region=region, persona=persona, session_id=session_id)
        return result
    return inner
```

- [ ] **Step 3: Run calllog tests**

Run: `uv run pytest tests/test_calllog.py -q`
Expected: 2 passed

- [ ] **Step 4: Write the failing MCP server test**

```python
# tests/test_mcp_server.py
import json
import pytest
from mcp import Client

from medibridge.mcp_server import build_server


@pytest.mark.anyio
async def test_patient_region_b_server_lists_gated_tools(data_dir, log_dir):
    server = build_server(persona="patient", region="B", session_id="t1")
    async with Client(server) as c:
        names = {t.name for t in (await c.list_tools()).tools}
    assert "mobile_money_payment_link" in names and "check_scheme_eligibility" not in names


@pytest.mark.anyio
async def test_call_tool_logs(data_dir, log_dir):
    server = build_server(persona="staff", region="A", session_id="t2")
    async with Client(server) as c:
        r = await c.call_tool("drug_stock", {"clinic_id": "cl-a1", "item": "metformin 500mg"})
    assert r.structured_content["below_reorder"] is True
    line = json.loads((log_dir / "tool_calls.jsonl").read_text().strip())
    assert line["tool"] == "drug_stock" and line["session_id"] == "t2"
```

- [ ] **Step 5: Run test to verify it fails**

Run: `uv run pytest tests/test_mcp_server.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 6: Write the server**

```python
# medibridge/mcp_server.py
"""Front door 1: the MediBridge tools over MCP.

Run by Claude Code via .mcp.json. Persona and region come from the environment so the
same server can be the staff surface for a hospital group (A) or the patient surface (B).
"""
import os
import uuid

from mcp.server import MCPServer

from medibridge.tools import calllog, registry


def build_server(persona: str, region: str, session_id: str) -> MCPServer:
    server = MCPServer("medibridge")
    for spec in registry.select(persona, region):
        server.add_tool(calllog.wrap(spec.fn, region=region, persona=persona, session_id=session_id),
                        name=spec.name, description=spec.fn.__doc__.strip())
    return server


if __name__ == "__main__":
    build_server(persona=os.environ.get("MEDIBRIDGE_PERSONA", "staff"),
                 region=os.environ.get("MEDIBRIDGE_REGION", "A"),
                 session_id=os.environ.get("MEDIBRIDGE_SESSION_ID") or uuid.uuid4().hex[:8]).run()
```

If `add_tool` fails to derive the schema through `functools.wraps`, replace `wrap` with a closure built by `exec` of the original signature is not acceptable; instead pass the original `spec.fn` to `add_tool` and have `build_server` install a `ToolManager`-level hook. Try `wraps` first; `inspect.signature` follows `__wrapped__`, which is what the SDK uses.

- [ ] **Step 7: Run tests**

Run: `uv run pytest -q`
Expected: all passed

- [ ] **Step 8: Write .mcp.json**

```json
{
  "mcpServers": {
    "medibridge": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${CLAUDE_PROJECT_DIR}", "python", "-m", "medibridge.mcp_server"],
      "env": {
        "MEDIBRIDGE_PERSONA": "${MEDIBRIDGE_PERSONA:-staff}",
        "MEDIBRIDGE_REGION": "${MEDIBRIDGE_REGION:-A}",
        "MEDIBRIDGE_LOG_DIR": "${CLAUDE_PROJECT_DIR}/medibridge/logs"
      }
    }
  }
}
```

- [ ] **Step 9: Verify the server loads in a real headless call**

Run: `MEDIBRIDGE_PERSONA=staff MEDIBRIDGE_REGION=A claude -p "List the tools you have from medibridge, names only." --output-format json --tools "" --model haiku | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])"`
Expected: a list including `drug_stock` and `check_scheme_eligibility`. If the server does not load, run `claude mcp list` from the repo root and read the error.

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "Add MCP server with call logging and project registration"
```

### Task 7: Setup check and /setup skill

**Files:**
- Create: `scripts/check.py`, `.claude/skills/setup/SKILL.md`, `README.md`

**Interfaces:**
- Produces: `scripts/check.py` exits 0 and prints one line per check: Python version, `mcp` import, tool count per persona and region, `claude --version`, and the two commands to start each front door.

- [ ] **Step 1: Write scripts/check.py**

```python
"""Pre-flight for the course. Run: uv run python scripts/check.py"""
import shutil
import subprocess
import sys

from medibridge.tools import registry


def main() -> int:
    ok = True
    print(f"python {sys.version.split()[0]}")
    try:
        import mcp  # noqa: F401
        print("mcp import ok")
    except ImportError as e:
        print(f"mcp import FAILED: {e}"); ok = False
    for persona in ("patient", "staff"):
        for region in ("A", "B"):
            print(f"tools {persona}/{region}: {len(registry.select(persona, region))}")
    if shutil.which("claude"):
        v = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"claude {v}")
    else:
        print("claude not found on PATH"); ok = False
    print("\nFront door 1 (MCP): open `claude` in this folder, then ask it to check drug stock at cl-a1.")
    print("Front door 2 (agent): uv run python -m medibridge.agent.server  then open http://127.0.0.1:8765")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write the /setup skill**

```markdown
---
name: setup
description: Prepare this laptop for the MediBridge course. Installs uv if missing, syncs dependencies, runs the pre-flight check, and explains the two front doors.
disable-model-invocation: true
---

You are preparing an attendee's machine for the course. Do these in order, and stop with a clear message if any step fails.

1. Run `uv --version`. If it is missing, install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`, then tell the user to restart their terminal if `uv` is still not found.
2. Run `uv sync` in the repo root.
3. Run `uv run pytest -q` and report the count.
4. Run `uv run python scripts/check.py` and show its output.
5. Confirm the MCP server is registered by running `claude mcp list` and checking that `medibridge` appears. If it says the project server needs approval, tell the user to accept it when prompted in their next interactive session.
6. Finish by printing, in plain words, how to open each front door:
   - Front door 1: this Claude Code session already has the MediBridge tools. Ask: "Check the stock of metformin 500mg at cl-a1."
   - Front door 2: run `uv run python -m medibridge.agent.server` in a terminal and open http://127.0.0.1:8765. (If that module does not exist yet, say the agent is built in a later step.)

Do not modify any files. Do not run anything outside the repo other than the uv installer.
```

- [ ] **Step 3: Write README.md** with: the one-line thesis, pre-work (clone, open Claude Code, run `/setup`), the two front doors, the skills table from the spec section 8, and a pointer to `docs/00-session-plan.md`. Keep it under 80 lines.

- [ ] **Step 4: Run the check**

Run: `uv run python scripts/check.py`
Expected: exit 0, tool counts patient/A 7, patient/B 8, staff/A 9, staff/B 9

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add pre-flight check, /setup skill, and README"
```

**Phase 1 checkpoint:** an attendee can clone, run `/setup`, and use the MediBridge tools from their own Claude Code. Front door 1 works.

---

## Phase 2: Controlled agent front door

### Task 8: Headless turn runner

**Files:**
- Create: `medibridge/agent/__init__.py`, `medibridge/agent/claude_runner.py`, `tests/test_claude_runner.py`

**Interfaces:**
- Produces:
  - `TurnResult` dataclass `(reply: str, session_id: str, tool_uses: list[dict], cost_usd: float, is_error: bool)`. Each tool use is `{"name": str, "input": dict, "result": str, "is_error": bool}` with the `mcp__medibridge__` prefix stripped from `name`.
  - `build_command(message: str, *, system_prompt: str, mcp_config: dict, session_id: str | None, model: str | None, cwd: Path) -> list[str]`
  - `parse_stream(lines: Iterable[str]) -> TurnResult`
  - `run_turn(message, *, system_prompt, mcp_config, session_id=None, model=None, cwd=REPO_ROOT, runner=subprocess.run) -> TurnResult`. `runner` is called with the command list and must return an object with `.stdout` (str) and `.returncode`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_claude_runner.py
import json
from types import SimpleNamespace

from medibridge.agent import claude_runner as cr

STREAM = [
    {"type": "system", "subtype": "init", "session_id": "sess-1"},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "tu1", "name": "mcp__medibridge__get_availability",
         "input": {"clinic_id": "cl-b1", "service": "general", "date": "2026-09-21"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "tu1", "content": [{"type": "text", "text": "{\"status\": \"ok\"}"}], "is_error": False}]}},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "Il y a deux créneaux."}]}},
    {"type": "result", "subtype": "success", "is_error": False, "result": "Il y a deux créneaux.",
     "session_id": "sess-1", "total_cost_usd": 0.01},
]


def test_parse_stream_collects_reply_session_and_tools():
    r = cr.parse_stream(json.dumps(l) for l in STREAM)
    assert r.reply == "Il y a deux créneaux." and r.session_id == "sess-1"
    assert r.tool_uses == [{"name": "get_availability",
                            "input": {"clinic_id": "cl-b1", "service": "general", "date": "2026-09-21"},
                            "result": '{"status": "ok"}', "is_error": False}]
    assert r.cost_usd == 0.01 and r.is_error is False


def test_build_command_locks_down_tools(tmp_path):
    cmd = cr.build_command("hi", system_prompt="SP", mcp_config={"mcpServers": {}}, session_id=None, model=None, cwd=tmp_path)
    assert cmd[:2] == ["claude", "-p"] and "hi" in cmd
    for flag in ("--output-format", "--verbose", "--strict-mcp-config", "--tools", "--allowedTools", "--permission-mode", "--system-prompt", "--mcp-config"):
        assert flag in cmd
    assert cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--allowedTools") + 1] == "mcp__medibridge__*"
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert "--resume" not in cmd


def test_build_command_resumes_when_session_given(tmp_path):
    cmd = cr.build_command("hi", system_prompt="SP", mcp_config={}, session_id="abc", model="sonnet", cwd=tmp_path)
    assert cmd[cmd.index("--resume") + 1] == "abc" and cmd[cmd.index("--model") + 1] == "sonnet"


def test_run_turn_uses_injected_runner(tmp_path):
    calls = []
    def fake(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(stdout="\n".join(json.dumps(l) for l in STREAM), returncode=0)
    r = cr.run_turn("hi", system_prompt="SP", mcp_config={}, cwd=tmp_path, runner=fake)
    assert r.session_id == "sess-1" and calls and calls[0][0] == "claude"


def test_run_turn_reports_nonzero_exit(tmp_path):
    def fake(cmd, **kw):
        return SimpleNamespace(stdout="", returncode=1, stderr="boom")
    r = cr.run_turn("hi", system_prompt="SP", mcp_config={}, cwd=tmp_path, runner=fake)
    assert r.is_error and "boom" in r.reply
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_claude_runner.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write the implementation**

```python
# medibridge/agent/claude_runner.py
"""One conversational turn through headless Claude Code.

This is the whole trick of the controlled agent: it is *our* Claude Code configuration,
with a locked system prompt and only the MediBridge MCP tools, instead of the customer's.
"""
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
PREFIX = "mcp__medibridge__"


@dataclass
class TurnResult:
    reply: str
    session_id: str
    tool_uses: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    is_error: bool = False


def build_command(message: str, *, system_prompt: str, mcp_config: dict, session_id: str | None,
                  model: str | None, cwd: Path) -> list[str]:
    cmd = ["claude", "-p", message,
           "--output-format", "stream-json", "--verbose",
           "--system-prompt", system_prompt,
           "--mcp-config", json.dumps(mcp_config), "--strict-mcp-config",
           "--tools", "",
           "--allowedTools", PREFIX + "*",
           "--permission-mode", "dontAsk",
           "--max-turns", "10"]
    if session_id:
        cmd += ["--resume", session_id]
    if model:
        cmd += ["--model", model]
    return cmd


def parse_stream(lines: Iterable[str]) -> TurnResult:
    pending: dict[str, dict] = {}
    tool_uses: list[dict] = []
    reply, session_id, cost, is_error = "", "", 0.0, False
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
                    pending[b["id"]] = rec
                    tool_uses.append(rec)
        elif t == "user":
            for b in d["message"]["content"]:
                if b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                    content = b.get("content")
                    if isinstance(content, list):
                        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
                    pending[b["tool_use_id"]].update(result=str(content or ""), is_error=bool(b.get("is_error")))
        elif t == "result":
            reply = d.get("result") or ""
            session_id = d.get("session_id", "")
            cost = float(d.get("total_cost_usd") or 0.0)
            is_error = bool(d.get("is_error"))
        elif t == "system" and d.get("subtype") == "init" and not session_id:
            session_id = d.get("session_id", "")
    return TurnResult(reply=reply, session_id=session_id, tool_uses=tool_uses, cost_usd=cost, is_error=is_error)


def run_turn(message: str, *, system_prompt: str, mcp_config: dict, session_id: str | None = None,
             model: str | None = None, cwd: Path = REPO_ROOT, runner=subprocess.run) -> TurnResult:
    cmd = build_command(message, system_prompt=system_prompt, mcp_config=mcp_config,
                        session_id=session_id, model=model, cwd=cwd)
    proc = runner(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 and not proc.stdout.strip():
        return TurnResult(reply=f"agent error: {getattr(proc, 'stderr', '')}".strip(), session_id=session_id or "", is_error=True)
    return parse_stream(proc.stdout.splitlines())
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_claude_runner.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add headless Claude Code turn runner with stream parsing"
```

### Task 9: Agent brief and prompt assembly

**Files:**
- Create: `medibridge/agent/brief.md`, `medibridge/agent/prompt.py`, `tests/test_prompt.py`

**Interfaces:**
- Produces: `prompt.system_prompt(region: str) -> str`, `prompt.mcp_config(region: str, session_id: str) -> dict` (the `--mcp-config` JSON for the patient persona, pointing at this repo, with `MEDIBRIDGE_SESSION_ID` set so tool-call logs and transcripts share an id).
- `brief.md` has a `## Region A` and `## Region B` section; `system_prompt` returns the common part plus the matching region section, and strips the other.

- [ ] **Step 1: Write brief.md** (this is the filled version of `templates/agent-brief.md`, which Task 16 derives from it)

```markdown
# MediBridge patient assistant

## Role
You are the MediBridge patient assistant. You help patients find clinics, book, move, or cancel appointments, learn whether lab results are ready, and see the dosing schedule on their own prescription. You do this only through the tools you have.

## Hard rules
- You do not diagnose, interpret symptoms, interpret results, or recommend treatment. Not even "it's probably nothing".
- Any symptom, pain, medication side effect, pregnancy concern, or "should I worry" question: call `escalate_to_human`. Use urgency `high` for chest pain, breathing difficulty, heavy bleeding, a child under two with fever, or anything the patient calls an emergency, and repeat the emergency instruction the tool returns word for word.
- Never state a result value. `results_status` only says ready or pending. If asked for the number, say the clinic will share it at the appointment or by the nurse call.
- Never invent availability, prices, or clinic details. If a tool returns `not_found` or `error`, say so plainly and offer the nearest alternative the tools support.
- If the patient asks for something no tool can do, say clearly that you cannot do it yet and offer `escalate_to_human` if it matters to them. Do not pretend.
- Ask for the patient id (looks like pt-a-001) before any booking, result, or prescription action. Do not guess it.

## Style
- Short messages. One question at a time. Confirm before booking: clinic, service, date, time.
- Match the patient's language. If they switch, switch.

## Logging
Every conversation is stored with the tools you used and whether you escalated. Product managers read them. Be clear about what you could not do; that is how tools get added.

## Region A
Context: urban private clinics with a patient portal. Patients expect scheme eligibility checks, results, renewals, referrals. Language: English. Payment: medical scheme or card. `check_scheme_eligibility` is available; offer it before booking a specialist service. Emergency number: 10177.

## Region B
Contexte : réseau de cliniques joignable par WhatsApp. Les patients attendent des réservations fiables, des rappels, et de savoir si leurs résultats sont prêts. Langue : français par défaut ; si le patient écrit en wolof ou en anglais, réponds dans sa langue si tu le peux, sinon en français simple. Paiement : mobile money ou espèces. `mobile_money_payment_link` est disponible (orange_money, wave, mtn). Numéro d'urgence : 18.
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_prompt.py
from medibridge.agent import prompt


def test_system_prompt_includes_only_requested_region():
    a = prompt.system_prompt("A")
    b = prompt.system_prompt("B")
    assert "## Region A" in a and "## Region B" not in a
    assert "## Region B" in b and "## Region A" not in b
    assert "## Hard rules" in a and "## Hard rules" in b


def test_mcp_config_targets_patient_persona_and_region():
    cfg = prompt.mcp_config("B", "sess-9")
    srv = cfg["mcpServers"]["medibridge"]
    assert srv["env"]["MEDIBRIDGE_PERSONA"] == "patient"
    assert srv["env"]["MEDIBRIDGE_REGION"] == "B"
    assert srv["env"]["MEDIBRIDGE_SESSION_ID"] == "sess-9"
    assert srv["args"][-2:] == ["-m", "medibridge.mcp_server"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_prompt.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Write the implementation**

```python
# medibridge/agent/prompt.py
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def system_prompt(region: str) -> str:
    text = (HERE / "brief.md").read_text()
    head, *sections = re.split(r"^## Region ", text, flags=re.M)
    keep = [s for s in sections if s.startswith(region)]
    return head.rstrip() + "\n\n## Region " + keep[0] if keep else head


def mcp_config(region: str, session_id: str) -> dict:
    return {"mcpServers": {"medibridge": {
        "type": "stdio", "command": "uv",
        "args": ["run", "--directory", str(REPO_ROOT), "python", "-m", "medibridge.mcp_server"],
        "env": {"MEDIBRIDGE_PERSONA": "patient", "MEDIBRIDGE_REGION": region,
                "MEDIBRIDGE_SESSION_ID": session_id,
                "MEDIBRIDGE_LOG_DIR": os.environ.get("MEDIBRIDGE_LOG_DIR", str(REPO_ROOT / "medibridge" / "logs")),
                "MEDIBRIDGE_DATA_DIR": os.environ.get("MEDIBRIDGE_DATA_DIR", str(REPO_ROOT / "medibridge" / "data"))}}}}
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_prompt.py -q`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Add the patient agent brief and per-region prompt assembly"
```

### Task 10: Transcripts and the web agent

**Files:**
- Create: `medibridge/agent/transcripts.py`, `medibridge/agent/server.py`, `medibridge/agent/static/index.html`, `tests/test_transcripts.py`, `tests/test_server.py`

**Interfaces:**
- Produces:
  - `transcripts.record_turn(session_id: str, region: str, user: str, result: TurnResult) -> Path`. Writes `$MEDIBRIDGE_LOG_DIR/transcripts/<session_id>.json` of shape `{"session_id", "persona": "patient", "region", "started", "messages": [{"role", "content", "ts"}], "tool_uses": [...], "escalated": bool, "cost_usd": float}`. Creates the file on first turn, appends after.
  - `transcripts.load_all(dir: Path) -> list[dict]`.
  - FastAPI app `server.app` with `GET /` (the page), `POST /chat` body `{"message": str, "region": "A"|"B", "session_id": str | null}` returning `{"reply", "session_id", "tool_uses"}`. The first turn generates `session_id = uuid4().hex[:12]` **before** calling Claude and passes it in the MCP env; Claude's own session id is stored separately as `claude_session_id` in a module-level dict so `--resume` works. `server.run_turn_fn` is a module attribute tests replace.
  - `python -m medibridge.agent.server` serves on `127.0.0.1:8765`.

- [ ] **Step 1: Write the failing transcript test**

```python
# tests/test_transcripts.py
import json
from medibridge.agent import transcripts as tr
from medibridge.agent.claude_runner import TurnResult


def test_record_turn_creates_then_appends(log_dir):
    r1 = TurnResult(reply="Bonjour", session_id="c1", tool_uses=[], cost_usd=0.01)
    path = tr.record_turn("s1", "B", "salut", r1)
    r2 = TurnResult(reply="ok", session_id="c1", cost_usd=0.02,
                    tool_uses=[{"name": "escalate_to_human", "input": {"reason": "x"}, "result": "{}", "is_error": False}])
    tr.record_turn("s1", "B", "j'ai mal", r2)
    d = json.loads(path.read_text())
    assert [m["role"] for m in d["messages"]] == ["user", "assistant", "user", "assistant"]
    assert d["escalated"] is True and d["region"] == "B" and d["persona"] == "patient"
    assert abs(d["cost_usd"] - 0.03) < 1e-9
    assert tr.load_all(log_dir / "transcripts")[0]["session_id"] == "s1"
```

- [ ] **Step 2: Write transcripts.py**

```python
# medibridge/agent/transcripts.py
"""One JSON file per controlled-agent conversation. This is the product signal the agent path gives you."""
import json
from datetime import datetime, timezone
from pathlib import Path

from medibridge.tools.calllog import log_dir
from .claude_runner import TurnResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_turn(session_id: str, region: str, user: str, result: TurnResult) -> Path:
    d = log_dir() / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{session_id}.json"
    doc = json.loads(path.read_text()) if path.exists() else {
        "session_id": session_id, "persona": "patient", "region": region, "started": _now(),
        "messages": [], "tool_uses": [], "escalated": False, "cost_usd": 0.0}
    doc["messages"] += [{"role": "user", "content": user, "ts": _now()},
                        {"role": "assistant", "content": result.reply, "ts": _now()}]
    doc["tool_uses"] += result.tool_uses
    doc["escalated"] = doc["escalated"] or any(t["name"] == "escalate_to_human" for t in result.tool_uses)
    doc["cost_usd"] = round(doc["cost_usd"] + result.cost_usd, 6)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return path


def load_all(directory: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(directory).glob("*.json"))]
```

- [ ] **Step 3: Run transcript test**

Run: `uv run pytest tests/test_transcripts.py -q`
Expected: 1 passed

- [ ] **Step 4: Write the failing server test**

```python
# tests/test_server.py
import json
from fastapi.testclient import TestClient

from medibridge.agent import server
from medibridge.agent.claude_runner import TurnResult


def test_chat_roundtrip_records_transcript(log_dir, data_dir, monkeypatch):
    seen = {}
    def fake_run_turn(message, *, system_prompt, mcp_config, session_id=None, model=None, **kw):
        seen.update(message=message, sp=system_prompt, cfg=mcp_config, resume=session_id)
        return TurnResult(reply="Hello Thandi", session_id="claude-abc", tool_uses=[], cost_usd=0.0)
    monkeypatch.setattr(server, "run_turn_fn", fake_run_turn)
    c = TestClient(server.app)
    r = c.post("/chat", json={"message": "hi", "region": "A", "session_id": None}).json()
    assert r["reply"] == "Hello Thandi" and len(r["session_id"]) == 12
    assert "## Region A" in seen["sp"] and seen["resume"] is None
    assert seen["cfg"]["mcpServers"]["medibridge"]["env"]["MEDIBRIDGE_SESSION_ID"] == r["session_id"]
    r2 = c.post("/chat", json={"message": "book", "region": "A", "session_id": r["session_id"]}).json()
    assert seen["resume"] == "claude-abc" and r2["session_id"] == r["session_id"]
    doc = json.loads((log_dir / "transcripts" / f"{r['session_id']}.json").read_text())
    assert len(doc["messages"]) == 4


def test_index_served(log_dir):
    assert TestClient(server.app).get("/").status_code == 200
```

- [ ] **Step 5: Write server.py**

```python
# medibridge/agent/server.py
"""Front door 2: the controlled patient agent as a web page."""
import os
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import claude_runner, prompt, transcripts

app = FastAPI(title="MediBridge patient assistant")
STATIC = Path(__file__).resolve().parent / "static"
run_turn_fn = claude_runner.run_turn
_claude_sessions: dict[str, str] = {}


class ChatIn(BaseModel):
    message: str
    region: str = "B"
    session_id: str | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/chat")
def chat(body: ChatIn):
    sid = body.session_id or uuid.uuid4().hex[:12]
    result = run_turn_fn(body.message, system_prompt=prompt.system_prompt(body.region),
                         mcp_config=prompt.mcp_config(body.region, sid),
                         session_id=_claude_sessions.get(sid), model=os.environ.get("MEDIBRIDGE_MODEL"))
    if result.session_id:
        _claude_sessions[sid] = result.session_id
    transcripts.record_turn(sid, body.region, body.message, result)
    return {"reply": result.reply, "session_id": sid, "tool_uses": result.tool_uses, "is_error": result.is_error}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MEDIBRIDGE_PORT", "8765")))
```

- [ ] **Step 6: Write static/index.html.** Single file, no build step, no external assets. Requirements: a region toggle (two buttons, A and B); region A renders a light "portal" layout with an English header "MediBridge Patient Portal"; region B renders a chat-bubble layout with a green header "MediBridge sur WhatsApp" and French placeholder "Écrivez votre message"; switching region starts a new session; each assistant message shows a small grey line listing tool names used; `session_id` kept in a JS variable; a "New conversation" link. Fetch `POST /chat` with `{message, region, session_id}`. Disable the input while waiting and show "…". Keep under 150 lines.

- [ ] **Step 7: Run tests**

Run: `uv run pytest -q`
Expected: all passed

- [ ] **Step 8: Real smoke test**

Run: `uv run python -m medibridge.agent.server` in one terminal. In another: `curl -s -X POST localhost:8765/chat -H 'content-type: application/json' -d '{"message":"Je suis pt-b-001, y a-t-il un créneau le 21 septembre à Dakar ?","region":"B"}'`
Expected: JSON with a French reply mentioning two slots, `tool_uses` containing `find_clinic` or `get_availability`, and a transcript file under `medibridge/logs/transcripts/`. Then open `http://127.0.0.1:8765` in a browser and send one message in each region.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "Add the controlled patient agent web front door with transcripts"
```

**Phase 2 checkpoint:** both front doors work. The same booking request can be made through the attendee's Claude Code and through the web page, and each leaves its own kind of log.

---

## Phase 3: The PM loop

### Task 11: Structured calls through headless Claude Code

**Files:**
- Create: `medibridge/pm/__init__.py`, `medibridge/pm/claude_json.py`, `tests/test_claude_json.py`

**Interfaces:**
- Produces: `ask_json(prompt: str, schema: dict, *, model: str = "haiku", runner=subprocess.run, cwd=REPO_ROOT) -> dict`. Runs `claude -p <prompt> --output-format json --json-schema <schema> --tools "" --strict-mcp-config --no-session-persistence --model <model>` and returns `structured_output`. Raises `RuntimeError` with the CLI's `result`/stderr when `is_error` or when `structured_output` is missing. `ask_json_many(jobs: list[tuple[str, dict]], *, workers: int = 4, **kw) -> list[dict]` runs them in a thread pool, preserving order.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_claude_json.py
import json
from types import SimpleNamespace
import pytest
from medibridge.pm import claude_json as cj

SCHEMA = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}


def test_ask_json_returns_structured_output():
    def fake(cmd, **kw):
        assert "--json-schema" in cmd and cmd[cmd.index("--tools") + 1] == ""
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": 3}}), returncode=0, stderr="")
    assert cj.ask_json("p", SCHEMA, runner=fake) == {"x": 3}


def test_ask_json_raises_on_error():
    def fake(cmd, **kw):
        return SimpleNamespace(stdout=json.dumps({"is_error": True, "result": "rate limited"}), returncode=0, stderr="")
    with pytest.raises(RuntimeError, match="rate limited"):
        cj.ask_json("p", SCHEMA, runner=fake)


def test_ask_json_many_preserves_order():
    def fake(cmd, **kw):
        n = int(cmd[2])
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": n}}), returncode=0, stderr="")
    out = cj.ask_json_many([(str(i), SCHEMA) for i in range(6)], workers=3, runner=fake)
    assert [o["x"] for o in out] == list(range(6))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_claude_json.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write the implementation**

```python
# medibridge/pm/claude_json.py
"""LLM judgment as a function call, through headless Claude Code. No API key, no SDK."""
import json
import subprocess
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


def ask_json_many(jobs: list[tuple[str, dict]], *, workers: int = 4, **kw) -> list[dict]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda j: ask_json(j[0], j[1], **kw), jobs))
```

- [ ] **Step 4: Run tests, then one real call**

Run: `uv run pytest tests/test_claude_json.py -q` then
`uv run python -c "from medibridge.pm.claude_json import ask_json; print(ask_json('Is water wet? Answer with a boolean field wet.', {'type':'object','properties':{'wet':{'type':'boolean'}},'required':['wet']}))"`
Expected: 3 passed, then `{'wet': True}`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add structured JSON calls through headless Claude Code"
```

### Task 12: Taxonomy and classifier

**Files:**
- Create: `medibridge/pm/taxonomy.md`, `medibridge/pm/classify.py`, `tests/test_classify.py`, `tests/fixtures/transcript_b.json`, `tests/fixtures/staff_a.jsonl`

**Interfaces:**
- Produces:
  - `classify.load_items(corpus_dir: Path, log_dir: Path) -> list[dict]`. Each item is `{"id": str, "persona": str, "region": str, "text": str}`. Patient items come from `corpus/patient/region{A,B}/*.json` and `log_dir/transcripts/*.json`, text rendered as `user: ...\nassistant: ...` lines plus a `tools used:` line. Staff items come from `corpus/staff/region{A,B}/*.jsonl` and `log_dir/tool_calls.jsonl`, grouped by `session_id`, text rendered one call per line as `tool(args) -> status [error]`. Item id is the filename stem for corpus files and `live-<session_id>` for logs.
  - `classify.RECORD_SCHEMA` (one record) and `classify.BATCH_SCHEMA` (`{"records": [RECORD]}`).
  - `classify.classify_items(items, *, batch_size=8, ask=claude_json.ask_json_many) -> list[dict]` returning one record per item, in order, with the item's `id`, `persona`, `region` copied in even if the model mislabelled them.
  - `classify.main()` writes `medibridge/pm/out/classified.jsonl`.
- Record fields: `id, persona, region, intent (str), outcome (resolved|partial|failed|escalated), tools_used (list[str]), unmet_need (bool), unmet_need_description (str), proposed_tool (str, snake_case or ""), language (en|fr|wo|mixed), evidence_quote (str)`.

- [ ] **Step 1: Write taxonomy.md** (also the filled version of `templates/taxonomy.md`)

```markdown
# MediBridge conversation taxonomy

Classify each conversation or tool-log session into one record.

- **intent**: what the user was trying to get done, in five words or fewer. Examples: book appointment, check results ready, pay by mobile money, find clinic hours, renew prescription, look up patient by phone.
- **outcome**: `resolved` (they got it), `partial` (some of it), `failed` (nothing useful, no handoff), `escalated` (handed to a human).
- **tools_used**: tool names that appear in the conversation or log.
- **unmet_need**: true when the user asked for something the available tools could not do, whether or not the assistant handled it gracefully. A polite refusal is still an unmet need.
- **unmet_need_description**: one sentence, in English, of what they wanted.
- **proposed_tool**: a snake_case name for the tool that would have served the need, or empty. Reuse names across conversations when the need is the same: `pay_by_mobile_money`, `renew_prescription`, `lookup_patient_by_phone`, `send_results_by_sms`, `book_for_family_member`, `get_directions`, `request_specialist_referral`, `book_telehealth`, `get_result_values`, `check_scheme_eligibility`, `send_sms_confirmation`, `add_stock_item`.
- **language**: `en`, `fr`, `wo`, or `mixed`.
- **evidence_quote**: the single user line that best shows the need, verbatim, in its original language.

Rules: a clinical question that was escalated is `escalated` and not an unmet need. Do not propose tools that would give clinical advice or result values to patients; for those set unmet_need true and proposed_tool `get_result_values` so the report can show the demand and the guardrail together.
```

- [ ] **Step 2: Write fixtures**

`tests/fixtures/transcript_b.json`:
```json
{"session_id": "fx-b-1", "persona": "patient", "region": "B", "started": "2026-09-16T10:00:00+00:00",
 "messages": [{"role": "user", "content": "Bonjour, je veux payer ma consultation par Orange Money", "ts": ""},
              {"role": "assistant", "content": "Je peux créer un lien de paiement.", "ts": ""}],
 "tool_uses": [{"name": "mobile_money_payment_link", "input": {}, "result": "{}", "is_error": false}],
 "escalated": false, "cost_usd": 0.01}
```

`tests/fixtures/staff_a.jsonl`:
```
{"ts": "2026-09-16T10:00:00+00:00", "session_id": "fx-a-1", "persona": "staff", "region": "A", "tool": "lookup_patient", "args": {"patient_id": "+27 82 555 1001"}, "status": "not_found", "error": "no patient with id"}
{"ts": "2026-09-16T10:00:05+00:00", "session_id": "fx-a-1", "persona": "staff", "region": "A", "tool": "lookup_patient", "args": {"patient_id": "pt-a-001"}, "status": "ok", "error": null}
```

- [ ] **Step 3: Write the failing tests**

```python
# tests/test_classify.py
import json
import shutil
from pathlib import Path
from medibridge.pm import classify as c

FX = Path(__file__).parent / "fixtures"


def _corpus(tmp_path):
    (tmp_path / "corpus/patient/regionB").mkdir(parents=True)
    (tmp_path / "corpus/staff/regionA").mkdir(parents=True)
    shutil.copy(FX / "transcript_b.json", tmp_path / "corpus/patient/regionB/b-001.json")
    shutil.copy(FX / "staff_a.jsonl", tmp_path / "corpus/staff/regionA/a-001.jsonl")
    (tmp_path / "logs").mkdir()
    return tmp_path / "corpus", tmp_path / "logs"


def test_load_items_renders_both_kinds(tmp_path):
    items = c.load_items(*_corpus(tmp_path))
    by = {i["id"]: i for i in items}
    assert by["b-001"]["persona"] == "patient" and "user: Bonjour" in by["b-001"]["text"]
    assert "tools used: mobile_money_payment_link" in by["b-001"]["text"]
    assert by["a-001"]["persona"] == "staff" and "lookup_patient" in by["a-001"]["text"] and "not_found" in by["a-001"]["text"]


def test_classify_items_batches_and_copies_ids():
    items = [{"id": f"i{n}", "persona": "patient", "region": "A", "text": "user: hi"} for n in range(10)]
    calls = []
    def fake_ask(jobs, **kw):
        calls.append(len(jobs))
        out = []
        for prompt, schema in jobs:
            n = prompt.count("### item")
            out.append({"records": [{"id": "wrong", "persona": "staff", "region": "B", "intent": "x", "outcome": "resolved",
                                     "tools_used": [], "unmet_need": False, "unmet_need_description": "", "proposed_tool": "",
                                     "language": "en", "evidence_quote": ""} for _ in range(n)]})
        return out
    recs = c.classify_items(items, batch_size=4, ask=fake_ask)
    assert [r["id"] for r in recs] == [f"i{n}" for n in range(10)]
    assert recs[0]["persona"] == "patient" and recs[0]["region"] == "A"
    assert calls == [3]
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_classify.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 5: Write classify.py**

```python
# medibridge/pm/classify.py
"""Step 2 of the loop: turn every conversation and tool-log session into one structured record."""
import json
from collections import defaultdict
from pathlib import Path

from . import claude_json

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT = HERE / "out"
TAXONOMY = (HERE / "taxonomy.md").read_text()

RECORD_SCHEMA = {"type": "object", "properties": {
    "id": {"type": "string"}, "persona": {"type": "string"}, "region": {"type": "string"},
    "intent": {"type": "string"}, "outcome": {"type": "string", "enum": ["resolved", "partial", "failed", "escalated"]},
    "tools_used": {"type": "array", "items": {"type": "string"}}, "unmet_need": {"type": "boolean"},
    "unmet_need_description": {"type": "string"}, "proposed_tool": {"type": "string"},
    "language": {"type": "string", "enum": ["en", "fr", "wo", "mixed"]}, "evidence_quote": {"type": "string"}},
    "required": ["id", "persona", "region", "intent", "outcome", "tools_used", "unmet_need",
                 "unmet_need_description", "proposed_tool", "language", "evidence_quote"]}
BATCH_SCHEMA = {"type": "object", "properties": {"records": {"type": "array", "items": RECORD_SCHEMA}}, "required": ["records"]}


def _render_transcript(doc: dict) -> str:
    lines = [f"{m['role']}: {m['content']}" for m in doc["messages"]]
    lines.append("tools used: " + ", ".join(t["name"] for t in doc.get("tool_uses", [])))
    return "\n".join(lines)


def _render_calls(calls: list[dict]) -> str:
    return "\n".join(f"{c['tool']}({json.dumps(c['args'], ensure_ascii=False)}) -> {c['status']}"
                     + (f" [{c['error']}]" if c.get("error") else "") for c in calls)


def load_items(corpus_dir: Path, log_dir: Path) -> list[dict]:
    items = []
    for region in ("A", "B"):
        for p in sorted((corpus_dir / "patient" / f"region{region}").glob("*.json")):
            items.append({"id": p.stem, "persona": "patient", "region": region, "text": _render_transcript(json.loads(p.read_text()))})
    for p in sorted((log_dir / "transcripts").glob("*.json")) if (log_dir / "transcripts").exists() else []:
        doc = json.loads(p.read_text())
        items.append({"id": f"live-{p.stem}", "persona": "patient", "region": doc["region"], "text": _render_transcript(doc)})
    for region in ("A", "B"):
        for p in sorted((corpus_dir / "staff" / f"region{region}").glob("*.jsonl")):
            calls = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            items.append({"id": p.stem, "persona": "staff", "region": region, "text": _render_calls(calls)})
    live = log_dir / "tool_calls.jsonl"
    if live.exists():
        groups = defaultdict(list)
        for l in live.read_text().splitlines():
            if l.strip():
                c = json.loads(l); groups[c["session_id"]].append(c)
        for sid, calls in groups.items():
            items.append({"id": f"live-{sid}", "persona": calls[0]["persona"], "region": calls[0]["region"], "text": _render_calls(calls)})
    return items


def _prompt(batch: list[dict]) -> str:
    body = "\n\n".join(f"### item {i['id']} (persona={i['persona']}, region={i['region']})\n{i['text']}" for i in batch)
    return (f"{TAXONOMY}\n\nClassify each item below. Return exactly {len(batch)} records in the same order, "
            f"copying each item's id, persona and region.\n\n{body}")


def classify_items(items: list[dict], *, batch_size: int = 8, ask=claude_json.ask_json_many) -> list[dict]:
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    outputs = ask([(_prompt(b), BATCH_SCHEMA) for b in batches])
    records = []
    for batch, out in zip(batches, outputs):
        recs = out["records"]
        for item, rec in zip(batch, recs + [None] * (len(batch) - len(recs))):
            rec = dict(rec or {"intent": "unclassified", "outcome": "failed", "tools_used": [], "unmet_need": False,
                               "unmet_need_description": "", "proposed_tool": "", "language": "en", "evidence_quote": ""})
            rec.update(id=item["id"], persona=item["persona"], region=item["region"])
            records.append(rec)
    return records


def main() -> None:
    items = load_items(REPO_ROOT / "corpus", REPO_ROOT / "medibridge" / "logs")
    print(f"classifying {len(items)} items")
    records = classify_items(items)
    OUT.mkdir(exist_ok=True)
    with (OUT / "classified.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {OUT / 'classified.jsonl'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_classify.py -q`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "Add the conversation taxonomy and classifier"
```

### Task 13: Aggregation and report

**Files:**
- Create: `medibridge/pm/aggregate.py`, `tests/test_aggregate.py`, `tests/fixtures/classified.jsonl`

**Interfaces:**
- Produces: `aggregate.candidates(records: list[dict]) -> list[dict]` sorted by count desc, each `{"region", "persona", "proposed_tool", "count", "share" (of that region+persona's records, 2 dp), "quotes": list[str] (max 3), "nearest_tools": list[str] (top 2 tools_used among those records), "description": str (the most common unmet_need_description)}`. Records with `unmet_need` false or empty `proposed_tool` are skipped. `aggregate.report(records, cands) -> str` markdown. `aggregate.main()` reads `out/classified.jsonl`, writes `out/report.md` and `out/candidates.json`.
- Report layout: a title, an outcome table per region and persona (`resolved/partial/failed/escalated` counts), then for each region a table "Candidate expansions" with columns tool, count, share, nearest existing tool, example quote. Then a "Same product, two roadmaps" paragraph listing the top three tools per region side by side.

- [ ] **Step 1: Write the fixture** `tests/fixtures/classified.jsonl` (6 lines)

```
{"id": "b1", "persona": "patient", "region": "B", "intent": "pay mobile money", "outcome": "failed", "tools_used": ["find_clinic"], "unmet_need": true, "unmet_need_description": "Pay consultation by Orange Money", "proposed_tool": "pay_by_mobile_money", "language": "fr", "evidence_quote": "je veux payer par Orange Money"}
{"id": "b2", "persona": "patient", "region": "B", "intent": "pay mobile money", "outcome": "failed", "tools_used": [], "unmet_need": true, "unmet_need_description": "Pay by Wave", "proposed_tool": "pay_by_mobile_money", "language": "fr", "evidence_quote": "payer avec Wave"}
{"id": "b3", "persona": "patient", "region": "B", "intent": "book appointment", "outcome": "resolved", "tools_used": ["book_appointment"], "unmet_need": false, "unmet_need_description": "", "proposed_tool": "", "language": "fr", "evidence_quote": ""}
{"id": "a1", "persona": "patient", "region": "A", "intent": "renew prescription", "outcome": "partial", "tools_used": ["medication_schedule"], "unmet_need": true, "unmet_need_description": "Renew metformin script", "proposed_tool": "renew_prescription", "language": "en", "evidence_quote": "can you renew my metformin"}
{"id": "a2", "persona": "staff", "region": "A", "intent": "lookup by phone", "outcome": "partial", "tools_used": ["lookup_patient"], "unmet_need": true, "unmet_need_description": "Find patient by phone number", "proposed_tool": "lookup_patient_by_phone", "language": "en", "evidence_quote": ""}
{"id": "a3", "persona": "patient", "region": "A", "intent": "symptom question", "outcome": "escalated", "tools_used": ["escalate_to_human"], "unmet_need": false, "unmet_need_description": "", "proposed_tool": "", "language": "en", "evidence_quote": ""}
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_aggregate.py
import json
from pathlib import Path
from medibridge.pm import aggregate as ag

RECS = [json.loads(l) for l in (Path(__file__).parent / "fixtures/classified.jsonl").read_text().splitlines()]


def test_candidates_counts_and_shares():
    c = ag.candidates(RECS)
    top = c[0]
    assert top["proposed_tool"] == "pay_by_mobile_money" and top["region"] == "B" and top["count"] == 2
    assert top["share"] == 0.67 and top["quotes"] == ["je veux payer par Orange Money", "payer avec Wave"]
    assert top["nearest_tools"] == ["find_clinic"]
    assert {x["proposed_tool"] for x in c} == {"pay_by_mobile_money", "renew_prescription", "lookup_patient_by_phone"}


def test_report_has_both_regions_and_outcomes():
    r = ag.report(RECS, ag.candidates(RECS))
    assert "## Region A" in r and "## Region B" in r
    assert "pay_by_mobile_money" in r and "renew_prescription" in r
    assert "escalated" in r and "Same product, two roadmaps" in r
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_aggregate.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Write aggregate.py**

```python
# medibridge/pm/aggregate.py
"""Step 3 of the loop: arithmetic, no LLM. Group unmet needs into candidate expansions per region."""
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUTCOMES = ("resolved", "partial", "failed", "escalated")


def candidates(records: list[dict]) -> list[dict]:
    totals = Counter((r["region"], r["persona"]) for r in records)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("unmet_need") and r.get("proposed_tool"):
            groups[(r["region"], r["persona"], r["proposed_tool"])].append(r)
    out = []
    for (region, persona, tool), rs in groups.items():
        near = Counter(t for r in rs for t in r.get("tools_used", []))
        desc = Counter(r["unmet_need_description"] for r in rs if r.get("unmet_need_description"))
        out.append({"region": region, "persona": persona, "proposed_tool": tool, "count": len(rs),
                    "share": round(len(rs) / totals[(region, persona)], 2),
                    "quotes": [r["evidence_quote"] for r in rs if r.get("evidence_quote")][:3],
                    "nearest_tools": [t for t, _ in near.most_common(2)],
                    "description": desc.most_common(1)[0][0] if desc else ""})
    return sorted(out, key=lambda c: (-c["count"], c["region"], c["proposed_tool"]))


def report(records: list[dict], cands: list[dict]) -> str:
    lines = ["# MediBridge PM loop report", "", f"{len(records)} conversations and tool-log sessions classified.", ""]
    for region in ("A", "B"):
        lines += [f"## Region {region}", "", "| persona | " + " | ".join(OUTCOMES) + " |", "|---|" + "---|" * len(OUTCOMES)]
        for persona in ("patient", "staff"):
            rs = [r for r in records if r["region"] == region and r["persona"] == persona]
            if rs:
                cnt = Counter(r["outcome"] for r in rs)
                lines.append(f"| {persona} | " + " | ".join(str(cnt.get(o, 0)) for o in OUTCOMES) + " |")
        lines += ["", "### Candidate expansions", "", "| tool | persona | count | share | nearest existing tool | example |", "|---|---|---|---|---|---|"]
        for c in [c for c in cands if c["region"] == region]:
            q = c["quotes"][0] if c["quotes"] else c["description"]
            lines.append(f"| `{c['proposed_tool']}` | {c['persona']} | {c['count']} | {int(c['share'] * 100)}% | {', '.join(c['nearest_tools']) or '-'} | {q} |")
        lines.append("")
    top = {r: [c["proposed_tool"] for c in cands if c["region"] == r][:3] for r in ("A", "B")}
    lines += ["## Same product, two roadmaps", "",
              f"Region A asks first for: {', '.join(top['A']) or 'nothing yet'}.",
              f"Region B asks first for: {', '.join(top['B']) or 'nothing yet'}.", ""]
    return "\n".join(lines)


def main() -> None:
    records = [json.loads(l) for l in (OUT / "classified.jsonl").read_text().splitlines() if l.strip()]
    cands = candidates(records)
    (OUT / "report.md").write_text(report(records, cands))
    (OUT / "candidates.json").write_text(json.dumps(cands, indent=2, ensure_ascii=False))
    print(f"{len(cands)} candidates -> {OUT / 'report.md'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_aggregate.py -q`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Add deterministic aggregation and the two-region report"
```

### Task 14: Synthetic corpus

**Files:**
- Create: `medibridge/pm/generate_corpus.py`, `tests/test_generate_corpus.py`, `corpus/patient/regionA/*.json`, `corpus/patient/regionB/*.json`, `corpus/staff/regionA/*.jsonl`, `corpus/staff/regionB/*.jsonl`

**Interfaces:**
- Produces: `generate_corpus.PROFILES: dict[str, dict]` keyed by region with `themes: list[tuple[str, int]]` (theme, weight) and `ordinary: list[str]`; `plan(region: str, n: int, seed: int) -> list[str]` returning a theme per conversation, weighted, deterministic; `PATIENT_SCHEMA`, `STAFF_SCHEMA`; `patient_prompt(region, theme, idx) -> str`; `staff_prompt(region, theme, idx) -> str`; `to_transcript(region, idx, out: dict) -> dict` matching the transcript file shape from Task 10 (`session_id` = `corpus-<region>-<idx:03d>`); `to_calls(region, idx, out) -> list[dict]` matching the tool-call log line shape; `main(n_patient=50, n_staff=40)`.
- Corpus files are named `<region lower>-<idx:03d>.json` and `.jsonl`.

- [ ] **Step 1: Write the profiles and generator**

```python
# medibridge/pm/generate_corpus.py
"""Author the synthetic corpus once, commit it. Attendees never run this; it exists so the
two regional backlogs diverge on stage for a reason we can explain."""
import json
import random
from pathlib import Path

from . import claude_json

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "corpus"

PROFILES = {
    "A": {"language": "English", "channel": "patient portal", "city": "Johannesburg or Cape Town",
          "themes": [("check medical scheme eligibility before booking a specialist", 8), ("renew a chronic prescription", 7),
                     ("get the actual lab result values", 6), ("get a specialist referral letter", 5), ("book a telehealth video consult", 5),
                     ("symptom or medication side-effect question that must be escalated", 5)],
          "ordinary": ["book a general appointment", "check whether results are ready", "move an appointment", "find clinic hours"],
          "staff_themes": [("look up a patient by phone number instead of id", 9), ("check stock of an item not in the catalogue", 5),
                           ("send an sms reminder that works", 4), ("check scheme eligibility for a walk-in", 4)]},
    "B": {"language": "French, with occasional Wolof or English words", "channel": "WhatsApp", "city": "Dakar or Abidjan",
          "themes": [("pay the consultation by Orange Money or Wave", 9), ("get an SMS confirmation because the phone is a feature phone", 6),
                     ("book for a family member such as a child or mother", 6), ("get directions or transport to the clinic", 5),
                     ("receive lab results by SMS", 5), ("write in Wolof and expect a reply", 4),
                     ("symptom question about a child with fever that must be escalated", 5)],
          "ordinary": ["prendre un rendez-vous", "savoir si les résultats sont prêts", "annuler un rendez-vous", "connaître les horaires"],
          "staff_themes": [("send a WhatsApp reminder", 6), ("send an sms reminder which fails in region B", 6),
                           ("check stock of TDR paludisme which is low", 5), ("look up a patient by phone number", 6)]},
}

PATIENT_SCHEMA = {"type": "object", "properties": {
    "messages": {"type": "array", "items": {"type": "object", "properties": {
        "role": {"type": "string", "enum": ["user", "assistant"]}, "content": {"type": "string"}}, "required": ["role", "content"]}},
    "tools_used": {"type": "array", "items": {"type": "string"}}, "escalated": {"type": "boolean"}},
    "required": ["messages", "tools_used", "escalated"]}
STAFF_SCHEMA = {"type": "object", "properties": {"calls": {"type": "array", "items": {"type": "object", "properties": {
    "tool": {"type": "string"}, "args": {"type": "object"}, "status": {"type": "string", "enum": ["ok", "not_found", "error"]},
    "error": {"type": "string"}}, "required": ["tool", "args", "status"]}}}, "required": ["calls"]}

TOOLS_TEXT = ("Available tools: find_clinic, get_availability, book_appointment, reschedule_or_cancel, results_status (ready or not, never values), "
              "medication_schedule, escalate_to_human; region A also check_scheme_eligibility; region B also mobile_money_payment_link. "
              "Staff tools: lookup_patient (takes a pt-... id), todays_schedule, drug_stock, send_reminder (sms works in A, whatsapp in B).")


def plan(region: str, n: int, seed: int, key: str = "themes") -> list[str]:
    rng = random.Random(seed)
    prof = PROFILES[region]
    themes = [t for t, w in prof[key] for _ in range(w)]
    ordinary = prof["ordinary"]
    out = []
    for i in range(n):
        out.append(rng.choice(ordinary) if (key == "themes" and i % 3 == 2) else rng.choice(themes))
    return out


def patient_prompt(region: str, theme: str, idx: int) -> str:
    p = PROFILES[region]
    return (f"Write a realistic {p['channel']} conversation between a patient in {p['city']} and the MediBridge patient assistant. "
            f"Language: {p['language']}. The patient's goal: {theme}. {TOOLS_TEXT} The assistant follows strict rules: never clinical advice, "
            f"never result values, escalates symptoms, says plainly when a tool cannot do something. 4 to 8 messages. Patient id pt-{region.lower()}-00{1 + idx % 2}. "
            f"Vary the opening and tone; conversation number {idx}. tools_used lists tool names the assistant would have called.")


def staff_prompt(region: str, theme: str, idx: int) -> str:
    return (f"Write the tool-call log of a clinic staff member in region {region} using MediBridge tools through their own AI assistant. "
            f"Goal: {theme}. {TOOLS_TEXT} 2 to 5 calls. Show realistic near-misses: wrong argument shapes, retries, errors with messages. Session {idx}.")


def to_transcript(region: str, idx: int, out: dict) -> dict:
    sid = f"corpus-{region.lower()}-{idx:03d}"
    return {"session_id": sid, "persona": "patient", "region": region, "started": "2026-09-01T09:00:00+00:00",
            "messages": [{**m, "ts": ""} for m in out["messages"]],
            "tool_uses": [{"name": t, "input": {}, "result": "", "is_error": False} for t in out["tools_used"]],
            "escalated": out["escalated"], "cost_usd": 0.0}


def to_calls(region: str, idx: int, out: dict) -> list[dict]:
    sid = f"corpus-{region.lower()}-s{idx:03d}"
    return [{"ts": "2026-09-01T09:00:00+00:00", "session_id": sid, "persona": "staff", "region": region,
             "tool": c["tool"], "args": c["args"], "status": c["status"], "error": c.get("error") or None} for c in out["calls"]]


def main(n_patient: int = 50, n_staff: int = 40, ask=claude_json.ask_json_many) -> None:
    for region in ("A", "B"):
        pdir = CORPUS / "patient" / f"region{region}"; sdir = CORPUS / "staff" / f"region{region}"
        pdir.mkdir(parents=True, exist_ok=True); sdir.mkdir(parents=True, exist_ok=True)
        themes = plan(region, n_patient, seed=1)
        outs = ask([(patient_prompt(region, t, i), PATIENT_SCHEMA) for i, t in enumerate(themes)], workers=6)
        for i, o in enumerate(outs):
            (pdir / f"{region.lower()}-{i:03d}.json").write_text(json.dumps(to_transcript(region, i, o), indent=2, ensure_ascii=False))
        sthemes = plan(region, n_staff, seed=2, key="staff_themes")
        outs = ask([(staff_prompt(region, t, i), STAFF_SCHEMA) for i, t in enumerate(sthemes)], workers=6)
        for i, o in enumerate(outs):
            (sdir / f"{region.lower()}-{i:03d}.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in to_calls(region, i, o)) + "\n")
        print(f"region {region}: {n_patient} transcripts, {n_staff} staff sessions")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the tests**

```python
# tests/test_generate_corpus.py
from medibridge.pm import generate_corpus as g


def test_plan_is_deterministic_and_weighted():
    a = g.plan("B", 30, seed=1)
    assert a == g.plan("B", 30, seed=1)
    assert sum("Orange Money" in t for t in a) >= 3
    assert any(t in g.PROFILES["B"]["ordinary"] for t in a)


def test_to_transcript_matches_agent_shape():
    d = g.to_transcript("A", 7, {"messages": [{"role": "user", "content": "hi"}], "tools_used": ["find_clinic"], "escalated": False})
    assert d["session_id"] == "corpus-a-007" and d["messages"][0]["ts"] == "" and d["tool_uses"][0]["name"] == "find_clinic"


def test_to_calls_matches_log_shape():
    rows = g.to_calls("B", 1, {"calls": [{"tool": "send_reminder", "args": {"channel": "sms"}, "status": "error", "error": "sms gateway not configured"}]})
    assert rows[0]["session_id"] == "corpus-b-s001" and rows[0]["error"].startswith("sms")
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_generate_corpus.py -q`
Expected: 3 passed

- [ ] **Step 4: Generate the corpus for real, then spot-check**

Run: `uv run python -m medibridge.pm.generate_corpus` (several minutes; 180 headless calls at 6 workers). Then `ls corpus/patient/regionA | wc -l` (50) and read three files from each region. Check: region B files are in French, region A in English, at least one escalated conversation per region, staff logs contain `not_found` for phone-number lookups. If a batch failed with a `RuntimeError`, rerun; files are overwritten by index.

- [ ] **Step 5: Add the skill for regeneration**

`.claude/skills/generate-corpus/SKILL.md`:
```markdown
---
name: generate-corpus
description: Regenerate the synthetic MediBridge corpus (100 patient transcripts, 80 staff tool-log sessions) from the region profiles. Course authors only; takes several minutes.
disable-model-invocation: true
---

Warn the user this overwrites `corpus/` and takes several minutes, and ask them to confirm. Then run `uv run python -m medibridge.pm.generate_corpus`, report the counts it prints, open two files per region, and summarise in three lines whether the regional contrast is visible (French vs English, payment vs scheme themes). If any file is missing or empty, rerun once.
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Add corpus generator and the committed synthetic corpus"
```

### Task 15: Proposals and the /pm-run skill

**Files:**
- Create: `medibridge/pm/propose.py`, `templates/expansion-proposal.md`, `tests/test_propose.py`, `.claude/skills/pm-run/SKILL.md`, `medibridge/pm/out/classified.jsonl`, `medibridge/pm/out/report.md`, `medibridge/pm/out/candidates.json`, `medibridge/pm/out/proposals/*.md`

**Interfaces:**
- Produces: `propose.PROPOSAL_SCHEMA` with fields `tool_name, description, input_schema (object), backend_needed, safety_notes, regions (list), personas (list)`; `propose.render(cand: dict, out: dict) -> str` fills `templates/expansion-proposal.md` by simple `{placeholder}` substitution; `propose.main(top_per_region=3, ask=...)` writes `out/proposals/<region>-<tool>.md` using `candidates.json`.

- [ ] **Step 1: Write the template** `templates/expansion-proposal.md`

```markdown
# Expansion proposal: `{tool_name}`

**Region(s):** {regions}  **Persona(s):** {personas}  **Evidence:** {count} conversations ({share}% of {region} {persona})

## What users asked for
{description}

Example quotes:
{quotes}

## Proposed tool
**Description (the docstring Claude will read):** {tool_description}

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
- [ ] Approve for implementation with `/expand {file_stem}`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_propose.py
from medibridge.pm import propose as pr

CAND = {"region": "B", "persona": "patient", "proposed_tool": "pay_by_mobile_money", "count": 9, "share": 0.18,
        "quotes": ["je veux payer par Orange Money"], "nearest_tools": ["find_clinic"], "description": "Pay consultation by mobile money"}
OUT = {"tool_name": "pay_by_mobile_money", "description": "Create a payment request.", "input_schema": {"type": "object", "properties": {"patient_id": {"type": "string"}}},
       "backend_needed": "Mobile money aggregator API.", "safety_notes": "Never store PINs.", "regions": ["B"], "personas": ["patient"]}


def test_render_fills_every_placeholder():
    text = pr.render(CAND, OUT)
    assert "{" not in text.replace("{\n", "").replace('{"type"', "") or "input_schema" not in text
    assert "`pay_by_mobile_money`" in text and "Orange Money" in text and "18%" in text and "/expand B-pay_by_mobile_money" in text
```

- [ ] **Step 3: Write propose.py**

```python
# medibridge/pm/propose.py
"""Step 4 of the loop: draft a tool spec for each top candidate. A human approves before /expand."""
import json
from pathlib import Path

from . import claude_json

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT = HERE / "out"
TEMPLATE = REPO_ROOT / "templates" / "expansion-proposal.md"

PROPOSAL_SCHEMA = {"type": "object", "properties": {
    "tool_name": {"type": "string"}, "description": {"type": "string"}, "input_schema": {"type": "object"},
    "backend_needed": {"type": "string"}, "safety_notes": {"type": "string"},
    "regions": {"type": "array", "items": {"type": "string"}}, "personas": {"type": "array", "items": {"type": "string"}}},
    "required": ["tool_name", "description", "input_schema", "backend_needed", "safety_notes", "regions", "personas"]}


def _prompt(c: dict) -> str:
    return (f"You are the product manager for MediBridge, a healthcare network. Users in region {c['region']} (persona {c['persona']}) "
            f"asked {c['count']} times for something our tools cannot do: {c['description']}. Quotes: {c['quotes']}. "
            f"Nearest existing tools: {c['nearest_tools']}. Draft a tool spec named {c['proposed_tool']}: a one-sentence description "
            f"that an LLM will read as the tool docstring, a JSON input schema with snake_case fields, what backend system it needs, "
            f"and safety notes. Patients must never receive clinical advice or lab result values through a tool; if the request is for "
            f"those, design the tool to route the request to a clinician instead and say so in safety_notes. Region A is an urban "
            f"portal-and-scheme market; region B is a WhatsApp-and-mobile-money market.")


def render(c: dict, out: dict) -> str:
    stem = f"{c['region']}-{c['proposed_tool']}"
    fill = {"tool_name": out["tool_name"], "regions": ", ".join(out["regions"]), "personas": ", ".join(out["personas"]),
            "count": c["count"], "share": int(c["share"] * 100), "region": c["region"], "persona": c["persona"],
            "description": c["description"], "quotes": "\n".join(f"- \"{q}\"" for q in c["quotes"]) or "- (none)",
            "tool_description": out["description"], "input_schema": json.dumps(out["input_schema"], indent=2),
            "nearest_tools": ", ".join(c["nearest_tools"]) or "-", "backend_needed": out["backend_needed"],
            "safety_notes": out["safety_notes"], "file_stem": stem}
    text = TEMPLATE.read_text()
    for k, v in fill.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def main(top_per_region: int = 3, ask=claude_json.ask_json_many) -> None:
    cands = json.loads((OUT / "candidates.json").read_text())
    chosen = [c for r in ("A", "B") for c in [c for c in cands if c["region"] == r][:top_per_region]]
    outs = ask([(_prompt(c), PROPOSAL_SCHEMA) for c in chosen], model="sonnet")
    (OUT / "proposals").mkdir(exist_ok=True)
    for c, o in zip(chosen, outs):
        path = OUT / "proposals" / f"{c['region']}-{c['proposed_tool']}.md"
        path.write_text(render(c, o))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_propose.py -q`
Expected: 1 passed

- [ ] **Step 5: Write the /pm-run skill**

```markdown
---
name: pm-run
description: Run the live product-management loop over the MediBridge corpus plus any live conversations and tool logs: classify, aggregate per region, and draft expansion proposals. Then walk the user through the two regional backlogs.
---

Run the loop and narrate it. The judgment steps call headless Claude Code; the counting is plain Python.

1. Say how many items will be classified: run `uv run python -c "from medibridge.pm.classify import load_items, REPO_ROOT; print(len(load_items(REPO_ROOT/'corpus', REPO_ROOT/'medibridge'/'logs')))"`. Tell the user this takes about two minutes.
2. Run `uv run python -m medibridge.pm.classify`. If it fails with a RuntimeError, run it once more.
3. Run `uv run python -m medibridge.pm.aggregate`.
4. Run `uv run python -m medibridge.pm.propose`.
5. Open `medibridge/pm/out/report.md` and present, in plain language: the outcome mix per region, the top three candidate expansions per region, and the one-paragraph "same product, two roadmaps" contrast. If the logs contained live conversations (ids starting with `live-`), find them in `classified.jsonl` and tell the user which candidate their own request landed in, quoting their line.
6. List the proposal files in `medibridge/pm/out/proposals/` and say: pick one and run `/expand <file stem>` to implement it, or open the file to reject or merge it.

Do not edit any tool code in this skill. Do not skip the aggregate step even if classification looks off; the report is how we see that it is off.
```

- [ ] **Step 6: Run the loop for real and commit the outputs**

Run: `uv run python -m medibridge.pm.classify && uv run python -m medibridge.pm.aggregate && uv run python -m medibridge.pm.propose`
Expected: `classified.jsonl` with 180 lines, `report.md` where region B's top tool is `pay_by_mobile_money` and region A's is `check_scheme_eligibility` or `renew_prescription`, and six proposal files. If the regional contrast is weak, fix the taxonomy wording before touching the corpus.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "Add proposals, the /pm-run skill, and the committed loop outputs"
```

### Task 16: The /expand skill

**Files:**
- Create: `templates/tool-spec.md`, `.claude/skills/expand/SKILL.md`, `medibridge/tools/specs/.gitkeep`

- [ ] **Step 1: Write the tool-spec template** `templates/tool-spec.md`

```markdown
# Tool: `{tool_name}`

**Module:** medibridge/tools/{module}.py  **Personas:** {personas}  **Regions:** {regions}

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

- [ ] **Step 2: Write the /expand skill**

```markdown
---
name: expand
description: Implement one approved expansion proposal end to end: write the tool spec, add the function, register it, add data if needed, run the tests, and explain how to see it in both front doors. Usage /expand <proposal file stem, e.g. B-pay_by_mobile_money>
arguments: [proposal]
---

Implement the proposal `medibridge/pm/out/proposals/$proposal.md`. Read it first. Then follow the repo's one procedure for adding a tool; it is the same procedure a human developer would follow, and the point of this skill is that it is short.

1. **Spec.** Copy `templates/tool-spec.md` to `medibridge/tools/specs/$proposal.md` and fill every placeholder from the proposal. Choose the module: `patient.py` if any persona is patient, else `staff.py`. Keyword arguments only, typed, with defaults where the proposal marks a field optional. Write at least three test cases in the spec: the happy path, a `not_found`, and an `error`.
2. **Tests first.** Add the test cases to `tests/test_patient_tools.py` or `tests/test_staff_tools.py` in the same style as the existing tests, using the `data_dir` fixture. Run `uv run pytest -q` and confirm the new tests fail.
3. **Function.** Add the function to the chosen module with the docstring from the spec. Never raise; return `status`. Read and write data through `store.load` / `store.save` / `store.append`. If the tool needs a new data file, create `medibridge/data/<name>.json` with three realistic seed rows that make the tests pass.
4. **Register.** Add one `_t(...)` line to `medibridge/tools/registry.py` with the personas and regions from the proposal. Run `uv run pytest -q`; everything must pass, including `test_registry`.
5. **Guardrail check.** If the proposal is `get_result_values` or anything that would give clinical content to a patient, the function must return `{"status": "error", "message": "..."}` explaining that results are shared by a clinician, and call nothing else. Say so to the user.
6. **Show it.** Tell the user, in three lines: restart the agent server (`uv run python -m medibridge.agent.server`) and ask for the new capability in the web page; start a fresh Claude Code session (or run `/mcp` and reconnect) so front door 1 picks up the new tool; then re-run `/pm-run` later to see the candidate disappear from the backlog.
7. Commit with a message naming the tool and the proposal.

Do not change existing tools' signatures. Do not edit `brief.md` unless the proposal's safety notes require a new rule, and if so show the diff before committing.
```

- [ ] **Step 3: Verify end to end on a scratch branch**

Run: `git checkout -b scratch/expand-check`, then in an interactive Claude Code session in the repo: `/expand B-pay_by_mobile_money` (or whichever region B proposal exists that is not already a tool; if `mobile_money_payment_link` already covers it, pick `A-renew_prescription`). Confirm tests pass, restart the agent, and ask the web page for the new capability in region B. Confirm the tool appears in `claude mcp list`-driven sessions. Then `git checkout main && git branch -D scratch/expand-check` so the demo can run it live.

- [ ] **Step 4: Commit the skill and template**

```bash
git add -A && git commit -m "Add the /expand skill and the tool spec template"
```

**Phase 3 checkpoint:** `/pm-run` produces two visibly different regional backlogs from the committed corpus, and `/expand` turns a proposal into a working tool in both front doors.

---

## Phase 4: Course material

### Task 17: Clean templates and the filled MediBridge brief

**Files:**
- Create: `templates/use-case-brief.md`, `templates/agent-brief.md`, `templates/taxonomy.md`, `docs/02-use-case-to-design.md`
- Already exist from earlier tasks and stay as the filled examples: `medibridge/agent/brief.md`, `medibridge/pm/taxonomy.md`, `templates/tool-spec.md`, `templates/expansion-proposal.md`

- [ ] **Step 1: Write `templates/use-case-brief.md`**

```markdown
# Use-case brief: {experience name}

## 1. Who talks to it
- Personas (one line each, who they are and what they are trying to get done):
- Where each persona already lives (their own AI assistant, a portal, WhatsApp, a phone line, a spreadsheet):

## 2. Regions or segments
| | Region 1: {name} | Region 2: {name} |
|---|---|---|
| Channel they use today | | |
| Language(s) | | |
| Payment | | |
| What "sophisticated" means to them | | |
| Regulation that bites | | |
| Who is liable if the assistant misspeaks | | |

## 3. The jobs, ranked
List the five things users will ask for most, in order. Mark each with the tool it needs and whether that tool exists today.

## 4. Product signal you need
- Do you need to read the user's words, or are tool calls enough?
- Who reads them, how often, and what do they do with what they find?

## 5. Front-door decision, per region
| Region | Front door | Why | What you give up |
|---|---|---|---|
| Region 1 | MCP to their agent / controlled agent / both | | |
| Region 2 | | | |

## 6. Guardrails that are non-negotiable
Three to five rules the assistant must never break, and what it does instead.

## 7. First release
The three tools you ship first, and the one metric that tells you whether the front door was right.
```

- [ ] **Step 2: Write `templates/agent-brief.md`** as a blank of `medibridge/agent/brief.md`: same headings (`Role`, `Hard rules`, `Style`, `Logging`, `Region 1`, `Region 2`) with one-line prompts under each instead of MediBridge content. Under `Hard rules` include the prompts: "what it must never state", "what triggers a handoff and how", "what to say when no tool fits". Under `Logging` include: "what is stored, who reads it, what they look for".

- [ ] **Step 3: Write `templates/taxonomy.md`** as a blank of `medibridge/pm/taxonomy.md`: same field list, with the MediBridge intent examples and tool names replaced by "{three intent examples from your brief}" and "{tool names you expect to propose; reuse them}". Keep the two rules at the end, generalised: "an escalation is not an unmet need" and "never propose a tool that breaks a hard rule; record the demand instead".

- [ ] **Step 4: Write `docs/02-use-case-to-design.md`**: the use-case brief filled for MediBridge. Sections 1 through 7 above, with real content: personas patient and staff; the region table from the spec section 2; the five jobs (book, results ready, move or cancel, find clinic, pay or check scheme); signal (patient words matter, staff tool calls suffice); front-door decision (A: MCP to the hospital group's agent for staff, controlled agent for patients through the portal; B: controlled agent for patients on WhatsApp, MCP unused until a partner appears); guardrails copied from `brief.md`; first release the three booking tools with "share of conversations resolved without escalation" as the metric. End with a short paragraph "What changed when we wrote it down" noting that the region table forced the front-door split.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add clean templates and the filled MediBridge use-case brief"
```

### Task 18: The /brief, /tools, and /agent skills

**Files:**
- Create: `.claude/skills/brief/SKILL.md`, `.claude/skills/tools/SKILL.md`, `.claude/skills/agent/SKILL.md`

- [ ] **Step 1: Write `/brief`**

```markdown
---
name: brief
description: Interview the user about one AI experience from their own company and fill templates/use-case-brief.md, ending in a front-door decision per region. Usage /brief <short name for the experience>
arguments: [name]
---

You are filling `templates/use-case-brief.md` for an experience called "$name". Work section by section. Ask one question at a time, offer two or three concrete options with each question, and accept short answers. Keep the whole interview under ten questions; infer the rest and say what you inferred.

Order: personas and where they live (section 1), the two regions or segments and the six rows of the table (section 2, ask for the two regions first, then fill rows in pairs), the five jobs (section 3, ask for the top three and propose two more), the signal question (section 4), guardrails (section 6, propose five and ask which to keep).

Then write section 5 yourself using this rule of thumb and show your reasoning in the "Why" column:
- Users already live inside their own AI assistant or a partner's platform, workflow spans several vendors, and tool calls are enough signal -> MCP to their agent.
- Users come to you, the domain is regulated or high-stakes, you need the user's words as product signal, or the channel is WhatsApp/SMS -> controlled agent.
- One region matches each -> both, and say which tools are shared.

Write section 7 last. Save the result to `briefs/$name.md` (create the folder). Finish by reading back the front-door table in two sentences and asking whether it matches their instinct. If it does not, that is the interesting part: ask what the table missed.
```

- [ ] **Step 2: Write `/tools`**

```markdown
---
name: tools
description: Turn a filled use-case brief into tool specs and working tool functions in the shared tool layer. Usage /tools <brief name>
arguments: [name]
---

Read `briefs/$name.md`. For each job in section 3 whose tool does not exist in `medibridge/tools/registry.py`, do the /expand procedure without a proposal file:

1. Write `medibridge/tools/specs/<tool_name>.md` from `templates/tool-spec.md`. Decide the module (patient.py or staff.py), personas, and regions from the brief. Three test cases minimum.
2. Add failing tests, then the function, then the registry line. Run `uv run pytest -q` after each tool.
3. If a job needs data the seed files lack, add a JSON file with three realistic rows.

Guardrails from brief section 6 override the jobs: if a job would break one, implement the tool as a hand-off (return status error with an explanation) and say so.

Stop after five tools even if the brief lists more, and list what remains. Commit once per tool.
```

- [ ] **Step 3: Write `/agent`**

```markdown
---
name: agent
description: Write the controlled agent's system prompt from a filled brief: role, hard rules, style, logging, and one section per region. Usage /agent <brief name>
arguments: [name]
---

Read `briefs/$name.md` and `templates/agent-brief.md`. Write `briefs/$name-agent-brief.md` using the template headings exactly, because `medibridge/agent/prompt.py` splits on `## Region ` to pick the region block.

Rules for writing it:
- Hard rules come from brief section 6, one bullet each, each ending with what the agent does instead.
- The "no tool fits" rule is mandatory: say clearly it cannot do it yet, offer the hand-off, never pretend.
- Region sections carry language, channel tone, payment method, which region-gated tools exist, and the emergency or escalation path for that region.
- Keep it under 60 lines. Long prompts get skimmed by models and by the people who maintain them.

Then ask whether to install it: if yes, copy it over `medibridge/agent/brief.md`, run `uv run pytest tests/test_prompt.py -q`, and tell the user to restart the agent server. If no, leave it in `briefs/`.
```

- [ ] **Step 4: Dry-run `/brief` on a made-up pharmacy chain in an interactive session** and confirm it writes `briefs/<name>.md` with all seven sections and asks at most ten questions. Do not commit the resulting brief; add `briefs/` to `.gitignore` except for a `briefs/.gitkeep`.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add the /brief, /tools, and /agent skills"
```

### Task 19: The /new-experience skill

**Files:**
- Create: `.claude/skills/new-experience/SKILL.md`, `scripts/new_experience.py`, `tests/test_new_experience.py`

**Interfaces:**
- Produces: `new_experience.create(name: str, dest: Path, repo_root: Path) -> Path` that creates `dest/<name>/` containing: `templates/` (copied), `.claude/skills/` (brief, tools, agent, pm-run, expand, setup copied), `.mcp.json` (copied), `pyproject.toml` with the `name` field changed to `<name>`, `medibridge/` renamed to `<name>/` with `tools/store.py`, `tools/calllog.py`, an empty `tools/registry.py` (`TOOLS = []` and the `select` function), `mcp_server.py`, `agent/` (`claude_runner.py`, `prompt.py`, `transcripts.py`, `server.py`, `static/`), an `agent/brief.md` copied from `templates/agent-brief.md`, `pm/` (`claude_json.py`, `classify.py`, `aggregate.py`, `propose.py`, `taxonomy.md` copied from the template), empty `data/`, `logs/.gitkeep`, and a `README.md` saying "Start with /brief <name>". All `medibridge` import strings inside copied `.py` and `.md` and `.mcp.json` files are replaced with `<name>`. It must not copy `corpus/`, `pm/out/`, `docs/`, `exercises/`, `slides/`, or `tests/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_new_experience.py
import json
from pathlib import Path
from scripts.new_experience import create

REPO = Path(__file__).resolve().parents[1]


def test_create_makes_clean_project(tmp_path):
    root = create("pharmaflow", tmp_path, REPO)
    assert (root / "pharmaflow" / "tools" / "registry.py").exists()
    assert "TOOLS: list[ToolSpec] = []" in (root / "pharmaflow" / "tools" / "registry.py").read_text()
    assert not (root / "corpus").exists() and not (root / "pharmaflow" / "pm" / "out").exists()
    assert "medibridge" not in (root / "pharmaflow" / "mcp_server.py").read_text()
    assert "pharmaflow.mcp_server" in json.dumps(json.loads((root / ".mcp.json").read_text()))
    assert 'name = "pharmaflow"' in (root / "pyproject.toml").read_text()
    assert (root / ".claude" / "skills" / "brief" / "SKILL.md").exists()
    assert (root / "pharmaflow" / "agent" / "brief.md").read_text() == (REPO / "templates" / "agent-brief.md").read_text()
```

- [ ] **Step 2: Write `scripts/__init__.py` (empty) and `scripts/new_experience.py`**

```python
"""Start a clean experience from the course templates. Run: uv run python scripts/new_experience.py <name> [dest]"""
import re
import shutil
import sys
from pathlib import Path

COPY_FILES = ["tools/store.py", "tools/calllog.py", "mcp_server.py", "agent/claude_runner.py", "agent/prompt.py",
              "agent/transcripts.py", "agent/server.py", "agent/static/index.html", "pm/claude_json.py",
              "pm/classify.py", "pm/aggregate.py", "pm/propose.py"]
SKILLS = ["setup", "brief", "tools", "agent", "pm-run", "expand"]
REGISTRY = '''"""The single list of tools for this experience. /tools and /expand add lines here."""
from dataclasses import dataclass
from typing import Callable

ALL_REGIONS = frozenset({"A", "B"})


@dataclass(frozen=True)
class ToolSpec:
    name: str
    fn: Callable
    personas: frozenset[str]
    regions: frozenset[str]


def _t(fn, personas, regions=ALL_REGIONS) -> ToolSpec:
    return ToolSpec(fn.__name__, fn, frozenset(personas), frozenset(regions))


TOOLS: list[ToolSpec] = []


def select(persona: str, region: str) -> list[ToolSpec]:
    return [t for t in TOOLS
            if (persona == "all" or persona in t.personas)
            and (region == "all" or region in t.regions)]
'''


def _rewrite(path: Path, name: str) -> None:
    text = path.read_text()
    path.write_text(text.replace("medibridge", name).replace("MEDIBRIDGE", name.upper()).replace("MediBridge", name))


def create(name: str, dest: Path, repo_root: Path) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError("name must be a lowercase python identifier")
    root = dest / name
    pkg = root / name
    for rel in COPY_FILES:
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo_root / "medibridge" / rel, pkg / rel)
        if (pkg / rel).suffix in {".py", ".html"}:
            _rewrite(pkg / rel, name)
    (pkg / "__init__.py").touch(); (pkg / "tools" / "__init__.py").touch()
    (pkg / "agent" / "__init__.py").touch(); (pkg / "pm" / "__init__.py").touch()
    (pkg / "tools" / "registry.py").write_text(REGISTRY)
    (pkg / "tools" / "patient.py").write_text('"""Tools for the first persona. /tools fills this."""\nfrom . import store\n')
    (pkg / "tools" / "staff.py").write_text('"""Tools for the second persona. /tools fills this."""\nfrom . import store\n')
    (pkg / "data").mkdir(); (pkg / "logs").mkdir(); (pkg / "logs" / ".gitkeep").touch()
    shutil.copy(repo_root / "templates" / "agent-brief.md", pkg / "agent" / "brief.md")
    shutil.copy(repo_root / "templates" / "taxonomy.md", pkg / "pm" / "taxonomy.md")
    shutil.copytree(repo_root / "templates", root / "templates")
    for s in SKILLS:
        shutil.copytree(repo_root / ".claude" / "skills" / s, root / ".claude" / "skills" / s)
        _rewrite(root / ".claude" / "skills" / s / "SKILL.md", name)
    shutil.copy(repo_root / ".mcp.json", root / ".mcp.json"); _rewrite(root / ".mcp.json", name)
    shutil.copy(repo_root / "scripts" / "check.py", root / "scripts" / "check.py") if (root / "scripts").mkdir() is None else None
    _rewrite(root / "scripts" / "check.py", name)
    py = (repo_root / "pyproject.toml").read_text()
    py = re.sub(r'^name = ".*"$', f'name = "{name}"', py, flags=re.M).replace('packages = ["medibridge"]', f'packages = ["{name}"]')
    (root / "pyproject.toml").write_text(py)
    shutil.copy(repo_root / ".gitignore", root / ".gitignore"); _rewrite(root / ".gitignore", name)
    (root / "tests").mkdir(); (root / "tests" / "__init__.py").touch()
    shutil.copy(repo_root / "tests" / "conftest.py", root / "tests" / "conftest.py"); _rewrite(root / "tests" / "conftest.py", name)
    (root / "README.md").write_text(f"# {name}\n\nA clean experience built from the course templates.\n\nStart with `/brief {name}`, then `/tools {name}`, then `/agent {name}`.\n")
    return root


if __name__ == "__main__":
    n = sys.argv[1]
    d = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd().parent
    print(create(n, d, Path(__file__).resolve().parents[1]))
```

- [ ] **Step 3: Run the test, then create one for real and sync it**

Run: `uv run pytest tests/test_new_experience.py -q`, then `uv run python scripts/new_experience.py demo_exp /tmp && cd /tmp/demo_exp && uv sync && uv run pytest -q && uv run python scripts/check.py; cd -`
Expected: test passes; in the new folder `uv sync` succeeds, pytest reports no tests, check prints tool counts of 0 and finds `claude`. Delete `/tmp/demo_exp` afterwards.

- [ ] **Step 4: Write the skill**

```markdown
---
name: new-experience
description: Create a clean sibling project from the course templates, with the skills, the empty tool registry, both front doors, and the PM loop, ready for /brief. Usage /new-experience <lowercase_name>
arguments: [name]
disable-model-invocation: true
---

Run `uv run python scripts/new_experience.py $name` (it creates `../$name`). Then `cd ../$name && uv sync && uv run pytest -q && uv run python scripts/check.py`. Report the path and the check output. Tell the user: open Claude Code in that folder and run `/brief $name`. There is no corpus in a new experience on purpose; the loop runs on the first real conversations.
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add /new-experience scaffolding script and skill"
```

### Task 20: Docs

**Files:**
- Create: `docs/00-session-plan.md`, `docs/01-tradeoff.md`, `docs/03-live-pm.md`, `docs/04-operating.md`

- [ ] **Step 1: Write `docs/01-tradeoff.md`.** Open with the thesis line. Then this table, verbatim, followed by one paragraph per row explaining it with a MediBridge example:

```markdown
| Dimension | MCP given to the customer | Controlled agent you host |
|---|---|---|
| Who runs the loop | Their agent, their prompt, their model | You |
| Distribution | Wherever they already work | They have to come to you |
| What you see | Tool calls: name, arguments, status | Every word, including what you could not do |
| Guardrails | You can refuse inside a tool; you cannot shape what is said around it | Yours, end to end |
| Who pays for tokens | They do | You do |
| Liability when it misspeaks | Shared and unclear; their agent said it, your tool fed it | Yours, and clear |
| Build cost | The tool layer only | Tool layer plus prompt, UI, hosting, logging |
| Time to first user | Days if they already have an agent | Weeks |
| Fit by region | Customers with an IT team and an agent platform | Customers with a phone and WhatsApp |
```

Then a section "Region row, expanded" with the MediBridge two-region table from the spec, and a closing section "The hybrid" explaining build once, consume from your own agent, publish the same server.

- [ ] **Step 2: Write `docs/03-live-pm.md`.** The five stages (capture, classify, aggregate, propose, ship), one short section each, naming the file that does it. Include a diagram in a fenced block:

```
transcripts/*.json  ─┐
                     ├─ classify.py ─► classified.jsonl ─► aggregate.py ─► report.md + candidates.json ─► propose.py ─► proposals/*.md ─► /expand ─► registry.py
tool_calls.jsonl    ─┘        (claude -p)                      (python)                                    (claude -p)                  (Claude Code)
```

Then "What each front door lets you see": a paragraph on transcripts vs tool logs with one real example of each from the committed corpus (quote a French payment request and a `lookup_patient` phone-number near-miss). Then "Why judgment and arithmetic are split". Then "Reading the committed report" with the two top-three lists copied from `medibridge/pm/out/report.md`.

- [ ] **Step 3: Write `docs/04-operating.md`.** Sections: who owns the backlog (a named PM reads `report.md` weekly; engineers never ship a proposal without the decision box ticked); review cadence (weekly loop, monthly taxonomy review); safety of generated tools (proposals are specs, not code; `/expand` writes tests first; the guardrail check in step 5 of `/expand`; a generated tool that touches money or health data gets a human-written test before merge); cost (state the per-conversation cost the agent server logs in `cost_usd`, and that classification of 180 items with haiku is a few cents; read the numbers from the committed transcripts rather than inventing them); what to do when the two regions disagree (ship per region, the registry already supports it).

- [ ] **Step 4: Write `docs/00-session-plan.md`.** The run-of-show table from spec section 5 with a "Presenter notes" column: for each block, the exact command or prompt to type, the file to have open, and the one sentence to land. Add a pre-work section (send three days ahead: clone URL, "open Claude Code in the folder, run /setup, tell us if it fails") and a "if the room's wifi dies" section (everything is local; the only network calls are to Claude; the committed `pm/out/` lets the PM block proceed as a read-through).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add the course docs: session plan, tradeoff, PM loop, operating"
```

### Task 21: Exercises

**Files:**
- Create: `exercises/README.md`, `exercises/01-pharmacy-chain.md`, `exercises/02-health-insurer.md`, `exercises/03-telemedicine-startup.md`

- [ ] **Step 1: Write the three exercises.** Each has: a one-paragraph business; a two-region contrast (pharmacy: urban chain with an app vs rural franchise on USSD; insurer: corporate scheme members with a portal vs informal-sector micro-insurance by mobile money; telemedicine: diaspora-funded video consults vs low-bandwidth voice-note triage); a "Read track" with three questions whose answers are the front-door table and the first three tools; a "Build track" that is `/new-experience <name>`, `/brief`, `/tools`, `/agent`, then talk to it five times and run `/pm-run`; and an "Answer sketch" at the end giving one defensible front-door decision per region with a sentence of why. The three exercises must reach different conclusions: pharmacy lands on MCP for the app region; insurer lands on controlled agent for both; telemedicine lands on the hybrid.

- [ ] **Step 2: Write `exercises/README.md`** explaining the two tracks and that the answer sketches are one defensible answer, not the answer.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "Add three business-case exercises with read and build tracks"
```

### Task 22: Slides

**Files:**
- Create: `slides/outline.md`, `slides/deck.pptx`

- [ ] **Step 1: Write `slides/outline.md`**, one `## Slide N: title` section per slide with bullet content and a `Speaker:` line. Fifteen slides:

1. Title: One tool layer, two front doors. Speaker: what they will do in the hour.
2. Same request, two surfaces (two screenshots: Claude Code with MCP, the web page in region B).
3. The thesis line, alone.
4. The tradeoff table from `docs/01-tradeoff.md`.
5. Region row expanded: the MediBridge two-region table.
6. Discussion prompt: which of your systems is which? (three questions)
7. From use case to design: the seven sections of the brief, and the front-door rule of thumb from `/brief`.
8. Hands-on: `/brief <name>`, ten minutes, three people read out section 5.
9. The loop diagram from `docs/03-live-pm.md`.
10. What each front door lets you see: a transcript excerpt and a tool-log excerpt side by side.
11. Hands-on: ask for something it cannot do, then `/pm-run`.
12. Two backlogs: the two top-three lists from the committed report.
13. Hands-on: `/expand`, restart, test in both front doors.
14. Operating it: owner, cadence, generated tools get tests first, cost.
15. Take it home: `/new-experience`, the exercises, the repo URL.

- [ ] **Step 2: Build the deck** using the `anthropic-skills:pptx` skill from the outline. Take the two screenshots for slide 2 with the running agent and a Claude Code session. Plain design: dark title slide, white content slides, one table or one code block per slide, no clip art.

- [ ] **Step 3: Check it** by rendering to images (the pptx skill's thumbnail step) and confirming every slide is legible at a glance. Commit.

```bash
git add -A && git commit -m "Add the presenter deck and its outline"
```

**Phase 4 checkpoint:** a fresh attendee can clone, run `/setup`, follow `docs/00-session-plan.md`, and a reader can follow every step from the docs and committed outputs. This matches spec section 10.

---

## Self-review against the spec

- Spec 1 thesis: docs 01 and 03, slides 3 and 9. Covered.
- Spec 2 domain and personas: data (Tasks 2-4), region gating (Task 5), tracks are the two front doors (Tasks 6, 10). Covered.
- Spec 3 constraints: no API key (Global Constraints; Tasks 8, 11 use `claude -p`), `uv` and `/setup` (Task 7). Covered.
- Spec 4.1-4.5: Tasks 3-6, 8-10, 11-15, 14. Covered.
- Spec 5 run of show, including the personal-request step: Task 20 session plan, Task 15 skill step 5 finds `live-` items. Covered.
- Spec 6 slides: Task 22. Spec 7 readable track: Tasks 15 (committed outputs), 17, 20, 21. Spec 8 skills: Tasks 7, 14, 15, 16, 18, 19. Spec 9 testing: every task. Spec 10 success criteria: phase checkpoints.
- Type consistency checked: `TurnResult` fields used identically in Tasks 8, 10; transcript shape identical in Tasks 10, 12, 14; log line shape identical in Tasks 6, 12, 14; candidate dict identical in Tasks 13, 15.
