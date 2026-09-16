#!/usr/bin/env Rscript
# Probe a candidate cohort gene-expression object WITHOUT assuming anything
# about it (scope blocker 3.2).
#
# Two candidates sit side by side on stornext and it is not documented which is
# canonical, so answer it empirically: class, dimensions, assay names, colData
# schema, and — the question that actually matters — whether its per-section
# coverage matches the 66 sections the cohort annotations CSV describes.
#
# An RDS is a serialised blob, so there is no partial read; this needs the whole
# object in memory (~6.4 GB reported) and therefore a SLURM job, not a login node.
#
# Usage: Rscript probe_cohort_object.R <path.rds> [sections.csv]

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("usage: probe_cohort_object.R <path.rds> [sections.csv]")
path <- args[1]
sections_csv <- if (length(args) > 1) args[2] else NA

cat("== probing:", path, "\n")
cat("   size:", format(file.info(path)$size / 1e9, digits = 3), "GB\n")
t0 <- Sys.time()
obj <- readRDS(path)
cat("   loaded in", format(difftime(Sys.time(), t0, units = "mins"), digits = 3), "\n\n")

cat("class:       ", paste(class(obj), collapse = ", "), "\n")

# Work for either a SingleCellExperiment or a Seurat object without requiring
# both packages to be attached.
dims <- tryCatch(dim(obj), error = function(e) NA)
cat("dim:         ", paste(dims, collapse = " x "), "\n")

assays <- tryCatch({
  if (methods::is(obj, "SingleCellExperiment")) SummarizedExperiment::assayNames(obj)
  else if (!is.null(obj@assays)) names(obj@assays)
  else NA
}, error = function(e) NA)
cat("assays:      ", paste(assays, collapse = ", "), "\n")

meta <- tryCatch({
  if (methods::is(obj, "SingleCellExperiment")) as.data.frame(SummarizedExperiment::colData(obj))
  else obj@meta.data
}, error = function(e) NULL)

if (is.null(meta)) {
  cat("could not extract cell metadata\n")
  quit(status = 1)
}

cat("meta columns:", paste(colnames(meta), collapse = ", "), "\n\n")

sample_col <- intersect(c("sample", "sample_id", "orig.ident"), colnames(meta))[1]
if (is.na(sample_col)) {
  cat("no recognisable sample column; cannot assess coverage\n")
  quit(status = 1)
}
cat("sample column:", sample_col, "\n")

tab <- sort(table(as.character(meta[[sample_col]])), decreasing = TRUE)
cat("distinct values:", length(tab), "\n")
cat("cells total:    ", format(sum(tab), big.mark = ","), "\n\n")

cat("per-sample cell counts:\n")
for (nm in names(tab)) cat(sprintf("  %-18s %10s\n", nm, format(tab[[nm]], big.mark = ",")))

# The question that decides whether this object can drive the cohort build.
if (!is.na(sections_csv) && file.exists(sections_csv)) {
  want <- read.csv(sections_csv, stringsAsFactors = FALSE)$section
  have <- names(tab)
  missing <- setdiff(want, have)
  extra <- setdiff(have, want)
  cat("\n== coverage vs sections table ==\n")
  cat("sections wanted:", length(want), "\n")
  cat("present:        ", length(intersect(want, have)), "\n")
  cat("MISSING:        ", length(missing),
      if (length(missing)) paste0(" -> ", paste(head(missing, 40), collapse = ", ")) else "", "\n")
  cat("extra in object:", length(extra),
      if (length(extra)) paste0(" -> ", paste(head(extra, 40), collapse = ", ")) else "", "\n")
  cat(if (length(missing) == 0) "\nVERDICT: covers every section — usable as the cohort gene source.\n"
      else "\nVERDICT: does NOT cover every section; see MISSING above.\n")
}

# A couple of gene names, to sanity-check the panel rather than trust the count.
genes <- tryCatch(rownames(obj), error = function(e) NULL)
if (!is.null(genes)) {
  cat("\ngenes:", length(genes), "| first 12:", paste(head(genes, 12), collapse = ", "), "\n")
}
