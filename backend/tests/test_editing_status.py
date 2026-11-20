"""Editing status is separate from AI generation; speech gate abstains on unsuitable audio."""
from __future__ import annotations

import numpy as np

from app.analyzers import deepfake as det
from app.api import adapters
from app.scoring import deepfake as df
from app.scoring import editing


def test_supported_copy_move_is_edited():
    st = editing.item_status([{"family": "copy_move", "band": "indicators"}], analysed=True)
    assert st["key"] == "edited" and st["label"] == "Edited — indicators detected" and "Copy-move region" in st["types"]


def test_weak_findings_are_possible_not_confirmed():
    st = editing.item_status([{"family": "ela", "band": "inconclusive"}], analysed=True)
    assert st["key"] == "possible"


def test_metadata_only_is_not_a_pixel_edit():
    st = editing.item_status([{"family": "metadata", "band": "indicators"}], analysed=True)
    assert st["key"] == "metadata" and st["label"] == "Metadata changes detected"


def test_missing_checks_cannot_say_no_indicators():
    assert editing.item_status([], analysed=False)["key"] == "unavailable"
    assert editing.item_status([], analysed=True, checks_failed=True)["key"] == "unavailable"
    assert editing.item_status([], analysed=True)["key"] == "none"


def test_below_threshold_and_ai_findings_do_not_count_as_editing():
    st = editing.item_status([{"family": "noise", "band": "none"}, {"family": "ai_image", "band": "strong"}], analysed=True)
    assert st["key"] == "none"


def test_low_ai_signal_cannot_hide_editing(monkeypatch):
    monkeypatch.setattr(df, "_table", lambda: {})
    ai = df.assess_item({"kind": "image", "raw": 0.02}, None, "image")
    ed = editing.item_status([{"family": "copy_move", "band": "strong"}], analysed=True)
    shown = adapters.with_editing({"key": ai["label"], **ai}, ed, "image")
    assert shown["editing"]["key"] == "edited"
    assert "authentic" not in shown["label"].lower() and "Low AI-generation signal" == shown["label"]


def test_case_summary_names_the_driving_items():
    case = editing.case_status({"E-01": editing.item_status([{"family": "copy_move", "band": "indicators"}], True),
                                "E-02": editing.item_status([], True)})
    assert case["key"] == "edited" and case["items"] == ["E-01"] and "1 other item" in case["note"]


def test_audio_wording_does_not_claim_cloning():
    assert adapters.ai_label("deepfake", "audio") == "Strong synthetic-speech signal"
    assert "clon" not in adapters.ai_label("authentic", "audio").lower()


SR = 16000


def _gate(y, transcript):
    return det.speech_applicability(y.astype(np.float32), SR, transcript)


def test_silence_noise_and_short_clips_are_not_assessed():
    rng = np.random.default_rng(0)
    assert not _gate(np.zeros(SR * 5), {"n_words": 0, "mean_conf": 0})[0]
    assert not _gate(0.01 * rng.standard_normal(SR * 5), {"n_words": 0, "mean_conf": 0})[0]   # steady noise
    assert not _gate(0.3 * rng.standard_normal(SR // 2), {"n_words": 5, "mean_conf": 0.9})[0]  # too short


def test_unconfirmed_speech_abstains_rather_than_calling_it_synthetic():
    t = np.arange(SR * 5) / SR
    tone_bursts = np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 2 * t) > 0)   # music-like / procedural
    ok, reason, _ = _gate(tone_bursts, {"n_words": 0, "mean_conf": 0.0})
    assert not ok and "could not be confirmed" in reason
    out = df.assess_item({"kind": "audio", "raw": None, "applicable": False, "reason": reason}, None, "audio")
    assert out["p"] is None and out["not_applicable"] and out["label"] == "uncertain"


def test_confirmed_speech_passes_the_gate():
    t = np.arange(SR * 5) / SR
    voiced = np.sin(2 * np.pi * 150 * t) * (np.sin(2 * np.pi * 3 * t) > -0.3)
    tr = {"n_words": 12, "mean_conf": 0.8, "segments": [{"text": "the minister said the schools will close on monday"}]}
    assert _gate(voiced, tr)[0]


def test_repeated_recognizer_fragments_do_not_confirm_speech():
    t = np.arange(SR * 5) / SR
    voiced = np.sin(2 * np.pi * 150 * t) * (np.sin(2 * np.pi * 3 * t) > -0.3)
    tr = {"n_words": 112, "mean_conf": 0.94, "segments": [{"text": "B-B-B-B-B-B-B-B-B-B"}]}
    assert not _gate(voiced, tr)[0]


def test_stale_pre_gate_audio_result_is_withdrawn_for_display():
    old = {"version": "ai-only-v3", "key": "deepfake", "label": "Likely deepfake", "p": 0.97, "lo": 0.95, "hi": 0.99,
           "calibrated": True, "why": "x"}
    shown = adapters.with_editing(old, editing.item_status([], True), "audio")
    assert shown["p"] is None and shown["requires_rerun"] and shown["label"] == "Synthetic-speech check inconclusive"
    assert old["p"] == 0.97   # stored result untouched
