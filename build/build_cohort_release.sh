#!/bin/bash
#SBATCH --job-name=atlas-build
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=4:00:00
#SBATCH --array=1-66%12
#SBATCH --output=/vast/scratch/users/kriel.j/atlas_cohort/logs/build_%A_%a.out
#SBATCH --error=/vast/scratch/users/kriel.j/atlas_cohort/logs/build_%A_%a.err
#
# Build one cohort section per array task: h5ad -> Vitessce-ready zarr + config.
#
# Per-task isolation is deliberate. The pilot pipeline collided on shared state
# (a fixed Nextflow work directory, unqualified gene-name files in one output
# dir), so nothing here writes to a path that is not section-specific, and the
# release directory receives only finished, uniquely-named artefacts.
#
# %12 throttles concurrency: 66 tasks each holding a dense float32 matrix would
# otherwise hammer the filesystem for no gain — this is I/O bound, not CPU bound.
#
#   sbatch build/build_cohort_release.sh
#   sbatch --array=1-2 build/build_cohort_release.sh      # a couple of sections
set -euo pipefail

REPO="${REPO:-/vast/projects/BCRL_Multi_Omics/venture_atlas/.claude/worktrees/nectar-5a}"
WORK="${WORK:-/vast/scratch/users/kriel.j/atlas_cohort}"
SECTIONS="${SECTIONS:-$WORK/sections.csv}"
RELEASE="${RELEASE:-$WORK/release}"
PALETTES="${PALETTES:-$WORK/palettes.json}"
PREFIX="${PREFIX:-venture_atlas}"
BASE_URL="${BASE_URL:-}"
PY="${PY:-/vast/projects/BCRL_Multi_Omics/spatialdata_env_2/bin/python3}"
VPY="${VPY:-/vast/scratch/users/kriel.j/vitessce_py/bin/python}"

mkdir -p "$RELEASE" "$WORK/logs"

# Array index -> section id (skip the header row).
SECTION="$(awk -F, -v n="${SLURM_ARRAY_TASK_ID:-1}" 'NR==n+1{print $1}' "$SECTIONS")"
[ -n "$SECTION" ] || { echo "no section at row ${SLURM_ARRAY_TASK_ID:-1}"; exit 0; }

H5AD="$WORK/h5ad/${SECTION}.h5ad"
if [ ! -f "$H5AD" ]; then
    echo "SKIP $SECTION — no h5ad (not present in the cohort object?)"
    exit 0
fi

CELLS="$RELEASE/${PREFIX}-${SECTION}-anndata.zarr"
CONFIG="$RELEASE/${PREFIX}-${SECTION}-config.json"
MS="$RELEASE/ms_${SECTION}-anndata.zarr"

echo "=== $SECTION"
"$PY" "$REPO/build/build_section_zarr.py" \
    --section "$SECTION" --h5ad "$H5AD" --out "$CELLS" --palettes "$PALETTES"

# MS is per-section and optional. Only ven2 currently has ST-frame-aligned
# metabolite coordinates; ven1 and ven3-ven6 hold raw pre-alignment matrices, so
# they are ST-only until lu.t names the canonical aligned file (scope §3.1).
MS_ARG="none"
[ -d "$MS" ] && MS_ARG="ms_${SECTION}-anndata.zarr"

"$VPY" "$REPO/webatlas/build_config_v8.py" \
    "${PREFIX}-${SECTION}-anndata.zarr" "$MS_ARG" "$CONFIG" "$PALETTES" "$BASE_URL" \
    --sample "$SECTION"

echo "=== $SECTION done"
