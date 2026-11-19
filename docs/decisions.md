# Decisions and deviations from the design doc

Each entry: what the design doc says, what we did, and why.

### D-01 · Frontend stays at the repo root, in JSX, with inline styles
Design doc §5.1 / §6.1: `frontend/src/` with TypeScript, Tailwind, wavesurfer.js, react-flow.
**We did:** keep the already-built UI where it is (`src/`, plain JSX, inline styles, hand-drawn SVG graph, server-rendered spectrogram).
**Why:** the brief forbids restructuring or restyling the built UI and adding UI libraries.

### D-02 · No data layer existed in the UI
Every sample value was a constant inside the screen components (ported from the Claude Design file).
**We did:** add `src/api/` (`client.js` + hooks) and edit each screen only where it read a constant or had a dead handler.
Layout and styles are unchanged. Every edit is listed in `ui_integration_map.md`.

### D-03 · `filetype` instead of `python-magic`
Design doc §3.2 allows either. `python-magic` needs the native libmagic; `filetype` is pure Python and reads the same magic bytes.

### D-04 · Extra tables and endpoints the UI needs
Beyond §5.2/§5.3 we added: a `jobs` table (per-analyzer progress and the live log the Analysis screen shows),
`GET /stats` (dashboard tiles), `GET /evidence` (Evidence Library), `GET /evidence/{id}/media` and
`GET /evidence/{id}/waveform` (viewers), `GET/PUT /settings` (analyzer toggles), `GET /cases/{id}/report` and
`/report.pdf` / `/report.json` downloads. All are read-only views over the same data or simple settings.

### D-05 · Rule IDs
The UI shows rule IDs (R-03, R-07, R-11, R-14). The six named rules from §3.7 get fixed IDs:
R-03 splice/jump time agreement, R-05 speech vs caption, R-07 lip-sync, R-09 same-location agreement,
R-11 claimed date vs capture metadata, R-14 recompression explains ELA.

### D-06 · Finding IDs are assigned after analysis, deterministically
IDs (`F-IMG-003`) are numbered per case and modality after all analyzers finish, sorted by
(evidence order, analyzer order, location). A rerun on the same originals therefore yields identical IDs.

### D-07 · Repository
The parent folder's git repo tracks an unrelated file and pushes to another GitHub project, so TruthLens has its own repo in `saptha_hack/`.

### D-08 · No authentication
The UI's sign-up / log-in dialog is a local, single-user gate (as in the design). There is no auth backend; the investigator name comes from settings. Listed in `limitations.md`.

### D-09 · API paths are under `/api`
Design doc §5.2 lists `/cases`, `/jobs/{id}` and so on. They are served as `/api/cases`, `/api/jobs/{id}`, …
so that one FastAPI process can also serve the built UI at `/` for `make run`.

### D-10 · MediaPipe Tasks API instead of `mp.solutions`
MediaPipe 1.2.3 (what pip resolved for Python 3.11/arm64) no longer ships the legacy `solutions.face_mesh`.
Face tracking uses `mediapipe.tasks` `FaceLandmarker` in IMAGE mode with `face_landmarker.task` (3.6 MB, fetched by `make setup`).
MediaPipe also pulls in `opencv-contrib-python` next to `opencv-python-headless`; both are pinned and the tests pass with both present.

### D-11 · Fusion has diminishing returns and caps
§3.8 specifies a weighted log-odds sum. A plain sum let five uncalibrated near-1.0 signals reach a 1.00–1.00 range,
which is unsupported certainty. Families are now added strongest first with the k-th counting 0.6^k, single
signals are clipped to [0.02, 0.95], the fused value is capped at 0.97, and a fused range is never narrower than ±0.05.

### D-12 · Image signal refinements after testing on synthetic splices
ELA thresholds a 3×3-block-smoothed, texture-normalised error map (raw ELA fired on every edge and missed pasted
regions). JPEG ghost compares each block's re-save curve *shape* with the image-wide shape instead of taking each
block's arg-min quality (which flagged clean images). Audio splice boundaries are placed by a robust change-point
fit on a rolling-minimum noise-floor trace (median error 5 ms on 8 seeded splices, vs ~0.5 s before).

### D-13 · Validation sources are synthetic
We have no own photos or recordings on this machine and analysis must stay offline, so the seeded test set is built
from the public-domain sample photos bundled with scikit-image (crops), synthetic voiced speech with room noise,
and camera pans rendered from those photos. `validation/synth.py` generates everything from fixed seeds.

### D-14 · macOS `say` instead of Piper for synthetic speech
Piper needs its voice models downloaded and was not installed. The validation harness uses the offline macOS
`say` command for real text-to-speech clips when it exists, and skips the TTS subset otherwise (noted in metrics.json).

### D-15 · Calibration for indicators that were always right (or always wrong)
Platt scaling needs both classes. When every validation finding of an indicator was a hit (or a miss), its probability
is the smoothed hit rate and its range comes from a Beta(hits+1, misses+1) posterior, so 16/16 on a small set gives
0.86–0.95 rather than near-certainty.
