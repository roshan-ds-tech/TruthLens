import cv2
import numpy as np

from app.correlate.visual import region_match
from app.correlate import rules


def textured(seed=7):
    rng = np.random.default_rng(seed)
    canvas = np.full((360, 480, 3), 240, np.uint8)
    for _ in range(220):
        x, y = rng.integers([8, 8], [472, 352])
        color = tuple(int(x) for x in rng.integers(0, 220, 3))
        cv2.circle(canvas, (int(x), int(y)), int(rng.integers(2, 8)), color, -1)
    return canvas


def loc(x, y, w=100, h=100):
    return {"type": "bbox", "x": x, "y": y, "w": w, "h": h, "image_w": 480, "image_h": 360}


def test_registered_regions_follow_a_translation():
    image = textured()
    frame = cv2.warpAffine(image, np.float32([[1, 0, 25], [0, 1, 15]]), (480, 360), borderValue=(240, 240, 240))
    match = region_match(image, frame, loc(120, 100), loc(145, 115))
    assert match and match["verified"] and match["iou"] > 0.8
    assert region_match(image, frame, loc(120, 100), loc(320, 240)) is None


def test_unrelated_images_with_identical_boxes_do_not_match():
    assert region_match(textured(7), textured(51), loc(120, 100), loc(120, 100)) is None


def test_r09_requires_computed_registration_not_equal_coordinates():
    a = rules.F("F-IMG-001", "E-01", "image", None, "image", "ela_inconsistency", "ela", loc(100, 100), .8, {})
    b = rules.F("F-VID-001", "E-02", "video", None, "video", "face_flicker", "face_flicker", loc(100, 100), .8, {})
    assert rules.r09_same_location([a, b], {}) == []
    ev = rules.Ev("E-01", "image", None, {}, {"region_matches": {"F-IMG-001:F-VID-001": {
        "verified": True, "inliers": 20, "iou": .9}}})
    edges = rules.r09_same_location([a, b], {"E-01": ev})
    assert len(edges) == 1 and edges[0].weak
    assert rules.independent_supports(edges, {a.finding_id: a.family, b.finding_id: b.family}) == 0
