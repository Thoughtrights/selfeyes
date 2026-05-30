"""Load configuration from config.toml + environment variables."""
from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.version_info >= (3, 12):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

from dotenv import load_dotenv

# Resolve paths relative to the pipeline/ directory regardless of cwd
PIPELINE_DIR = Path(__file__).parent.parent
CONFIG_FILE = PIPELINE_DIR / "config.toml"


def load() -> dict:
    """Return merged config dict with env vars injected where relevant."""
    load_dotenv(PIPELINE_DIR / ".env")

    with open(CONFIG_FILE, "rb") as f:
        cfg = tomllib.load(f)

    # Inject API keys from env
    flickr_key = os.environ.get("FLICKR_API_KEY")
    flickr_secret = os.environ.get("FLICKR_API_SECRET")
    if flickr_key:
        cfg.setdefault("flickr", {})["api_key"] = flickr_key
    if flickr_secret:
        cfg.setdefault("flickr", {})["api_secret"] = flickr_secret

    si_key = os.environ.get("SMITHSONIAN_API_KEY")
    if si_key:
        cfg.setdefault("smithsonian", {})["api_key"] = si_key

    # Resolve relative paths to absolute, anchored at pipeline/
    p = cfg.setdefault("paths", {})
    for key in ("cache_dir", "db_path", "output_dir", "manifest_json"):
        if key in p:
            resolved = (PIPELINE_DIR / p[key]).resolve()
            p[key] = str(resolved)

    return cfg
