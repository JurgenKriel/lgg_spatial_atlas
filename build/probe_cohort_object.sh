#!/bin/bash
#SBATCH --job-name=atlas-probe
#SBATCH --cpus-per-task=2
#SBATCH --mem=96G
#SBATCH --time=2:00:00
#SBATCH --output=/vast/scratch/users/kriel.j/atlas_cohort/logs/probe_%j.out
#SBATCH --error=/vast/scratch/users/kriel.j/atlas_cohort/logs/probe_%j.err
#
# Answer scope blocker 3.2 empirically rather than waiting on a decision:
# does full_ven_integrated_cleaned.rds cover all 66 cohort sections?
#
# 96 GB because the object is reported at ~6.4 GB in memory and readRDS peaks
# well above the resident size; a 7M-cell colData is not small either.
set -euo pipefail

REPO="${REPO:-/vast/projects/BCRL_Multi_Omics/venture_atlas/.claude/worktrees/nectar-5a}"
SECTIONS="${SECTIONS:-/vast/scratch/users/kriel.j/sections.csv}"
RDS="${RDS:-/stornext/Bioinf/data/lab_brain_cancer/projects/tme_spatial/transcriptomics/venture/ST/data/processed/full_ven_integrated_cleaned.rds}"

mkdir -p /vast/scratch/users/kriel.j/atlas_cohort/logs

source /etc/profile.d/modules.sh
module load R/4.5.3
# Project convention: R needs libiconv from the cellpose env, and the project
# library paths, or Bioconductor packages fail to load.
export LD_LIBRARY_PATH="/vast/projects/BCRL_Multi_Omics/cellpose_env/lib:${LD_LIBRARY_PATH:-}"
export R_LIBS="/vast/projects/BCRL_Multi_Omics/R_libraries:/vast/projects/BCRL_Multi_Omics/Venture_lib/lib/R/library"

Rscript "$REPO/build/probe_cohort_object.R" "$RDS" "$SECTIONS"
