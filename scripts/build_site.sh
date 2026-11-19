#!/usr/bin/env bash
# Stage the pinned SDK, build with Great Docs + Quarto (CPU only, no venv, no Ruff), post-process, optionally validate.
# Usage: scripts/build_site.sh [--validate] [path-to-local-SDK-checkout]
set -euo pipefail
cd "$(dirname "$0")/.."
VALIDATE=0; SDK_ARG=()
for a in "$@"; do [ "$a" = "--validate" ] && VALIDATE=1 || SDK_ARG=(--sdk-repo "$a"); done
PY=python3.13
command -v "$PY" >/dev/null || { echo "python3.13 required"; exit 1; }
export PATH="$HOME/.local/opt/quarto-1.11.9/bin:$PATH" QUARTO_PYTHON="$(command -v $PY)" PYTHONDONTWRITEBYTECODE=1
command -v quarto >/dev/null || { echo "standalone Quarto 1.11.9 not found (see requirements-docs.txt)"; exit 1; }
GD_SHA=$($PY -c "import json;print(json.load(open('SOURCE.lock.json'))['great_docs']['commit'])")
GD="${XDG_CACHE_HOME:-$HOME/.cache}/stokastisk-docs/great-docs-${GD_SHA:0:8}"
if [ ! -d "$GD/great_docs" ]; then
  mkdir -p "$GD" && git init -q "$GD" && git -C "$GD" fetch -q --depth 1 https://github.com/posit-dev/great-docs.git "$GD_SHA" \
    && git -C "$GD" -c advice.detachedHead=false checkout -q FETCH_HEAD && rm -rf "$GD/.git"
fi
export PYTHONPATH="$GD"
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT         # staged SDK copy lives outside the repository
$PY scripts/stage_source.py --out "$STAGE/stokastisk" "${SDK_ARG[@]}"
export STAGED="$STAGE/stokastisk"
( cd "$STAGED" && $PY -m great_docs.cli build --config website/great-docs.yml )
$PY scripts/postprocess_site.py --staged "$STAGED"
if [ "$VALIDATE" = 1 ]; then
  mkdir -p reports
  ( cd "$STAGED" && $PY -m great_docs.cli seo --config website/great-docs.yml )
  $PY scripts/check_site.py --site "$STAGED/website/_site" --release "$STAGED/RELEASE.json"
  $PY scripts/api_coverage.py --staged "$STAGED"
  ( cd "$STAGED" && $PY -m great_docs.cli check-links --config website/great-docs.yml --docs-only ) || true
fi
# keep the finished site for the Pages artifact / local preview
rm -rf _site && cp -a "$STAGED/website/_site" _site
echo "site ready: $(pwd)/_site"
