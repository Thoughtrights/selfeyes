# selfeyes-pipeline

Automated ingestion pipeline for the [selfeyes](https://thoughtrights.com/selfeyes/) gallery.

Discovers portrait photographs from Flickr, the Library of Congress, and the Smithsonian; detects faces and eye regions; scores for probable corneal reflections; and feeds approved crops into the gallery's `manifest.json`.

---

## No facial recognition

This pipeline detects eye *regions* — geometry only. It locates where a corneal reflection might appear. It does **not**:

- Identify who is in a photograph
- Compute face embeddings or similarity scores
- Match or cluster faces across images
- Store any biometric data

The only "AI" step is [mediapipe Face Mesh](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker), which returns 468 landmark coordinates per face. Those coordinates are used to compute bounding boxes. Nothing else is done with them.

---

## Setup

```bash
cd pipeline

# Python 3.9–3.12 required (mediapipe does not support 3.13 yet)
python3.9 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create a `.env` file (never committed to git):

```
FLICKR_API_KEY=your_key_here
FLICKR_API_SECRET=your_secret_here
SMITHSONIAN_API_KEY=your_key_here   # register free at https://api.si.edu
```

---

## Command reference

### `discover` — find candidates

Search photo sources and store candidates in the database. Does **not** download images.

```bash
# All sources
python -m selfeyes_pipeline discover

# Specific source only
python -m selfeyes_pipeline discover --source flickr
python -m selfeyes_pipeline discover --source loc
python -m selfeyes_pipeline discover --source smithsonian

# Override max pages fetched per search term
python -m selfeyes_pipeline discover --source flickr --max-pages 10
python -m selfeyes_pipeline discover --source loc --max-pages 5
```

---

### `process` — download, detect, score, crop

Downloads candidates that haven't been fetched yet, runs mediapipe face/eye detection, scores for reflections, and generates face and eye crops.

```bash
# Process all pending candidates (all sources)
python -m selfeyes_pipeline process

# Process only a specific source
python -m selfeyes_pipeline process --source loc
python -m selfeyes_pipeline process --source smithsonian
python -m selfeyes_pipeline process --source flickr

# Limit to N candidates (useful for test runs)
python -m selfeyes_pipeline process --limit 20
python -m selfeyes_pipeline process --source loc --limit 50

# Re-run detection on already-downloaded images that produced no eyes
# (use this after changing min_eye_px or other detection settings)
python -m selfeyes_pipeline process --reprocess
python -m selfeyes_pipeline process --reprocess --source loc
python -m selfeyes_pipeline process --reprocess --limit 100
```

---

### `run` — discover + process in one shot

```bash
# Discover and process all sources
python -m selfeyes_pipeline run

# Single source, limited batch
python -m selfeyes_pipeline run --source flickr --max-pages 2 --limit 100
```

---

### `review` — launch the curation UI

Opens a local Flask app at http://localhost:5050. Cards are sorted by reflection score (highest first). Approving an item immediately writes it to `html/manifest.json`.

```bash
python -m selfeyes_pipeline review

# Custom port if 5050 is in use
python -m selfeyes_pipeline review --port 5051
```

**Keyboard shortcuts in the UI:**
- `A` — approve (add to gallery)
- `S` — skip
- `O` — open source page in browser
- `↑` / `↓` — navigate between cards
- `Esc` — close lightbox

---

### `stats` — pipeline summary

```bash
python -m selfeyes_pipeline stats
```

Output:
```
Pipeline stats
──────────────────────────────
  Candidates discovered : 17253
  Downloaded            : 4840
  Eyes detected         : 199
  Pending review        : 76
  Approved              : 50
  Skipped               : 82
```

---

## Typical workflow

```bash
# 1. Fill the queue
python -m selfeyes_pipeline discover

# 2. Process a test batch first to verify quality
python -m selfeyes_pipeline process --limit 50

# 3. Open the review UI and approve what looks good
python -m selfeyes_pipeline review

# 4. Process the full queue (runs for hours — leave it going)
python -m selfeyes_pipeline process

# 5. Keep reviewing as new candidates appear
python -m selfeyes_pipeline review

# 6. After approval, deploy the gallery
cd .. && ./deploy.sh
```

---

## Adding new Flickr search terms

Edit `config.toml` under `[flickr] search_terms`, then re-run discovery. Already-seen photos are skipped (deduped by photo ID).

```bash
python -m selfeyes_pipeline discover --source flickr
python -m selfeyes_pipeline process --source flickr
```

---

## Configuration

All settings are in `config.toml`. Key values:

| Setting | Default | Effect |
|---|---|---|
| `filters.min_long_side_px` | 2400 | Skip images smaller than this |
| `filters.min_eye_px` | 200 | Skip eyes narrower than this (px) |
| `filters.sharpness_min_variance` | 100 | Drop blurry eye crops |
| `crop.face_longest_side_px` | 1400 | Gallery thumbnail size |
| `crop.face_padding_pct` | 0.15 | Padding around face boundary |
| `crop.eye_padding_pct` | 0.40 | Padding around eye crop |

---

## Sources

| Source | License | Key required | Notes |
|---|---|---|---|
| Flickr | CC BY, CC BY-SA, CC0, Public Domain, U.S. Gov | Yes (free) | flickr.com/services/apps/create |
| Library of Congress | U.S. Gov / Public Domain | No | Historical portraits, daguerreotypes |
| Smithsonian (NPG, NMAAHC) | CC0 | Yes (free) | api.si.edu — National Portrait Gallery + NMAAHC |

---

## Ethics and licensing

- Only permissive licenses are fetched — no all-rights-reserved, no ND
- Every approved gallery item carries photographer attribution, source URL, license name, and license URL
- This pipeline never scrapes social media or any source without a documented public API
- No facial recognition, no embeddings, no identity matching
