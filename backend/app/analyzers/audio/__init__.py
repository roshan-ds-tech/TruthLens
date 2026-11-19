from ..base import FnAnalyzer
from . import bandlimit, prosody, splice, transcribe

ANALYZERS = [
    FnAnalyzer("noise_floor", "Noise floor", ("audio",), splice.run, "Noise floor and spectrum",
               "Splice and level steps in audio", "audiofx 1.0"),
    FnAnalyzer("band_limit", "Band limit", ("audio",), bandlimit.run, "Band-limit check",
               "Sharp spectral cutoff typical of synthetic speech", "bandlimit 1.0"),
    FnAnalyzer("prosody", "Prosody", ("audio",), prosody.run, "Pitch and pause statistics",
               "Unusually uniform pitch and pauses (weak)", "pyin 1.0", optional_dep="librosa"),
    FnAnalyzer("transcript", "Transcript", ("audio",), transcribe.run, "Transcript",
               "Word-level speech to text", "faster-whisper base int8", optional_dep="faster_whisper"),
]
