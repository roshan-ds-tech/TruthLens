# TruthLens — handoff for coding agents

This file is the complete working memory of the previous agent (Claude Code) that built TruthLens with the owner
(Roshan D S, GitHub `roshan-ds-tech`). Read it fully before changing anything. It covers what the project is, the rules
the owner set, how every part works, how it is deployed, what was done in which order, what went wrong and how it was
fixed, the measured results, the known limitations, and what is still open. Details live in `docs/`; this file tells
you where.

State at hand-off: `main` at `f98ace0`, CI green, live demo running.

---

## 1. What TruthLens is

An **offline, CPU-only forensic triage tool for image, video, audio and text evidence**, built for the INNOVEDGE
Hackathon 2026, **Problem Statement 04** (multimodal misinformation / deepfake detection).

An investigator opens a case, adds media and the caption that came with it, runs an analysis, and gets:

- **Findings**: each one points to a region, frame or time span, has a calibrated confidence *range*, an explanation,
  and alternative innocent explanations. The reviewer can accept, reject or annotate it.
- **Cross-modal correlation rules** (R-03, R-05, R-07, R-09, R-11, R-14) showing where signals from different media
  support or weaken each other, drawn as a graph.
- **A manipulation verdict** per item and per case: No indicators found / Inconclusive / Indicators of manipulation /
  Strong indicators, with a range.
- **A deepfake assessment** per item and per case (added last): **Likely deepfake / Likely authentic / Uncertain**
  with a calibrated probability and range.
- **A hash-chained, append-only chain-of-custody log**, plus an exportable report (PDF, HTML, JSON).

The owner's stated main objective (latest): *"say whether the media is deepfake or not … give the confidence level of
deepfake"*. Both the forensic bands and the deepfake assessment are shown everywhere.

---

## 2. Owner's rules (still in force unless noted)

From the original build prompt:

1. **Do not redesign, restyle, rename or restructure the UI.** The UI came from a Claude Design file
   (`TruthLens.dc.html`) and was ported to React as-is. **Ask before any change that alters the UI's appearance.**
   Adding requested features (for example the Video evidence page and the deepfake cards) was explicitly asked for.
2. Stack: **Python 3.11, FastAPI, SQLite**; **offline at analysis time, CPU only, ₹0 cost, under 3 GB RAM,
   deterministic** (fixed seed).
3. **Originals are read-only**; the **custody log is append-only** (SQLite triggers block UPDATE and DELETE).
4. **No fabricated numbers anywhere.** Every metric shown comes from `validation/results/metrics.json`, produced by a
   script you can rerun.
5. **Ask before deleting files, or before adding a heavy dependency** (over about 500 MB or needing a GPU).
   The owner approved the ~2.4 GB of deepfake detector downloads.
6. Original wording rule: never use the words "fake" or "real" in outputs. **Superseded for the deepfake label only**:
   the owner asked for the word "deepfake". The labels are "Likely deepfake / Likely authentic / Uncertain"; "real" is
   still avoided in UI copy (D-21).
7. Deliverables (Phases 1–9 in `docs/plan.md`): tests, Makefile, CLI, `samples/` demo with `expected_report.json`,
   README, docs (`ui_integration_map.md`, `plan.md`, `decisions.md`, and more).

Working-style preferences the owner showed:

- They want work **pushed** to GitHub and the **live backend restarted by the agent** after backend changes
  ("push everything and stop the backend and start backend by yourself").
- They ask for progress updates when a long job runs.
- They accepted the "3-way with %" verdict (with Uncertain) over a strict yes/no.
- They chose "Real footage, no talking face" for the Home clip: no AI-generated talking person.
- The original source PDFs (problem statement and design docs) must stay **out of the public repo**.

---

## 3. Repository map

```
/                      React 19 + Vite frontend at the repo root (D-01)
  index.html, vite.config.js, package.json, vercel.json
  src/
    App.jsx            shell: sidebar nav, header, screen switching (all screens stay mounted, hidden with display:none)
    ui.jsx             shared tokens and components (colours c.*, YELLOW, VERDICTS, Icon, VerdictPill, RangeBar …)
    Deepfake.jsx       DeepfakePill + DeepfakeCard (deepfake verdict UI, used everywhere)
    api/client.js      data layer: api.get/post/patch, useApi hook, useMediaUrl (authenticated blob URLs),
                       download(), useServerMode, PRIVACY copy table, API_BASE + /api-config.json refresh
    api/media.jsx      AuthImg, EvidencePreview
    screens/           Home, HomePreview, Dashboard, Cases, NewCase, Analysis, CaseWorkspace, VideoViewer,
                       ImageViewer, AudioViewer, TextViewer, ReportPreview, EvidenceLibrary, Validation, Settings
  public/              fonts (Inter, IBM Plex Mono, Material Symbols, bundled), img/, media/home-demo.mp4 + .json
  tests/api-address.test.mjs   frontend unit test for the API-address recovery
backend/
  app/
    main.py            FastAPI app, CORS, static UI serving
    config.py          paths, env vars, labels, FAMILY_WEIGHTS, limitations text
    models.py          SQLModel tables: Case, Evidence, FindingRow, Correlation, Review, CustodyLog, ReportRow, Job,
                       User, AuthSession, Setting
    db.py, jobs.py     engine/session; background job executor
    auth.py            /api/auth/signup|login|logout|me; scrypt hashes; SHA-256-hashed bearer tokens (7 days);
                       login rate limit; can_see(case, user)
    custody.py         hash-chained custody log
    ingest/            type detection (filetype), metadata (EXIF, ffprobe), ingest_file / ingest_text,
                       derived audio track from video
    analyzers/
      base.py          AnalysisContext, RawFinding, FnAnalyzer, fmt_t, isolated() (run a model in a child process)
      image/           ela, noise, jpeg_ghost, copy_move (ORB + RANSAC), exif_rules
      video/           frames, phash_dupes, flow_jumps (Farneback), face_flicker (MediaPipe FaceLandmarker)
      audio/           splice (noise floor), bandlimit, prosody (pYIN), transcribe (faster-whisper base int8)
      text/            claims (dateparser/spaCy vs EXIF/transcript), consistency (MiniLM), gazetteer
      deepfake.py      learned AI-generation detectors (image, video frames, voice, text)
    correlate/         rules.py (R-xx), lipsync.py (R-07), graph.py
    scoring/
      calibrate.py     Platt + bootstrap per indicator (validation/results/calibration.json)
      fuse.py          log-odds fusion with 0.6^k decay and caps → manipulation bands
      deepfake.py      deepfake assessment (calibration from deepfake_calibration.json, 3-way label)
    pipeline.py        run_case(): runs analyzers, assigns finding IDs, calibrates, correlates, fuses, persists,
                       custody entries, findings digest
    registry.py        analyzer registry, ORDER per media kind, DATA_STEPS, AI_STEPS, enabled map, versions
    api/routes.py      all /api routes; api/adapters.py turns DB rows into the exact shapes the UI expects
    report/            render.py + templates/report.html.j2 → WeasyPrint PDF; fonts embedded
  cli.py               CLI (wrapped by ./truthlens): analyze | rerun | report | validate
  scripts/fetch_models.py   downloads all models into backend/models (git-ignored)
  tests/               pytest (70 tests): analyzers, auth, custody/ingest, deepfake, end-to-end, scoring/rules
  requirements.txt     pinned; torch==2.14.1, torchvision==0.29.1
validation/
  synth.py, run_validation.py          seeded synthetic test set (204 items) → metrics.json + calibration.json
  fetch_deepfake_sets.py               downloads public labelled real-vs-AI samples (validation/data/, git-ignored)
  run_deepfake_validation.py           compares candidate detectors, picks best, calibrates
  results/metrics.json, calibration.json, deepfake_calibration.json   (committed)
samples/
  demo_case/ (clip.mp4, podium_photo.jpg, caption.txt), make_demo.py, check_demo.py, expected_report.json
  make_home_demo.py    builds public/media/home-demo.mp4 + home-demo.json (Home page live preview)
scripts/demo_host.py   start | stop | status | connect: Mac backend + Cloudflare Quick Tunnel + Vercel redeploy
docs/                  plan, decisions (D-01…D-22), methodology, limitations, requirements_map, ui_integration_map,
                       deployment, visual-qa-2026-11-19, manual-walkthrough
Dockerfile, deploy/hf-space/   Hugging Face Space path (workflow disabled: Docker Spaces need PRO)
.github/workflows/ci.yml       backend tests + demo reproduction + frontend build (models cached by script hash)
truthlens              shell wrapper for backend/cli.py
```

Git-ignored but present locally: `backend/.venv`, `backend/models` (~3.9 GB including losing candidates), `data/`
(cases; hosted demo data in `data/hosted-demo`), `validation/data/`, `samples/.stock-cache/`,
`source_docs_recovered/` (text and page PNGs recovered from the original PDFs).

---

## 4. Commands

```bash
make setup              # venv, pinned deps, models (~2.8 GB, online once), npm install + build
make run                # API + built UI on http://localhost:8000, fully offline
make dev                # API with reload on :8000, Vite on :5173
make test               # cd backend && pytest -q   (70 tests, ~2 min because the detectors run)
make validate           # seeded synthetic set → metrics.json + calibration.json
make validate-deepfake  # fetch public samples if missing, compare detectors → deepfake_calibration.json
make demo               # build demo case, analyze, compare with samples/expected_report.json
python samples/check_demo.py --update   # rewrite expected_report.json after an intended change
python samples/make_home_demo.py        # rebuild the Home page clip + its analysis JSON
python backend/scripts/fetch_models.py [--candidates]   # models; --candidates adds the losing detectors
npx vite build          # frontend build check
./truthlens analyze <files…> | rerun --case C-0001 | report --case C-0001 | validate
```

Live demo host (on the owner's Mac):

```bash
python3 scripts/demo_host.py stop      # wait until status shows backend_running false and tunnel_running false
python3 scripts/demo_host.py status
python3 scripts/demo_host.py start     # starts uvicorn on :8786 (TRUTHLENS_MODE=hosted), a new Quick Tunnel URL,
                                       # writes VITE_API_BASE to Vercel and triggers a production redeploy
```

Use `backend/.venv/bin/python` for anything that does HTTPS. The system `python3` (3.14) has no CA certificates.
`demo_host.py` only uses curl, so `python3` is fine for it.

---

## 5. How the analysis works (short; full detail in `docs/methodology.md`)

1. **Ingest**: hash the original (SHA-256), store it read-only, read metadata, derive a 16 kHz audio track from video
   (as its own evidence item, `derived_from`), and add custody entries.
2. **Analyzers** run per item in `registry.ORDER` (the AI detectors are **last** in each kind, so they never renumber
   the forensic finding IDs):
   - video: av_metadata, frames, frame_dupes, optical_flow, face_flicker, frame_forensics, ai_video
   - audio: av_metadata, noise_floor, band_limit, prosody, transcript, ai_voice
   - image: exif, ela, noise, jpeg_ghost, copy_move, ai_image
   - text: claims, consistency, ai_text
   Every analyzer is isolated by try/except. A failed forensic detector makes "no findings" become "Inconclusive".
   A failed **AI** detector only adds a limitation and leaves the deepfake score to the other evidence (`AI_STEPS`).
3. **Finding IDs** (`F-VID-001` …) are assigned deterministically after analysis (D-06). Each finding is calibrated
   (Platt + 200 bootstrap refits; indicators with < 6 validation findings stay uncalibrated, ±0.12).
4. **Correlation rules** link findings (supports / weakens); R-14 halves weights.
5. **Fusion** (manipulation): log-odds, one term per method family, 0.6^k decay, P ≤ 0.97. Bands are decided on the
   range; "Strong" needs corroboration (two families, or a supports rule).
6. **Deepfake assessment** (`scoring/deepfake.py`):
   `P = 1 − (1 − P_ai)(1 − P_manip)`, clipped to [0.01, 0.99].
   - `P_ai` is the calibrated detector score.
   - `P_manip` is the fused manipulation probability, counted only when the item has findings, and **never for text**
     (a contradicting caption is misleading, not AI-written).
   - Texts under 40 words get a range that always spans 45–55 %.
   - Video ranges are widened by ±0.15 (calibrated on stills).
   - Labels: deepfake if P ≥ 0.65 and lo ≥ 0.50; authentic if P ≤ 0.35 and hi ≤ 0.50; otherwise uncertain.
   - A case takes its most likely item ("decided by E-02").
7. **Persist**: findings, correlations, verdict JSON (including `deepfake`), custody entry with the findings digest
   (SHA-256 of IDs, locations, raw scores, scores, ranges, bands).
8. **Report**: Jinja2 → WeasyPrint PDF + JSON, report hash in custody, page count sidecar.

### Learned deepfake detectors (all Apache 2.0, in `backend/models/`, chosen by validation)

| Modality | Model folder (HF repo) | Input |
|---|---|---|
| Image, video frames | `smaug-ai-image-detector` (abacusai/Smaug-AI-Image-Detector, EmbeddingGemma-2, 440M params, sentence-transformers) | 3 × 528 px crops for stills; 12 frames × 1 crop for video, **median** |
| Voice | `wav2vec2-large-xlsr-deepfake-audio-classification` (Gustking, XLS-R, trained on ASVspoof2019) | 4 s windows at 16 kHz, median |
| Text | `ai-text-detector-modernbert` (rasbt, ModernBERT-base, 2026) | first 512 tokens |

Losing candidates (only with `--candidates`): umm-maybe/AI-image-detector, jacoballessio/ai-image-detect-distilled,
mo-thecreator/Deepfake-audio-detection, MelodyMachine/Deepfake-audio-detection-V2.
`validation/results/deepfake_calibration.json` records `models` (the choice), Platt A/B and bootstraps.
`analyzers/deepfake.chosen()` reads it.

Implementation details that matter:

- Smaug loads in its stored bfloat16, then `_float_except_vocab()` converts module by module to float32 but keeps the
  262k-token vocabulary table in bfloat16, with a patched forward that uses `scalar_embed_scale`. Scores equal a
  float32 load (max difference 5e-5).
- Crops are encoded with batch_size=1 (memory).
- **Image, voice and transcription models run in a short-lived spawned child process** (`analyzers/base.isolated`).
  The allocator otherwise keeps about 0.7 GB after a model is freed. Set `TRUTHLENS_NO_ISOLATION=1` to run in-process
  (debugging).
- Stored detector scores are rounded to 0.01 so float noise between CPUs cannot change a report.
- The voice finding's end time is rounded to 0.5 s: the derived audio length differs by ffmpeg build (D-18).
- Labels are read from each model's own `id2label` (`fake_index()`), never hard-coded.
- **Peak RAM** for the demo case: main process 0.94 GB, largest child 2.29 GB while the main process holds about
  0.5 GB, so about 2.8 GB in total (budget 3 GB).

---

## 6. Measured results (from committed JSON; never invent others)

Seeded synthetic set, 204 items (`make validate`; full table in README and on the Validation page):

| Indicator | Detection rate | False-positive rate |
|---|---|---|
| Copy-move | 0.92 | 0.00 |
| ELA | 0.47 | 0.11 |
| Noise map | 0.28 | 0.19 |
| JPEG ghost | 0.75 | 0.31 |
| Noise-floor splice | 1.00 | 0.00 |
| Band limit | 1.00 | 0.00 |
| Flow jump / duplicate frame | 1.00 / 0.88 | 0.00 |
| Caption date / quote conflict | 1.00 / 1.00 | 0.00 |

Image region IoU is 0.71.

Deepfake detectors, 5-fold cross-validated, decision point 0.5 (`make validate-deepfake`):

| Detector | Samples | AUC | Accuracy | Detected | False alarms |
|---|---|---|---|---|---|
| Image (Smaug) | 240 OpenFake core/test images, 2025–26 generators | 0.991 | 0.925 | 0.858 | 0.008 |
| Voice (XLS-R) | 240 In-The-Wild clips, 42 speakers | 0.927 | 0.817 | 0.683 | 0.050 |
| Text (ModernBERT) | 116 textsightai 2026 benchmark texts | 0.913 | 0.819 | 0.679 | 0.050 |

Text on 30-word snippets: AUC 0.731. The models were chosen on these same samples, so the numbers are optimistic.
Video has not been validated on labelled videos.

Demo case `C-0007` (`samples/expected_report.json`): Strong indicators 0.92–0.97, rules R-03 and R-11.
Deepfake: case Likely deepfake 99 % (decided by E-02, the TTS voice).
- E-01 video: Likely deepfake, from manipulation evidence.
- E-02 audio: Likely deepfake.
- E-03 photo: Uncertain.
- E-04 caption: Uncertain.

---

## 7. Deployment

- **GitHub**: https://github.com/roshan-ds-tech/TruthLens (`main`). CI (`.github/workflows/ci.yml`) installs torch and
  torchvision from the PyTorch **CPU index**, the rest from PyPI, and libEGL/GLES for MediaPipe. It caches
  `backend/models` keyed on the hash of `fetch_models.py`, runs pytest, runs `samples/check_demo.py`, and builds the UI.
  A first run downloads about 2.4 GB of detectors.
- **Frontend**: Vercel project `truthlens`, team `roshan-dss-projects`, production URL
  https://truthlens-six-mu.vercel.app. It redeploys automatically on push. `vercel.json` has SPA rewrites,
  security headers and `/api-config.json` with no-store.
- **Backend**: runs on the owner's Mac via `scripts/demo_host.py` (uvicorn on port 8786, `TRUTHLENS_MODE=hosted`, data
  in `data/hosted-demo`), exposed by a **Cloudflare Quick Tunnel**. The URL changes on every start; `demo_host.py`
  pushes it to Vercel as `VITE_API_BASE` and redeploys. Open tabs recover the new address from `/api-config.json`.
  The Mac must stay awake and online. Allowed CORS origins: the two Vercel URLs.
  Current tunnel at hand-off: `https://trademarks-bridge-canberra-abilities.trycloudflare.com`.
- The Hugging Face Space path (`Dockerfile`, `deploy/hf-space`) exists, but its workflow is disabled because Docker
  Spaces need PRO (HTTP 402).
- Hosted mode adds accounts (sign-up / log-in), per-user cases (`owner_id`, `can_see`), and privacy copy that says
  data goes to the server (`PRIVACY` table in `client.js`).
- **Cases analysed before the deepfake feature have no deepfake result until re-run** (Workspace → Re-run analysis).

---

## 8. Chronological history of the work

1. **Design import**: Claude Design project `TruthLens.dc.html` + `support.js` ported to React/Vite (Phase 1:
   audit, `ui_integration_map.md`, `plan.md`).
2. **Backend Phases 2–7**: ingest, custody, all forensic analyzers, correlation, scoring, report, CLI, tests.
3. **UI wiring** to real data (two parts); Phase 8 validation harness and Platt calibration; Phase 9 demo case,
   expected report, AIFF support, docs.
4. **Production**: accounts, per-user cases, hosted mode. Pushed to GitHub, Vercel frontend. The HF Space was blocked
   by the paywall, so the Mac + Cloudflare tunnel host was adopted (owner's choice).
5. **Source PDFs removed from git history.** The filter-branch + `gc --prune=now` destroyed the local copies too. Text
   and page images were recovered to `source_docs_recovered/` (git-ignored); the owner was told.
6. **Placeholder images** replaced with licensed photos and real evidence previews (`public/img/CREDITS.md`).
7. **Visual-QA fixes 1–9**: per-case review state, text-only uploads count, draft resume, mode-aware privacy copy,
   working search, real PDF page count, path-free errors, analysed-only evidence count, review copy.
8. **Typography**: Inter + IBM Plex Mono, bundled, also embedded in the PDF.
9. **Home page live preview** (`HomePreview.jsx`): plays `home-demo.mp4` and replays TruthLens's real analysis in
   sync. First built from a zooming photo, then rebuilt on the owner's request from **Mixkit stock footage** (clips
   4632, 23035, 24214, 20810, no speaker's face) with off-screen macOS TTS narration ("Rishi"). Deliberate edits:
   0.8 s cut at 8.0 s, noisier-room splice at 8.2 s.
10. **Optical-flow detector hardened on real footage** (D-20): shot-change detection by shift-aligned NCC
    (phaseCorrelate sign bug found and fixed), only isolated single-frame jumps ≥ 3× the surrounding motion count.
    Face flicker skips single-sample segments.
11. **Deepfake feature** (owner: "main objective … deepfake or not … probability … text too … no page for video"):
    - detectors added and validated;
    - `scoring/deepfake.py`;
    - API `deepfake` fields on cases and evidence;
    - new **Video evidence page** (`VideoViewer.jsx`: player, frame stepping, 0.25–1× speed, suspicion curve,
      per-frame AI strip, finding cards with thumbnails, audio-track link);
    - deepfake card on Workspace, Video, Image, Audio and Text pages, pills on the Cases and Dashboard lists;
    - report section, Validation tiles, Home pill;
    - D-21, D-22.
12. **CI fixes**: torch 2.15 had no matching torchvision on Linux, so both are pinned to 2.14.1 / 0.29.1 from the CPU
    index. Platform-stable voice finding location. The demo check prints a per-finding diff on a digest mismatch.

Recent commits: `a1bc135` deepfake feature, `1081c3f` torch pin, `f98ace0` demo check stability (CI green).

---

## 9. Lessons and gotchas (things that cost time)

- **Downloads**: `huggingface_hub.snapshot_download` stalled at 0 bytes (Xet). Use plain HTTPS with resume
  (`fetch_models.detectors()` does this). Bandwidth here was about 1 MB/s; multi-connection range downloads help only
  per connection.
- **`pkill -f <pattern>`** also kills the parent shell whose command line contains the pattern. That killed parallel
  downloads once.
- **Datasets**: the datasets-server `/filter` endpoint is unusable on huge datasets ("index is loading"); sample with
  `/rows` at random offsets. Always check that labels aren't confounded with file format:
  `garystafford/deepfake-audio-detection` has every human clip at 44.1 kHz stereo and every AI clip at 16 kHz mono, so
  it was discarded. A linear probe scored 0.999 on it purely from format.
- **Old detectors don't generalise**: image detectors from 2023–24 scored 0.62–0.68 AUC on 2025–26 generators;
  MelodyMachine voice scored 0.39 on In-The-Wild. Always measure on recent, format-matched data.
- **Compressed video**: Smaug scored single frames of our heavily compressed genuine stock clip as AI (0.99). Hence
  median aggregation, no face crops in the score, and a wider video range.
- **Transformers 5** can't load legacy `ViTFeatureExtractor` configs. Preprocessing is done manually
  (`_image_prep`). Smaug's processor needs torchvision.
- **macOS vs Linux**: derived AAC-to-WAV audio differs by ffmpeg build. Never put derived-audio-dependent precise
  values in the findings digest. The demo check compares original hashes only.
- **BSD sed** on macOS: use `sed -i ''`. Python patch scripts with unique anchors and `assert count == 1` were the
  safe way to edit. A mis-anchored slice once corrupted `Analysis.jsx`; it was restored from git.
- The **Claude-in-Chrome extension was not connected**, so the deepfake UI pages were built and type-checked
  (`vite build`) but **not visually checked in a browser**. Do this first.
- **Hooks**: never call React hooks conditionally (a bug like `st.data?.mode || useServerMode()` was fixed once).
- Detector findings use `sort=0.0` and run last, so existing finding IDs stay stable.

---

## 10. Known limitations (see `docs/limitations.md`)

- Learned detectors miss generators they weren't trained on. "Likely authentic" is not proof.
- Small validation samples, with the model chosen on them, so the numbers are optimistic. Video is not validated on
  labelled videos.
- Text is weakest on short captions. Formal, edited or non-native human writing is flagged more often.
- Voice: noise suppression and phone audio can raise scores on human speech.
- Forensic analyzers: the noise map and JPEG ghost have high false-positive rates on the synthetic set. Whisper base is
  weak on noise. The gazetteer has about 45 places.
- The TTS voice in demos is macOS "Rishi" (non-commercial demo use only).
- Hosted mode sends evidence to the Mac server, which departs from "offline" (D-17).

---

## 11. Open items and suggested next steps

1. **Visually check** the new pages on the live site and at phone width: Video evidence page, deepfake cards (Workspace,
   Video, Image, Audio, Text), Cases and Dashboard pills, Validation "Deepfake detectors" tiles, report PDF deepfake
   box, Home preview pill.
2. Re-run older hosted cases so they get deepfake results (or add a notice in the UI).
3. Validate the video detector on a labelled real-vs-generated video set; consider a dedicated video model.
4. A larger, licence-clean validation split, separate from the selection split, for honest metrics.
5. README screenshots (still missing).
6. Keep `samples/expected_report.json` and `public/media/home-demo.json` in sync after any scoring change
   (`check_demo.py --update`, `make_home_demo.py`), and **restart the hosted backend** after backend changes.

## 12. Checklist before you push

```bash
(cd backend && .venv/bin/python -m pytest -q)     # expect 70 passed
backend/.venv/bin/python samples/check_demo.py    # "Demo reproduces … exactly"
npx vite build
git push && gh run watch                          # CI must be green
python3 scripts/demo_host.py stop && python3 scripts/demo_host.py start   # if the backend changed
```

Commit messages in this repo end with a `Co-Authored-By:` trailer naming the agent that made the change.
