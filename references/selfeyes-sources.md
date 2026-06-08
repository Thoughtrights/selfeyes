# Selfeyes Photo Sources Reference

How to understand, tune, and extend the photo sources used by the ingestion pipeline.

---

## License compatibility

Only these licenses are accepted. Enforced in code; never relax this without legal review.

| License | Flickr ID | Gallery use | Attribution required |
|---|---|---|---|
| CC BY 2.0 / 3.0 / 4.0 | 4 | ✓ | Yes |
| CC BY-SA 2.0 / 3.0 / 4.0 | 5 | ✓ | Yes |
| CC0 (No Rights Reserved) | 9 | ✓ | Recommended |
| Public Domain Mark | 10 | ✓ | Recommended |
| U.S. Government Work | 8 | ✓ | Recommended |
| CC BY-NC / CC BY-ND | — | ✗ blocked | — |
| All Rights Reserved | — | ✗ blocked | — |

> `allow_non_commercial = false` in `config.toml`. Set to `true` only if the gallery never has commercial dimensions (print sales, ad revenue, sponsored content).

---

## Existing sources

### Flickr
- **Module**: `pipeline/selfeyes_pipeline/sources/flickr.py`
- **API**: `flickr.photos.search` REST
- **Credentials**: `FLICKR_API_KEY` + `FLICKR_API_SECRET` in `pipeline/.env`
  Register free at https://www.flickr.com/services/apps/create/
- **Rate limits**: ~3,600 req/hour; pipeline uses 1.2s polite delay between downloads
- **Image URL preference**: `url_o` (original) → `url_k` (2048px) → `url_l` (1024px)
- **Key config** (`config.toml [flickr]`):
  - `search_terms` — list of query strings; one paginated API call per term
  - `max_pages_per_term` — cap per term (currently 10 × 500/page = up to 5,000 per term)
  - `include_commons = true` — includes Flickr Commons (public domain museum photos)

**Notes:**
- `content_type=1` limits to photos only (not video, not "other")
- `safe_search=1` handles adult content; do not add a `safety_level` filter
- Tags are normalised (hyphens/underscores stripped) before blocklist comparison
- Resolution filter applied post-download (not in API) because Flickr metadata is unreliable

---

### Library of Congress (LoC)
- **Module**: `pipeline/selfeyes_pipeline/sources/loc.py`
- **API**: `https://www.loc.gov/search/?q=<term>&fo=json`
- **Credentials**: None required
- **License**: All results are U.S. Government Work (public domain)
- **Image URL**: `item.image_url[-1]` — LoC returns sizes ascending; last is largest
- **Key config** (`config.toml [loc]`):
  - `search_terms` — plain text queries; works well with descriptive historical terms
  - `max_pages_per_term`, `results_per_page` (max 50 per page)
- **Blocklist matching**: whole-word (`re.findall(r"[a-z]+", ...)`) to avoid
  substring false positives (e.g. "ai" inside "portrait")

**Good search terms for LoC:**
- `"daguerreotype portrait face"` — 19th-century close-up portraits
- `"tintype portrait face"` — Civil War era, often very detailed irises
- `"portrait face closeup photograph"` — 20th-century photographic prints
- `"photograph eyes face"` — direct eye-contact portraits

**Notes:**
- LoC collections include Farm Security Administration (FSA) photographs, which
  are exceptionally high resolution and feature intense eye contact
- Response format: `results[].image_url` is a list of URLs ordered by size

---

### Smithsonian Open Access
- **Module**: `pipeline/selfeyes_pipeline/sources/smithsonian.py`
- **API**: `https://api.si.edu/openaccess/api/v1.0/search`
- **Credentials**: `SMITHSONIAN_API_KEY` in `pipeline/.env`
  Register free at https://api.si.edu (takes ~2 minutes)
- **License**: CC0 only; checked in `media[0].usage.access` field
- **Image URL**: parsed from `media[0].resources[]` array — filters out TIFFs,
  picks highest-resolution JPEG
- **Key config** (`config.toml [smithsonian]`):
  - `search_terms` — use `unit_code:XXX` prefix to target specific museums
  - `rows_per_request`, `max_requests_per_term`

**Museum unit codes for portraits:**
| Code | Museum |
|---|---|
| `NPG` | National Portrait Gallery |
| `NMAAHC` | African American History & Culture |
| `NMAH` | American History |
| `SAAM` | American Art Museum |
| `NMNH` | Natural History (for ethnographic portraits) |

**Example search terms:**
```toml
search_terms = [
  "unit_code:NPG portrait photograph",
  "unit_code:NPG daguerreotype",
  "unit_code:NPG tintype",
  "unit_code:NMAAHC portrait photograph",
  "unit_code:SAAM portrait photograph",
]
```

---

## Planned sources

### DPLA (Digital Public Library of America)
- **API**: `https://api.dp.la/v2/items`
- **Credentials**: Free API key at https://dp.la/info/developers/codex/
- **License**: Filter on `sourceResource.rights` for CC0/public domain strings
- **Image URL**: `object` field or `hasView[0].@id`
- **Why useful**: Aggregates 4,000+ US libraries and archives; strong historical
  portrait collections from institutions not on Flickr or Smithsonian
- **Module to create**: `pipeline/selfeyes_pipeline/sources/dpla.py`
- **Suggested search terms**: `"portrait photograph face"`, `"daguerreotype"`,
  `"tintype portrait"`, `"photograph eyes"`
- **Rate limit**: 100 req/hour without key; 1,000/hour with free key

### Wikimedia Commons
- **API**: `https://commons.wikimedia.org/w/api.php`
- **Credentials**: None for read-only
- **License**: Filter for CC0, CC-BY, CC-BY-SA, PD-old
- **Image URL**: `imageinfo[0].url` from `action=query&prop=imageinfo`
- **Why useful**: Enormous collection; well-tagged portrait categories; includes
  many CC-licensed contemporary portrait photographers
- **Module to create**: `pipeline/selfeyes_pipeline/sources/wikimedia.py`
- **Good categories to query**:
  - `Category:Portrait_photographs`
  - `Category:Photographs_of_eyes`
  - `Category:Macro_photographs_of_eyes`
  - `Category:Close-up_photographs_of_human_faces`
- **Caveat**: Illustrations and digital art are common on Commons; the tag blocklist
  must be aggressive, and `mime` type should be filtered to `image/jpeg`
- **Rate limit**: 200 req/min without authentication

---

## Adding a new source

### 1. Create the source module

```python
# pipeline/selfeyes_pipeline/sources/mysource.py
from __future__ import annotations
import re
from typing import Iterator
from .base import Source, CandidateRecord

class MySource(Source):
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg.get("mysource", {})
        self.search_terms = self.cfg.get("search_terms", [])
        # load tag blocklist for whole-word matching
        raw = cfg.get("filters", {}).get("tag_blocklist", [])
        self.tag_blocklist = set(raw)

    def discover(self) -> Iterator[CandidateRecord]:
        for term in self.search_terms:
            yield from self._search(term)

    def _is_blocked(self, text: str) -> bool:
        words = set(re.findall(r"[a-z]+", text.lower()))
        return bool(words & self.tag_blocklist)

    def _search(self, term: str) -> Iterator[CandidateRecord]:
        # ... paginated API calls ...
        for item in results:
            if self._is_blocked(item.get("tags", "") + " " + item.get("title", "")):
                continue
            yield CandidateRecord(
                id=f"mysource-{item['id']}",
                source="myource",
                original_url=item["image_url"],
                source_page_url=item["page_url"],
                photographer=item.get("creator", ""),
                license_name="CC0",
                license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                width_px=item.get("width", 0),
                height_px=item.get("height", 0),
                tags=item.get("tags", []),
                date_taken=item.get("date", None),
                description=item.get("description", ""),
            )
```

### 2. Register in `__init__.py`

```python
# pipeline/selfeyes_pipeline/sources/__init__.py
from .myource import MySource
```

### 3. Register in `cli.py`

In both `discover()` and `process()`:
```python
if source in (None, "myource"):
    sources_to_run.append(("myource", MySource(cfg)))
```

### 4. Add config section

```toml
# pipeline/config.toml
[myource]
search_terms = ["portrait face", "eye closeup"]
max_requests_per_term = 5
```

### 5. Test

```bash
python -m selfeyes_pipeline discover --source myource --max-pages 1
python -m selfeyes_pipeline stats
```

---

## Tag blocklist rationale

The blocklist (`config.toml [filters] tag_blocklist`) uses **whole-word matching**
via `re.findall(r"[a-z]+", text)` — this prevents "ai" from matching "portrait"
(which contains "ai") while still catching `#AIArt`.

### Blocklist categories

| Category | Example tags | Reason |
|---|---|---|
| Minors | baby, infant, child, kid | Legal and ethical protection |
| AI-generated | midjourney, stablediffusion, dalle | Photos only; AI irises look wrong |
| Illustration | illustration, drawing, painting | Not photographs |
| Digital art | digitalart, 3drender, cgi, blender | Not photographs |
| Soft filters | anime, cartoon, vector | Not photographs |

### Adding new blocklist entries

Edit `config.toml` → `[filters] tag_blocklist`. Then re-run discovery to reclassify:
```bash
python -m selfeyes_pipeline discover --source flickr
```
Already-downloaded candidates are not re-evaluated by blocklist unless you delete
and re-discover them.

---

## Search term strategy

**What works well:**
- Compound terms: `"face closeup portrait"` yields tighter crops than `"portrait"` alone
- Body part specificity: `"eye closeup"`, `"eyes macro"` surface relevant images
- Reflective surface terms: `"sunglasses reflection"`, `"cornea reflection"` are very targeted
- Historical format terms: `"daguerreotype"`, `"tintype"` yield pre-1930 portraits with
  large, detailed irises (film grain amplifies corneal texture)

**What generates noise:**
- Single broad terms (`"portrait"`, `"face"`) — most results have no useful eye detail
- Emotion terms (`"happy"`, `"smiling"`) — tend toward wide shots, not close-ups
- Occupation terms without "closeup" — `"nurse portrait"` yields many group shots

**Adding new terms:**
```toml
[flickr]
search_terms = [
  # ... existing terms ...
  "my new term",
]
```
Then: `python -m selfeyes_pipeline discover --source flickr`

Already-discovered photos are skipped (deduped by photo ID), so rediscovery is safe.
