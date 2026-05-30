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

# Python 3.9–3.12 required (mediapipe doesn't support 3.13 yet)
python3.9 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create a `.env` file (never committed):

```
FLICKR_API_KEY=your_key_here
FLICKR_API_SECRET=your_secret_here
# SMITHSONIAN_API_KEY=   ← register free at https://api.si.edu
```

---

## Usage

```bash
# 1. Discover candidates (no download yet)
python -m selfeyes_pipeline discover --source flickr
python -m selfeyes_pipeline discover --source loc
python -m selfeyes_pipeline discover   # all sources

# 2. Download, detect faces, score reflections, generate crops
python -m selfeyes_pipeline process
python -m selfeyes_pipeline process --limit 20   # small test run

# 3. Launch the review UI
python -m selfeyes_pipeline review
# → http://localhost:5050

# Or do everything at once:
python -m selfeyes_pipeline run

# Check pipeline stats
python -m selfeyes_pipeline stats
```

---

## Review UI

`python -m selfeyes_pipeline review` opens a local web app at http://localhost:5050.

Each card shows:
- **Face crop** (left) — what will appear in the gallery grid
- **Eye crop** (right) — the cornea/iris zone; click to open full-size. This is what you're evaluating: is there a visible reflection of a room, a person, a scene?
- **Reflection score** — automated estimate based on specular highlights and contrast in the iris zone. Ranked highest-first. Not a hard filter — the human decides.

Keyboard shortcuts: `A` approve · `S` skip · `O` open source · `↑↓` navigate · `Esc` close lightbox.

Approving an item immediately adds it to `html/manifest.json` and the gallery.

---

## Configuration

See `config.toml` for search terms, thresholds, and crop settings.

---

## Ethics and licensing

- Only permissive licenses are fetched (Flickr: CC BY, CC BY-SA, CC0, Public Domain, U.S. Gov, Flickr Commons)
- Every approved gallery item carries photographer attribution, source URL, license name, and license URL
- A takedown contact should be listed on the gallery's credits page
- This pipeline never scrapes social media or any source without a documented public API
