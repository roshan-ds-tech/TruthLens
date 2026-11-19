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
