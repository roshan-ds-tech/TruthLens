"""Deepfake assessment: label mapping, probability combination and the three-way verdict."""
from __future__ import annotations

import pytest

from app.analyzers import deepfake as det
from app.scoring import deepfake as df


@pytest.mark.parametrize("labels,expected", [
    ({"0": "fake", "1": "real"}, 0),
    ({"0": "artificial", "1": "human"}, 0),
    ({"0": "HUMAN", "1": "AI"}, 1),
    ({"0": "Human", "1": "ChatGPT"}, 1),
    ({"0": "bonafide", "1": "spoof"}, 1),
])
def test_fake_index_reads_the_models_own_labels(labels, expected):
    assert det.fake_index(labels) == expected


def test_fake_index_refuses_unknown_labels():
    with pytest.raises(ValueError):
        det.fake_index({"0": "cat", "1": "dog"})


@pytest.mark.parametrize("p,lo,hi,label", [
    (0.90, 0.80, 0.95, "deepfake"),
    (0.70, 0.45, 0.85, "uncertain"),     # range dips below 50 %
    (0.10, 0.05, 0.20, "authentic"),
    (0.30, 0.10, 0.55, "uncertain"),     # range reaches above 50 %
    (0.50, 0.40, 0.60, "uncertain"),
])
def test_three_way_label(p, lo, hi, label):
    assert df.label(p, lo, hi) == label


def _no_calibration(monkeypatch):
    monkeypatch.setattr(df, "_table", lambda: {})


def test_uncalibrated_detector_gets_a_wide_range(monkeypatch):
    _no_calibration(monkeypatch)
    out = df.calibrate("ai_image", 0.9)
    assert out["calibrated"] is False and out["lo"] == pytest.approx(0.7) and out["hi"] == pytest.approx(1.0)


def test_calibrated_detector_uses_platt_and_bootstrap(monkeypatch):
    monkeypatch.setattr(df, "_table", lambda: {"detectors": {"ai_image": {"A": 8.0, "B": -4.0, "auc": 0.95, "n": 200,
                                                                          "boot": [[7.5, -3.8], [8.5, -4.2], [8.0, -4.0]]}}})
    hi_score, lo_score = df.calibrate("ai_image", 0.95), df.calibrate("ai_image", 0.05)
    assert hi_score["calibrated"] and hi_score["p"] > 0.95 and lo_score["p"] < 0.05
    assert hi_score["lo"] <= hi_score["p"] <= hi_score["hi"]


def test_item_combines_detector_and_manipulation(monkeypatch):
    _no_calibration(monkeypatch)
    out = df.assess_item({"kind": "image", "raw": 0.5}, {"p": 0.8, "lo": 0.7, "hi": 0.9, "findings": 2}, "image")
    assert out["p"] == pytest.approx(1 - 0.5 * 0.2)       # 1 − (1 − P_ai)(1 − P_manip)
    assert out["label"] == "deepfake"
    assert "AI-generation detector" in out["why"] and "manipulation evidence" in out["why"]


def test_manipulation_without_findings_is_ignored(monkeypatch):
    _no_calibration(monkeypatch)
    out = df.assess_item({"kind": "audio", "raw": 0.1}, {"p": 0.6, "lo": 0.5, "hi": 0.7, "findings": 0}, "audio")
    assert out["p"] == pytest.approx(0.1) and out["manipulation"] is None


def test_short_text_cannot_be_confident(monkeypatch):
    _no_calibration(monkeypatch)
    out = df.assess_item({"kind": "text", "raw": 0.97}, None, "text", text_words=12)
    assert out["label"] == "uncertain" and out["ai"]["short_text"]


def test_probability_never_reaches_certainty(monkeypatch):
    _no_calibration(monkeypatch)
    out = df.assess_item({"kind": "audio", "raw": 1.0}, {"p": 0.97, "lo": 0.95, "hi": 0.97, "findings": 1}, "audio")
    assert out["p"] == df.P_MAX and out["hi"] == df.P_MAX


def test_text_contradicting_other_evidence_is_not_called_ai_written(monkeypatch):
    _no_calibration(monkeypatch)
    out = df.assess_item({"kind": "text", "raw": 0.1}, {"p": 0.9, "lo": 0.8, "hi": 0.95, "findings": 1}, "text", text_words=80)
    assert out["manipulation"] is None and out["p"] == pytest.approx(0.1)


def test_nothing_to_go_on_is_uncertain_without_a_number():
    out = df.assess_item(None, None, "image")
    assert out["label"] == "uncertain" and out["p"] is None


def test_case_follows_its_most_likely_item(monkeypatch):
    _no_calibration(monkeypatch)
    items = {"E-01": df.assess_item({"kind": "video", "raw": 0.1}, None, "video"),
             "E-02": df.assess_item({"kind": "audio", "raw": 0.95}, None, "audio"),
             "E-03": df.assess_item(None, None, "text")}
    case = df.assess_case(items)
    assert case["driver"] == "E-02" and case["p"] == items["E-02"]["p"] and case["why"].startswith("E-02")
