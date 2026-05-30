"""Flickr discovery source.

Uses the Flickr REST API (authenticated with a Pro API key) to search for
portrait photos under permissive licenses and yield CandidateRecord objects.

No face recognition is performed here or anywhere in this codebase.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

import requests

from .base import CandidateRecord, Source

FLICKR_API = "https://www.flickr.com/services/rest/"

LICENSE_NAMES = {
    4: ("CC BY 2.0", "https://creativecommons.org/licenses/by/2.0/"),
    5: ("CC BY-SA 2.0", "https://creativecommons.org/licenses/by-sa/2.0/"),
    7: ("No known copyright restrictions", "https://www.flickr.com/commons/usage/"),
    8: ("U.S. Government Work", "https://www.usa.gov/government-works"),
    9: ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    10: ("Public Domain Mark 1.0", "https://creativecommons.org/publicdomain/mark/1.0/"),
}


class FlickrSource(Source):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.api_key = cfg["flickr"].get("api_key", "")
        self.fcfg = cfg["flickr"]
        self.filters = cfg.get("filters", {})
        self.allowed_licenses = set(cfg.get("licenses", {}).get("flickr_allowed", [4, 5, 7, 8, 9, 10]))
        self.tag_blocklist = set(self.filters.get("tag_blocklist", []))
        self.min_long_side = self.filters.get("min_long_side_px", 2400)
        self.cache_dir = Path(cfg["paths"]["cache_dir"]) / "api" / "flickr"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _call(self, method: str, params: dict, retries: int = 5) -> dict:
        params = {
            "method": method,
            "api_key": self.api_key,
            "format": "json",
            "nojsoncallback": "1",
            **params,
        }
        delay = 1.0
        for attempt in range(retries):
            try:
                r = requests.get(FLICKR_API, params=params, timeout=30)
                if r.status_code == 429:
                    print(f"  [flickr] rate limited, waiting {delay:.0f}s…")
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                r.raise_for_status()
                data = r.json()
                if data.get("stat") == "fail":
                    code = data.get("code", 0)
                    if code == 105:  # service unavailable
                        time.sleep(delay)
                        delay = min(delay * 2, 60)
                        continue
                    raise RuntimeError(f"Flickr API error {code}: {data.get('message')}")
                return data
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise
                print(f"  [flickr] request error: {e}; retrying…")
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise RuntimeError("Flickr API: max retries exceeded")

    def _passes_filter(self, photo: dict) -> bool:
        license_id = int(photo.get("license", 0))
        if license_id not in self.allowed_licenses:
            return False
        # Note: safe_search=1 in the query already ensures safe results;
        # safety_level in the extras response is often "0" (unset by owner)
        # even for genuinely safe photos, so we do NOT filter on it here.
        tags = {t.lower() for t in photo.get("tags", "").split()}
        if tags & self.tag_blocklist:
            return False
        return True

    def discover(self) -> Iterator[CandidateRecord]:
        search_terms = self.fcfg.get("search_terms", [])
        per_page = min(self.fcfg.get("per_page", 500), 500)
        max_pages = self.fcfg.get("max_pages_per_term", 4)
        include_commons = self.fcfg.get("include_commons", True)
        seen: set[str] = set()

        def _search_params(term: str, page: int, is_commons: bool) -> dict:
            p: dict = {
                "text": term,
                "license": ",".join(str(x) for x in sorted(self.allowed_licenses)),
                "extras": "license,owner_name,date_taken,url_o,o_dims,url_l,url_k,width_l,height_l,tags,description,safety_level",
                "media": "photos",
                "content_types": "0",
                "safe_search": "1",
                "per_page": str(per_page),
                "page": str(page),
            }
            if is_commons:
                p["is_commons"] = "1"
            return p

        for term in search_terms:
            for is_commons in ([False, True] if include_commons else [False]):
                label = f"[commons] {term}" if is_commons else term
                print(f"  [flickr] searching: {label!r}")
                for page in range(1, max_pages + 1):
                    data = self._call("flickr.photos.search", _search_params(term, page, is_commons))
                    photos = data.get("photos", {})
                    items = photos.get("photo", [])
                    if not items:
                        break

                    cache_path = self.cache_dir / f"{term.replace(' ','_')}_p{page}_commons{int(is_commons)}.json"
                    cache_path.write_text(json.dumps(data, indent=2))

                    for photo in items:
                        pid = photo.get("id", "")
                        if pid in seen:
                            continue
                        seen.add(pid)

                        if not self._passes_filter(photo):
                            continue

                        license_id = int(photo.get("license", 0))
                        lic_name, lic_url = LICENSE_NAMES.get(license_id, ("Unknown", ""))

                        # Prefer original > 2k ("k") > large
                        best_url = (photo.get("url_o")
                                    or photo.get("url_k")
                                    or photo.get("url_l")
                                    or "")

                        yield CandidateRecord(
                            id=f"flickr-{pid}",
                            source="flickr",
                            original_url=best_url,
                            source_page_url=f"https://www.flickr.com/photos/{photo.get('owner','')}/{pid}",
                            photographer=photo.get("owner_name", "Unknown"),
                            license_name=lic_name,
                            license_url=lic_url,
                            width_px=int(photo.get("width_o", 0)),
                            height_px=int(photo.get("height_o", 0)),
                            tags=photo.get("tags", "").split(),
                            date_taken=photo.get("datetaken"),
                            description=photo.get("description", {}).get("_content", "") if isinstance(photo.get("description"), dict) else "",
                        )

                    total_pages = int(photos.get("pages", 1))
                    if page >= total_pages:
                        break
                    time.sleep(0.3)  # polite delay between pages
