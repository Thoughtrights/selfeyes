# selfeyes — ingestion pipeline PLAN

## Context

The existing project lives at `github.com/thoughtrights/selfeyes` and deploys to
`thoughtrights.com/selfeyes/`. It is a static lightbox gallery of high-resolution
portraits zoomed into eye reflections — a play on "selfies" → "self eyes." Current
sourcing is manual.

This plan adds an automated ingestion pipeline that sources photos from Flickr
(and later from institutional public-domain archives), filters for license and
eye-region resolution, generates eye crops, and produces output that drops into
the existing static gallery.

**Artistic intent:** invite viewers to notice the information they unknowingly
share in their photos. The implementation must therefore not itself be the
creepy thing the project critiques — see *Hard constraints*.

## Repo relationship

- **`selfeyes`** (existing, MIT-licensed) — static lightbox gallery. The
  pipeline produces files + a manifest that drop into `selfeyes/html/`. **No
  change** to the gallery's static deploy model.
- **`selfeyes-pipeline`** (new, this work) — Python tool. Reads from Flickr/etc.
  via APIs, writes images + JSON. Separate repo or sibling directory; should not
  be coupled to the gallery's runtime.

## Hard constraints

These are non-negotiable and should be enforced in code, not just in policy.

1. **Permissive licenses only.** For Flickr, allow license IDs `4, 5, 7, 8, 9, 10`:
   - 4: CC BY 2.0
   - 5: CC BY-SA 2.0
   - 7: No known copyright restrictions (Flickr Commons)
   - 8: U.S. Government Work
   - 9: CC0 1.0
   - 10: Public Domain Mark 1.0
   - **Conditionally** allow 1, 2 (NC-licensed) behind a config flag — depends on
     whether the gallery has commercial dimensions (prints, ads, gallery sales).
     Default off.
   - **Never** allow 0 (ARR), 3 (NC-ND), 6 (ND). Our crop is a derivative.

2. **No face recognition, no identity matching, no biometric templates.** The
   pipeline detects eye *regions* and produces *crops*. It does not:
   - Run facial recognition / identification
   - Compute or store face embeddings
   - Cluster or match by person across photos
   - Store anything that could function as a biometric template

   This is both a legal firewall (BIPA-style exposure) and the ethical core of
   the project. Code structure should make doing the wrong thing actively harder
   — e.g. don't import face-recognition libraries at all.

3. **Attribution is mandatory.** Every image surfaced in the gallery carries
   photographer name, source URL, license name, license URL. CC BY and CC BY-SA
   require this; we apply it uniformly for hygiene.

4. **Reversibility.** Every ingested item must be removable on request. The
   manifest stores enough metadata (source URL, owner ID) to find and pull
   anything. The gallery includes a takedown contact / form.

5. **Document, in code comments and in `README.md`, that this pipeline does not
   do facial recognition.** Future maintainers and curious viewers should be
   able to verify this claim.

## Tech stack

- **Python 3.11+**
- **HTTP**: `requests` (or `httpx`)
- **Flickr API**: direct REST calls; the API is small enough that a third-party
  wrapper isn't needed. JSON response format (`format=json&nojsoncallback=1`).
- **Image I/O**: `Pillow`
- **Detection**: `mediapipe` (Face Mesh — gives precise eye landmarks, CPU-only,
  no GPU dependency). Fallback to OpenCV Haar cascade `haarcascade_eye.xml` for
  cases where mediapipe doesn't load.
- **Sharpness**: OpenCV (`cv2.Laplacian` variance).
- **Storage**: SQLite for the manifest (better queries than flat JSON during
  iteration); JSON export for the static gallery.
- **Config**: TOML.
- **CLI**: `click` or `typer`.

No ML training, no model fine-tuning, no GPU. Everything runs on a laptop.

## Proposed layout

```
selfeyes-pipeline/
├── pyproject.toml
├── config.toml                 # license allowlist, thresholds, search terms
├── README.md                   # includes the "no face recognition" claim
├── selfeyes_pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py             # Source interface
│   │   ├── flickr.py           # Phase 1
│   │   ├── loc.py              # Phase 4 — Library of Congress
│   │   ├── nypl.py             # Phase 4 — NY Public Library
│   │   └── smithsonian.py      # Phase 4
│   ├── detect.py               # eye region detection
│   ├── score.py                # sharpness, eye-size filter, reflection score
│   ├── crop.py                 # produce preview / eye / zoom crops
│   ├── store.py                # SQLite manifest + filesystem layout
│   ├── export.py               # manifest.json + credits.html
│   └── cli.py
├── data/                       # gitignored
│   ├── cache/                  # raw downloaded originals
│   ├── crops/                  # generated eye-region crops
│   └── manifest.sqlite
└── tests/
```

## Pipeline stages

### Stage 1 — Discover (Flickr)

Use `flickr.photos.search`. Authenticated with the user's Pro API key.

Parameters:
- `license` = `4,5,7,8,9,10` (read from config)
- `extras` = `license,owner_name,date_taken,url_o,o_dims,tags,description,path_alias,safety_level`
- `media` = `photos`
- `content_types` = `0` (photos only — exclude screenshots, illustrations, virtual photography)
- `safe_search` = `1`
- `per_page` = `500` (Flickr max)
- `format` = `json`, `nojsoncallback` = `1`

Search terms (configurable; suggested starter list):
- Human portraits: `selfie portrait`, `self portrait`, `sunglasses portrait`,
  `aviators portrait`, `mirror selfie`, `mirror reflection portrait`
- Pets: `dog portrait close-up`, `cat portrait close-up`, `pet eyes`
- Animals: `horse eye`, `cow eye macro`

Also run `is_commons=1` searches over the same terms — that subset (Library of
Congress, Smithsonian, etc. on Flickr) is the safest discoverable contemporary
material.

**Rate limit**: 3600/hour authenticated. Exponential backoff on `429` and on
Flickr's `code=105` (service unavailable). Persist raw API responses to
`data/cache/api/<endpoint>/<timestamp>.json` for replay/debugging.

**Output**: rows in `candidates` table:
- `photo_id`, `source` (flickr), `owner_id`, `owner_name`, `license_id`,
  `license_name`, `license_url`, `original_url`, `source_url`,
  `width`, `height`, `tags`, `description`, `date_taken`, `ingested_at`

### Stage 2 — Metadata filter

Apply before downloading anything.

- Drop if longest side `< min_long_side` (default **2400 px**). A photo without
  enough resolution can't yield a usable eye crop regardless of composition.
- Drop if `license_id` not in allowlist (defense in depth — config could change).
- Drop if `safety_level != 1`.
- Drop on tag blocklist (configurable). Starter list: anything that suggests the
  photo is of a minor by the photographer's own labeling (`baby`, `infant`,
  `toddler`, `child`, `kid`, `kids`, `school`, etc.). Be over-inclusive here.

### Stage 3 — Download

- Fetch `url_o` (Flickr Pro key unlocks originals).
- Save to `data/cache/flickr/<photo_id>.<ext>`.
- Compute and store SHA256.
- If file already exists with matching SHA, skip.
- Polite delay between downloads.

### Stage 4 — Eye region detection

For each cached image, run mediapipe Face Mesh.

- For each detected face, extract left-eye and right-eye landmark groups.
  (Mediapipe eye contour landmark indices are well documented — Claude Code
  can look these up; the canonical sets are around 33/133/159/145 for the right
  eye and 362/263/386/374 for the left, with the full contour being 16 points
  per eye.)
- Compute the axis-aligned bounding box of each eye's landmarks, pad by ~40%.
- **Reject** any eye bbox whose width `< min_eye_px` (default **400 px**). This
  is the real quality filter for the project.
- Store one row per surviving eye in an `eyes` table: `photo_id`, `side`,
  `bbox` (x, y, w, h), `bbox_px_width`, `detection_confidence`.

**Important**: detection is the only "vision AI" step. Detection is allowed —
identification is not. The mediapipe Face Mesh returns geometry, not identity;
we do not pipe that geometry into any matching algorithm.

### Stage 5 — Score

Per surviving eye:
- **Sharpness**: `cv2.Laplacian(eye_crop_grayscale, cv2.CV_64F).var()`. Drop
  bottom quartile, or anything below a fixed threshold (tune empirically on the
  first batch).
- **Reflection score** (rank, don't filter): count specular bright pixels in
  the iris/pupil region relative to surrounding darkness. Higher score = more
  likely to have interesting reflections. Use this to surface candidates for
  human review.

### Stage 6 — Crop

For surviving eyes, produce three crops:
- `preview` — face-and-shoulders wider crop, ~1200 px wide. Gallery thumbnail.
- `eye` — tight eye crop, ~1600 px wide. The featured "selfeye."
- `zoom` — maximum-resolution eye crop at native resolution. Powers the slow
  zoom effect noted in the existing gallery's `script.js` change log.

Write to `data/crops/<source>/<photo_id>_<side>_{preview,eye,zoom}.jpg`. JPEG
quality 92.

### Stage 7 — Export

Generate two outputs that integrate with the existing static gallery.

**A.** `manifest.json` — list of items the gallery iterates over. Look at
`selfeyes/html/script.js` first to determine the actual shape the gallery
expects; extend it as needed for attribution. Suggested schema:

```json
{
  "version": 1,
  "items": [
    {
      "id": "flickr-12345-left",
      "preview": "items/flickr-12345-left_preview.jpg",
      "eye":     "items/flickr-12345-left_eye.jpg",
      "zoom":    "items/flickr-12345-left_zoom.jpg",
      "caption": "optional, manually written",
      "attribution": {
        "photographer": "Jane Doe",
        "source_url":   "https://www.flickr.com/photos/janedoe/12345",
        "license":      "CC BY 2.0",
        "license_url":  "https://creativecommons.org/licenses/by/2.0/"
      }
    }
  ]
}
```

**B.** `credits.html` — a complete attribution page listing every photo used,
with photographer, source link, license. Linked from the gallery footer.

## Phasing

Build in this order. Don't skip ahead.

**Phase 1 — Flickr discovery only.**
- Implement `sources/flickr.py` with search + pagination.
- Implement metadata filter.
- Run a small batch (~50 candidates); print to console; do not download.
- Verify license filtering is correct: spot-check that every result is in the
  allowed license set.

**Phase 2 — Download + detection.**
- Add download stage (cache + SHA).
- Add mediapipe detection + bbox extraction.
- Add sharpness scoring.
- Run end-to-end on the Phase 1 batch.
- Tune `min_eye_px` and sharpness thresholds against what survives.

**Phase 3 — Crop + export.**
- Implement crop stage producing the three sizes.
- Read `selfeyes/html/script.js` to confirm gallery manifest format.
- Emit `manifest.json` + `credits.html`.
- Manually integrate output into a local copy of the gallery; visually verify.

**Phase 4 — Institutional sources.**
- Implement `sources/loc.py`, `sources/nypl.py`, `sources/smithsonian.py`.
- All three have JSON APIs with public-domain filtering. Same downstream
  pipeline.

**Phase 5 — Curation UX.**
- Simple local Flask app: show pending candidates with their three crops,
  metadata, and reflection score. Approve/reject buttons; optional caption
  field. Approved items go into the published manifest.
- This human-in-the-loop step is where the artistic value lives — what's
  *visible* in the reflection is the curatorial decision and should be written
  by a human, not generated.

## Explicitly out of scope

- Dynamic / server-rendered gallery
- Anything resembling a public web service
- Face recognition, face matching, face clustering, person identification
- Storing biometric data of any kind
- Scraping any source other than via its documented public API
- Sources beyond what's listed
- ML model training or fine-tuning

## Things to decide as we iterate

- Whether to add a sunglasses-specific classifier in a later phase. Sunglasses
  yield the best reflections; tag-based filtering on Flickr (`sunglasses`,
  `aviators`) is a cheap start.
- Pet detection: mediapipe Face Mesh is human-only. For the animal series,
  options are (a) rely on tag-based discovery + manual review, or (b) add a
  small pet-eye detector. Defer to a later phase.
- Takedown flow: even though everything is licensed, offering a "remove this"
  contact link on the credits page reflects the project's ethics in its
  mechanics. Recommend adding.

## Configuration starter (`config.toml`)

```toml
[licenses]
flickr_allowed = [4, 5, 7, 8, 9, 10]
# Set true only if the gallery has a commercial dimension.
allow_non_commercial = false

[filters]
min_long_side_px = 2400
min_eye_px = 400
sharpness_min_variance = 100.0
tag_blocklist = [
  "baby", "babies", "infant", "toddler",
  "child", "children", "kid", "kids", "school", "classroom",
]

[flickr]
search_terms = [
  "selfie portrait",
  "self portrait",
  "sunglasses portrait",
  "aviators portrait",
  "mirror selfie",
  "mirror reflection portrait",
  "dog portrait close-up",
  "cat portrait close-up",
  "pet eyes",
  "horse eye macro",
]
include_commons = true
per_page = 500
max_pages_per_term = 4

[paths]
cache_dir = "data/cache"
crops_dir = "data/crops"
manifest_db = "data/manifest.sqlite"
export_dir = "../selfeyes/html/items"
manifest_json = "../selfeyes/html/manifest.json"
credits_html = "../selfeyes/html/credits.html"
```

## Acceptance criteria

The pipeline is "done" for Phase 3 when:

1. `python -m selfeyes_pipeline discover flickr` populates the `candidates`
   table with hundreds of correctly-licensed Flickr photos.
2. `python -m selfeyes_pipeline process` runs all stages and produces eye crops
   on disk and rows in the `eyes` table.
3. `python -m selfeyes_pipeline export` produces a `manifest.json` and
   `credits.html` that the existing gallery loads without modification (beyond
   pointing it at the new manifest).
4. Every item in the published manifest carries valid attribution.
5. No facial recognition library is imported anywhere in the codebase. Grep for
   `face_recognition`, `deepface`, `arcface`, `facenet` returns nothing.
6. The README documents the no-recognition stance.
