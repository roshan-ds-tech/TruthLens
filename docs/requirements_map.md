# Requirements map

Left column: Problem Statement 04, page 4 ("Core capabilities", "What the report should show", "Expected deliverable").

| PDF capability | TruthLens feature | Code | Test / proof |
|---|---|---|---|
| Image authenticity analysis | ELA, noise residual, JPEG ghost, ORB+RANSAC copy-move, EXIF rules (editor tag, missing camera tags, date gap, stale thumbnail) | `backend/app/analyzers/image/` | `test_analyzers.py::test_image_*`, `test_copy_move_found`, `test_exif_rules`; validation IoU 0.71 |
| Video forensics | Frame decode, pHash duplicates, timestamp gaps, Farneback flow jumps, MediaPipe face flicker, image pipeline on top frames, per-second suspicion curve | `analyzers/video/` | `test_video_jump_and_duplicate`, `test_video_clean_no_findings`; validation edit error 0.04 s |
| Audio & voice analysis | Noise-floor splice (persistent step + change-point), band-limit check, pitch/pause statistics, faster-whisper words | `analyzers/audio/` | `test_audio_splice_timestamp`, `test_band_limit`, `test_prosody_runs`, `test_transcript_when_model_present`; splice error 0.007 s |
| Text & context analysis | Claim extraction (dates, places, people, numbers, quotes); checks against EXIF date/GPS, video creation time, transcript (MiniLM) | `analyzers/text/` | `test_claims_extraction`, `test_caption_date_conflict_with_exif`, `test_caption_consistent_date_is_not_flagged` |
| Cross-modal correlation | Named rules R-03 splice↔motion, R-05 caption↔speech, R-07 lip-sync, R-09 same location, R-11 date↔metadata, R-14 recompression weakens ELA; networkx evidence graph; independence rule | `correlate/` | `test_scoring_rules.py::test_r03_*`, `test_r14_*`, `test_r11_*`; demo fires R-03 and R-11 |
| Manipulation indicators | Typed indicator catalogue; every finding has location, method, explanation, alternatives, artifacts | `analyzers/base.py`, `models.py` (Finding contract) | `test_full_workflow` asserts method, explanation and location on every finding |
| Confidence & uncertainty | Platt calibration from validation, Beta ranges, weighted log-odds fusion with diminishing returns, verdict bands incl. Inconclusive, limitations per verdict | `scoring/` | `test_scoring_rules.py`, `test_clean_files_are_not_strong`, `test_failed_analyzer_does_not_fail_case` |
| Forensic report & traceability | SHA-256, read-only originals, hash-chained append-only custody log, HTML/PDF/JSON report with own hash in custody, rerun command | `custody.py`, `report/` | `test_custody_table_is_append_only`, `test_hash_store_readonly_and_chain`, `test_full_workflow`, `test_rerun_is_deterministic` |
| Human review (keep conclusions reviewable) | Accept / reject / note per finding, logged in custody, printed in report | `api/routes.py` `review_finding` | `test_full_workflow` |
| Workflow: Ingest → Analyze → Correlate → Review → Report | New case → Analysis → Workspace → Report screens | `src/screens/` | `samples/check_demo.py` (`make demo`) |
| Report shows: flagged evidence, indicator, cross-modal context, confidence, source trace, summary + recommended checks | Report sections: evidence table with hashes, findings with thumbnails/locations, correlation summary, ranges, claims table, limitations, recommended human checks, reviewer decisions | `report/templates/report.html.j2` | `samples/expected_report.json` |
| Calibrated confidence and honest uncertainty | Validation harness and reliability table (5-fold CV) | `validation/run_validation.py` | `validation/results/metrics.json` |
