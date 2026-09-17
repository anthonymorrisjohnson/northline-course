from scripts import export_deck as ex


def test_slides_meta_reads_titles_and_notes():
    meta = ex.slides_meta(ex.SOURCE.read_text(encoding="utf-8"))
    assert len(meta) == 16
    assert meta[0]["title"] == "Setup, while you arrive" and meta[2]["title"] == "The Monday email"
    assert all(m["notes"] for m in meta)
    assert meta[2]["notes"].startswith("ROOM: Read the email aloud")
    assert "<" not in meta[5]["notes"] and "\n\n" in meta[5]["notes"]


def test_slides_meta_handles_a_slide_without_notes():
    meta = ex.slides_meta('<section class="slide" data-title="A &amp; B"><h2>x</h2></section>')
    assert meta == [{"title": "A & B", "notes": ""}]


def test_follow_along_is_built_from_its_body_and_has_notes():
    from scripts import build_follow_along as b
    built = b.OUT.read_text(encoding="utf-8")
    assert built.startswith("<title>Northline Follow Along</title>")
    b.build()
    assert b.OUT.read_text(encoding="utf-8") == built, "follow-along.html is stale: run scripts/build_follow_along.py"
    meta = ex.slides_meta(built)
    assert len(meta) == 16 and all(m["notes"] for m in meta) and meta[5]["title"] == "Step 1: /pm-run"
