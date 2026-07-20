#!/bin/bash
# Smoke-run webatlas-pipeline (Full_pipeline) on a tiny synthetic AnnData.
# Usage: bash run_example.sh   (runs directly; wrap in sbatch for real data)
set -euo pipefail
source /etc/profile.d/modules.sh
module load apptainer/1.4.1
HERE="$(cd "$(dirname "$0")" && pwd)"
export NXF_SINGULARITY_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
export APPTAINER_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
export NXF_HOME="$HERE/.nextflow"
# numba (via scanpy) can't write its cache into the read-only container fs.
# Point it at a writable dir and pass it INTO the apptainer container.
export NUMBA_CACHE_DIR=/vast/scratch/users/kriel.j/numba_cache
export MPLCONFIGDIR=/vast/scratch/users/kriel.j/mpl_cache
mkdir -p "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
export APPTAINERENV_NUMBA_CACHE_DIR=/tmp/numba_cache
export APPTAINERENV_MPLCONFIGDIR=/tmp/mpl_cache
export SINGULARITYENV_NUMBA_CACHE_DIR=/tmp/numba_cache
export SINGULARITYENV_MPLCONFIGDIR=/tmp/mpl_cache
NF=${NEXTFLOW_BIN:-$HOME/bin/nextflow}
WORK=/vast/scratch/users/kriel.j/webatlas_smoke_work
cd "$HERE/webatlas-pipeline"
"$NF" run main.nf \
  -params-file "$HERE/smoke/smoke_params.yaml" \
  -entry Full_pipeline \
  -profile singularity \
  -work-dir "$WORK" \
  -c "$HERE/smoke/extra.config" \
  -ansi-log false
