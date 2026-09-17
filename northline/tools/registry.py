"""The single list of Northline tools. Both front doors and the triage agent read this.

Adding a tool is one function with a docstring plus one line here. A tool with `requires`
appears only once that deployment is live in data/deployments.json; that is how /northline-deploy
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
