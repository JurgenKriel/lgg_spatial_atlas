#!/bin/bash
# Serve a webatlas output dir over http for Vitessce. Config uses http://localhost:3000.
# From your laptop: ssh -L 3000:localhost:3000 <you>@<this-node>, then open
#   https://vitessce.io/#?url=http://localhost:3000/<config>.json
set -euo pipefail
DIR="${1:-/vast/scratch/users/kriel.j/webatlas_smoke_out/0.5.3}"
cd "$DIR"
echo "Serving $DIR at http://localhost:3000  (Ctrl-C to stop)"
echo "Config(s):"; ls *-config.json 2>/dev/null
exec python3 -m http.server 3000
