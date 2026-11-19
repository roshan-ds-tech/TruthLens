from ..base import FnAnalyzer
from . import copy_move, ela, exif_rules, jpeg_ghost, noise

ANALYZERS = [
    FnAnalyzer("exif", "Metadata", ("image",), exif_rules.run, "Metadata rules",
               "Editor tags, missing camera tags, date and thumbnail conflicts", "exif-rules 1.0"),
    FnAnalyzer("ela", "Error level analysis", ("image",), ela.run, "Error level analysis",
               "JPEG recompression differences", "ela 1.2.0"),
    FnAnalyzer("noise", "Noise map", ("image",), noise.run, "Noise map",
               "Sensor noise consistency across regions", "noise-residual 1.0"),
    FnAnalyzer("jpeg_ghost", "JPEG ghost", ("image",), jpeg_ghost.run, "JPEG ghost",
               "Regions saved at a different JPEG quality", "ghost 1.0"),
    FnAnalyzer("copy_move", "Copy-move", ("image",), copy_move.run, "Copy-move",
               "Duplicated regions within one image", "orb-ransac 1.0"),
]
