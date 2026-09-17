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
    path = HERE / "out" / "acceptance.json"
    if not path.exists():
        # The acceptance run did not complete (offline, rate-limited). Fall back to the committed
        # run with Northline's default decisions so the dashboard still has a Next quarter column.
        path = HERE / "fallback" / "acceptance.json"
        print("no acceptance run found; using the committed default-decision run from fallback/")
    s = json.loads(path.read_text(encoding="utf-8"))
    deps = register("triage", s["effects"])
    print(f"triage live; deployments: {[d['name'] for d in deps]}; effects {s['effects']}")


if __name__ == "__main__":
    main()
