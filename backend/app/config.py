"""Limits, thresholds and weights. Every tunable number lives here so methodology.md can cite it."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("TRUTHLENS_DATA", ROOT / "data")).resolve()
DB_PATH = DATA_DIR / "truthlens.db"
EVIDENCE_DIR = DATA_DIR / "evidence"      # read-only originals: evidence/<case>/<sha>/original.<ext>
DERIVED_DIR = DATA_DIR / "derived"        # decoded frames, 16 kHz WAV, transcripts
ARTIFACT_DIR = DATA_DIR / "artifacts"     # heatmaps, overlays, spectrograms
REPORT_DIR = DATA_DIR / "reports"
MODEL_DIR = Path(os.environ.get("TRUTHLENS_MODELS", ROOT / "backend" / "models")).resolve()
VALIDATION_DIR = ROOT / "validation"
METRICS_PATH = VALIDATION_DIR / "results" / "metrics.json"
CALIBRATION_PATH = VALIDATION_DIR / "results" / "calibration.json"
REQUIREMENTS_PATH = ROOT / "backend" / "requirements.txt"

APP_VERSION = "1.0.0"

# --- Deployment ---
# "local": single machine; cases opened by the CLI (no owner) are visible to every account.
# "hosted": internet-facing; only the owner of a case can see it.
MODE = os.environ.get("TRUTHLENS_MODE", "local")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "TRUTHLENS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174").split(",") if o.strip()]
ALLOWED_ORIGIN_REGEX = os.environ.get("TRUTHLENS_ALLOWED_ORIGIN_REGEX") or None   # e.g. https://truthlens-.*\.vercel\.app
SESSION_DAYS = 7
ALLOW_SIGNUP = os.environ.get("TRUTHLENS_ALLOW_SIGNUP", "1") == "1"
LOGIN_MAX_FAILURES = 8          # per email per window, then 429
LOGIN_WINDOW_S = 15 * 60
DEFAULT_INVESTIGATOR = "Priya S."
SEED = 7

# --- Input limits (design doc §3.2) ---
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_SECONDS = 60.0
MAX_VIDEO_HEIGHT = 720
MAX_AUDIO_SECONDS = 120.0
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_TEXT_CHARS = 5000

# --- Image analyzer ---
ELA_QUALITY = 90
ELA_BLOCK = 16
ELA_K_MAD = 3.6            # flag blocks whose (3×3-smoothed) error is > k·MAD above the median
NOISE_BLOCK = 32
NOISE_Z = 3.0              # robust z threshold for residual variance
GHOST_QUALITIES = list(range(50, 100, 5))
COPYMOVE_MIN_DIST = 40     # px between matched keypoints
COPYMOVE_MIN_INLIERS = 12
COPYMOVE_MAX_FEATURES = 3000
MIN_REGION_FRACTION = 0.002  # ignore flagged regions smaller than this share of the image
EDITOR_SOFTWARE = ("photoshop", "gimp", "snapseed", "lightroom", "picsart", "pixlr", "affinity", "canva", "facetune", "meitu")

# --- Video analyzer ---
VIDEO_SAMPLE_FPS = 4.0
VIDEO_WORK_WIDTH = 320       # optical flow runs on frames downscaled to this width
FLOW_Z = 4.0
PHASH_DUP_MAX = 0            # identical perceptual hash inside motion = duplicate frame
TOP_SUSPICIOUS_FRAMES = 3
FACE_FLICKER_Z = 4.0

# --- Audio analyzer ---
AUDIO_SR = 16000
NOISE_FLOOR_FRAME_S = 0.02
NOISE_FLOOR_WINDOW_S = 1.0
NOISE_FLOOR_STEP_DB = 6.0    # "step change > X dB" from §3.5
BANDLIMIT_DROP_DB = 40.0
WHISPER_MODEL = "base"
WHISPER_COMPUTE = "int8"

# --- Text analyzer ---
SIMILARITY_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPEECH_MISMATCH_SIM = 0.4    # §3.7 rule: transcript similarity < 0.4

# --- Correlation ---
SPLICE_SYNC_WINDOW_S = 0.5

# --- Confidence and verdicts (§3.8) ---
BAND_NONE_MAX = 0.40         # whole range below → No indicators found
BAND_INDICATORS_MIN = 0.55   # range low end at or above → Indicators of manipulation
BAND_STRONG_MIN = 0.70       # low end at or above AND corroborated → Strong indicators
DEFAULT_RANGE_HALF_WIDTH = 0.12  # used when an indicator has no calibration yet

# Fusion weight per method family (lower = known high false-positive rate).
FAMILY_WEIGHTS = {
    "ela": 0.6, "noise": 0.7, "jpeg_ghost": 0.6, "copy_move": 0.9, "metadata": 0.5,
    "frame_dupes": 0.8, "optical_flow": 0.9, "face_flicker": 0.6, "frame_forensics": 0.5,
    "noise_floor": 0.9, "band_limit": 0.6, "prosody": 0.3,
    "claim_date": 0.9, "claim_speech": 0.7, "claim_entity": 0.4, "lipsync": 0.4,
}

VERDICT_LABELS = {
    "none": "No indicators found",
    "inconclusive": "Inconclusive",
    "indicators": "Indicators of manipulation",
    "strong": "Strong indicators",
}

GENERAL_LIMITATIONS = [
    "Confidence ranges describe how strongly the analyzers agree. They are not the probability that the content was edited.",
    "Fully AI-generated media without editing traces may not be detected.",
    "Social-platform recompression can produce error-level patterns similar to editing.",
    "Analyzers were calibrated on a small self-made test set only. This is not a general accuracy claim.",
    "This report does not establish who created or altered the content.",
]


def set_data_dir(path: os.PathLike | str) -> None:
    """Point all storage at another folder (tests and validation use temp dirs).
    Callers must read paths as ``config.X`` at call time, never ``from config import X``."""
    global DATA_DIR, DB_PATH, EVIDENCE_DIR, DERIVED_DIR, ARTIFACT_DIR, REPORT_DIR
    DATA_DIR = Path(path).resolve()
    DB_PATH = DATA_DIR / "truthlens.db"
    EVIDENCE_DIR = DATA_DIR / "evidence"
    DERIVED_DIR = DATA_DIR / "derived"
    ARTIFACT_DIR = DATA_DIR / "artifacts"
    REPORT_DIR = DATA_DIR / "reports"


def ensure_dirs() -> None:
    for d in (DATA_DIR, EVIDENCE_DIR, DERIVED_DIR, ARTIFACT_DIR, REPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)
