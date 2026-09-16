#!/usr/bin/env bash
# Preview a built release from the HPC, over an SSH tunnel — no VM required.
#
# Serves the app and a release from one origin, exactly as the Nectar host will,
# so what you see here is what a reviewer will see. Then you forward the port to
# your laptop and open it in a normal browser.
#
#   # on the HPC
#   deploy/preview_local.sh --release /vast/scratch/users/$USER/atlas_cohort/release
#
#   # on your laptop (the script prints this line with the right values)
#   ssh -N -L 8080:localhost:8080 <you>@<the-node-it-names>
#
#   # then open http://localhost:8080/
#
# Run it on a compute node for a large release (`srun --pty bash`) rather than
# the login node — serving 14k objects to a browser is real I/O.
set -euo pipefail

RELEASE=""; PORT=8080; ROOT=""
usage() {
    cat <<'EOF'
Usage: preview_local.sh --release DIR [--port N] [--root DIR]

  --release DIR   the built release (holds *-anndata.zarr and manifest.json)
  --port N        port to serve on (default 8080)
  --root DIR      where to assemble the preview tree (default: a temp dir)
EOF
}
while [ $# -gt 0 ]; do
    case "$1" in
        --release) RELEASE="$2"; shift 2;;
        --port) PORT="$2"; shift 2;;
        --root) ROOT="$2"; shift 2;;
        -h|--help) usage; exit 0;;
        *) echo "unknown option: $1"; usage; exit 1;;
    esac
done
[ -n "$RELEASE" ] || { usage; exit 1; }
[ -d "$RELEASE" ] || { echo "no such release: $RELEASE"; exit 1; }
[ -f "$RELEASE/manifest.json" ] || { echo "no manifest.json in $RELEASE — run make_manifest.py first"; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -d "$HERE/app/vendor" ] || { echo "app/vendor missing — run app/build.sh first"; exit 1; }

VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$RELEASE/manifest.json")"
ROOT="${ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/atlas-preview-XXXXXX")}"

# Assemble the same layout nginx serves: app at /, release under /data/<version>,
# with /data/current pointing at it. Symlinks, so nothing is copied.
mkdir -p "$ROOT/data"
ln -sfn "$HERE/app/index.html" "$ROOT/index.html"
ln -sfn "$HERE/app/vendor" "$ROOT/vendor"
ln -sfn "$RELEASE" "$ROOT/data/$VERSION"
ln -sfn "$RELEASE" "$ROOT/data/current"

HOSTNAME_FQ="$(hostname -f 2>/dev/null || hostname)"
cat <<EOF

  Release : $RELEASE
  Version : $VERSION
  Root    : $ROOT
  Serving : http://127.0.0.1:$PORT/  (loopback only - reach it via the tunnel below)

  From your laptop, in another terminal:

      ssh -N -L ${PORT}:localhost:${PORT} ${USER}@${HOSTNAME_FQ}

  then open:  http://localhost:${PORT}/

  Ctrl-C here to stop.

EOF

cd "$ROOT"
exec python3 - "$PORT" <<'PY'
import functools, http.server, os, socketserver, sys

class Handler(http.server.SimpleHTTPRequestHandler):
    """Static handler that gets Zarr right.

    Two things the stock handler gets wrong for this payload, both of which the
    real nginx config handles explicitly:
      * Zarr metadata dotfiles (.zarray/.zgroup/.zattrs/.zmetadata) must be
        served, and as JSON — the stock guesser calls them octet-stream.
      * chunk files have no extension and must come back as binary, not as
        text/html, which is what the guesser falls back to.
    """
    def guess_type(self, path):
        name = os.path.basename(path)
        if name in (".zarray", ".zgroup", ".zattrs", ".zmetadata") or name.endswith(".json"):
            return "application/json"
        if name.endswith(".js") or name.endswith(".mjs"):
            return "text/javascript"
        if name.endswith(".css"):
            return "text/css"
        if name.endswith(".html"):
            return "text/html"
        base, ext = os.path.splitext(name)
        if not ext or all(p.isdigit() for p in name.split(".") if p):
            return "application/octet-stream"
        return super().guess_type(path)

    def end_headers(self):
        # The manifest must never be cached or a re-run serves the old cohort.
        if self.path.endswith("manifest.json"):
            self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt, *a):
        if "404" in (fmt % a):          # surface misses, stay quiet otherwise
            sys.stderr.write("404 " + (fmt % a) + "\n")

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

port = int(sys.argv[1])
# Bind loopback ONLY. This serves unpublished, patient-derived data; on
# 0.0.0.0 anyone who could reach this node's port would read it without
# credentials. An SSH tunnel is the access path, so loopback suffices —
# set ATLAS_PREVIEW_BIND to override deliberately.
BIND = os.environ.get("ATLAS_PREVIEW_BIND", "127.0.0.1")
with Server((BIND, port), Handler) as httpd:
    print(f"serving on port {port} — Ctrl-C to stop", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
PY
