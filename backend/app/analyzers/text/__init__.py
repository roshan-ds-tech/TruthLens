from ..base import FnAnalyzer
from . import consistency

ANALYZERS = [
    FnAnalyzer("claims", "Claim extraction", ("text",), consistency.extract_only, "Claim extraction",
               "Dates, places, names, numbers and quotes from captions", "claims 1.0"),
    FnAnalyzer("consistency", "Consistency check", ("text",), consistency.run, "Claim consistency",
               "Claims vs EXIF, creation time, GPS and transcript", "consistency 1.0"),
]
