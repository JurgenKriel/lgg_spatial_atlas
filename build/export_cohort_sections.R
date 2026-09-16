#!/usr/bin/env Rscript
# Export one h5ad per cohort section from the cohort SingleCellExperiment.
#
# Load the 7M-cell object ONCE and slice it, rather than 66 times. The object is
# ~6.4 GB resident and takes ~40 s to read, so per-section loading would cost
# hours of pure I/O.
#
# NAME MATCHING
# Section ids disagree across sources in punctuation only:
#     sections table   SCE colData$sample
#     GL0043_1.1       GL0043_1_1
#     LGG-A1           LGGA1
#     ven5.2.1         ven_5_2_1
# Stripping non-alphanumerics and lowercasing reconciles every one of them, so
# match on that canonical key rather than maintaining a hand-written lookup that
# will drift. Anything that still fails to match is reported, not silently
# skipped — a section quietly missing from the atlas is worse than a loud error.
#
# Usage:
#   export_cohort_sections.R <cohort.rds> <sections.csv> <outdir> [only_section ...]

suppressPackageStartupMessages({
  library(SingleCellExperiment)
  library(zellkonverter)
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

# Column names must be unique and stable — they are the join key downstream.
cell_ids <- colnames(sce)
if (is.null(cell_ids) || anyDuplicated(cell_ids)) {
  cat("  ! colnames absent or not unique; synthesising <sample>:<index>\n")
  cell_ids <- paste0(sce_samples, ":", seq_len(ncol(sce)))
  colnames(sce) <- cell_ids
}

keep_cols <- intersect(
  c("annotation", "annotation_intermediates", "niche", "x_coord", "y_coord",
    "sample", "sample_id", "batch"),
  colnames(cd))
cat("carrying colData:", paste(keep_cols, collapse = ", "), "\n\n")

ok <- 0; failed <- character(0)
for (i in seq_len(nrow(sections))) {
  section <- sections$section[i]
  key <- canon(section)
  sce_name <- key_to_sample[[key]]

  if (is.null(sce_name) || is.na(sce_name)) {
    cat(sprintf("[%2d/%d] %-16s NOT IN OBJECT — skipped\n", i, nrow(sections), section))
    failed <- c(failed, section)
    next
  }

  idx <- which(sce_samples == sce_name)
  if (!length(idx)) { failed <- c(failed, section); next }

  sub <- sce[, idx]
  colData(sub) <- colData(sub)[, keep_cols, drop = FALSE]
  # One assay, named X — anything else confuses the python side.
  if (!"X" %in% assayNames(sub)) assayNames(sub)[1] <- "X"
  for (a in setdiff(assayNames(sub), "X")) assay(sub, a) <- NULL
  reducedDims(sub) <- list()

  out <- file.path(outdir, paste0(section, ".h5ad"))
  tryCatch({
    writeH5AD(sub, out, X_name = "X", compression = "gzip", verbose = FALSE)
    cat(sprintf("[%2d/%d] %-16s <- %-16s %8s cells  %6.0f MB\n",
                i, nrow(sections), section, sce_name,
                format(length(idx), big.mark = ","),
                file.info(out)$size / 1e6))
    ok <- ok + 1
  }, error = function(e) {
    cat(sprintf("[%2d/%d] %-16s FAILED: %s\n", i, nrow(sections), section, conditionMessage(e)))
    failed <<- c(failed, section)
  })
  rm(sub); gc(verbose = FALSE)
}

cat("\nexported", ok, "of", nrow(sections), "sections to", outdir, "\n")
if (length(failed)) {
  cat("NOT exported (", length(failed), "):", paste(failed, collapse = ", "), "\n")
}
