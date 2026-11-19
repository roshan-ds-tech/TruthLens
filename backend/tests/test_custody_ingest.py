import os
import stat

import pytest
import sqlalchemy

from conftest import FIXTURES, upload


def test_hash_store_readonly_and_chain(data_dir):
    from app import config, custody, db
    from app.models import Case

    with db.session() as s:
        s.add(Case(id="C-0001", title="t", investigator="Priya S."))
        s.commit()
        sha = custody.sha256_file(FIXTURES / "image_clean.jpg")
        p = custody.store_original("C-0001", FIXTURES / "image_clean.jpg", sha, "jpg")
        assert p.parent.name == sha and str(p).startswith(str(config.EVIDENCE_DIR))
        assert not (os.stat(p).st_mode & stat.S_IWUSR), "original must be read-only"
        assert custody.verify_original("C-0001", sha)
        custody.log(s, "C-0001", "Priya S.", "a", "t", "—", "x")
        custody.log(s, "C-0001", "Priya S.", "b", "t", "x", "y")
        rows = custody.entries(s, "C-0001")
        assert custody.verify_chain(rows)
        rows[0].action = "edited"
        assert not custody.verify_chain(rows), "editing an entry must break the hash chain"


def test_custody_table_is_append_only(data_dir):
    from app import custody, db
    from app.models import Case

    with db.session() as s:
        s.add(Case(id="C-0001", title="t", investigator="p"))
        s.commit()
        custody.log(s, "C-0001", "p", "a", "t")
        with pytest.raises(sqlalchemy.exc.DatabaseError):
            s.exec(sqlalchemy.text("UPDATE custody_log SET action='x'"))
        s.rollback()
        with pytest.raises(sqlalchemy.exc.DatabaseError):
            s.exec(sqlalchemy.text("DELETE FROM custody_log"))


def test_magic_byte_detection():
    from app.ingest.detect_type import UnsupportedType, detect

    assert detect(FIXTURES / "image_clean.jpg").kind == "image"
    assert detect(FIXTURES / "video_clean.mp4").kind == "video"
    assert detect(FIXTURES / "audio_clean.wav").kind == "audio"
    assert detect(FIXTURES / "caption.txt").kind == "text"
    with pytest.raises(UnsupportedType):
        detect(FIXTURES / "unsupported.bin")


def test_upload_rules(client):
    cid = client.post("/api/cases", json={"title": "Ingest"}).json()["id"]
    r = upload(client, cid, "image_exif_edited.jpg")
    assert r.status_code == 200
    ev = r.json()
    assert ev["kind"] == "image" and len(ev["sha256"]) == 64 and ev["meta_label"].startswith("Image · 384×384")
    assert upload(client, cid, "image_exif_edited.jpg").json()["id"] == ev["id"], "same file twice → same evidence"
    assert upload(client, cid, "unsupported.bin").status_code == 415
    bad = upload(client, cid, "corrupt.jpg")
    assert bad.status_code == 422
    assert "/" not in bad.json()["detail"] and "tmp" not in bad.json()["detail"], "no server paths in user-facing errors"
    assert client.post(f"/api/cases/{cid}/evidence", data={"text": "   "}).status_code == 400
    t = client.post(f"/api/cases/{cid}/evidence", data={"text": "Caption 12 Nov 2026"}).json()
    assert t["kind"] == "text"
    actions = [e["action"] for e in client.get(f"/api/cases/{cid}/custody").json()["entries"]]
    assert actions[0] == "Case opened" and any("Image ingested and sealed" in a for a in actions)


def test_oversized_image_rejected(client, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "MAX_IMAGE_BYTES", 1000)
    cid = client.post("/api/cases", json={"title": "Big"}).json()["id"]
    assert upload(client, cid, "image_clean.jpg").status_code == 413


def test_video_with_audio_gets_derived_track(client, tmp_path):
    import synth

    import numpy as np

    frames = synth.pan_frames(np.asarray(dict(synth.photos())["coffee"]), 3.0, 25, (160, 120))
    p = tmp_path / "clip.mp4"
    synth.write_video(p, frames, 25, synth.recording(3.0, 5))
    cid = client.post("/api/cases", json={"title": "AV"}).json()["id"]
    with open(p, "rb") as f:
        assert client.post(f"/api/cases/{cid}/evidence", files={"file": ("clip.mp4", f, "video/mp4")}).status_code == 200
    evs = client.get(f"/api/cases/{cid}").json()["evidence"]
    assert [e["kind"] for e in evs] == ["video", "audio"]
    assert evs[1]["derived_from"] == "E-01"
