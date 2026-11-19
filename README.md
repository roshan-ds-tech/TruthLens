# TruthLens

**Offline, CPU-only forensic triage for image, video, audio and text evidence.** An investigator opens a case, adds
the media and the caption that came with it, and gets a reviewable report. Each finding points to a region, frame or
time span, carries a calibrated confidence *range* and names alternative explanations. Cross-modal rules show where
signals from different media support or weaken each other, and a hash-chained custody log records every step.
TruthLens never says "fake" or "real". It shows where the evidence disagrees, how strongly, and what a human should
check next. Everything runs locally for ₹0 (INNOVEDGE Hackathon 2026 · Problem Statement 04).

## Quick start

```sh
make setup     # Python 3.11 venv, pinned deps, models (needs the network once), UI build
make run       # http://127.0.0.1:8000 — API and UI, fully offline from here on
make demo      # analyze samples/demo_case and compare with samples/expected_report.json
```

Prerequisites on macOS: `brew install python@3.11 ffmpeg pango` and Node 20+. Other targets: `make test`,
`make validate`, `make dev` (API with reload on :8000 + Vite on :5173).

**Hosted version:** UI on Vercel, analysis API on a Hugging Face Space, both redeployed from `main`; sign up to use it.
Setup and hosted-mode behaviour: [`docs/deployment.md`](docs/deployment.md).

CLI: `./truthlens analyze clip.mp4 photo.jpg --caption caption.txt --report`, `./truthlens rerun --case C-0001`,
`./truthlens validate`.

## What the demo shows

`samples/demo_case/` follows the design-doc walkthrough: a 25 s clip with a cut at 14.0 s whose speech was recorded
in two rooms (noise steps up at 14.2 s), a still photo whose EXIF says Photoshop and 3 Mar 2024, and a caption dated
12 Nov 2026. `make demo` reproduces, exactly:

| Finding | Range | Rule |
|---|---|---|
| F-VID-001 optical-flow discontinuity · 00:14.0 | 0.87–0.95 | R-03 with F-AUD-001 |
| F-AUD-001 noise-floor step · 00:14.2 | 0.86–0.95 | R-03 |
| F-IMG-001 editing software tag · F-IMG-003 stale EXIF thumbnail | 0.77–0.95 | |
| F-TXT-001 caption date vs EXIF date | 0.76–0.95 | R-11 |
| **Case verdict: Strong indicators** | **0.92–0.97** | corroborated by two methods |

Untouched files do not get flagged: the original sample photos shipped with scikit-image and the macOS system sounds
all come out *No indicators found*. The Hubble JPEG comes out *Inconclusive*, because its EXIF says it was saved by
Photoshop CS5 and one metadata signal is never enough on its own.

## Screens

Dashboard · Cases · New case (drag-and-drop upload, hashing, caption) · Analysis (live per-analyzer progress and log) ·
Case workspace (video player, suspicion timeline, finding cards with accept / reject / note, correlation graph, custody
drawer) · Image viewer (original vs ELA / noise / copy-move layers, numbered regions, EXIF conflicts) · Audio viewer
(waveform, spectrogram, word-timed transcript) · Report preview (PDF / JSON export) · Validation · Settings (analyzer
toggles). Screenshots are not included yet; see `docs/limitations.md`.

## Requirements map

Full table with code paths and tests: [`docs/requirements_map.md`](docs/requirements_map.md).

| PDF capability | Feature |
|---|---|
| Image authenticity | ELA, noise residual, JPEG ghost, copy-move, EXIF rules → heatmaps + regions |
| Video forensics | duplicate / dropped frames, flow jumps, face flicker, frame forensics, suspicion curve |
| Audio & voice | noise-floor splice, band-limit, prosody, Whisper word timestamps |
| Text & context | claims vs EXIF date / GPS, creation time and transcript |
| Cross-modal correlation | named rules R-03 / 05 / 07 / 09 / 11 / 14 + evidence graph + independence rule |
| Manipulation indicators | typed findings with location, method, explanation, alternatives |
| Confidence & uncertainty | Platt-calibrated ranges, log-odds fusion, *Inconclusive* band, limitations |
| Report & traceability | SHA-256, read-only originals, hash-chained custody, PDF + JSON with its own hash, rerun command |

## Validation

`make validate` rebuilds a seeded test set (204 items) and writes `validation/results/metrics.json` and the calibration
the scorer uses. **Small self-made test set, not a general accuracy claim.**

| Indicator | Detection rate | False-positive rate |
|---|---|---|
| Copy-move | 0.92 | 0.00 |
| Error level (ELA) | 0.47 | 0.11 |
| Noise map | 0.28 | 0.19 |
| JPEG ghost | 0.75 | 0.31 |
| Audio noise-floor splice | 1.00 (median error 0.007 s) | 0.00 |
| Band limit (TTS / upsampled) | 1.00 | 0.00 |
| Flow jump / duplicate frame | 1.00 / 0.88 (median error 0.04 s) | 0.00 |
| Caption date / quote conflict | 1.00 / 1.00 | 0.00 |

Image region IoU 0.71. The Validation screen shows the full table, the reliability chart (5-fold cross-validated) and
the false-positive table.

## Repository

```
backend/app/        FastAPI app: ingest, custody, analyzers, correlate, scoring, report, api
backend/tests/      47 pytest tests incl. end-to-end, determinism, failure isolation, accounts
src/                React UI (already designed; wired through src/api/client.js)
validation/         synth.py (seeded generators), run_validation.py, results/
samples/            demo case + expected_report.json
docs/               methodology, limitations, requirements map, decisions, UI integration map, plan
```

## Limitations

Fully AI-generated media without editing traces may not be detected; pixel-level image signals are weak and the
validation set is small and synthetic; accounts have no password reset; the free hosted demo does not keep data;
search is not wired. Details:
[`docs/limitations.md`](docs/limitations.md). Design deviations and why: [`docs/decisions.md`](docs/decisions.md).
