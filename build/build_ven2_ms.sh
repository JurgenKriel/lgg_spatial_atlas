#!/usr/bin/env bash
# Build the MS ion-density layer for ven2's eight planes.
#
# ven2 is currently the ONLY patient with ST-frame-aligned metabolite
# coordinates. ven1 and ven3-ven6 hold raw pre-alignment matrices in
# metabolomics_edge_removed/, and their aligned outputs are spread across
# versioned attempt directories with no canonical marker — scope blocker 3.1,
# owned by lu.t. Those patients are ST-only in the viewer until that is settled,
# at which point adding them is a data change with no code change.
#
# Each plane is validated against its own cells store by nearest-neighbour
# distance, so a wrong coordinate column fails the build rather than silently
# shipping a misplaced layer.
#
# Usage: build_ven2_ms.sh [release_dir]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
RELEASE="${1:-/vast/scratch/users/$USER/atlas_cohort/release}"
SRC_ROOT="${SRC_ROOT:-/vast/projects/BCRL_Multi_Omics/venture_pt2/aligned_metabolites}"
PY="${PY:-/vast/projects/BCRL_Multi_Omics/spatialdata_env_2/bin/python3}"
PREFIX="${PREFIX:-venture_atlas}"

built=0; skipped=0
for z in 1 2 3 4 5 6 7 8; do
    section="ven2_z${z}"
    src=$(ls "$SRC_ROOT/layer_${z}"/*_aligned_metabolites.csv 2>/dev/null | head -1 || true)
    cells="$RELEASE/${PREFIX}-${section}-anndata.zarr"

    if [ -z "$src" ]; then
        echo "-- $section: no aligned metabolites file under layer_${z}, skipping"
        skipped=$((skipped+1)); continue
    fi
    if [ ! -d "$cells" ]; then
        echo "-- $section: cells store not built yet, skipping"
        skipped=$((skipped+1)); continue
    fi

    "$PY" "$REPO/build/build_ms_section.py" \
        --section "$section" --src "$src" \
        --out "$RELEASE/ms_${section}-anndata.zarr" \
        --cells "$cells"
    built=$((built+1))
done

echo
echo "MS layers built: $built, skipped: $skipped"
echo "Re-run build_cohort_release.sh for those sections so their configs pick up the MS panel."
