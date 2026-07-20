#!/bin/bash
set -euo pipefail
source /etc/profile.d/modules.sh; module load apptainer/1.4.1
HERE="$(cd "$(dirname "$0")" && pwd)"; PARAMS="${1:?params}"
export NXF_SINGULARITY_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
export APPTAINER_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
export NXF_HOME="$HERE/.nextflow"
NF=${NEXTFLOW_BIN:-$HOME/bin/nextflow}
cd "$HERE/webatlas-pipeline"
"$NF" run multimodal.nf -params-file "$PARAMS" -profile singularity \
  -work-dir /vast/scratch/users/kriel.j/webatlas_pt2_mm_work \
  -c "$HERE/smoke/extra.config" -ansi-log false
