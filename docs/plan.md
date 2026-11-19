# TruthLens build plan

Source of truth: `TruthLens — System Design, Architecture & UI Brief.pdf` (17 pages, 19 Nov 2026) and
Problem Statement 04 (page 4 of `1_2_3_4_merged.pdf`). The React UI in `src/` is already built and is
not redesigned; the backend is shaped to fit it (see `ui_integration_map.md`).

Each phase ends with `make test` green and a commit.

| # | Phase | Done when |
|---|-------|-----------|
| 1 | Audit and plan | `docs/ui_integration_map.md`, `docs/plan.md`, `docs/decisions.md` written |
| 2 | Backbone | SQLite models, Finding schema, custody log, ingest (magic bytes, SHA-256, read-only store, metadata), 1-worker job queue with progress, case / evidence / job endpoints. UI: case list, new case, upload, progress wired |
| 3 | Image analyzer | ELA, noise residual, copy-move (ORB + RANSAC), EXIF rules, JPEG ghost, each with heatmap / overlay artifacts. UI: image viewer + layer toggles wired |
| 4 | Audio + text | Noise-floor splice, band-limit, pitch/pause stats, faster-whisper words; caption claims + consistency. UI: waveform, spectrogram, transcript wired |
| 5 | Video | Frame sampling, pHash dupes/drops, Farneback flow jumps, MediaPipe face flicker, image pipeline on top frames, per-second suspicion curve, audio track extraction. UI: timeline wired |
| 6 | Correlation + confidence | Named rules (R-03, R-05, R-07, R-09, R-11, R-14), evidence graph, independence rule, Platt calibration, log-odds fusion, ranges, verdict bands. UI: findings panel, range bars, graph, case verdict wired |
| 7 | Review + report | Accept / reject / note; Jinja2 → WeasyPrint PDF + JSON with hashes, rerun command, report hash in custody. UI: report preview + custody drawer wired |
| 8 | Validation | Seeded image / audio / video sets with ground truth, `metrics.json`, reliability table, calibration fit. UI: validation page reads `metrics.json` |
| 9 | Hardening | Clean files → No indicators / Inconclusive; corrupt, unsupported, oversized inputs; analyzer crash → limitation, never a failed case |

Cut order if behind (from the design doc): face flicker → JPEG ghost → lip-sync rule → prosody.
Never cut: custody, image pipeline, cross-modal rules, Inconclusive verdict, validation metrics, report.

## Deliverables checklist

- `Makefile`: `setup`, `run`, `test`, `validate`, `demo`
- CLI: `truthlens analyze <files>`, `truthlens rerun --case <id>`, `truthlens validate`
- `pytest`: one test module per analyzer (with a clean fixture per modality that must not be "Strong"),
  end-to-end, determinism
- `samples/` demo case + `expected_report.json`
- `README.md`, `docs/methodology.md`, `docs/limitations.md`, `docs/requirements_map.md`,
  `docs/ui_integration_map.md`, `docs/decisions.md`
