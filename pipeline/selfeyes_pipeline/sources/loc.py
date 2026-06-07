"""Library of Congress discovery source.

Uses the loc.gov search JSON API (no key required).
All results are U.S. Government Work or explicitly public domain.
"""
from __future__ import annotations

import re
import time
from typing import Iterator
from urllib.parse import urlencode

import requests

from .base import CandidateRecord, Source

LOC_SEARCH = "https://www.loc.gov/search/"
LOC_LICENSE_NAME = "U.S. Government Work / Public Domain"
LOC_LICENSE_URL = "https://www.usa.gov/government-works"


class LocSource(Source):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.lcfg = cfg.get("loc", {})
        self.filters = cfg.get("filters", {})
        self.min_long_side = self.filters.get("min_long_side_px", 2400)
        self.tag_blocklist = set(self.filters.get("tag_blocklist", []))

    def _fetch_page(self, term: str, page: int, count: int) -> dict:
        params = {
            "q": term,
            "fo": "json",
            "c": count,
            "sp": page,
            "fa": "online-format:image",
        }
        url = f"{LOC_SEARCH}?{urlencode(params)}"
        for attempt in range(4):
            try:
                r = requests.get(url, timeout=30, headers={"User-Agent": "selfeyes-pipeline/0.1"})
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                if attempt == 3:
                    raise
                wait = 2 ** attempt
                print(f"  [loc] request error: {e}; retrying in {wait}s…")
                time.sleep(wait)
        return {}

    def _best_image_url(self, item: dict) -> str | None:
        """Return the highest-resolution image URL available."""
        urls: list[str] = item.get("image_url", [])
        # LoC lists sizes ascending; last is largest
        for url in reversed(urls):
            if url.startswith("http"):
                return url
        return None

    def discover(self) -> Iterator[CandidateRecord]:
        search_terms = self.lcfg.get("search_terms", [])
        max_pages = self.lcfg.get("max_pages_per_term", 3)
        count = self.lcfg.get("results_per_page", 50)
        seen: set[str] = set()

        for term in search_terms:
            print(f"  [loc] searching: {term!r}")
            for page in range(1, max_pages + 1):
                data = self._fetch_page(term, page, count)
                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    item_id = item.get("id", "")
                    uid = f"loc-{item_id.strip('/').replace('/', '-')}"
                    if uid in seen:
                        continue
                    seen.add(uid)

                    # Skip non-image online formats
                    formats = item.get("online_format", [])
                    if "image" not in [f.lower() for f in formats]:
                        continue

                    # Skip access-restricted items
                    if item.get("access_restricted", False):
                        continue

                    image_url = self._best_image_url(item)
                    if not image_url:
                        continue

                    # Tag blocklist — whole-word match to avoid false positives
                    subjects = " ".join(item.get("subject", [])).lower()
                    title = (item.get("title") or "").lower()
                    combined_words = set(re.findall(r"[a-z]+", subjects + " " + title))
                    if combined_words & self.tag_blocklist:
                        continue

                    # Attribution
                    contributors = item.get("contributor", []) or item.get("creator", [])
                    photographer = contributors[0] if contributors else "Library of Congress"
                    source_page = item.get("url", f"https://www.loc.gov{item_id}")

                    yield CandidateRecord(
                        id=uid,
                        source="loc",
                        original_url=image_url,
                        source_page_url=source_page,
                        photographer=photographer,
                        license_name=LOC_LICENSE_NAME,
                        license_url=LOC_LICENSE_URL,
                        width_px=0,   # LoC metadata doesn't include pixel dims; checked after download
                        height_px=0,
                        tags=item.get("subject", []),
                        date_taken=item.get("date", None),
                        description=item.get("description", [""])[0] if item.get("description") else "",
                    )

                pagination = data.get("pagination", {})
                if not pagination.get("next"):
                    break
                time.sleep(0.5)
