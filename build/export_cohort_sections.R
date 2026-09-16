#!/usr/bin/env Rscript
# Export one cohort section per file from the cohort SingleCellExperiment.
#
# Load the 7M-cell object ONCE and slice it; per-section loading would be hours
# of pure I/O for no benefit.
#
# INTERCHANGE FORMAT — why not h5ad
# The obvious choice, zellkonverter::writeH5AD, bridges to python via
# basilisk/reticulate and starts installing a pyenv into $HOME. This project's
# home directory is inode-constrained (it has broken package installs before),
# and a python environment inside an R job is a dependency risk that buys
# nothing here. So each section is written as three plain files instead:
#
#   <section>.X.f32     raw float32, column-major, genes x cells
#   <section>.obs.tsv   one row per cell, the annotation columns
#   <section>.json      shape, gene names, and the column order
#
# Base R only, no bridge, and numpy reads the matrix with a single fromfile.
#
# NAME MATCHING
# Section ids disagree across sources in punctuation only:
#     sections table   SCE colData$sample
#     GL0043_1.1       GL0043_1_1
#     LGG-A1           LGGA1
#     ven5.2.1         ven_5_2_1
# Stripping non-alphanumerics and lowercasing reconciles every one, so match on
# that canonical key rather than a hand-written lookup that will drift. Anything
# that still fails to match is reported, never silently skipped — a section
# quietly missing from the atlas is worse than a loud error.
#
# Usage:
#   export_cohort_sections.R <cohort.rds> <sections.csv> <outdir> [only_section ...]

suppressPackageStartupMessages({
  library(SingleCellExperiment)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("usage: export_cohort_sections.R <rds> <sections.csv> <outdir> [only ...]")
rds_path <- args[1]; sections_csv <- args[2]; outdir <- args[3]
only <- if (length(args) > 3) args[-(1:3)] else character(0)

dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
canon <- function(x) gsub("[^a-z0-9]", "", tolower(x))

sections <- read.csv(sections_csv, stringsAsFactors = FALSE)
if (length(only)) sections <- sections[sections$section %in% only, , drop = FALSE]
cat("sections to export:", nrow(sections), "\n")

cat("reading", rds_path, "\n")
t0 <- Sys.time()
sce <- readRDS(rds_path)
cat("  loaded in", format(difftime(Sys.time(), t0, units = "mins"), digits = 3), "\n")

cd <- colData(sce)
stopifnot("sample" %in% colnames(cd))
sce_samples <- as.character(cd$sample)
key_to_sample <- tapply(sce_samples, canon(sce_samples), function(v) v[1])

genes <- rownames(sce)
cat("genes:", length(genes), "\n")

keep_cols <- intersect(
  c("annotation", "annotation_intermediates", "niche", "x_coord", "y_coord",
    "sample", "sample_id", "batch"),
  colnames(cd))
cat("carrying colData:", paste(keep_cols, collapse = ", "), "\n\n")

assay_name <- if ("X" %in% assayNames(sce)) "X" else assayNames(sce)[1]

ok <- 0; failed <- character(0)
for (i in seq_len(nrow(sections))) {
  section <- sections$section[i]

  # Already exported? Skip, so a failed run resumes rather than redoing work.
  if (file.exists(file.path(outdir, paste0(section, ".json")))) {
    cat(sprintf("[%2d/%d] %-16s already exported — skipping\n", i, nrow(sections), section))
    ok <- ok + 1
    next
  }

  # `[[` on a missing name throws "subscript out of bounds" rather than
  # returning NULL, which turned the intended skip-and-report into a hard
  # failure on the first section absent from the object. Check membership.
  key <- canon(section)
  sce_name <- if (key %in% names(key_to_sample)) key_to_sample[[key]] else NA_character_

  if (is.null(sce_name) || is.na(sce_name)) {
    cat(sprintf("[%2d/%d] %-16s NOT IN OBJECT — skipped\n", i, nrow(sections), section))
    failed <- c(failed, section); next
  }
  idx <- which(sce_samples == sce_name)
  if (!length(idx)) { failed <- c(failed, section); next }

  res <- tryCatch({
    m <- assay(sce, assay_name)[, idx, drop = FALSE]
    m <- as.matrix(m)                       # genes x cells, column-major
    storage.mode(m) <- "double"
    m[!is.finite(m)] <- 0

    con <- file(file.path(outdir, paste0(section, ".X.f32")), "wb")
    writeBin(as.vector(m), con, size = 4)   # float32, column-major
    close(con)

    obs <- as.data.frame(cd[idx, keep_cols, drop = FALSE])
    obs$cell_index <- idx
    write.table(obs, file.path(outdir, paste0(section, ".obs.tsv")),
                sep = "\t", quote = FALSE, row.names = FALSE, na = "")

    meta <- list(section = section, sce_sample = sce_name,
                 n_genes = nrow(m), n_cells = ncol(m),
                 order = "F", dtype = "float32", genes = genes)
    writeLines(jsonlite::toJSON(meta, auto_unbox = TRUE),
               file.path(outdir, paste0(section, ".json")))

    sz <- file.info(file.path(outdir, paste0(section, ".X.f32")))$size / 1e6
    cat(sprintf("[%2d/%d] %-16s <- %-16s %9s cells  %6.0f MB\n",
                i, nrow(sections), section, sce_name,
                format(ncol(m), big.mark = ","), sz))
    rm(m); gc(verbose = FALSE)
    TRUE
  }, error = function(e) {
    cat(sprintf("[%2d/%d] %-16s FAILED: %s\n", i, nrow(sections), section,
                conditionMessage(e)))
    FALSE
  })
  if (isTRUE(res)) ok <- ok + 1 else failed <- c(failed, section)
}

cat("\nexported", ok, "of", nrow(sections), "sections to", outdir, "\n")
if (length(failed)) cat("NOT exported (", length(failed), "):",
                        paste(failed, collapse = ", "), "\n")
