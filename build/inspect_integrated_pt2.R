# Inspect the pt2 integrated (ST + metabolomics) object structure & cell keys.
suppressWarnings(suppressMessages({
  f <- "/vast/projects/BCRL_Multi_Omics/venture_pt2/integrated/integrated_data_250925.rds"
  cat("Reading", f, "...\n"); obj <- readRDS(f)
}))
cat("class:", paste(class(obj), collapse=","), "\n")
if (inherits(obj, "Seurat")) {
  suppressWarnings(suppressMessages(library(SeuratObject)))
  cat("dim (features x cells):", paste(dim(obj), collapse=" x "), "\n")
  cat("assays:", paste(SeuratObject::Assays(obj), collapse=", "), "\n")
  cat("DefaultAssay:", SeuratObject::DefaultAssay(obj), "\n")
  for (a in SeuratObject::Assays(obj)) {
    d <- dim(obj[[a]]); fn <- head(rownames(obj[[a]]), 6)
    cat(sprintf("  assay %-14s : %d features x %d cells | feat ex: %s\n",
                a, d[1], d[2], paste(fn, collapse=", ")))
  }
  cat("cell name ex:", paste(head(colnames(obj), 4), collapse=", "), "\n")
  cat("meta.data cols:", paste(colnames(obj@meta.data), collapse=", "), "\n")
  # show a few candidate annotation columns
  for (col in c("celltype","cell_type","Anno","annotation","niche","sample","sample_id","patient","orig.ident")) {
    if (col %in% colnames(obj@meta.data)) {
      u <- unique(as.character(obj@meta.data[[col]]))
      cat(sprintf("  meta[%s]: %d uniq -> %s\n", col, length(u), paste(head(u,8), collapse=", ")))
    }
  }
  cat("reductions:", paste(SeuratObject::Reductions(obj), collapse=", "), "\n")
  cat("images:", paste(names(obj@images), collapse=", "), "\n")
} else {
  cat("str (2 levels):\n"); str(obj, max.level=2)
}
