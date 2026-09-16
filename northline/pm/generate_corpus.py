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
AGENT_TOOLS = ["log_reading", "log_medication", "escalate_to_nurse", "next_checkin"]
PLAN_TOOLS = ["member_engagement", "outcome_evidence", "enrollment_status", "enroll_members"]
TRANSCRIPT_SCHEMA = {"type": "object", "properties": {
    "messages": {"type": "array", "minItems": 4, "maxItems": 8, "items": {"type": "object", "properties": {
        "role": {"type": "string", "enum": ["user", "assistant"]}, "content": {"type": "string"}}, "required": ["role", "content"]}},
    "tools_used": {"type": "array", "items": {"type": "string", "enum": AGENT_TOOLS}}, "escalated": {"type": "boolean"}}, "required": ["messages", "tools_used", "escalated"]}
PLAN_SCHEMA = {"type": "object", "properties": {"calls": {"type": "array", "minItems": 2, "maxItems": 5, "items": {"type": "object", "properties": {
    "tool": {"type": "string", "enum": PLAN_TOOLS}, "args": {"type": "object"}, "status": {"type": "string", "enum": ["ok", "not_found", "error"]}, "error": {"type": "string"}},
    "required": ["tool", "args", "status"]}}}, "required": ["calls"]}
TOOLS = ("Tools the agent has: log_reading, log_medication, escalate_to_nurse (returns 'median response time is currently 31 hours'), next_checkin. "
         "It cannot do refills, insurance, transport, diet advice, device support, or reply to loneliness beyond kindness; it says so plainly.")

# Ruling 2: draw after-hours (weekday>=5, or hour outside 8-17 — the same test aggregate.queue_metrics uses) with
# probability 0.46, as either a weekend day at any hour or a weekday at an evening/night hour; otherwise a weekday
# between 08:00 and 17:59. That makes the after-hours share aggregate.queue_metrics computes land near 0.46, instead
# of drifting above it the way drawing an hour independently of the day of week would.
_WINDOW_DAYS = 91
_WEEKDAY_OFFSETS = [d for d in range(_WINDOW_DAYS) if (Q_START + timedelta(days=d)).weekday() < 5]
_WEEKEND_OFFSETS = [d for d in range(_WINDOW_DAYS) if (Q_START + timedelta(days=d)).weekday() >= 5]
_EVENING_NIGHT_HOURS = [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]


def _stamp(rng: random.Random) -> datetime:
    if rng.random() < 0.46:
        if rng.random() < 0.5:
            day_offset, hour = rng.choice(_WEEKEND_OFFSETS), rng.randint(0, 23)
        else:
            day_offset, hour = rng.choice(_WEEKDAY_OFFSETS), rng.choice(_EVENING_NIGHT_HOURS)
    else:
        day_offset, hour = rng.choice(_WEEKDAY_OFFSETS), rng.randint(8, 17)
    return Q_START + timedelta(days=day_offset, hours=hour, minutes=rng.randint(0, 59))


def plan(n: int, seed: int) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    pool = [(t, tier) for t, w, tier in THEMES for _ in range(w)]
    return [rng.choice(pool) for _ in range(n)]


def transcript_prompt(theme: str, tier: str, idx: int) -> str:
    return ("Return only the structured fields. Do not describe or restate this task. "
            f"Write a realistic SMS conversation, 4 to 8 short texts, between a patient in rural North Dakota with hypertension or type 2 diabetes "
            f"and Northline Care's weekly check-in agent. Situation: {theme}. {TOOLS} "
            "The conversation opens with an assistant message (the weekly check-in text); roles alternate strictly between assistant and user for 4 to 8 messages total. "
            f"Patient id pt-{1000 + idx % 8 + 1}. Do not put timestamps or speaker labels inside content — each message's content is the raw text only. "
            "The agent never gives clinical advice. It calls escalate_to_nurse only for clinical content (a flagged reading, a symptom, a medication problem); "
            "for non-clinical requests (insurance, transport, device errors, loneliness, opting out) it says plainly it cannot do that yet and does not escalate. "
            f"Vary tone and wording; conversation number {idx}. "
            "tools_used lists the tools the agent would call, using only the four tool names given above; "
            "escalated is true only when escalate_to_nurse is in tools_used, and false otherwise.")


def plan_prompt(idx: int) -> str:
    return ("Return only the structured fields. Do not describe or restate this task. "
            f"Write the tool-call log of a health-plan analyst using Northline's MCP tools through their own AI assistant. Tools: member_engagement(plan_id), "
            f"outcome_evidence(plan_id, metric in bp_control|readings|satisfaction|escalations), enrollment_status(member_id like pt-1001), enroll_members(plan_id, count). "
            "Every tool value must be one of those four names exactly: member_engagement, outcome_evidence, enrollment_status, enroll_members. "
            f"Plan id plan-prairie. 2 to 5 calls. Session {idx}. Some sessions try a phone number or name as member_id and get not_found; almost none ask for escalations.")


def _valid_transcript(out: dict) -> bool:
    msgs = out.get("messages") or []
    if not (4 <= len(msgs) <= 8):
        return False
    for i, m in enumerate(msgs):
        if m.get("role") != ("assistant" if i % 2 == 0 else "user"):
            return False
        content = m.get("content") or ""
        if any(p in content for p in ("Write a", "conversation number", "tools_used")):
            return False
    return out.get("escalated") == ("escalate_to_nurse" in (out.get("tools_used") or []))


def _valid_plan(out: dict) -> bool:
    calls = out.get("calls") or []
    return (2 <= len(calls) <= 5) and all(c.get("tool") in PLAN_TOOLS for c in calls)


def _generate_validated(jobs: list[tuple[str, dict]], validate, *, ask, model: str = "sonnet", workers: int = 6, max_extra_attempts: int = 2) -> tuple[list[dict], list[int], int]:
    """Ask each job once; re-ask only the items that fail `validate`, up to `max_extra_attempts` more times each.
    Returns (results indexed like jobs, indices still invalid after all attempts, total re-ask count)."""
    results = ask(jobs, workers=workers, model=model)
    invalid = [i for i, o in enumerate(results) if not validate(o)]
    reasked = 0
    for _ in range(max_extra_attempts):
        if not invalid:
            break
        reasked += len(invalid)
        redo = ask([jobs[i] for i in invalid], workers=workers, model=model)
        for i, o in zip(invalid, redo):
            results[i] = o
        invalid = [i for i in invalid if not validate(results[i])]
    return results, invalid, reasked


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
        if rng.random() < 0.989:
            hours = math.exp(math.log(median) + rng.gauss(0, 0.7))
            answered = (created + timedelta(hours=hours)).isoformat(timespec="seconds")
        rows.append({"id": f"corpus-esc-{i:04d}", "patient_id": f"pt-{rng.randint(1, 40000)}", "reason": tier.replace("_", " "),
                     "urgency": "urgent" if tier == "urgent_clinical" else "routine", "created_at": created.isoformat(timespec="seconds"),
                     "answered_at": answered, "tier": tier, "route": None})
    return rows


def seed_exhibit_e(rows: list[dict]) -> None:
    for e in json.loads((TRIAGE / "exhibit_e.json").read_text(encoding="utf-8")):
        t = datetime.strptime(e["time"], "%I:%M %p")
        day = datetime(2026, 9, 8) if t.hour >= 12 else datetime(2026, 9, 9)
        rows.append({"id": f"exhibit-e-{e['n']:02d}", "patient_id": f"pt-e{e['n']:02d}", "reason": e["text"], "urgency": "routine",
                     "created_at": day.replace(hour=t.hour, minute=t.minute).isoformat(timespec="seconds"), "answered_at": None, "tier": None, "route": None})


def main(n_transcripts: int = 120, n_plan: int = 40, n_queue: int = 31200, ask=claude_json.ask_json_many) -> None:
    rng = random.Random(7)
    (CORPUS / "patient").mkdir(parents=True, exist_ok=True); (CORPUS / "plan").mkdir(exist_ok=True)
    for p in (CORPUS / "patient").glob("*.json"):
        p.unlink()
    for p in (CORPUS / "plan").glob("*.jsonl"):
        p.unlink()

    themes = plan(n_transcripts, seed=1)
    t_jobs = [(transcript_prompt(t, tier, i), TRANSCRIPT_SCHEMA) for i, (t, tier) in enumerate(themes)]
    t_results, t_dropped, t_reasked = _generate_validated(t_jobs, _valid_transcript, ask=ask)
    for i, (t, _) in enumerate(themes):
        if i not in t_dropped:
            (CORPUS / "patient" / f"p-{i:03d}.json").write_text(json.dumps(to_transcript(i, t, t_results[i], rng), indent=2), encoding="utf-8")
    print(f"transcripts: {n_transcripts - len(t_dropped)} written, {t_reasked} re-asked, {len(t_dropped)} dropped {sorted(t_dropped)}")

    p_jobs = [(plan_prompt(i), PLAN_SCHEMA) for i in range(n_plan)]
    p_results, p_dropped, p_reasked = _generate_validated(p_jobs, _valid_plan, ask=ask)
    for i in range(n_plan):
        if i in p_dropped:
            continue
        lines = [json.dumps({"ts": _stamp(rng).isoformat(timespec="seconds"), "session_id": f"corpus-s-{i:03d}", "persona": "plan",
                             "tool": c["tool"], "args": c["args"], "status": c["status"], "error": c.get("error") or None}) for c in p_results[i]["calls"]]
        (CORPUS / "plan" / f"s-{i:03d}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"plan sessions: {n_plan - len(p_dropped)} written, {p_reasked} re-asked, {len(p_dropped)} dropped {sorted(p_dropped)}")

    summary = json.loads((REPO_ROOT / "northline" / "sim" / "out" / "summary.json").read_text(encoding="utf-8"))["last_quarter"]
    rows = queue_rows(summary, n_queue, seed=2); seed_exhibit_e(rows)
    (CORPUS / "queue.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"{n_transcripts - len(t_dropped)} transcripts, {n_plan - len(p_dropped)} plan sessions, {len(rows)} queue rows")


if __name__ == "__main__":
    main()
