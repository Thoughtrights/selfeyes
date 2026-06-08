"""Selfeyes pipeline CLI.

Commands:
  discover   -- Search sources and populate the candidates table
  process    -- Download, detect, score, and crop candidates
  run        -- discover + process in one shot
  review     -- Launch the Flask curation UI
  stats      -- Print current pipeline statistics
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Optional

import typer
from tqdm import tqdm

from . import config as _config
from .sources import FlickrSource, LocSource, SmithsonianSource
from .store import Store
from .detect import detect_eyes
from .score import sharpness as calc_sharpness, reflection_score as calc_reflection, load_eye_crop_array
from .crop import make_face_crop, make_eye_crop

app = typer.Typer(help="Selfeyes ingestion pipeline")


def _get_store_and_cfg():
    cfg = _config.load()
    store = Store(cfg["paths"]["db_path"])
    return store, cfg


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── discover ──────────────────────────────────────────────────────────────

@app.command()
def discover(
    source: Optional[str] = typer.Option(None, "--source", "-s",
        help="Which source to run: flickr, loc, smithsonian. Omit for all."),
    max_pages: Optional[int] = typer.Option(None, "--max-pages",
        help="Override max_pages_per_term for this run."),
):
    """Search photo sources and store candidates in the database."""
    store, cfg = _get_store_and_cfg()

    if max_pages is not None:
        for key in ("flickr", "loc", "smithsonian"):
            cfg.setdefault(key, {})["max_pages_per_term"] = max_pages
            cfg.setdefault(key, {})["max_requests_per_term"] = max_pages

    sources_to_run = []
    if source in (None, "flickr"):
        if cfg.get("flickr", {}).get("api_key"):
            sources_to_run.append(("flickr", FlickrSource(cfg)))
        else:
            typer.echo("  [flickr] FLICKR_API_KEY not set — skipping.")
    if source in (None, "loc"):
        sources_to_run.append(("loc", LocSource(cfg)))
    if source in (None, "smithsonian"):
        si_key = cfg.get("smithsonian", {}).get("api_key")
        if si_key:
            sources_to_run.append(("smithsonian", SmithsonianSource(cfg)))
        else:
            typer.echo("  [smithsonian] SMITHSONIAN_API_KEY not set — skipping.")

    total = 0
    for name, src in sources_to_run:
        typer.echo(f"\n── Discovering from {name} ──")
        count = 0
        for rec in src.discover():
            store.upsert_candidate(rec)
            count += 1
        typer.echo(f"  [{name}] {count} candidates stored.")
        total += count

    typer.echo(f"\nTotal new candidates this run: {total}")
    s = store.stats()
    typer.echo(f"DB totals: {s['candidates']} candidates, {s['downloaded']} downloaded, {s['eyes']} eyes")


# ── process ───────────────────────────────────────────────────────────────

@app.command()
def process(
    limit: Optional[int] = typer.Option(None, "--limit", "-n",
        help="Process at most N candidates (useful for test runs)."),
    source: Optional[str] = typer.Option(None, "--source", "-s",
        help="Only process candidates from this source: flickr, loc, smithsonian."),
    reprocess: bool = typer.Option(False, "--reprocess",
        help="Re-run detection on already-downloaded images that have no eyes yet."),
):
    """Download, detect, score, and crop all pending candidates."""
    import requests as req

    store, cfg = _get_store_and_cfg()
    filters = cfg.get("filters", {})
    crop_cfg = cfg.get("crop", {})
    min_eye_px = filters.get("min_eye_px", 200)
    min_long_side = filters.get("min_long_side_px", 2400)
    sharpness_min = filters.get("sharpness_min_variance", 100.0)
    output_dir = Path(cfg["paths"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    if reprocess:
        with store._conn() as conn:
            q = """
                SELECT * FROM candidates
                WHERE local_path IS NOT NULL
                AND id NOT IN (SELECT DISTINCT candidate_id FROM eyes)
            """
            params = []
            if source:
                q += " AND source = ?"
                params.append(source)
            q += " ORDER BY MAX(width_px, height_px) DESC"
            rows = conn.execute(q, params).fetchall()
        candidates = rows
        label = f"{source} " if source else ""
        typer.echo(f"\n── Re-processing {len(candidates)} already-downloaded {label}candidates ──")
    else:
        with store._conn() as conn:
            q = "SELECT * FROM candidates WHERE local_path IS NULL AND original_url != ''"
            params = []
            if source:
                q += " AND source = ?"
                params.append(source)
            q += " ORDER BY MAX(width_px, height_px) DESC, id"
            candidates = conn.execute(q, params).fetchall()
        label = f"{source} " if source else ""
        typer.echo(f"\n── Processing {len(candidates)} {label}candidates ──")

    if limit:
        candidates = candidates[:limit]

    typer.echo(f"\n── Processing {len(candidates)} candidates ──")

    for cand in tqdm(candidates, unit="photo"):
        cid = cand["id"]
        url = cand["original_url"]
        if not url:
            continue

        # ── Download (skip if already cached) ─────────────────────────────
        existing_path = cand["local_path"]
        if existing_path and Path(existing_path).exists():
            local_path = Path(existing_path)
        else:
            ext = url.split(".")[-1].split("?")[0].lower() or "jpg"
            source_name = cand["source"]
            cache_dir = Path(cfg["paths"]["cache_dir"]) / source_name
            cache_dir.mkdir(parents=True, exist_ok=True)
            local_path = cache_dir / f"{cid}.{ext}"

            if not local_path.exists():
                downloaded = False
                delay = 5.0
                for attempt in range(5):
                    try:
                        r = req.get(url, timeout=60, headers={"User-Agent": "selfeyes-pipeline/0.1"})
                        if r.status_code == 429:
                            tqdm.write(f"  [download] 429 rate-limited, waiting {delay:.0f}s…")
                            time.sleep(delay)
                            delay = min(delay * 2, 120)
                            continue
                        r.raise_for_status()
                        local_path.write_bytes(r.content)
                        time.sleep(1.2)  # polite delay between downloads
                        downloaded = True
                        break
                    except Exception as e:
                        if attempt == 4:
                            tqdm.write(f"  [download] failed {cid}: {e}")
                        else:
                            time.sleep(delay)
                            delay = min(delay * 2, 60)
                if not downloaded:
                    continue

            sha = _sha256(str(local_path))
            store.set_downloaded(cid, str(local_path), sha)

        # ── Resolution check after download ───────────────────────────────
        try:
            from PIL import Image as _PILImage
            with _PILImage.open(str(local_path)) as _im:
                iw, ih = _im.size
            if max(iw, ih) < min_long_side:
                tqdm.write(f"  [process] {cid} too small ({iw}×{ih}) — skipping")
                continue
        except Exception:
            pass  # if we can't read dims, proceed and let detect fail

        # ── Detect ────────────────────────────────────────────────────────
        try:
            detections = detect_eyes(str(local_path), min_eye_px=min_eye_px)
        except Exception as e:
            tqdm.write(f"  [detect] failed {cid}: {e}")
            continue

        if not detections:
            continue

        # ── Score + Crop ───────────────────────────────────────────────────
        for det in detections:
            eye_id = f"{cid}-{det.side}"

            # Score on raw eye region
            arr = load_eye_crop_array(str(local_path), det.bbox)
            if arr is None:
                continue

            sharp = calc_sharpness(arr)
            if sharp < sharpness_min:
                continue  # drop blurry

            refl = calc_reflection(arr)

            # Crop files
            face_path = output_dir / f"{cid}_{det.side}_face.jpg"
            eye_path  = output_dir / f"{cid}_{det.side}_eye.jpg"

            make_face_crop(
                str(local_path), det.face_bbox, str(face_path),
                pad_pct=crop_cfg.get("face_padding_pct", 0.15),
                longest_side_px=crop_cfg.get("face_longest_side_px", 1400),
                jpeg_quality=crop_cfg.get("jpeg_quality_face", 88),
            )
            make_eye_crop(
                str(local_path), det.bbox, str(eye_path),
                pad_pct=crop_cfg.get("eye_padding_pct", 0.40),
                jpeg_quality=crop_cfg.get("jpeg_quality_eye", 92),
            )

            # Compute perceptual hash of face crop for similarity detection
            phash_str = ""
            try:
                import imagehash as _ih  # noqa: PLC0415
                from PIL import Image as _PI  # noqa: PLC0415
                phash_str = str(_ih.phash(_PI.open(str(face_path)).convert("RGB")))
            except Exception:
                pass

            store.upsert_eye(
                eye_id=eye_id,
                candidate_id=cid,
                side=det.side,
                bbox=det.bbox,
                face_bbox=det.face_bbox,
                sharpness=sharp,
                reflection_score=refl,
                face_crop_path=str(face_path),
                eye_crop_path=str(eye_path),
                phash=phash_str,
            )

    s = store.stats()
    typer.echo(f"\nDone. Eyes in DB: {s['eyes']} | Pending review: {s['pending']}")


# ── run ───────────────────────────────────────────────────────────────────

@app.command()
def run(
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    max_pages: Optional[int] = typer.Option(None, "--max-pages"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n"),
):
    """Discover + process in one shot."""
    ctx = typer.get_current_context()
    ctx.invoke(discover, source=source, max_pages=max_pages)
    ctx.invoke(process, limit=limit)


# ── review ────────────────────────────────────────────────────────────────

@app.command()
def review(
    port: int = typer.Option(5050, "--port"),
    host: str = typer.Option("127.0.0.1", "--host"),
):
    """Launch the Flask curation UI at http://localhost:5050."""
    from .review import create_app as make_flask_app

    store, cfg = _get_store_and_cfg()
    flask_app = make_flask_app(store, cfg)
    typer.echo(f"\nSelfeyes Review UI → http://{host}:{port}\n")
    flask_app.run(host=host, port=port, debug=False)


# ── stats ─────────────────────────────────────────────────────────────────

@app.command()
def rehash():
    """Compute/update perceptual hashes for all existing face crops."""
    import imagehash as _ih
    from PIL import Image as _PI

    store, _ = _get_store_and_cfg()
    with store._conn() as conn:
        rows = conn.execute(
            "SELECT id, face_crop_path FROM eyes WHERE face_crop_path IS NOT NULL"
        ).fetchall()

    typer.echo(f"\n── Computing pHash for {len(rows)} eye crops ──")
    updated = 0
    for row in tqdm(rows, unit="crop"):
        path = row["face_crop_path"]
        if not path or not Path(path).exists():
            continue
        try:
            h = str(_ih.phash(_PI.open(path).convert("RGB")))
            with store._conn() as conn:
                conn.execute("UPDATE eyes SET phash=? WHERE id=?", (h, row["id"]))
            updated += 1
        except Exception as e:
            tqdm.write(f"  [rehash] {row['id']}: {e}")

    typer.echo(f"Done. {updated} hashes computed.")


@app.command()
def stats():
    """Print current pipeline statistics."""
    store, _ = _get_store_and_cfg()
    s = store.stats()
    typer.echo(f"""
Pipeline stats
──────────────────────────────
  Candidates discovered : {s['candidates']}
  Downloaded            : {s['downloaded']}
  Eyes detected         : {s['eyes']}
  Pending review        : {s['pending']}
  Approved              : {s['approved']}
  Skipped               : {s['skipped']}
""")


if __name__ == "__main__":
    app()
