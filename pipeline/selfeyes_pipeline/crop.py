"""Generate face-boundary and eye crops from detected landmark bboxes."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None  # we control the source; decompression bomb check not needed


def _pad_bbox(x: int, y: int, w: int, h: int,
              pad_pct: float, img_w: int, img_h: int) -> tuple[int, int, int, int]:
    """Expand a bounding box by pad_pct on all sides, clamped to image bounds."""
    px = int(w * pad_pct)
    py = int(h * pad_pct)
    x0 = max(0, x - px)
    y0 = max(0, y - py)
    x1 = min(img_w, x + w + px)
    y1 = min(img_h, y + h + py)
    return x0, y0, x1 - x0, y1 - y0


def make_face_crop(
    image_path: str | Path,
    face_bbox: tuple,  # (x, y, w, h)
    output_path: str | Path,
    pad_pct: float = 0.15,
    longest_side_px: int = 1400,
    jpeg_quality: int = 88,
) -> bool:
    """Crop the face region from image_path and save to output_path.

    The face_bbox uses the convex hull of all Face Mesh landmarks, giving a
    tight boundary around the face. We pad by pad_pct and scale so the longest
    side is longest_side_px.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        iw, ih = img.size
        x, y, w, h = _pad_bbox(*face_bbox, pad_pct, iw, ih)
        crop = img.crop((x, y, x + w, y + h))

        # Scale so longest side = longest_side_px (never upscale)
        cw, ch = crop.size
        scale = min(1.0, longest_side_px / max(cw, ch))
        if scale < 1.0:
            new_w = int(cw * scale)
            new_h = int(ch * scale)
            crop = crop.resize((new_w, new_h), Image.LANCZOS)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        crop.save(str(output_path), "JPEG", quality=jpeg_quality)
        return True
    except Exception as e:
        print(f"  [crop] face crop failed for {image_path}: {e}")
        return False


def make_eye_crop(
    image_path: str | Path,
    eye_bbox: tuple,   # (x, y, w, h)
    output_path: str | Path,
    pad_pct: float = 0.40,
    jpeg_quality: int = 92,
) -> bool:
    """Crop the eye region from image_path at maximum native resolution.

    The eye crop is the zoom target in the gallery — it must be as large
    and sharp as the original image allows. No downscaling is applied.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        iw, ih = img.size
        x, y, w, h = _pad_bbox(*eye_bbox, pad_pct, iw, ih)
        crop = img.crop((x, y, x + w, y + h))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        crop.save(str(output_path), "JPEG", quality=jpeg_quality)
        return True
    except Exception as e:
        print(f"  [crop] eye crop failed for {image_path}: {e}")
        return False
