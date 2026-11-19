# UI integration map

Every UI element that showed sample data, the endpoint and field that now backs it, and its status.
All endpoints are served under `/api` (see D-09 in `decisions.md`). The Vite dev server proxies `/api` to
`localhost:8000`; `make run` serves the built UI and the API from one FastAPI process.

Status: **planned** = not wired yet · **done** = wired to real data and tested · **sample** = still labelled sample data (see
`limitations.md`) · **static** = true, fixed copy that needs no backend.

UI vocabulary adapter (`backend/app/api/adapters.py`): the backend's verdict bands
(`none`, `inconclusive`, `indicators`, `strong`) are returned to the UI as the keys it already uses
(`none`, `inc`, `ind`, `strong`, plus `review` for cases not analyzed yet), together with the exact band label.

## App shell (`src/App.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Sign up / Log in dialog | none — local single-user gate (D-08) | static |
| Sidebar "Open case · C-0007" + case nav | client state `caseId` (set when a case is opened or created) | planned |
| Top-bar investigator "Priya S." / avatar | `GET /settings` → `investigator` | planned |
| Search box | none — not implemented | sample (listed in limitations) |
| "Running locally · ₹0" badge | static fact (no network access in analysis) | static |

## Dashboard (`screens/Dashboard.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Eyebrow date, greeting name | client date; `GET /settings` → `investigator` | planned |
| "11 findings waiting … 6 active cases" | `GET /stats` → `pending_review`, `active_cases` | planned |
| 4 stat tiles | `GET /stats` → `active_cases`, `opened_this_week`, `evidence_count`, `pending_review`, `top_pending_case`, `avg_analysis_seconds` | planned |
| "How TruthLens works" hero | static copy | static |
| Recent cases (5 rows) | `GET /cases` → first 5: `id`, `title`, `why`, `types`, `verdict.key/label`, `updated_at` | planned |
| Validation snapshot | `GET /validation/metrics` → `indicators[].precision`, `n_items` | planned (shows "no validation run yet" when missing) |

## Cases (`screens/Cases.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Eyebrow counts, filter chips + counts | `GET /cases` → `closed`, `needs_review`, `verdict.key` (counted client-side) | planned |
| Table rows | `GET /cases` → `id`, `title`, `why`, `types`, `verdict`, `findings_count`, `investigator`, `updated_at` | planned |
| Row click | opens workspace for that case id | planned |

## Evidence Library (`screens/EvidenceLibrary.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Eyebrow "48 items · 2.3 GB" | `GET /evidence` → `count`, `total_bytes` | planned |
| Cards | `GET /evidence` → `items[]`: `filename`, `case_id`, `kind`, `meta_label`, `verdict`, `sha256` | planned |
| Card thumbnail | `GET /evidence/{id}/thumb` (image / video frame), striped placeholder for audio / text | planned |

## New case (`screens/NewCase.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Title, investigator, description fields | `POST /cases` `{title, investigator, description}` | planned |
| Drop zone + "browse files" | `POST /cases/{id}/evidence` (multipart) → `{id, sha256, kind, meta_label, status}`; limits enforced server-side, error shown in the zone's hint line | planned |
| Uploaded evidence cards | response of the upload: `filename`, `meta_label`, `sha256`, `status` | planned |
| "Paste caption or claim" | `POST /cases/{id}/evidence` `{text}` (stored as a text evidence item) | planned |
| Save draft | `POST /cases` (+ caption) without analysis | planned |
| Start analysis | `POST /cases/{id}/analyze` → `job_id`, then Analysis screen | planned |

## Analysis (`screens/Analysis.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Headline, elapsed, overall bar | `GET /jobs/{job_id}` (polled 1 s) → `status`, `elapsed_s`, `progress`, `findings_count` | planned |
| Per-evidence rows + step chips | `GET /jobs/{job_id}` → `items[].steps[] {label, status: done/running/queued/failed/skipped}` | planned |
| Live log | `GET /jobs/{job_id}` → `log[] {t, src, msg}` | planned |
| Failed analyzer | step status `failed` shown with the queued-chip style + log line; becomes a limitation | planned |

## Case workspace (`screens/CaseWorkspace.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Header eyebrow, title, verdict pill + range, "Why" | `GET /cases/{id}` → `id`, `created_at`, `title`, `verdict {key,label,lo,hi}`, `why` | planned |
| Limitations panel | `GET /cases/{id}` → `limitations[]` | planned |
| Evidence list cards | `GET /cases/{id}` → `evidence[]`: `kind`, `display_name`, `meta_label`, `verdict`, `sha256` | planned |
| Video viewer | `GET /evidence/{id}/media` (original, read-only) in the frame area; overlay box from the selected finding's `location.bbox` | planned |
| Suspicion curve | `GET /evidence/{id}/findings` → evidence `extra.suspicion_curve` (per second) | planned |
| Timeline tracks + marks | findings with `location.type` `frame_range` / `time_range`, grouped by modality | planned |
| Finding cards | `GET /cases/{id}/findings` → `finding_id`, `name`, `modality`, `loc_label`, `conf_low/high`, `band`, `explanation`, `alternatives`, `compare`, `review` | planned |
| Accept / Reject / Note | `PATCH /findings/{id}/review` `{decision, note}` | planned |
| Correlation graph + rule list + combined range | `GET /cases/{id}/graph` → `nodes`, `rules[] {id,name,links,detail,tag,relation,edges}`, `combined` | planned |
| Chain of custody drawer | `GET /cases/{id}/custody` | planned |
| Re-run analysis | `POST /cases/{id}/analyze` → Analysis screen | planned |
| Export report | `POST /cases/{id}/report` → Report screen | planned |

## Image viewer (`screens/ImageViewer.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Header, verdict, why | `GET /cases/{id}` → evidence item | planned |
| Original / analysis slider | original: `GET /evidence/{id}/media`; analysis layers: `GET /evidence/{id}/artifacts/{ela,noise,copymove,ghost}.png` | planned |
| Layer toggles (Error level, Noise map, Copy-move, Regions) | same artifacts; Regions = finding bboxes | planned |
| Region boxes + cards | `GET /evidence/{id}/findings` → `location.bbox` (fractions of width/height), ranges, explanation, alternatives | planned |
| EXIF table + conflict markers | `GET /evidence/{id}` → `metadata.exif_rows[] {k, v, note}` | planned |

## Audio viewer (`screens/AudioViewer.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Header, verdict, why | `GET /cases/{id}` → evidence item | planned |
| Play button + time | `<audio src=/evidence/{id}/media>` (wiring a dead handler) | planned |
| Waveform bars | `GET /evidence/{id}/waveform` → `peaks[]`, `duration` | planned |
| Spectrogram | `GET /evidence/{id}/artifacts/spectrogram.png` drawn into the existing canvas | planned |
| Flagged segments + finding cards | findings with `location.type == time_range` | planned |
| Transcript with word timestamps | `GET /evidence/{id}/waveform` → `transcript.segments[].words[]` | planned |

## Report (`screens/ReportPreview.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Whole A4 preview | `GET /cases/{id}/report` → `report.json` content | planned |
| Export JSON / Download PDF | `GET /cases/{id}/report.json`, `GET /cases/{id}/report.pdf` | planned |
| Report hash footer | `report.sha256` (also logged in custody) | planned |

## Validation (`screens/Validation.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Tiles per indicator | `GET /validation/metrics` → `indicators[] {name, modality, precision, recall, fpr, n}` | planned |
| Reliability chart | `metrics.reliability[] {bin_mid, observed, count}` | planned |
| False-positive table | `metrics.false_positives[]` | planned |
| "SAMPLE DATA" badge | becomes "TEST SET vX · n items"; whole page says "no validation run yet" until `make validate` has run | planned |

## Settings (`screens/Settings.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Analyzer list, versions, toggles | `GET/PUT /settings` → `analyzers[] {key, name, desc, version, enabled}`; disabled analyzers are skipped and logged | planned |
| models.lock hash | `settings.models_lock` (SHA-256 of `requirements.txt` + model files) | planned |
| Privacy and storage | `settings.vault {path, bytes}`; network/telemetry/cost are true static facts | planned |
