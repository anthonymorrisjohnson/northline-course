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
