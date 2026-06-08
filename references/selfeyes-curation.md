# Selfeyes Curation Reference

How to evaluate candidates in the review UI at **http://localhost:5050**.

---

## The artistic criterion

Selfeyes is about **what photographs contain beyond what they were meant to show** — specifically, the photographer's reflection trapped in the subject's iris or cornea, or in reflective surfaces on or near the face. Every approved image should have something worth finding when the viewer zooms in.

The primary question when reviewing: **Is there a visible scene, object, or person reflected in the eye?**

Everything else (sharpness, resolution, face composition) is a quality gate. The reflection is the content.

---

## The review UI

**Cards are sorted by reflection score (highest first).** Work top-to-bottom — the best candidates surface first. Low-scoring candidates near the bottom are often not worth approving.

### Keyboard shortcuts
| Key | Action |
|---|---|
| `A` | Approve — adds to gallery |
| `S` | Skip — hides from gallery, stays in DB |
| `O` | Open source page in browser |
| `↑` / `↓` | Navigate between cards |
| `Esc` | Close eye crop lightbox |

### What the UI shows
- **Left panel** — face crop (what appears in the gallery grid)
- **Right panel** — eye crop (the zoom target; what you're actually evaluating)
- Click the eye crop to open it full-size in the lightbox

**Always click the eye crop full-size before approving.** The thumbnail is too small to judge reflection quality.

---

## Approve if

- **Identifiable scene reflection** — you can make out a room, a window, a landscape, another person, a camera, or any recognizable shape in the iris/cornea
- **Photographer reflection** — the shooter is visible in the subject's eye; this is the project's core motif
- **Strong specular highlight** — even if the reflected scene isn't perfectly sharp, a bright corneal glint with visible structure around it is worth keeping
- **Reflective lenses / surfaces** — sunglasses, eyeglasses, or other face-level reflective surfaces where a scene is clearly visible (not just ambient glare)
- **Animal eyes** — dogs, cats, horses with visible reflections are valid; the reflection criterion applies equally
- **Compelling composition** — even a borderline reflection is worth approving if the face crop is striking on its own

---

## Skip if

### Reflection quality
- No reflection visible — the eye is present but the iris is dark or uniformly lit
- Only ambient glare or lens flare — a white spot with no scene structure
- Reflection too small to see even at full zoom (sub-10px bright area)
- Reflection is clearly just a studio softbox or ring light with no environmental content

### Image quality
- Visibly blurry or out-of-focus eye region (pipeline sharpness filter misses some)
- Heavy JPEG compression artifacts in the iris zone
- Eye is partially cropped by the face bbox (half an eye)
- Face crop is so heavily cropped that the subject is unrecognisable as a face

### Content issues
- Child or infant (tag blocklist should catch these, but some slip through)
- AI-generated or illustrated face (very occasionally passes tag filter)
- Painting or drawing where the "reflection" is painted-in texture
- Heavily processed / filtered image where the iris is synthetic-looking
- The image is a cartoon, animation frame, or rendering

### Technical issues
- Face crop is another body part misdetected as a face
- Eye crop is centered on eyebrow, eyelash, or nose rather than iris
- Image is very low resolution for its stated dimensions (upscaled)

---

## Reflection score interpretation

The score is `specular_ratio × local_contrast` in the iris zone:

| Score range | Typical quality |
|---|---|
| 0.30 + | Strong specular highlight; likely has visible scene reflection |
| 0.15 – 0.30 | Moderate; worth checking the eye crop full-size |
| 0.05 – 0.15 | Subtle; approve only if the scene reflection is compelling |
| < 0.05 | Very low; almost always skip |

The score is a **ranking signal**, not a pass/fail gate. Some excellent images score low because the reflection is dark but detailed. Some high scorers are just glare. Always look at the eye crop.

---

## Duplicate and similarity groups

The **Duplicates** tab groups images with perceptual hash distance ≤ 10 (very similar face crops). Common causes:
- Same photo, left eye and right eye crops — often worth keeping both
- Same session, different frames — keep the one with the best reflection
- Same image ingested from two sources — skip the lower-quality source

### Group review buttons
- **Keep highest score, skip rest** — good default for same-frame duplicates
- **Skip all** — use when an entire group is poor quality
- Individual **Keep / Skip** — use for same-session variants where you want the best one

After reviewing groups, **run the Duplicates tab again** — groups do not auto-refresh.

---

## After review

Once you've approved a batch:

```bash
# Export newly approved items to html/manifest.json
python -m selfeyes_pipeline export

# Add w/h dimensions for new items
pipeline/.venv/bin/python -c "
import json; from pathlib import Path; from PIL import Image
m = json.load(open('html/manifest.json'))
for item in m['items']:
    if 'w' not in item:
        p = Path('html') / item['src']
        with Image.open(p) as img: item['w'], item['h'] = img.size
json.dump(m, open('html/manifest.json','w'), indent=2)
"

# Deploy
./deploy.sh
```

---

## Reversibility

Approving or skipping an item only sets the `review.status` field in SQLite.
Nothing is deleted. To change a decision:

```python
# In python with pipeline venv active
from selfeyes_pipeline import config as _config
from selfeyes_pipeline.store import Store
cfg = _config.load()
store = Store(cfg["paths"]["db_path"])
store.set_review_status("flickr-12345-left", "approved")   # or "skipped" or "pending"
```

To remove an already-exported item from the live gallery, edit `manifest.json`
directly (remove the item) and redeploy. The crop files stay in `html/assets/pipeline/`
— they are not automatically deleted.
