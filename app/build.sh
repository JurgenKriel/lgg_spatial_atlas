#!/usr/bin/env bash
# Venture Atlas — bundle the self-hosted viewer (component E-1).
#
# Vitessce ships as ESM with bare imports and code-splitting; there is no UMD
# build to drop in a <script> tag. So we bundle it ourselves into a set of
# self-contained, same-origin chunks that are committed to this repo and served
# from /vendor/. No CDN at runtime, nothing for the review gate to leak around.
#
# The build workspace lives on SCRATCH, never in the project tree: the vitessce
# dependency tree is ~1 GB and tens of thousands of inodes, and /vast/projects
# is inode-bound.
#
#   ./app/build.sh            # bundle using the existing scratch workspace
#   ./app/build.sh --install  # (re)install node deps first
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
WORK="${ATLAS_BUILD_DIR:-/vast/scratch/users/$USER/vitessce_build}"
CACHE="${ATLAS_NPM_CACHE:-/vast/scratch/users/$USER/npm_cache}"
OUT="$HERE/vendor"

# Pinned — the built configs are schema 1.0.16, which this line of Vitessce
# understands. Bump deliberately, then re-run smoke_test.sh.
VITESSCE_VERSION="${VITESSCE_VERSION:-3.7.0}"
REACT_VERSION="18.3.1"
ESBUILD_VERSION="0.25.0"

command -v node >/dev/null || { echo "node not found (try: module load nodejs/20.16.0)"; exit 1; }
echo "==> node $(node --version)"

if [ "${1:-}" = "--install" ] || [ ! -d "$WORK/node_modules/vitessce" ]; then
    echo "==> installing build deps into $WORK"
    mkdir -p "$WORK" "$CACHE"
    [ -f "$WORK/package.json" ] || printf '{"name":"venture-atlas-viewer-build","private":true,"type":"module"}\n' > "$WORK/package.json"
    npm install --prefix "$WORK" --cache "$CACHE" --no-audit --no-fund --loglevel=error \
        "vitessce@$VITESSCE_VERSION" "react@$REACT_VERSION" "react-dom@$REACT_VERSION" "esbuild@$ESBUILD_VERSION"
fi

ESBUILD="$WORK/node_modules/.bin/esbuild"
[ -x "$ESBUILD" ] || { echo "esbuild not found at $ESBUILD — run with --install"; exit 1; }

echo "==> bundling"
rm -rf "$OUT"; mkdir -p "$OUT"

# Sourcemaps are off by default: they triple the committed size (14 MB -> 46 MB)
# to map minified third-party code we do not maintain. Set ATLAS_SOURCEMAP=1 if
# you are actually debugging inside Vitessce.
SOURCEMAP=(); [ "${ATLAS_SOURCEMAP:-0}" = "1" ] && SOURCEMAP=(--sourcemap)

# --splitting keeps the heavy optional pieces (higlass, three/XR, neuroglancer)
# in lazily-fetched chunks instead of one enormous first payload.
NODE_PATH="$WORK/node_modules" "$ESBUILD" "$HERE/src/main.jsx" \
    --bundle \
    --format=esm \
    --splitting \
    --minify \
    "${SOURCEMAP[@]}" \
    --target=es2020 \
    --jsx=automatic \
    --loader:.jsx=jsx \
    --loader:.js=jsx \
    --loader:.png=dataurl \
    --loader:.svg=dataurl \
    --loader:.woff=file \
    --loader:.woff2=file \
    --loader:.ttf=file \
    --define:process.env.NODE_ENV=\"production\" \
    --define:global=globalThis \
    --outdir="$OUT" \
    --entry-names=main \
    --public-path=/vendor \
    --resolve-extensions=.jsx,.js,.mjs,.json \
    --log-level=warning \
    --metafile="$OUT/meta.json"

# esbuild only emits main.css if something in the graph imports CSS. The page
# links it unconditionally, so make sure the file exists either way.
[ -f "$OUT/main.css" ] || printf '/* vitessce styles are injected at runtime in this build */\n' > "$OUT/main.css"

echo "==> output"
du -sh "$OUT"
ls -lh "$OUT"/*.js 2>/dev/null | awk '{printf "    %-46s %s\n", $9, $5}' | sed "s|$OUT/||"
total=$(du -sb "$OUT" | cut -f1)
echo "    total $(numfmt --to=iec "$total")  across $(find "$OUT" -type f | wc -l) files"

# Sanity: the bundle must understand the schema our configs are written in.
if grep -qF '1.0.16' "$OUT"/*.js 2>/dev/null; then
    echo "==> OK: bundle knows config schema 1.0.16"
else
    echo "==> WARNING: '1.0.16' not found in the bundle — check Vitessce version vs config schema_version"
fi

echo
echo "Bundled into app/vendor/. Commit it: the VM has no build step and no CDN."
