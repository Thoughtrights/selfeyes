#!/bin/bash
# deploy.sh — build check + deploy selfeyes to thoughtrights host
# Usage: ./deploy.sh [--dry-run]
#
# Destination: thoughtrights:docroot/selfeyes
# The SSH host alias "thoughtrights" must be configured in ~/.ssh/config.

set -euo pipefail

REMOTE="thoughtrights"
REMOTE_PATH="docroot/selfeyes"
SRC="html/"
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── 1. Build check ────────────────────────────────────────────────────────────

echo "==> Build check..."

# Validate manifest.json is well-formed JSON
if ! python3 -c "import json,sys; json.load(open('html/manifest.json'))" 2>&1; then
    echo "ERROR: html/manifest.json is not valid JSON"
    exit 1
fi

# Check all image files referenced in manifest actually exist
MISSING=$(python3 - <<'PYEOF'
import json, sys, os
manifest = json.load(open("html/manifest.json"))
missing = [item["src"] for item in manifest["items"]
           if not os.path.exists(os.path.join("html", item["src"]))]
for m in missing:
    print(m)
PYEOF
)

if [ -n "$MISSING" ]; then
    echo "ERROR: manifest references files that don't exist:"
    echo "$MISSING"
    exit 1
fi

ITEM_COUNT=$(python3 -c "import json; print(len(json.load(open('html/manifest.json'))['items']))")
echo "    manifest OK — $ITEM_COUNT items"
echo "    required files present"
echo "    build check passed"

# ── 2. Deploy ─────────────────────────────────────────────────────────────────

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "==> Dry run — would rsync to ${REMOTE}:${REMOTE_PATH}"
    rsync --dry-run -avz --delete \
        --exclude='.DS_Store' \
        --exclude='*~' \
        --exclude='utils/' \
        "$SRC" "${REMOTE}:${REMOTE_PATH}/"
    echo ""
    echo "    (dry run complete — no files transferred)"
    exit 0
fi

echo ""
echo "==> Deploying to ${REMOTE}:${REMOTE_PATH} ..."
rsync -avz --delete \
    --exclude='.DS_Store' \
    --exclude='*~' \
    --exclude='utils/' \
    "$SRC" "${REMOTE}:${REMOTE_PATH}/"

echo ""
echo "==> Done. Live at https://thoughtrights.com/selfeyes/"
