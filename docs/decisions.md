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

### D-16 · Accounts (sign-up / log-in) for the hosted deployment
The design is a single-user local tool. To put it on the internet, the existing log-in dialog now creates real
accounts: scrypt password hashes (standard library), random bearer tokens stored only as SHA-256, 7-day expiry,
8 failed log-ins per email per 15 minutes, and every case owned by one account. Bearer tokens (not cookies) because
the UI (Vercel) and API (Hugging Face) are on different sites; protected media is fetched with the token and shown
from object URLs.

### D-17 · Hosted on Hugging Face Spaces, which departs from "offline, no data leaves the device"
Hosting was requested. The backend runs as a Docker Space (CPU, models baked in, no outbound calls during analysis);
the UI says plainly that it is a hosted server and that evidence is visible only to the uploading account. Local
mode keeps the original promise. Free Spaces have no persistent disk, so hosted data is temporary.

### D-18 · Reproducibility across platforms
CI runs on Ubuntu (ffmpeg 6) while development used macOS (ffmpeg 9). Finding IDs, scores, ranges, verdicts and the
findings digest are identical on both. The only difference is the SHA-256 of the derived audio track: AAC decoders in
different ffmpeg versions produce slightly different PCM. `samples/check_demo.py` therefore compares hashes of
originals only. Reruns on one installation are bit-identical, including derived files.

### D-19 · Typography: Inter and IBM Plex Mono
The design used Manrope (geometric, rounded) at weight 800 with tight tracking (down to −0.045em), which read as heavy
and casual. The UI and the PDF report now use Inter for text and IBM Plex Mono for hashes, timestamps and IDs;
headings are weight 700 with tracking between −0.012em and −0.025em. Both fonts (SIL OFL) are bundled in
`public/fonts/` and `backend/app/report/fonts/`, so the UI and the PDF render identically offline.

### D-20 · Optical-flow jumps tested on real footage
The Home demo clip uses real stock footage. It showed that ordinary shot changes between similar-coloured shots and
natural movement (people, a hand-held camera) were reported as motion breaks. A jump now counts only if (1) the frames
still match once a pure camera shift is undone (phase correlation; a new shot does not), and (2) it is one isolated
frame at least 3× the surrounding motion (flow or pixel difference). Validation is unchanged at recall 1.00 with no
false positives, and `test_shot_change_is_not_a_motion_break` guards it.

### D-21 · Deepfake probability alongside the manipulation bands
The project goal is to say whether media is a deepfake. The forensic analyzers find editing traces but cannot recognise
fully AI-generated media, so pretrained detectors were added per modality (image/video frames, voice, text). They raise
the download from about 0.3 GB to about 1.9 GB (approved by the user). Each item and case now shows "Likely deepfake",
"Likely authentic" or "Uncertain" with a calibrated probability and range (rules in methodology.md). "Uncertain" was
kept, at the user's choice, so that close calls are not stated with confidence. The user asked for the word "deepfake"
in outputs, which supersedes the earlier rule against the word "fake" for this one label; "real" is still not used.
The models were chosen by measured AUC on public samples: two older image detectors scored 0.62–0.68 on 2025–26
generators against 0.99 for Smaug, and an older ChatGPT-era text detector was dropped in favour of a 2026 ModernBERT
model. For voices, the first test set (`garystafford/deepfake-audio-detection`) was discarded because every human clip
is 44.1 kHz stereo and every synthetic one 16 kHz mono, so the format alone gives the label away. On In-The-Wild
(genuine vs cloned speech of the same public figures) the first voice model scored below chance (AUC 0.39); the
ASVspoof2019-trained XLS-R model scored 0.93 and was chosen over a model with equal AUC but undisclosed training data.

### D-22 · Memory: large detectors run in a child process
The image detector needs about 2.1 GB while loaded, and the memory allocator keeps about 0.7 GB after it is freed.
The image, voice and transcription models now run in a short-lived child process (`analyzers/base.py: isolated`),
the image detector is loaded in its stored bfloat16 and converted to float32 per module with the 262k-token
vocabulary table left in bfloat16 (identical scores), and crops are encoded one at a time. Measured on the demo case:
main process peak 0.94 GB, largest child 2.29 GB while the main process holds about 0.5 GB, so about 2.8 GB in all.

## D-23 Separate AI generation estimates and verify cross-media evidence

The Problem Statement 04 audit identified that editing evidence could inflate the separate deepfake percentage through a noisy-OR combination, including correlated signals already used in fusion. AI-generation estimates now use the learned detector once; forensic editing indicators remain separate context. Missing AI results have no fabricated percentage, partial coverage cannot produce an authentic case label, video identifies transferred image calibration, and legacy scoring requests reanalysis.

Regression tests confirm the existing media-before-text ordering is upload-order independent. CLI runs now persist coverage and tool provenance as API jobs do. R-09 now requires feature registration of the source image to the flagged video frame; matching normalized screen coordinates are not a correspondence proof. Reports export original text, coverage/model provenance and a verifiable pre-export custody snapshot with complete job logs in JSON. Existing originals and report drafts are preserved.


## D-24 Abstain on unvalidated video probabilities

A genuine road clip reproduced unstable still-image detector frame scores. Applying still-image Platt calibration to their median inflated the displayed video percentage. Extra crops did not resolve the error. Video now retains raw frame diagnostics but abstains from an authenticity probability or label; short texts likewise have no misleading percentage. Existing v2 video estimates are withdrawn at the API boundary without requiring the user to rerun first. Image/voice models and their measured calibration remain unchanged; no universal-video accuracy claim is made.

Optical-flow spikes require a two-sided baseline, preventing startup/ending frames from being called isolated splices. A regression test retains detection of an interior jump while excluding the startup spike. The compact assessment panel uses neutral borders, a clear status and expandable evidence/limitations; weak region findings no longer crowd the video preview by default. Originals, saved reports and custody history are preserved.
