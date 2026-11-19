from app.correlate import rules
from app.scoring import calibrate, fuse


def sig(fid, fam, p, spread=0.06):
    return fuse.Signal(fid, fam, p, max(0, p - spread), min(1, p + spread))


def test_no_findings_is_no_indicators():
    out = fuse.fuse([])
    assert out.band == "none" and out.hi < 0.4


def test_single_signal_never_strong():
    out = fuse.fuse([sig("a", "noise_floor", 0.95)])
    assert out.band in ("indicators", "inconclusive") and not out.corroborated


def test_two_independent_families_can_be_strong():
    out = fuse.fuse([sig("a", "noise_floor", 0.86), sig("b", "optical_flow", 0.84)])
    assert out.corroborated and out.band == "strong"


def test_same_family_is_not_counted_twice():
    one = fuse.fuse([sig("a", "ela", 0.8)])
    two = fuse.fuse([sig("a", "ela", 0.8), sig("b", "ela", 0.79)])
    assert one.p == two.p and not two.corroborated


def test_weak_range_is_inconclusive():
    out = fuse.fuse([sig("a", "prosody", 0.45, 0.12)])
    assert out.band in ("inconclusive", "none")
    mid = fuse.band(0.45, 0.62, False)
    assert mid == "inconclusive"


def test_uncalibrated_fallback_is_flagged():
    c = calibrate.calibrate("no_such_indicator", 0.6)
    assert not c.calibrated and c.lo < c.p < c.hi


def F(fid, ev, ind, fam, loc, parent=None, mod=None, p=0.8, extra=None, kind=None):
    return rules.F(fid, ev, kind or mod or "video", parent, mod or "video", ind, fam, loc, p, extra or {})


def test_r03_splice_sync_fires_only_on_same_timeline():
    a = F("F-AUD-001", "E-02", "noise_floor_step", "noise_floor", {"type": "time_range", "start": 14.2, "end": 14.7},
          parent="E-01", mod="audio")
    v = F("F-VID-001", "E-01", "flow_discontinuity", "optical_flow", {"type": "frame_range", "start": 14.0, "end": 14.04})
    edges = rules.r03_splice_sync([a, v], {})
    assert len(edges) == 1 and edges[0].relation == "supports"
    far = F("F-VID-002", "E-01", "flow_discontinuity", "optical_flow", {"type": "frame_range", "start": 20.0, "end": 20.04})
    assert rules.r03_splice_sync([a, far], {}) == []
    other = F("F-AUD-002", "E-09", "noise_floor_step", "noise_floor", {"type": "time_range", "start": 14.2, "end": 14.7}, mod="audio")
    assert rules.r03_splice_sync([other, v], {}) == []
    fam = {"F-AUD-001": "noise_floor", "F-VID-001": "optical_flow"}
    assert rules.independent_supports(edges, fam) == 1


def test_r14_weakens_ela_on_stripped_recompressed_image():
    f = F("F-IMG-001", "E-01", "ela_inconsistency", "ela", {"type": "bbox", "x": 0, "y": 0, "w": 10, "h": 10},
          mod="image", extra={"area_fraction": 0.05})
    ev = {"E-01": rules.Ev("E-01", "image", None, {"exif": {}, "jpeg_quality": 82}, {})}
    edges = rules.r14_recompression([f], ev)
    assert edges and edges[0].relation == "weakens" and edges[0].weight_scale["F-IMG-001"] == 0.5
    ev_cam = {"E-01": rules.Ev("E-01", "image", None, {"exif": {"Make": "x"}, "jpeg_quality": 95}, {})}
    assert rules.r14_recompression([f], ev_cam) == []


def test_r11_date_conflict_links_to_image():
    t = F("F-TXT-001", "E-03", "claim_date_conflict", "claim_date", {"type": "text_span", "start": 0, "end": 5},
          mod="text", extra={"target_evidence": "E-02", "gap_days": 984})
    i = F("F-IMG-001", "E-02", "ela_inconsistency", "ela", {"type": "bbox"}, mod="image", p=0.6)
    edges = rules.r11_claimed_date([t, i], {})
    assert edges[0].target == "F-IMG-001"
