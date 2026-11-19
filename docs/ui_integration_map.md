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
| Sidebar "Open case · C-0007" + case nav | client state `caseId` (set when a case is opened or created) | done |
| Top-bar investigator "Priya S." / avatar | `GET /settings` → `investigator` | done |
| Search box | none — not implemented | sample (listed in limitations) |
| "Running locally · ₹0" badge | static fact (no network access in analysis) | static |

## Dashboard (`screens/Dashboard.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Eyebrow date, greeting name | client date; `GET /settings` → `investigator` | done |
| "11 findings waiting … 6 active cases" | `GET /stats` → `pending_review`, `active_cases` | done |
| 4 stat tiles | `GET /stats` → `active_cases`, `opened_this_week`, `evidence_count`, `pending_review`, `top_pending_case`, `avg_analysis_seconds` | done |
| "How TruthLens works" hero | static copy | static |
| Recent cases (5 rows) | `GET /cases` → first 5: `id`, `title`, `why`, `types`, `verdict.key/label`, `updated_at` | done |
| Validation snapshot | `GET /validation/metrics` → `indicators[].precision`, `n_items` | done (shows "no validation run yet" when missing) |

## Cases (`screens/Cases.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Eyebrow counts, filter chips + counts | `GET /cases` → `closed`, `needs_review`, `verdict.key` (counted client-side) | done |
| Table rows | `GET /cases` → `id`, `title`, `why`, `types`, `verdict`, `findings_count`, `investigator`, `updated_at` | done |
| Row click | opens workspace for that case id | done |

## Evidence Library (`screens/EvidenceLibrary.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Eyebrow "48 items · 2.3 GB" | `GET /evidence` → `count`, `total_bytes` | done |
| Cards | `GET /evidence` → `items[]`: `filename`, `case_id`, `kind`, `meta_label`, `verdict`, `sha256` | done |
| Card thumbnail | `GET /evidence/{id}/thumb` (image / video frame), striped placeholder for audio / text | done |

## New case (`screens/NewCase.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Title, investigator, description fields | `POST /cases` `{title, investigator, description}` | done |
| Drop zone + "browse files" | `POST /cases/{id}/evidence` (multipart) → `{id, sha256, kind, meta_label, status}`; limits enforced server-side, error shown in the zone's hint line | done |
| Uploaded evidence cards | response of the upload: `filename`, `meta_label`, `sha256`, `status` | done |
| "Paste caption or claim" | `POST /cases/{id}/evidence` `{text}` (stored as a text evidence item) | done |
| Save draft | `POST /cases` (+ caption) without analysis | done |
| Start analysis | `POST /cases/{id}/analyze` → `job_id`, then Analysis screen | done |

## Analysis (`screens/Analysis.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Headline, elapsed, overall bar | `GET /jobs/{job_id}` (polled 1 s) → `status`, `elapsed_s`, `progress`, `findings_count` | done |
| Per-evidence rows + step chips | `GET /jobs/{job_id}` → `items[].steps[] {label, status: done/running/queued/failed/skipped}` | done |
| Live log | `GET /jobs/{job_id}` → `log[] {t, src, msg}` | done |
| Failed analyzer | step status `failed` shown with the queued-chip style + log line; becomes a limitation | done |

## Case workspace (`screens/CaseWorkspace.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Header eyebrow, title, verdict pill + range, "Why" | `GET /cases/{id}` → `id`, `created_at`, `title`, `verdict {key,label,lo,hi}`, `why` | done |
| Limitations panel | `GET /cases/{id}` → `limitations[]` | done |
| Evidence list cards | `GET /cases/{id}` → `evidence[]`: `kind`, `display_name`, `meta_label`, `verdict`, `sha256` | done |
| Video viewer | `GET /evidence/{id}/media` (original, read-only) in the frame area; overlay box from the selected finding's `location.bbox` | done |
| Suspicion curve | `GET /evidence/{id}/findings` → evidence `extra.suspicion_curve` (per second) | done |
| Timeline tracks + marks | findings with `location.type` `frame_range` / `time_range`, grouped by modality | done |
| Finding cards | `GET /cases/{id}/findings` → `finding_id`, `name`, `modality`, `loc_label`, `conf_low/high`, `band`, `explanation`, `alternatives`, `compare`, `review` | done |
| Accept / Reject / Note | `PATCH /findings/{id}/review` `{decision, note}` | done |
| Correlation graph + rule list + combined range | `GET /cases/{id}/graph` → `nodes`, `rules[] {id,name,links,detail,tag,relation,edges}`, `combined` | done |
| Chain of custody drawer | `GET /cases/{id}/custody` | done |
| Re-run analysis | `POST /cases/{id}/analyze` → Analysis screen | done |
| Export report | `POST /cases/{id}/report` → Report screen | done |

## Image viewer (`screens/ImageViewer.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Header, verdict, why | `GET /cases/{id}` → evidence item | done |
| Original / analysis slider | original: `GET /evidence/{id}/media`; analysis layers: `GET /evidence/{id}/artifacts/{ela,noise,copymove,ghost}.png` | done |
| Layer toggles (Error level, Noise map, Copy-move, Regions) | same artifacts; Regions = finding bboxes | done |
| Region boxes + cards | `GET /evidence/{id}/findings` → `location.bbox` (fractions of width/height), ranges, explanation, alternatives | done |
| EXIF table + conflict markers | `GET /evidence/{id}` → `metadata.exif_rows[] {k, v, note}` | done |

## Audio viewer (`screens/AudioViewer.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Header, verdict, why | `GET /cases/{id}` → evidence item | done |
| Play button + time | `<audio src=/evidence/{id}/media>` (wiring a dead handler) | done |
| Waveform bars | `GET /evidence/{id}/waveform` → `peaks[]`, `duration` | done |
| Spectrogram | `GET /evidence/{id}/artifacts/spectrogram.png` drawn into the existing canvas | done |
| Flagged segments + finding cards | findings with `location.type == time_range` | done |
| Transcript with word timestamps | `GET /evidence/{id}/waveform` → `transcript.segments[].words[]` | done |

## Report (`screens/ReportPreview.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Whole A4 preview | `GET /cases/{id}/report` → `report.json` content | done |
| Export JSON / Download PDF | `GET /cases/{id}/report.json`, `GET /cases/{id}/report.pdf` | done |
| Report hash footer | `report.sha256` (also logged in custody) | done |

## Validation (`screens/Validation.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Tiles per indicator | `GET /validation/metrics` → `indicators[] {name, modality, precision, recall, fpr, n}` | done |
| Reliability chart | `metrics.reliability[] {bin_mid, observed, count}` | done |
| False-positive table | `metrics.false_positives[]` | done |
| "SAMPLE DATA" badge | becomes "TEST SET vX · n items"; whole page says "no validation run yet" until `make validate` has run | done |

## Settings (`screens/Settings.jsx`)

| UI element | Endpoint → field | Status |
|---|---|---|
| Analyzer list, versions, toggles | `GET/PUT /settings` → `analyzers[] {key, name, desc, version, enabled}`; disabled analyzers are skipped and logged | done |
| models.lock hash | `settings.models_lock` (SHA-256 of `requirements.txt` + model files) | done |
| Privacy and storage | `settings.vault {path, bytes}`; network/telemetry/cost are true static facts | done |

## Component edits made to wire data (rule 4)

All styling and layout are unchanged. Edits replaced in-file constants with API data and wired dead handlers:

- `App.jsx`: open-case / evidence / job state passed to screens; investigator name and initials from `/settings`.
- `ui.jsx`: added `Muted` (the screens' existing grey footnote style) for loading, empty and error lines.
- `NewCase.jsx`: fields became controlled inputs; drop zone and "browse files" upload; Save draft and Start analysis call the API.
- `Analysis.jsx`: simulated ticker replaced by polling `/jobs/{id}`; failed/skipped steps reuse the queued chip with a suffix.
- `CaseWorkspace.jsx`: the striped frame now plays the real video (`<video>`) or shows the image; overlays, timeline, curve,
  findings, rules, graph and custody come from the API; "+2 in image" link removed (it was sample-only).
- `ImageViewer.jsx`: real image and heatmap PNGs inside the existing slider; the frame takes the photo's aspect ratio so boxes align.
- `AudioViewer.jsx`: real `<audio>` playback; the existing canvas draws the server-rendered spectrogram.
- `ReportPreview.jsx`: renders `report.json`; Export JSON / Download PDF open the generated files.
- `Validation.jsx`: the SAMPLE DATA badge now shows the test-set version and size from `metrics.json`.
