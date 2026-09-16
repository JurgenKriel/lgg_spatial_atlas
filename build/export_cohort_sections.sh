#!/bin/bash
#SBATCH --job-name=atlas-export
#SBATCH --cpus-per-task=4
#SBATCH --mem=120G
#SBATCH --time=12:00:00
#SBATCH --output=/vast/scratch/users/kriel.j/atlas_cohort/logs/export_%j.out
#SBATCH --error=/vast/scratch/users/kriel.j/atlas_cohort/logs/export_%j.err
#
# Export one h5ad per cohort section from the 7M-cell SingleCellExperiment.
# Loads the object once and slices it; per-section loading would be hours of
# pure I/O. 120 GB because readRDS peaks well above the ~6.4 GB resident size
# and each subset copies.
#
#   sbatch build/export_cohort_sections.sh                 # all sections
#   ONLY="ven2_z1 GL0018_2" sbatch build/export_cohort_sections.sh   # a subset
set -euo pipefail

REPO="${REPO:-/vast/projects/BCRL_Multi_Omics/venture_atlas/.claude/worktrees/nectar-5a}"
WORK="${WORK:-/vast/scratch/users/kriel.j/atlas_cohort}"
SECTIONS="${SECTIONS:-$WORK/sections.csv}"
RDS="${RDS:-/stornext/Bioinf/data/lab_brain_cancer/projects/tme_spatial/transcriptomics/venture/ST/data/processed/full_ven_integrated_cleaned.rds}"
ONLY="${ONLY:-}"

mkdir -p "$WORK/logs" "$WORK/h5ad"

source /etc/profile.d/modules.sh
module load R/4.5.3
# Project convention: R needs libiconv from the cellpose env plus the project
# library paths, or Bioconductor packages fail to load.
export LD_LIBRARY_PATH="/vast/projects/BCRL_Multi_Omics/cellpose_env/lib:${LD_LIBRARY_PATH:-}"
export R_LIBS="/vast/projects/BCRL_Multi_Omics/R_libraries:/vast/projects/BCRL_Multi_Omics/Venture_lib/lib/R/library"

# shellcheck disable=SC2086
Rscript "$REPO/build/export_cohort_sections.R" "$RDS" "$SECTIONS" "$WORK/h5ad" $ONLY
