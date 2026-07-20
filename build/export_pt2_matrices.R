# Export per-z-plane SPT (genes) + SPM (metabolites) matrices + obs from the
# integrated pt2 object. Avoids subset() (image validation bug) by column-slicing
# the full assay matrices directly.
suppressWarnings(suppressMessages({
  library(SeuratObject); library(Matrix)
  obj <- readRDS("/vast/projects/BCRL_Multi_Omics/venture_pt2/integrated/integrated_data_250925.rds")
}))
OUT <- "/vast/scratch/users/kriel.j/atlas_pt2/matrices"; dir.create(OUT, showWarnings=FALSE, recursive=TRUE)
getfull <- function(o, assay) {
  o[[assay]] <- tryCatch(SeuratObject::JoinLayers(o[[assay]]), error=function(e) o[[assay]])
  la <- SeuratObject::Layers(o[[assay]])
  cat("   ", assay, "layers:", paste(la, collapse=","), "\n")
  layer <- if ("data" %in% la) "data" else if ("counts" %in% la) "counts" else la[1]
  list(m=as(SeuratObject::LayerData(o[[assay]], layer=layer), "CsparseMatrix"), layer=layer)
}
SPT <- getfull(obj, "SPT"); SPM <- getfull(obj, "SPM")
cat(sprintf("full SPT %dx%d (%s); SPM %dx%d (%s)\n", nrow(SPT$m),ncol(SPT$m),SPT$layer, nrow(SPM$m),ncol(SPM$m),SPM$layer))
md <- obj@meta.data; md$cellname <- rownames(md)
obscols <- intersect(c("cell_id","sample_id","Anno","x_centroid","y_centroid","x_aligned","y_aligned"), colnames(md))
stopifnot(identical(colnames(SPT$m), rownames(md)))   # column order == meta rows
for (s in sort(unique(md$sample_id))) {
  cols <- which(md$sample_id==s)
  Matrix::writeMM(SPT$m[, cols, drop=FALSE], file.path(OUT, paste0(s, "_SPT.mtx")))
  Matrix::writeMM(SPM$m[, cols, drop=FALSE], file.path(OUT, paste0(s, "_SPM.mtx")))
  writeLines(colnames(SPT$m)[cols], file.path(OUT, paste0(s, "_cells.txt")))
  write.csv(md[cols, obscols], file.path(OUT, paste0(s, "_obs.csv")), row.names=FALSE)
  cat(sprintf("  %s: %d cells\n", s, length(cols)))
}
writeLines(rownames(obj[["SPT"]]), file.path(OUT, "SPT_genes.txt"))
writeLines(rownames(obj[["SPM"]]), file.path(OUT, "SPM_metabolites.txt"))
cat("DONE\n")
