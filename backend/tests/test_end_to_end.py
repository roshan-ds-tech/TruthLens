"""Case → upload → analyze → findings → review → report, plus determinism and failure isolation."""
from pathlib import Path

from conftest import run_analysis, upload


def _new_case(client, title="Viral clip"):
    return client.post("/api/cases", json={"title": title, "description": "End-to-end test"}).json()["id"]


def test_full_workflow(client):
    cid = _new_case(client)
    for name in ("video_jump.mp4", "image_exif_edited.jpg"):
        assert upload(client, cid, name).status_code == 200
    caption = (Path(__file__).parent / "fixtures" / "caption.txt").read_text()
    assert client.post(f"/api/cases/{cid}/evidence", data={"text": caption}).status_code == 200
    job = run_analysis(client, cid)
    assert job["progress"] == 1.0 and job["log"][-1]["msg"].startswith("complete")

    case = client.get(f"/api/cases/{cid}").json()
    assert case["status"] == "analyzed" and case["verdict"]["key"] in ("strong", "ind", "inc", "none")
    findings = client.get(f"/api/cases/{cid}/findings").json()
    ids = [f["finding_id"] for f in findings]
    assert len(ids) == len(set(ids)) and any(i.startswith("F-VID-") for i in ids) and any(i.startswith("F-TXT-") for i in ids)
    for f in findings:
        assert 0 <= f["conf_low"] <= f["score"] <= f["conf_high"] <= 1
        assert f["method"] and f["explanation"] and f["location"]["type"]
    date = next(f for f in findings if f["indicator"] == "claim_date_conflict")
    graph = client.get(f"/api/cases/{cid}/graph").json()
    assert any(r["id"] == "R-11" for r in graph["rules"]), graph["rules"]

    r = client.patch(f"/api/findings/{date['id']}/review", json={"decision": "accepted", "note": "EXIF checked"})
    assert r.status_code == 200 and r.json()["review"]["status"] == "accepted"
    assert client.get(f"/api/cases/{cid}").json()["pending_review"] == len(findings) - 1

    rep = client.post(f"/api/cases/{cid}/report").json()
    assert len(rep["sha256"]) == 64
    for kind in ("json", "html"):
        assert client.get(f"/api/cases/{cid}/report.{kind}").status_code == 200
    body = client.get(f"/api/cases/{cid}/report").json()
    assert body["sha256"] == rep["sha256"] and body["rerun_command"] == f"truthlens rerun --case {cid}"
    assert any(d["decision"] == "accepted" and d["note"] == "EXIF checked" for d in body["review_decisions"])
    assert body["source_context"][0]["text"] == caption.strip()
    assert body["analysis"]["run_count"] == 1 and body["analysis"]["status"] == "done"
    assert body["analysis"]["steps"] and body["analysis"]["tool_versions"]
    assert body["custody"]["entries"] == len(body["analysis_history"])
    from app import custody
    previous = custody.GENESIS
    for entry in body["analysis_history"]:
        assert entry["prev_hash"] == previous
        assert entry["entry_hash"] == custody._entry_hash(previous, cid, entry["ts"], entry["actor"],
            entry["action"], entry["tool"], entry["input_hash"], entry["output_hash"])
        previous = entry["entry_hash"]
    report_html = client.get(f"/api/cases/{cid}/report.html").text
    assert "Original text and evidence context" in report_html
    assert "Analysis and custody history" in report_html
    assert "EXIF checked" in report_html

    cust = client.get(f"/api/cases/{cid}/custody").json()
    assert cust["chain_valid"]
    last = cust["entries"][-1]
    assert last["action"].startswith("Report draft") and rep["sha256"] in last["output_hash"]
    assert any(e["action"].startswith("F-TXT") and "accepted" in e["action"] for e in cust["entries"])


def test_clean_files_are_not_strong(client):
    cid = _new_case(client, "Clean set")
    for name in ("image_clean.jpg", "video_clean.mp4", "audio_clean.wav"):
        upload(client, cid, name)
    run_analysis(client, cid)
    case = client.get(f"/api/cases/{cid}").json()
    assert case["verdict"]["key"] in ("none", "inc"), case["verdict"]
    for ev in case["evidence"]:
        assert ev["verdict"]["key"] != "strong", ev


def test_rerun_is_deterministic(client):
    cid = _new_case(client, "Determinism")
    for name in ("image_spliced.jpg", "audio_spliced.wav", "video_jump.mp4"):
        upload(client, cid, name)
    run_analysis(client, cid)
    first = [(f["finding_id"], f["indicator"], f["score"], f["conf_low"], f["conf_high"], f["location"])
             for f in client.get(f"/api/cases/{cid}/findings").json()]
    run_analysis(client, cid)
    second = [(f["finding_id"], f["indicator"], f["score"], f["conf_low"], f["conf_high"], f["location"])
              for f in client.get(f"/api/cases/{cid}/findings").json()]
    assert first and first == second
    runs = [e for e in client.get(f"/api/cases/{cid}/custody").json()["entries"] if e["action"].startswith("Analysis run")]
    assert len(runs) == 2 and runs[0]["output_hash"] == runs[1]["output_hash"]


def test_failed_analyzer_does_not_fail_case(client, monkeypatch):
    from app import registry

    def boom(ctx):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(registry.ALL["ela"], "fn", boom)
    cid = _new_case(client, "Crash")
    upload(client, cid, "image_clean.jpg")
    job = run_analysis(client, cid)
    steps = {s["key"]: s["status"] for s in job["items"][0]["steps"]}
    assert steps["ela"] == "failed" and steps["noise"] == "done"
    case = client.get(f"/api/cases/{cid}").json()
    assert any("Error level analysis failed" in l for l in case["limitations"])
    assert case["verdict"]["key"] == "inc", "a missing detector must not produce 'No indicators found'"


def test_disabled_analyzer_is_skipped(client):
    client.put("/api/settings", json={"analyzers": {"copy_move": False}})
    cid = _new_case(client, "Settings")
    upload(client, cid, "image_clean.jpg")
    job = run_analysis(client, cid)
    assert {s["key"]: s["status"] for s in job["items"][0]["steps"]}["copy_move"] == "skipped"


def test_api_errors(client):
    cid = _new_case(client, "Errors")
    assert client.post(f"/api/cases/{cid}/analyze").status_code == 400
    assert client.get("/api/cases/C-9999").status_code == 404
    assert client.patch("/api/findings/9999/review", json={"decision": "accepted"}).status_code == 404
    assert client.post(f"/api/cases/{cid}/report").status_code == 409
    assert client.post("/api/cases", json={"title": " "}).status_code == 400


import pytest

@pytest.mark.parametrize("text_first", [True, False])
def test_caption_checks_transcript_independently_of_upload_order(client, monkeypatch, text_first):
    from app import registry
    from app.analyzers.text import consistency
    client.put("/api/settings", json={"analyzers": {k: k in ("transcript", "consistency") for k in registry.ALL}})
    def transcript(ctx):
        data = {"segments": [{"text": "We discuss the annual budget today.", "start": 0, "end": 3}]}
        ctx.shared.setdefault("transcripts", {})[ctx.label] = data
        ctx.extra["transcript"] = data
        return []
    monkeypatch.setattr(registry.ALL["transcript"], "fn", transcript)
    monkeypatch.setattr(consistency, "similarities", lambda query, candidates: [.05] * len(candidates))
    cid = _new_case(client, "Caption dependency")
    caption = 'The speaker said "The spacecraft landed on Mars."'
    if text_first:
        client.post(f"/api/cases/{cid}/evidence", data={"text": caption})
    audio = upload(client, cid, "audio_clean.wav").json()
    if not text_first:
        client.post(f"/api/cases/{cid}/evidence", data={"text": caption})
    run_analysis(client, cid)
    findings = client.get(f"/api/cases/{cid}/findings").json()
    conflicts = [f for f in findings if f["indicator"] == "claim_speech_mismatch"]
    assert conflicts and conflicts[0]["extra"]["target_evidence"] == audio["label"]


def test_turning_off_all_detectors_is_not_a_clean_bill_of_health(client):
    from app import registry
    client.put("/api/settings", json={"analyzers": {k: False for k in registry.ALL}})
    cid = _new_case(client, "No analysis coverage")
    upload(client, cid, "image_clean.jpg")
    run_analysis(client, cid)
    case = client.get(f"/api/cases/{cid}").json()
    assert case["verdict"]["key"] == "inc"
    assert case["deepfake"]["key"] == "uncertain" and case["deepfake"]["p"] is None


def test_command_line_analysis_retains_coverage_for_report(client):
    from app import db, pipeline, registry
    client.put("/api/settings", json={"analyzers": {k: False for k in registry.ALL}})
    cid = _new_case(client, "CLI traceability")
    upload(client, cid, "image_clean.jpg")
    with db.session() as session:
        pipeline.run_case(session, cid, None, "CLI QA")
    assert client.post(f"/api/cases/{cid}/report").status_code == 200
    report = client.get(f"/api/cases/{cid}/report").json()
    assert report["analysis"]["origin"] == "command-line"
    assert report["analysis"]["status"] == "done" and report["analysis"]["steps"]
    assert report["analysis"]["tool_versions"] and report["analysis"]["log"]
    assert all(step["status"] == "skipped" for step in report["analysis"]["steps"][0]["steps"])
