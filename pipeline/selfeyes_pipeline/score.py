"""Scoring functions for eye crops.

Primary signal: reflection_score — estimates whether a visible scene
reflection is present in the cornea/iris zone of the eye.

Sharpness is a secondary quality gate (used to discard blurry eyes),
not the primary curatorial criterion.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def sharpness(eye_crop: np.ndarray) -> float:
    """Laplacian variance of the eye crop in grayscale.

    Higher = sharper. Typical usable images score > 100.
    """
    gray = cv2.cvtColor(eye_crop, cv2.COLOR_RGB2GRAY) if eye_crop.ndim == 3 else eye_crop
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def reflection_score(eye_crop: np.ndarray) -> float:
    """Estimate the probability that the eye contains a visible scene reflection.

    Method:
    1. Extract the iris zone — center ellipse of the eye bbox, ~55% of w/h.
    2. Count specular-highlight pixels (luma > 220) as a fraction of iris area.
    3. Measure local contrast (std-dev of luma) in the iris zone.
       A reflection has both bright AND dark pixels; a plain bright reflection
       or overexposure has high luma but low contrast.
    4. Score = specular_ratio * log1p(contrast_std) — normalized to ~[0,1].

    Returns a float. Higher values rank higher in the review UI.
    """
    if eye_crop is None or eye_crop.size == 0:
        return 0.0

    h, w = eye_crop.shape[:2]

    # Iris zone: center ellipse, 55% of bbox dimensions
    iris_w = max(1, int(w * 0.55))
    iris_h = max(1, int(h * 0.55))
    cx, cy = w // 2, h // 2
    x0 = max(0, cx - iris_w // 2)
    y0 = max(0, cy - iris_h // 2)
    x1 = min(w, x0 + iris_w)
    y1 = min(h, y0 + iris_h)

    iris_region = eye_crop[y0:y1, x0:x1]
    if iris_region.size == 0:
        return 0.0

    # Convert to grayscale luma
    if iris_region.ndim == 3:
        gray = cv2.cvtColor(iris_region, cv2.COLOR_RGB2GRAY)
    else:
        gray = iris_region

    # Specular ratio: fraction of iris pixels that are very bright (>220 luma)
    specular_mask = gray > 220
    specular_ratio = float(specular_mask.sum()) / gray.size

    # Local contrast in iris zone — std dev of luma
    contrast_std = float(gray.std())

    # Combined score: need both bright highlights AND local variation
    # log1p normalises contrast_std from [0,128] → [0,~5]
    score = specular_ratio * float(np.log1p(contrast_std))

    # Clamp to [0, 1] — typical values top out around 0.5
    return min(score, 1.0)


def load_eye_crop_array(image_path: str, bbox: tuple) -> np.ndarray | None:
    """Load an eye crop from disk given an (x,y,w,h) bbox in the original image."""
    try:
        img = Image.open(image_path).convert("RGB")
        x, y, bw, bh = bbox
        crop = img.crop((x, y, x + bw, y + bh))
        return np.array(crop)
    except Exception:
        return None
