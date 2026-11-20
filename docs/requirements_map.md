# Problem Statement 04 requirements audit

Vero implements all eight core capability areas and the Ingest → Analyze → Correlate → Review → Report prototype workflow in the supplied problem statement. This is a functional coverage assessment, not a claim of perfect detection, universal calibration, or guaranteed competition acceptance. The confidence requirement is supported by measured detector calibration and explicit uncertainty; temporal-video AI estimates still lack independent labelled-video validation.

## Core capability coverage

| Problem statement area | Implemented behavior | Code | Verification and bounds |
|---|---|---|---|
| Image authenticity | Metadata rules, ELA, noise residuals, JPEG ghost, copy-move regions, learned AI-image classification | `backend/app/analyzers/image/`, `analyzers/deepfake.py`, `src/screens/ImageViewer.jsx` | Analyzer tests, clean controls, labelled image-detector evaluation. Compression/editing can cause false alarms. |
| Video forensics | Duplicate frames, optical-flow changes with shot-change handling, face flicker, suspicious-frame forensics, sampled AI frames, playable timestamp/frame findings | `analyzers/video/`, `analyzers/deepfake.py`, `src/screens/VideoViewer.jsx` | Edited/clean video tests and synthetic timing validation. AI-frame scores are diagnostic only; no video probability is issued without labelled-video validation. |
| Audio and voice | Noise-floor splice, spectrum cutoff, pitch/pause measurements, word-timed transcription, learned synthetic/cloned-voice detector | `analyzers/audio/`, `analyzers/deepfake.py`, `src/screens/AudioViewer.jsx` | Splice timing, band-limit and transcription tests; labelled voice evaluation. Phone codecs/denoising can trigger warnings. |
| Text and context | Extract dates/entities/quotes; compare against EXIF/GPS/creation time and speech; classify AI-writing separately; highlight source text | `analyzers/text/`, `pipeline.py`, `src/screens/TextViewer.jsx` | Date consistency/conflict tests and caption-before/after-audio regression tests. No general web fact-checking; short-text AI estimates remain uncertain. |
| Cross-modal correlation | Named support/weakening rules: linked audio/video timing, caption/speech, lip-sync, registered image/frame regions, caption/metadata, recompression alternative | `correlate/rules.py`, `correlate/visual.py`, `correlate/lipsync.py`, `correlate/graph.py` | Same-timeline tests, registered translation positive control, unrelated-image negative control, recompression down-weighting and date links. Equal screen coordinates alone cannot fire R-09. |
| Manipulation indicators | Typed finding IDs, locations/regions/times/spans, methods, explanations, alternatives, heatmaps and thumbnails | `analyzers/base.py`, `pipeline.py`, `api/adapters.py`, evidence viewers | Full-workflow test checks locations, methods and explanations. Indicators are leads, not proof. |
| Confidence and uncertainty | Per-indicator calibration/ranges, weighted fusion, corroboration gate, limitations, unavailable/disabled-method coverage, AI-generation estimate separate from editing | `scoring/`, `pipeline.py`, `src/Deepfake.jsx`, `src/screens/Validation.jsx` | Deepfake/score tests ensure editing never raises an AI-generation estimate, missing detectors do not fabricate a probability, partial case coverage is not labelled authentic, and disabled forensic methods do not imply a clean result. Small-sample measurements remain limited. |
| Forensic report and traceability | PDF/HTML/JSON with evidence references/hashes, findings, correlations, source text, uncertainty, review decisions, method/model coverage, linked custody history and analysis logs | `report/render.py`, `report/templates/report.html.j2`, `custody.py`, `db.py` | Full workflow exports source context and verifiable pre-export hash chain. Read-only originals, append-only triggers and deterministic rerun tests. This is a tamper-evident local log, not a blockchain or proof of pre-upload provenance. |

## Required workflow

| Stage | User behavior | Backend / UI |
|---|---|---|
| Ingest | Create or resume case, upload supported media, add text context | Signature detection, metadata/limits, SHA-256, read-only original storage, custody event; New case screen |
| Analyze | Start job and inspect progress | Single analysis worker, enabled methods, failures isolated and logged; Analysis screen |
| Correlate | Compare related evidence and alternatives | Named rules/graph, same-timeline checks, verified visual registration; Workspace |
| Review | Inspect exact evidence location, uncertainty and alternatives; accept/reject/note | Image/Video/Audio/Text viewers, review API, custody events |
| Report | Generate and download reproducible evidence-linked output | Report preview, PDF/HTML/JSON endpoints; existing reports remain immutable snapshots |

## Required report contents

| Required content | Where it appears |
|---|---|
| Flagged evidence | Evidence table and finding ID, source evidence ID, thumbnail/region or time/span location; structured location in JSON |
| Indicator and explanation | Finding name, method, observed measurement, explanation and alternative explanations |
| Cross-modal context | Correlation summary and source references; graph nodes/edges in JSON |
| Calibrated score with limitations | Per-finding ranges and calibration status, AI calibration scope, case limitations; indicator strength is not presented as proof |
| Source trace | Original filenames, evidence labels, SHA-256, original caption/text context, derived-from links |
| Summary and human checks | Case summary, limitations, recommended checks and review decisions |
| Analysis history | Completed/skipped/failed methods, run times, AI checkpoints, tool versions, custody event table; full job log and previous/entry hashes in JSON |

The custody history in an export is an explicit snapshot before that report's generation event. The generation event is appended after computing the report hash, avoiding a self-referential hash or a fabricated future event count.

## Corrections made by this audit

1. **Separate AI generation from editing.** Removed the noisy-OR combination of AI and editing scores, which could count correlated evidence twice and label ordinary editing as AI generation. Editing indicators remain visible separately. An unavailable AI detector now gives an uncertain result without an invented percentage.
2. **Require reanalysis of legacy scoring.** Old stored combined probabilities are not silently presented as current AI-generation estimates. The UI requests a re-run; originals and previous reports are unchanged.
3. **Respect incomplete coverage.** A case cannot receive a likely-authentic label when another item is unassessed/uncertain. Disabled forensic methods are recorded as coverage gaps instead of treating an unexamined file as clean.
4. **Verify upload-order independence.** The existing kind ordering already completes media before text. New before/after-audio tests preserve this behavior; no execution-order change was needed.
5. **Verify visual correspondence.** R-09 requires ORB feature matches and a RANSAC image-to-frame transform, sufficient distributed inliers, and overlap of registered regions. Coincidental normalized coordinate overlap in unrelated pictures is insufficient. Registered scene matches are weak support and do not establish independent corroboration.
6. **Export context and history.** Reports include original text, method coverage, model/tool provenance, the custody snapshot, and full structured logs/hashes in JSON. Custody timestamps use canonical UTC for hash verification.
7. **Retain CLI provenance.** Completed method states, logs and runtime tool versions are stored for command-line analyses as well as queued API jobs. Older analyses without recorded versions request a re-run rather than substituting current versions as historical facts.
8. **Describe calibration accurately.** Sampled video scores are diagnostic only and cannot produce a video authenticity percentage. Registry descriptions name the models actually selected.

## Remaining limits

- Image, voice and text detector metrics come from small labelled samples also used for model selection; they are not a universal product accuracy figure.
- No independent end-to-end labelled-video AI benchmark is currently available. Conventional temporal forensics and sample-frame AI detection are implemented, with that limitation disclosed.
- No detector proves authorship, intent, factual truth, or authenticity. Metadata may be missing/altered, transcription may be wrong, and processed authentic media can be flagged.
- A successful functional prototype satisfies the requested workflow; larger independent validation and stronger production hosting/queue capacity are future work.

## Verification commands

```sh
(cd backend && .venv/bin/python -m pytest -q)
node --test tests/api-address.test.mjs
backend/.venv/bin/python samples/check_demo.py
npm run build
```

Targeted regressions are in `backend/tests/test_deepfake.py`, `test_end_to_end.py`, `test_scoring_rules.py`, and `test_visual_correspondence.py`. The supplied statement image and original source PDFs are not copied into the public repository.
