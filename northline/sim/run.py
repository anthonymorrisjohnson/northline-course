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
    new_live = any(d["name"] != "checkin_agent" and d.get("live_from_week", 1) <= 52 for d in deps)
    summary = {"before": before, "last_quarter": last_q, "next_quarter": next_q, "prairie": m.average(prairie),
               "prairie_without": m.average(prairie_wo), "now": next_q if new_live else last_q, "deployments": deps}
    OUT.mkdir(exist_ok=True)
    (OUT / "weekly.json").write_text(json.dumps({"history": history, "next_quarter": nxt, "prairie": prairie, "prairie_without": prairie_wo}), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    s = main()
    print(f"last quarter: median {s['last_quarter']['nurse_response_median_h']}h, nurses {s['last_quarter']['nurses']}, "
          f"overtime {s['last_quarter']['overtime_hours_per_month']}h; prairie without new deployments: {s['prairie_without']['nurse_response_median_h']}h")
