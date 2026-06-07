"""Smithsonian Open Access discovery source.

Uses the Smithsonian Institution Open Access API.
Filters for CC0 / public domain items only.
API key required (free at https://api.si.edu).
"""
from __future__ import annotations

import re
import time
from typing import Iterator

import requests

from .base import CandidateRecord, Source

SI_API = "https://api.si.edu/openaccess/api/v1.0/search"
SI_LICENSE_NAME = "CC0 1.0 / Public Domain"
SI_LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"


class SmithsonianSource(Source):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.scfg = cfg.get("smithsonian", {})
        self.api_key = self.scfg.get("api_key", "")
        self.filters = cfg.get("filters", {})
        self.tag_blocklist = set(self.filters.get("tag_blocklist", []))

    def _fetch(self, term: str, start: int, rows: int) -> dict:
        if not self.api_key:
            raise RuntimeError("SMITHSONIAN_API_KEY not set. Register free at https://api.si.edu.")
        params = {
            "q": term,
            "start": start,
            "rows": rows,
            "api_key": self.api_key,
        }
        for attempt in range(4):
            try:
                r = requests.get(SI_API, params=params, timeout=30)
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                if attempt == 3:
                    raise
                wait = 2 ** attempt
                print(f"  [smithsonian] request error: {e}; retrying in {wait}s…")
                time.sleep(wait)
        return {}

    def _best_image(self, media: dict) -> tuple[str, int, int]:
        """Return (url, width, height) for the best available JPEG resource."""
        # Prefer high-res JPEG from resources list
        resources = media.get("resources", [])
        best_url, best_w, best_h = "", 0, 0
        for res in resources:
            url = res.get("url", "")
            w = res.get("width", 0) or 0
            h = res.get("height", 0) or 0
            label = res.get("label", "").lower()
            if not url.startswith("http"):
                continue
            # Prefer JPEG over TIFF (TIFF can be enormous)
            if "tiff" in label or url.endswith(".tif"):
                continue
            if max(w, h) > max(best_w, best_h):
                best_url, best_w, best_h = url, w, h
        if best_url:
            return best_url, best_w, best_h
        # Fall back to content URL
        content_url = media.get("content", "")
        return (content_url, 0, 0) if content_url.startswith("http") else ("", 0, 0)

    def discover(self) -> Iterator[CandidateRecord]:
        if not self.api_key:
            print("  [smithsonian] SMITHSONIAN_API_KEY not set — skipping.")
            return

        search_terms = self.scfg.get("search_terms", [])
        rows = self.scfg.get("rows_per_request", 100)
        max_requests = self.scfg.get("max_requests_per_term", 3)
        seen: set[str] = set()

        for term in search_terms:
            print(f"  [smithsonian] searching: {term!r}")
            for req_num in range(max_requests):
                start = req_num * rows
                data = self._fetch(term, start, rows)
                rows_data = data.get("response", {}).get("rows", [])
                if not rows_data:
                    break

                for row in rows_data:
                    uid = f"smithsonian-{row.get('id','unknown')}"
                    if uid in seen:
                        continue
                    seen.add(uid)

                    content = row.get("content", {})
                    dnr = content.get("descriptiveNonRepeating", {})
                    media_list = dnr.get("online_media", {}).get("media", [])

                    # Find first image media with CC0 usage
                    image_url, width_px, height_px = "", 0, 0
                    for media in media_list:
                        if media.get("type") != "Images":
                            continue
                        # CC0 check lives in media[].usage.access
                        access = media.get("usage", {}).get("access", "")
                        if "CC0" not in access and "Public" not in access:
                            continue
                        url, w, h = self._best_image(media)
                        if url:
                            image_url, width_px, height_px = url, w, h
                            break

                    if not image_url:
                        continue

                    # Tag/description blocklist — whole-word match only to avoid
                    # false positives (e.g. "ai" inside "portrait")
                    desc_text = " ".join([
                        str(v) for v in content.get("freetext", {}).values()
                        if isinstance(v, (str, list))
                    ]).lower()
                    desc_words = set(re.findall(r"[a-z]+", desc_text))
                    if desc_words & self.tag_blocklist:
                        continue

                    title = row.get("title", "")
                    source_page = (
                        dnr.get("record_link", "")
                        or f"https://www.si.edu/object/{row.get('id','')}"
                    )
                    data_source = dnr.get("data_source", "Smithsonian")

                    yield CandidateRecord(
                        id=uid,
                        source="smithsonian",
                        original_url=image_url,
                        source_page_url=source_page,
                        photographer=data_source,
                        license_name=SI_LICENSE_NAME,
                        license_url=SI_LICENSE_URL,
                        width_px=width_px,
                        height_px=height_px,
                        tags=[],
                        date_taken=None,
                        description=title,
                    )

                time.sleep(0.3)
