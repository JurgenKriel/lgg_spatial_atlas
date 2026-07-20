# Dump integrated pt2 meta.data + feature lists for join validation (no matrices yet).
suppressWarnings(suppressMessages({
  obj <- readRDS("/vast/projects/BCRL_Multi_Omics/venture_pt2/integrated/integrated_data_250925.rds")
  library(SeuratObject)
}))
md <- obj@meta.data
md$cellname <- rownames(md)
keep <- intersect(c("cellname","cell_id","sample_id","orig.ident","Anno","Anno_2",
                    "x_centroid","y_centroid","x_aligned","y_aligned"), colnames(md))
outdir <- "/vast/scratch/users/kriel.j/atlas_pt2"; dir.create(outdir, showWarnings=FALSE, recursive=TRUE)
write.csv(md[, keep], file.path(outdir,"integrated_meta.csv"), row.names=FALSE)
cat("wrote integrated_meta.csv rows:", nrow(md), "cols:", paste(keep, collapse=","), "\n")
cat("cell_id ex:", paste(head(md$cell_id,4), collapse=", "), "\n")
cat("cellname ex:", paste(head(md$cellname,4), collapse=", "), "\n")
# feature lists
writeLines(rownames(obj[["SPT"]]), file.path(outdir,"SPT_genes.txt"))
writeLines(rownames(obj[["SPM"]]), file.path(outdir,"SPM_metabolites.txt"))
cat("SPT genes:", nrow(obj[["SPT"]]), " SPM metabolites:", nrow(obj[["SPM"]]), "\n")
# sample_id x-tab with coord ranges to help map to ven2_z*
cat("sample_id counts:\n"); print(table(md$sample_id))
