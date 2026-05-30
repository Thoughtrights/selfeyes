"""Face and eye detection using mediapipe Face Mesh.

This module detects eye *regions* (geometry/landmarks) to locate where
corneal reflections may appear. It does NOT perform facial recognition,
identity matching, or biometric embedding. The mediapipe Face Mesh model
returns landmark coordinates only — no identity information.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# mediapipe is imported lazily so the rest of the pipeline can load
# even if mediapipe fails to install on a given platform.
_mp = None


def _get_mp():
    global _mp
    if _mp is None:
        import mediapipe as mp  # noqa: PLC0415
        _mp = mp
    return _mp


# mediapipe Face Mesh eye contour landmark indices
# Left eye contour (from camera perspective = subject's right eye)
LEFT_EYE_INDICES = [
    362, 382, 381, 380, 374, 373, 390, 249, 263,
    466, 388, 387, 386, 385, 384, 398,
]
# Right eye contour (from camera perspective = subject's left eye)
RIGHT_EYE_INDICES = [
    33, 7, 163, 144, 145, 153, 154, 155, 133,
    173, 157, 158, 159, 160, 161, 246,
]


@dataclass
class EyeDetection:
    side: str          # "left" | "right"
    bbox: tuple        # (x, y, w, h) in pixels
    face_bbox: tuple   # (x, y, w, h) of the full face in pixels


def detect_eyes(image_path: str | Path, min_eye_px: int = 400) -> list[EyeDetection]:
    """Run face mesh on image; return surviving eye detections.

    Returns one EyeDetection per eye that meets the min_eye_px threshold.
    An image with no face or no large-enough eyes returns an empty list.
    """
    mp = _get_mp()
    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        return []

    h, w = img_bgr.shape[:2]
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=4,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    )

    results = face_mesh.process(img_rgb)
    face_mesh.close()

    if not results.multi_face_landmarks:
        return []

    detections: list[EyeDetection] = []

    for face_landmarks in results.multi_face_landmarks:
        lms = face_landmarks.landmark  # normalized [0,1]

        # Full face bounding box from all 468 landmarks
        xs = [lm.x * w for lm in lms]
        ys = [lm.y * h for lm in lms]
        face_bbox = (
            int(min(xs)), int(min(ys)),
            int(max(xs) - min(xs)), int(max(ys) - min(ys)),
        )

        for side, indices in [("left", LEFT_EYE_INDICES), ("right", RIGHT_EYE_INDICES)]:
            pts = [(int(lms[i].x * w), int(lms[i].y * h)) for i in indices]
            ex = [p[0] for p in pts]
            ey = [p[1] for p in pts]
            bx, by = min(ex), min(ey)
            bw, bh = max(ex) - bx, max(ey) - by

            if bw < min_eye_px:
                continue

            detections.append(EyeDetection(
                side=side,
                bbox=(bx, by, bw, bh),
                face_bbox=face_bbox,
            ))

    return detections
