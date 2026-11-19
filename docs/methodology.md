# Methodology

Every number below is in `backend/app/config.py` or next to the analyzer that uses it. Measured behaviour comes
from `validation/results/metrics.json` (204-item self-made set, seed 7).

## Pipeline

1. **Ingest** — type from magic bytes (`filetype`), SHA-256, original copied to `data/evidence/<case>/<sha>/original.<ext>`
   and made read-only, metadata extracted (EXIF via exifread/Pillow, container via ffprobe). A video's audio track is
   derived as its own evidence item (16 kHz mono WAV, bit-exact ffmpeg flags) and logged in custody.
2. **Analyze** — one worker; analyzers run per item in a fixed order, each in its own try/except. A failure marks the
   step failed and becomes a limitation; a missing detector turns *No indicators found* into *Inconclusive*.
3. **IDs** — assigned after all analyzers finish, sorted by (evidence order, analyzer order, position), so reruns give
   identical IDs. Findings whose whole range is below 0.30 are logged, not listed.
4. **Calibrate → correlate → fuse → persist**, then a custody entry with the evidence-set hash and the findings hash.

## Image (`analyzers/image/`)

| Signal | Computation | Threshold | Known false-positive causes |
|---|---|---|---|
| ELA | Re-save JPEG q=90; per-16 px block mean absolute error ÷ (block mean \|Laplacian\| + 4); 3×3-block mean; robust z = (x − median)/(1.4826·MAD) | z > 3.6, region ≥ 0.8 % of image | sharp edges, text, social-platform recompression, never-JPEG files (score ×0.7) |
| Noise residual | gray − 3×3 median; log variance per 32 px block; robust z | \|z\| > 3 (smooth side only where block texture std > 6) | bokeh / mixed focus, in-camera denoising |
| JPEG ghost | Re-save at q = 50…95; per-block log difference-curve *shape* minus the image-wide median shape (qualities ≤ file q − 5), 3×3 mean, robust z | z > 4, region ≥ 1.2 % | flat areas, repeated recompression |
| Copy-move | ORB (3000 kp) matched against itself, Lowe ratio 0.75, distance > 40 px, canonical direction, RANSAC similarity (seeded); up to 2 clusters | ≥ 12 inliers and shift ≥ 40 px | repeating texture, logos, symmetric objects |
| EXIF rules | editor in `Software`; EXIF without Make/Model; `DateTime` − `DateTimeOriginal` > 1 day; pHash(EXIF thumbnail) vs pHash(main) | pHash distance > 12 | routine colour correction, wrong camera clock, crop before thumbnail |

Region scores: `raw = 1 / (1 + exp(−(mean_z − mid)/scale))` with per-signal `mid`/`scale` in each module.

## Video (`analyzers/video/`)

- **Decode**: every frame up to 60 s, downscaled to 320 px wide (grey) for motion; ≤ 720p for frame forensics.
- **Duplicates**: pHash distance 0 to the previous frame, mean grey change < 0.25, both neighbours > 1.5 (inside motion).
- **Drops**: timestamp gap > 1.8 × median frame interval.
- **Flow jumps**: Farneback mean magnitude and mean frame difference; z against a rolling ±2 s median/MAD
  (MAD floor 0.05 + 0.1·median); z > 4. A jump with histogram correlation < 0.6 is a scene cut (note, not a finding).
- **Face flicker**: MediaPipe FaceLandmarker at 8 fps; log(face Laplacian variance / background variance) and face
  luminance; robust z > 4 while background |z| < 2.5. Also records mouth opening (landmarks 13–14 / face height).
- **Frame forensics**: ELA + noise map on the 3 most suspicious frames (score ×0.8: H.264 weakens still-image signals).
- **Suspicion curve**: per second, max of squashed flow z, face z and covering findings' raw scores.

## Audio (`analyzers/audio/`)

- **Noise-floor splice**: 20 ms frames, 10 ms hop. For each candidate boundary *t* (50 ms grid) the step is
  p10(dB, 2.5 s after) − p10(dB, 2.5 s before), |step| ≥ 6 dB. It is kept only if it **persists**: the 1st percentile
  on the louder side over 4 s stays ≥ 4.5 dB above the quieter side (dense speech has pauses back at the old floor).
  The boundary is placed by a least-absolute-deviation change point on a 0.5 s rolling-minimum trace, shifted by half
  a window. Validation: recall 1.00, FPR 0.00, median error 0.007 s. FP causes: gain changes, noise suppression,
  background sources starting/stopping.
- **Band limit**: Welch spectrum at the native rate (the parent video for derived tracks); cutoff = first frequency
  > 3 kHz above which ≥ 97 % of bins are 40 dB below the 0.5–4 kHz median. Flag if cutoff ≤ 0.8·Nyquist and < 15 kHz;
  skipped below 32 kHz. FP causes: phone-band or low-bitrate sources.
- **Prosody** (weak): pYIN f0 (70–400 Hz) on ≤ 60 s; flag when f0 CV < 0.08 and pause-length CV < 0.25 (≥ 4 pauses ≥ 150 ms).
- **Transcript**: faster-whisper base int8, beam 5, temperature 0, word timestamps; model loaded per file and released.

## Text (`analyzers/text/`)

Claims by regex + dateparser (dates), spaCy `en_core_web_sm` (places, people, organisations), number+unit regex,
quoted or reported speech. Checks: date vs EXIF `DateTimeOriginal` / video creation time (tolerance 2 days);
quote vs every transcript sentence window with all-MiniLM-L6-v2 cosine (< 0.40 = conflict, ≥ 0.60 = consistent);
place vs EXIF GPS via a 45-entry offline gazetteer (> 150 km = conflict); number vs transcript.

## Calibration (`scoring/calibrate.py`, `validation/run_validation.py`)

For each indicator, every validation finding is labelled hit (right item and location: IoU ≥ 0.1, or within 0.5 s)
or miss. Platt scaling `p = σ(A·raw + B)` (scikit-learn, C = 10) with 200 bootstrap refits; the range is their
10th–90th percentile at the finding's raw score, at least ±0.04. If all findings were hits (or all misses) A = 0 and the
range comes from Beta(hits+1, misses+1). Probabilities are clipped to [0.02, 0.95]. Indicators with < 6 validation
findings stay uncalibrated (identity, ±0.12) and say so.

## Fusion and verdicts (`scoring/fuse.py`)

Per evidence item and per case, one term per method family (strongest finding):

    logit(P) = logit(0.2) + Σ_k 0.6^k · w_f · (logit(p_f) − logit(0.2))     (families sorted by contribution, p_f > 0.2)

`w_f` from `FAMILY_WEIGHTS` (e.g. copy-move 0.9, ELA 0.6, prosody 0.3), halved by R-14. P ≤ 0.97; the range is the same
sum on the findings' low and high ends, at least ±0.05.

| Band | Condition on [lo, hi] |
|---|---|
| No indicators found | hi < 0.40 |
| Strong indicators | lo ≥ 0.70 **and** corroborated (≥ 2 families with p ≥ 0.55, or a supports rule between two families) |
| Indicators of manipulation | lo ≥ 0.55 |
| Inconclusive | otherwise (the range touches the middle band), or no findings while a detector failed |

## Cross-modal rules (`correlate/rules.py`)

| ID | Rule | Effect |
|---|---|---|
| R-03 | Audio noise-floor step within 0.5 s of a flow jump / duplicate / drop on the same clip | supports (counts as corroboration) |
| R-05 | Caption quote not found in the transcript | supports the conflict finding |
| R-07 | Lip-sync drop (mouth opening vs speech RMS, 4 s windows, r < min(0.15, median − 0.3)) overlapping a flagged segment | weak support (not corroboration) |
| R-09 | Image region IoU ≥ 0.3 with a flagged face / frame region in the video | supports |
| R-11 | Caption date conflicts with capture metadata | links the text finding to the image/video |
| R-14 | ELA/ghost on an image with no EXIF and q ≤ 85, or covering > 25 % of it | weakens (weight × 0.5, alternative added) |

## Custody

Each entry stores actor, action, tool version, input and output hashes, and `entry_hash = SHA-256(prev_hash | fields)`.
SQLite triggers reject UPDATE and DELETE on the table; `GET /api/cases/{id}/custody` reports whether the chain verifies.
