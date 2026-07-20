#!/bin/bash
set -x
source /etc/profile.d/modules.sh
module load apptainer/1.4.1
export APPTAINER_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
export NXF_SINGULARITY_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache
mkdir -p "$NXF_SINGULARITY_CACHEDIR"
cd "$NXF_SINGULARITY_CACHEDIR"
echo "[$(date)] pulling main container..."
apptainer pull --force webatlas-pipeline-0.5.2.sif docker://haniffalab/webatlas-pipeline:0.5.2
echo "[$(date)] pulling build_config container..."
apptainer pull --force webatlas-pipeline-build-config-0.5.2.sif docker://haniffalab/webatlas-pipeline-build-config:0.5.2
echo "[$(date)] DONE"
ls -lh "$NXF_SINGULARITY_CACHEDIR"/*.sif
