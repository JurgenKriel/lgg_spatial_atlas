import pandas as pd, numpy as np
OUT="/vast/scratch/users/kriel.j/atlas_pt2"
integ = pd.read_csv(f"{OUT}/integrated_meta.csv")
coh   = pd.read_csv(f"{OUT}/cohort_ven2.csv")
print(f"integrated cells: {len(integ)} | cohort ven2 cells: {len(coh)}")

# 1) map integrated sample_id -> cohort ven2 sample via cell_id overlap
coh_by_samp = {s: set(g["cell_id"]) for s,g in coh.groupby("sample")}
mapping = {}
print("\nsample_id -> best ven2 match (overlap / integrated-sample-size):")
for sid, g in integ.groupby("sample_id"):
    ids = set(g["cell_id"]); best=None; bestov=-1
    for cs, cids in coh_by_samp.items():
        ov = len(ids & cids)
        if ov>bestov: bestov=ov; best=cs
    mapping[sid]=best
    print(f"  {sid} -> {best}  overlap={bestov}/{len(ids)} ({100*bestov/len(ids):.1f}%)")

# 2) join niche using (mapped_sample, cell_id)
integ["ven2_sample"]=integ["sample_id"].map(mapping)
coh_key = coh.set_index(["sample","cell_id"])
idx = list(zip(integ["ven2_sample"], integ["cell_id"]))
niche = coh_key["niche"].reindex(idx).values
celltype_csv = coh_key["celltype"].reindex(idx).values
integ["niche"]=niche
matched = pd.notna(niche).sum()
print(f"\nMATCHED FRACTION (niche joined): {matched}/{len(integ)} = {100*matched/len(integ):.2f}%")

# 3) cross-check Anno(integrated) vs celltype(CSV) agreement on matched cells
m = pd.notna(niche)
agree = (integ.loc[m,"Anno"].astype(str).values == pd.Series(celltype_csv[m]).astype(str).values).mean()
print(f"cell-type agreement (integrated Anno vs CSV celltype) on matched cells: {100*agree:.1f}%")
print(f"niche value counts (joined):\n{integ['niche'].value_counts(dropna=False).head(15)}")
