"""SQLite storage for the selfeyes pipeline.

Tables:
  candidates   — one row per discovered photo that passed metadata filters
  eyes         — one row per surviving (candidate, side) pair after detection
  review       — one row per eye: status (pending|approved|skipped), caption
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    original_url    TEXT NOT NULL,
    source_page_url TEXT NOT NULL,
    photographer    TEXT,
    license_name    TEXT,
    license_url     TEXT,
    width_px        INTEGER,
    height_px       INTEGER,
    tags            TEXT,          -- JSON array
    date_taken      TEXT,
    description     TEXT,
    local_path      TEXT,          -- path to cached original, set after download
    sha256          TEXT,
    downloaded_at   TEXT,
    ingested_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS eyes (
    id              TEXT PRIMARY KEY,   -- e.g. "flickr-12345-left"
    candidate_id    TEXT NOT NULL REFERENCES candidates(id),
    side            TEXT NOT NULL,      -- "left" | "right"
    bbox_x          INTEGER,
    bbox_y          INTEGER,
    bbox_w          INTEGER,
    bbox_h          INTEGER,
    bbox_px_width   INTEGER,
    face_bbox_x     INTEGER,
    face_bbox_y     INTEGER,
    face_bbox_w     INTEGER,
    face_bbox_h     INTEGER,
    sharpness       REAL,
    reflection_score REAL,
    face_crop_path  TEXT,
    eye_crop_path   TEXT,
    phash           TEXT,          -- perceptual hash of face crop (hex)
    detected_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS review (
    eye_id      TEXT PRIMARY KEY REFERENCES eyes(id),
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending|approved|skipped
    caption     TEXT DEFAULT '',
    reviewed_at TEXT
);
"""


class Store:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            # Migrations — add columns that may not exist in older DBs
            for migration in [
                "ALTER TABLE eyes ADD COLUMN phash TEXT",
            ]:
                try:
                    conn.execute(migration)
                except Exception:
                    pass  # column already exists

    # ── Candidates ─────────────────────────────────────────────────────────

    def upsert_candidate(self, rec) -> None:
        """Insert or update a CandidateRecord."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO candidates
                    (id, source, original_url, source_page_url, photographer,
                     license_name, license_url, width_px, height_px, tags,
                     date_taken, description)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    original_url = excluded.original_url,
                    width_px = excluded.width_px,
                    height_px = excluded.height_px
            """, (
                rec.id, rec.source, rec.original_url, rec.source_page_url,
                rec.photographer, rec.license_name, rec.license_url,
                rec.width_px, rec.height_px,
                json.dumps(rec.tags), rec.date_taken, rec.description,
            ))

    def set_downloaded(self, candidate_id: str, local_path: str, sha256: str) -> None:
        with self._conn() as conn:
            conn.execute("""
                UPDATE candidates SET local_path=?, sha256=?, downloaded_at=datetime('now')
                WHERE id=?
            """, (local_path, sha256, candidate_id))

    def get_candidates_for_download(self) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute("""
                SELECT * FROM candidates
                WHERE local_path IS NULL AND original_url != ''
                ORDER BY MAX(width_px, height_px) DESC, id
            """).fetchall()

    def get_candidate(self, candidate_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()

    def get_downloaded_candidates(self) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute("""
                SELECT * FROM candidates WHERE local_path IS NOT NULL
            """).fetchall()

    # ── Eyes ───────────────────────────────────────────────────────────────

    def upsert_eye(self, eye_id: str, candidate_id: str, side: str,
                   bbox: tuple, face_bbox: tuple,
                   sharpness: float, reflection_score: float,
                   face_crop_path: str, eye_crop_path: str,
                   phash: str = "") -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO eyes
                    (id, candidate_id, side, bbox_x, bbox_y, bbox_w, bbox_h, bbox_px_width,
                     face_bbox_x, face_bbox_y, face_bbox_w, face_bbox_h,
                     sharpness, reflection_score, face_crop_path, eye_crop_path, phash)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    sharpness=excluded.sharpness,
                    reflection_score=excluded.reflection_score,
                    face_crop_path=excluded.face_crop_path,
                    eye_crop_path=excluded.eye_crop_path,
                    phash=excluded.phash
            """, (
                eye_id, candidate_id, side,
                bbox[0], bbox[1], bbox[2], bbox[3], bbox[2],
                face_bbox[0], face_bbox[1], face_bbox[2], face_bbox[3],
                sharpness, reflection_score,
                face_crop_path, eye_crop_path, phash,
            ))
            # Ensure review row exists
            conn.execute("""
                INSERT OR IGNORE INTO review (eye_id, status) VALUES (?, 'pending')
            """, (eye_id,))

    def get_eyes_for_review(self, status: str | None = None) -> list[sqlite3.Row]:
        with self._conn() as conn:
            if status:
                return conn.execute("""
                    SELECT e.*, r.status, r.caption, c.photographer, c.license_name,
                           c.license_url, c.source_page_url, c.source, c.date_taken
                    FROM eyes e
                    JOIN review r ON e.id = r.eye_id
                    JOIN candidates c ON e.candidate_id = c.id
                    WHERE r.status = ?
                    ORDER BY e.reflection_score DESC
                """, (status,)).fetchall()
            return conn.execute("""
                SELECT e.*, r.status, r.caption, c.photographer, c.license_name,
                       c.license_url, c.source_page_url, c.source, c.date_taken
                FROM eyes e
                JOIN review r ON e.id = r.eye_id
                JOIN candidates c ON e.candidate_id = c.id
                ORDER BY e.reflection_score DESC
            """).fetchall()

    def set_review_status(self, eye_id: str, status: str, caption: str = "") -> None:
        with self._conn() as conn:
            conn.execute("""
                UPDATE review SET status=?, caption=?, reviewed_at=datetime('now')
                WHERE eye_id=?
            """, (status, caption, eye_id))

    def get_approved_eyes(self) -> list[sqlite3.Row]:
        return self.get_eyes_for_review(status="approved")

    def get_similarity_groups(self, threshold: int = 10) -> list[list[sqlite3.Row]]:
        """Return groups of eyes whose face crops are perceptually similar.

        Uses Hamming distance between pHash hex strings. Groups with only one
        member are excluded (nothing to compare). Threshold of 10 out of 64
        bits catches same-photo variants; lower values are stricter.
        """
        import imagehash  # noqa: PLC0415

        with self._conn() as conn:
            rows = conn.execute("""
                SELECT e.*, r.status, r.caption, c.photographer, c.license_name,
                       c.license_url, c.source_page_url, c.source, c.date_taken
                FROM eyes e
                JOIN review r ON e.id = r.eye_id
                JOIN candidates c ON e.candidate_id = c.id
                WHERE e.phash IS NOT NULL AND e.phash != ''
                ORDER BY e.reflection_score DESC
            """).fetchall()

        if not rows:
            return []

        # Parse hashes
        parsed = []
        for row in rows:
            try:
                h = imagehash.hex_to_hash(row["phash"])
                parsed.append((row, h))
            except Exception:
                continue

        # Single-pass greedy grouping
        grouped: list[list] = []
        used = set()
        for i, (row_i, hash_i) in enumerate(parsed):
            if i in used:
                continue
            group = [row_i]
            used.add(i)
            for j, (row_j, hash_j) in enumerate(parsed):
                if j in used:
                    continue
                if hash_i - hash_j <= threshold:
                    group.append(row_j)
                    used.add(j)
            if len(group) > 1:
                grouped.append(group)

        return grouped

    def stats(self) -> dict:
        with self._conn() as conn:
            return {
                "candidates": conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
                "downloaded": conn.execute("SELECT COUNT(*) FROM candidates WHERE local_path IS NOT NULL").fetchone()[0],
                "eyes": conn.execute("SELECT COUNT(*) FROM eyes").fetchone()[0],
                "pending": conn.execute("SELECT COUNT(*) FROM review WHERE status='pending'").fetchone()[0],
                "approved": conn.execute("SELECT COUNT(*) FROM review WHERE status='approved'").fetchone()[0],
                "skipped": conn.execute("SELECT COUNT(*) FROM review WHERE status='skipped'").fetchone()[0],
            }
