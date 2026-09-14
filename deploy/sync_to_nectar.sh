#!/usr/bin/env bash
# Venture Atlas — push a release from HPC to the Nectar VM (components D-2, D-3)
#
# PUSH, never pull. Pulling would mean putting HPC credentials on a public host.
#
# Releases are immutable and versioned; the only mutable thing on the server is
# the `current` symlink, flipped at the end. A half-finished rsync is therefore
# never servable, and a bad release is one symlink away from being rolled back.
#
# Run from a SLURM job, not the login node (project convention):
#   sbatch --job-name=atlas-sync --cpus-per-task=4 --mem=8G --time=2:00:00 \
#          --wrap "deploy/sync_to_nectar.sh --host ubuntu@atlas.example.org --version v1"
#
# Or interactively for the small pilot:
#   deploy/sync_to_nectar.sh --host ubuntu@atlas.example.org --version v1
set -euo pipefail

HOST=""; VERSION=""; SRC=""; KEY=""; ACTIVATE=1; DRYRUN=0
usage() {
    cat <<'EOF'
Usage: sync_to_nectar.sh --host user@vm [options]

  --host user@vm      required. ssh destination of the Nectar instance
  --version vN        release name (default: v<UTC date>-<git short sha>)
  --src DIR           what to upload (default: ./docs/atlas — the built pilot)
  --key FILE          ssh identity file
  --no-activate       upload but do not flip `current` (stage a release)
  --dry-run           show what rsync would do
EOF
}
while [ $# -gt 0 ]; do
    case "$1" in
        --host) HOST="$2"; shift 2;;
        --version) VERSION="$2"; shift 2;;
        --src) SRC="$2"; shift 2;;
        --key) KEY="$2"; shift 2;;
        --no-activate) ACTIVATE=0; shift;;
        --dry-run) DRYRUN=1; shift;;
        -h|--help) usage; exit 0;;
        *) echo "unknown option: $1"; usage; exit 1;;
    esac
done
[ -n "$HOST" ] || { usage; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${SRC:-$HERE/docs/atlas}"
[ -d "$SRC" ] || { echo "source not found: $SRC"; exit 1; }

if [ -z "$VERSION" ]; then
    SHA="$(git -C "$HERE" rev-parse --short HEAD 2>/dev/null || echo nogit)"
    VERSION="v$(date -u +%Y%m%d)-$SHA"
fi

SSH=(ssh -o BatchMode=yes); [ -n "$KEY" ] && SSH+=(-i "$KEY")
RSH="${SSH[*]}"

REMOTE_DATA="/srv/atlas/data"
REMOTE_REL="$REMOTE_DATA/$VERSION"

echo "==> release  : $VERSION"
echo "==> source   : $SRC"
echo "==> target   : $HOST:$REMOTE_REL"

nfiles=$(find "$SRC" -type f | wc -l)
nbytes=$(du -sh "$SRC" | cut -f1)
echo "==> payload  : $nfiles files, $nbytes"

# --- build the manifest (component D-3 / early REQ-11) -----------------------
# The viewer reads this to know which planes exist, so the z-slider is data
# driven rather than hard-coded. Phase 6 extends the same file across samples.
MANIFEST="$(mktemp)"
trap 'rm -f "$MANIFEST"' EXIT
python3 "$HERE/deploy/make_manifest.py" "$SRC" "$VERSION" > "$MANIFEST"

RSYNC_OPTS=(-rlt --info=progress2 --human-readable
            # many small files over a WAN: delta-encoding costs more than it saves
            --whole-file
            --chmod=D755,F644)
[ "$DRYRUN" = "1" ] && RSYNC_OPTS+=(--dry-run)

echo "==> uploading"
"${SSH[@]}" "$HOST" "mkdir -p '$REMOTE_REL'"
rsync "${RSYNC_OPTS[@]}" -e "$RSH" "$SRC"/ "$HOST:$REMOTE_REL/"
rsync "${RSYNC_OPTS[@]}" -e "$RSH" "$MANIFEST" "$HOST:$REMOTE_REL/manifest.json"

if [ "$DRYRUN" = "1" ]; then echo "==> dry run, stopping here"; exit 0; fi

remote_files=$("${SSH[@]}" "$HOST" "find '$REMOTE_REL' -type f | wc -l")
echo "==> uploaded : $remote_files files on the server (local payload was $nfiles + manifest)"

if [ "$ACTIVATE" = "1" ]; then
    echo "==> activating $VERSION"
    # ln -sfn onto a temp name then mv is atomic; a viewer mid-session never
    # sees a missing `current`.
    "${SSH[@]}" "$HOST" "ln -sfn '$REMOTE_REL' '$REMOTE_DATA/.current.new' && mv -Tf '$REMOTE_DATA/.current.new' '$REMOTE_DATA/current'"
    echo "==> live"
else
    echo "==> staged (not activated). Activate with:"
    echo "    ${SSH[*]} $HOST \"ln -sfn '$REMOTE_REL' '$REMOTE_DATA/.current.new' && mv -Tf '$REMOTE_DATA/.current.new' '$REMOTE_DATA/current'\""
fi

echo
echo "Verify:  deploy/smoke_test.sh https://<domain>/ <user>:<pass>"
echo "Roll back to a previous release:"
echo "    ${SSH[*]} $HOST \"ls $REMOTE_DATA\"   # pick one, then re-run the ln/mv above"
