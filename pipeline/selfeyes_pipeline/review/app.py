"""Flask review UI for the selfeyes pipeline.

Runs locally on http://localhost:5050. Never deployed.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from ..store import Store
from ..export import promote_approved


def create_app(store: Store, cfg: dict) -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["store"] = store
    app.config["cfg"] = cfg

    # Serve crop images directly from disk
    @app.route("/img/<path:filepath>")
    def serve_image(filepath: str):
        full = Path(filepath)
        if not full.exists():
            return "not found", 404
        mime = mimetypes.guess_type(str(full))[0] or "image/jpeg"
        return send_file(str(full.resolve()), mimetype=mime)

    @app.route("/")
    def index():
        status_filter = request.args.get("status", "pending")
        s: Store = app.config["store"]
        eyes = s.get_eyes_for_review(status=status_filter if status_filter != "all" else None)
        stats = s.stats()
        return render_template(
            "index.html",
            eyes=eyes,
            stats=stats,
            status_filter=status_filter,
        )

    @app.route("/approve", methods=["POST"])
    def approve():
        data = request.get_json()
        eye_id = data.get("eye_id", "")
        caption = data.get("caption", "")
        s: Store = app.config["store"]
        s.set_review_status(eye_id, "approved", caption)
        # Immediately push to manifest
        promote_approved(s, app.config["cfg"])
        stats = s.stats()
        return jsonify({"ok": True, "stats": stats})

    @app.route("/skip", methods=["POST"])
    def skip():
        data = request.get_json()
        eye_id = data.get("eye_id", "")
        s: Store = app.config["store"]
        s.set_review_status(eye_id, "skipped")
        stats = s.stats()
        return jsonify({"ok": True, "stats": stats})

    @app.route("/stats")
    def stats():
        s: Store = app.config["store"]
        return jsonify(s.stats())

    return app
