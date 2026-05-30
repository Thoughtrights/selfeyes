"""Smithsonian Open Access discovery source.

Uses the Smithsonian Institution Open Access API.
Filters for CC0 / public domain items only.
API key required (free at https://api.si.edu).
"""
from __future__ import annotations

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

    def _extract_image_url(self, content: dict) -> str | None:
        """Drill into the Smithsonian content blob to find a usable image URL."""
        try:
            media_list = (
                content.get("descriptiveNonRepeating", {})
                .get("online_media", {})
                .get("media", [])
            )
            for media in media_list:
                if media.get("type") == "Images":
                    resources = media.get("resources", [])
                    # Pick the largest by label (LoC-style) or just first
                    for res in reversed(resources):
                        url = res.get("url", "")
                        if url.startswith("http"):
                            return url
                    url = media.get("content", "")
                    if url.startswith("http"):
                        return url
        except (KeyError, TypeError, IndexError):
            pass
        return None

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

                    # Only CC0 / public domain
                    usage = content.get("descriptiveNonRepeating", {}).get("media_usage", {}).get("access", "")
                    if "CC0" not in usage and "Public" not in usage:
                        continue

                    image_url = self._extract_image_url(content)
                    if not image_url:
                        continue

                    # Tag blocklist
                    desc_text = " ".join([
                        str(v) for v in content.get("freetext", {}).values()
                        if isinstance(v, (str, list))
                    ]).lower()
                    if any(blocked in desc_text for blocked in self.tag_blocklist):
                        continue

                    title = row.get("title", "")
                    source_page = (
                        content.get("descriptiveNonRepeating", {}).get("record_link", "")
                        or f"https://www.si.edu/object/{row.get('id','')}"
                    )
                    data_source = (
                        content.get("descriptiveNonRepeating", {}).get("data_source", "Smithsonian")
                    )

                    yield CandidateRecord(
                        id=uid,
                        source="smithsonian",
                        original_url=image_url,
                        source_page_url=source_page,
                        photographer=data_source,
                        license_name=SI_LICENSE_NAME,
                        license_url=SI_LICENSE_URL,
                        width_px=0,
                        height_px=0,
                        tags=[],
                        date_taken=None,
                        description=title,
                    )

                time.sleep(0.3)
