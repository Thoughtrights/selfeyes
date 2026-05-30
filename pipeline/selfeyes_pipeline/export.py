"""Export approved eyes to html/manifest.json."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from .store import Store


def promote_approved(store: Store, cfg: dict) -> int:
    """Append all approved eyes to manifest.json. Returns count of new items added."""
    manifest_path = Path(cfg["paths"]["manifest_json"])
    output_dir = Path(cfg["paths"]["output_dir"])

    # Load existing manifest
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
    else:
        manifest = {"version": 1, "items": []}

    existing_ids = {item.get("id") for item in manifest.get("items", []) if "id" in item}

    approved = store.get_approved_eyes()
    added = 0

    for eye in approved:
        if eye["id"] in existing_ids:
            continue  # already in manifest

        face_src = Path(eye["face_crop_path"])
        eye_src = Path(eye["eye_crop_path"])

        # Copy crops to html/assets/pipeline/ if not already there
        face_dest = output_dir / face_src.name
        eye_dest = output_dir / eye_src.name
        output_dir.mkdir(parents=True, exist_ok=True)

        if face_src.exists() and not face_dest.exists():
            shutil.copy2(face_src, face_dest)
        if eye_src.exists() and not eye_dest.exists():
            shutil.copy2(eye_src, eye_dest)

        # Path relative to html/ for the manifest
        rel_face = "assets/pipeline/" + face_dest.name
        rel_eye = "assets/pipeline/" + eye_dest.name

        item = {
            "id": eye["id"],
            "src": rel_face,
            "zoom": rel_eye,
            "alt": eye["caption"] or "",
            "attribution": {
                "photographer": eye["photographer"],
                "source_url": eye["source_page_url"],
                "license": eye["license_name"],
                "license_url": eye["license_url"],
            },
        }
        manifest["items"].append(item)
        existing_ids.add(eye["id"])
        added += 1

    if added > 0:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"  [export] added {added} item(s) to {manifest_path}")
    else:
        print("  [export] no new approved items to add.")

    return added
