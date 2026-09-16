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
