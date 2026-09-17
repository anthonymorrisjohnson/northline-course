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


def test_main_falls_back_to_committed_default_run(data_dir, monkeypatch, tmp_path, capsys):
    from northline.sim import run as sim_run
    monkeypatch.setattr(sim_run, "OUT", tmp_path)
    monkeypatch.setattr(deploy, "HERE", tmp_path / "triage")
    (tmp_path / "triage" / "fallback").mkdir(parents=True)
    (tmp_path / "triage" / "fallback" / "acceptance.json").write_text(json.dumps({"effects": {"inbound_to_nurse_share": 0.3, "routine_time_factor": 0.6, "urgent_recall": 1.0}}), encoding="utf-8")
    deploy.main()
    assert "fallback" in capsys.readouterr().out
    assert any(d["name"] == "triage" for d in store.load("deployments"))
