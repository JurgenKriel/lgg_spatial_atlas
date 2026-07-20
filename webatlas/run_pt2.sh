#!/bin/bash
# Run webatlas Full_pipeline on real pt2 data. Usage: bash run_pt2.sh <params.yaml> <workdir-tag>
set -euo pipefail
source /etc/profile.d/modules.sh
module load apptainer/1.4.1
HERE="$(cd "$(dirname "$0")" && pwd)"
PARAMS="${1:?need params yaml}"; TAG="${2:-pt2}"
export NXF_SINGULARITY_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
export APPTAINER_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
export NXF_HOME="$HERE/.nextflow"
NF=${NEXTFLOW_BIN:-$HOME/bin/nextflow}
cd "$HERE/webatlas-pipeline"
"$NF" run main.nf -params-file "$PARAMS" -entry Full_pipeline -profile singularity \
  -work-dir "/vast/scratch/users/kriel.j/webatlas_${TAG}_work" \
  -c "$HERE/smoke/extra.config" -ansi-log false
