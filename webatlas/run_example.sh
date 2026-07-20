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
NF=${NEXTFLOW_BIN:-$HOME/bin/nextflow}
WORK=/vast/scratch/users/kriel.j/webatlas_smoke_work
cd "$HERE/webatlas-pipeline"
"$NF" run main.nf \
  -params-file "$HERE/smoke/smoke_params.yaml" \
  -entry Full_pipeline \
  -profile singularity \
  -work-dir "$WORK" \
  -ansi-log false
