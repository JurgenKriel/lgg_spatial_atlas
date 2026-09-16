# Phase 6 — cohort atlas: scope

What it takes to go from the one-patient pilot to the full cohort, grounded in a
data inventory done 2026-09-16 rather than in the roadmap's assumptions. Several
of those assumptions were wrong; the corrections are in §1 and they change the
shape of the work.

Companions: `06-VIEWER-ARCHITECTURE.md` (settled design), `06-STORE-EFFICIENCY.md`
(what the cohort costs).

---

## 1. The cohort is not what the roadmap says

The roadmap describes "15 ST samples × 8 z-planes, 6 with matched SM". Three
parts of that are wrong, and one of them is a correctness problem rather than a
counting problem.

### 1.1 There are two axes, not one

| Group | Patients | Shape | Axis |
|---|---|---|---|
| ven series | ven1–ven6 | serial z-stack of one block (ven2/3/4/6 × 8, ven1 × 2, ven5 × 8 + 2) | **depth** |
| GL / GX / LGG | 9 patients | flat 2D sections, one per clinical timepoint | **time** |

The nine non-ven patients are **not z-stacks**. Their extra sections are
different clinical timepoints — primary versus recurrent, split by treatment
(`recurrent_nil`, `recurrent_rt`, `recurrent_tmz_bev`, `recurrent_tmz_rt`,
`recurrent_safu`, `recurrent_vora`) — and in several cases a different specimen
entirely. GX0008 alone is a primary plus three differently-treated recurrences.

`export_centroids_to_spatialdata.py` collapses this by filling `z_layer = "z0"`
for any sample not matching `_z<N>$`, which throws the distinction away. Had we
built the cohort atlas on that, **the viewer would have presented a recurrent
tumour as "another z-plane" of the primary** — a scientific misstatement, not a
cosmetic one. A depth slider between two specimens implies a spatial continuity
that does not exist.

**Resolved in this phase:** `build/make_sections_table.py` recovers the
distinction from the cohort annotations CSV, and the manifest and viewer carry an
`axis` per patient — a slider for depth, a labelled list for timepoints.

### 1.2 The real counts

Measured from `venture_ST/full_ven_cohort_annotations.csv` (7,148,072 rows):

**66 sections across 15 patients; 7.15M cells.** Six patients have a z-stack.
ven5 is genuinely mixed (an 8-plane stack plus two later `recurrent_vora`
sections), so "mixed" is a real axis value, not a defect.

Per-patient cell counts range from 126k (GL0184) to 1.33M (ven3). ven3 alone has
more cells than the entire pt2 pilot by a factor of four.

### 1.3 Metabolomics coverage is thinner and messier than recorded

The roadmap says all six ven samples have matched MS. Actually:

| Patient | MS planes | Format | State |
|---|---|---|---|
| ven1 | **2 only** | `metabolomics_edge_removed` | hard data limit, AND raw/unaligned — unusable as-is |
| ven2 | 8 | `aligned_metabolites/layer_{1..8}/` | **aligned**, `x_transformed`/`y_transformed` present |
| ven3–ven6 | 8 each | `metabolomics_edge_removed` | **raw, pre-alignment** — only `x`,`y` |

This is the single largest blocker (§3.1). pt2 is the only patient with a clean,
canonical, ST-frame-aligned file per plane. For ven3–ven6 the aligned outputs are
scattered across `final_aligned/`, `aligned_lddmm/`, `aligned_lddmm_2/`,
`aligned_coordinates/` — 11–24 GB per patient of versioned attempts
(`iter_500/800/1000/5000`, `_shifted`, `_update`, `_2/_3/_4`) with no marker for
which is canonical.

### 1.4 Other corrections

- **The gene panel is 307 genes, not 339.** Confirmed two ways (the measured
  `spatial_counts*.txt` header, and the cohort SCE's `dim`). The pilot's 339
  figure appears to be a different panel version or an imputed matrix.
- **Centroids stores are healthy.** All 30 were regenerated 2026-08-21; the
  "29 emptied" incident is closed. Not a blocker.
- **`white` is a bogus niche category** present across samples (pt2 and GL0184
  both), with no biological identity. It should be filtered or renamed at build
  time, not shown in a legend.
- **Names do not match across sources**: the CSV says `GX008`/`LGGA`; the stores
  say `GX0008`/`LGG-A1`. `make_sections_table.py` is now the normaliser.

---

## 2. What is already built

Done and tested against real data in this phase:

| Component | State |
|---|---|
| `build/make_sections_table.py` | Derives 66 sections, two axes, treatment labels, grades, cell counts from the cohort CSV in ~23 s. Also the naming normaliser. |
| `build/niche_key.json` | Canonical 12-niche code → display → biological identity, in the repo rather than in someone's head. |
| `deploy/make_manifest.py` | Schema 3: patients → sections, per-patient `axis`/`grade`/`modalities`, cohort legend with identities, per-section cell counts. |
| `app/` viewer | Patient selector; depth slider **or** timepoint list per axis; ST-only layout; niche key with identities; URL state (`?patient=&section=`) for deep links. |
| `webatlas/build_config_v8.py` | MS now optional — ST-only samples get a full-width panel, not a dead one. Names derived from the section instead of the literal `ven2_z1` every config previously carried. |
| `deploy/smoke_test.sh` | Schema-3 aware; fails rather than skips when it cannot check. |

Verified end to end: a two-patient release (ven2 z-stack + GL0018 timepoint,
mixed modalities) served through real nginx passes **16/16** checks, including
every data URL across all four configs resolving.

---

## 3. Blockers — these need decisions, not code

### 3.1 Which MS file is canonical for ven3–ven6? *(blocks the MS layer for 4 patients)*

**Owner: lu.t** (confirmed 2026-09-16). lu.t must name, per patient per plane,
the one ST-frame-aligned coordinate file among the versioned attempts. Until then the cohort atlas
can ship **ven2's 8 MS planes and ven1's 2**, and the other four ven patients are
ST-only in the viewer. That is a perfectly shippable first cohort release, and it
is the recommended path rather than blocking everything on an alignment cleanup.

### 3.2 Which cohort gene-expression object is canonical? — **RESOLVED 2026-09-16**

Answered empirically rather than by waiting (`build/probe_cohort_object.R`).
**`full_ven_integrated_cleaned.rds` is usable as the cohort gene source**: a
SingleCellExperiment, one assay `X`, 307 genes × 7,063,837 cells, colData
carrying `annotation`, `niche`, `x_coord`, `y_coord`, `sample`.

It covers **65 of the 66 sections**. The probe initially reported 12 missing,
but 11 of those were the same sections under different punctuation —
`GL0043_1.1` vs `GL0043_1_1`, `LGG-A1` vs `LGGA1`, `ven5.2.1` vs `ven_5_2_1`.
Stripping non-alphanumerics and lowercasing reconciles every one, so the
exporter matches on that canonical key rather than a hand-written lookup.

**Genuinely absent: `GL0184_prim_1`** — the smallest section in the cohort at
2,900 cells. The first release therefore carries 65 sections, and that one
needs moffet.j only if it is wanted.

A useful consequence: because the colData already carries cell type, niche and
coordinates, **the build does not need the centroids stores at all**. That
removes the three-way join — and its matched-fraction risk — from the cohort
path entirely.

### 3.3 pt6 z4 has two unreconciled files

`Ven6D_..._with_xy.csv` (lu.t, Jan) and `..._with_xy2.csv` (moffet.j, Feb): same
row and column counts, every field in a different position. Needs an owner call.

### 3.4 The z-plane pairing risk is now resolvable — and should be resolved

`ST_MS_PLANE_MAPPING.md` records that pt2's cell planes z1/z2 were swapped and
that **z3–z8 pairings are UNVERIFIED**, because footprint overlap cannot separate
planes of the same block. The independent registration record it asked for
exists: the per-section `z_centroid` depths recorded for pt2's eight Xenium
sections are 70, 10, 190, 130, 250, 310, 370, 430 µm — **not monotonic in the
z label**. That is exactly the reported z1/z2 inversion, and it says the same
inversion applies to z3/z4, while z5–z8 are already in depth order.

This should be confirmed and applied before publishing further planes, and
before the same convention is applied 66 times. Shipping unverified pairings
across the cohort would multiply a known error.

---

## 4. Remaining build work

Ordered by what unblocks what. The audit found the pipeline is parameterised
almost nowhere; most of this is threading arguments through.

1. **Cohort palette** — one union palette over all samples, replacing per-sample
   `uns` colours. Without it the same cell type takes different colours in
   different patients. Filter `white` here.
2. **Parameterise the build scripts** — `export_pt2_matrices.R` and
   `build_pt2_anndata.py` have zero arguments; the sample→z map is a literal
   dict, hand-transcribed from a script that only prints to stdout. Make
   `validate_join.py` emit that mapping as a file and consume it.
3. **Fix the shared-state collisions** before any parallel run:
   `run_pt2_multimodal.sh` has a fixed Nextflow work directory (two samples race
   and corrupt both); `export_pt2_matrices.R` writes unqualified
   `SPT_genes.txt`/`SPM_metabolites.txt` into one shared directory.
4. **Slim the stores** — float32 instead of float64 for `X` halves the atlas and
   halves per-interaction egress; drop unused `obsp/` and `obsm/X_pca`. See
   `06-STORE-EFFICIENCY.md`.
5. **Cohort driver** — a SLURM array over the 66 sections with per-section output
   paths, writing into one release directory using the filename convention the
   manifest keys off.
6. **Resolve the `var/is_gene` mismatch** — the config builder filters on
   `var/is_gene`, but the AnnData builders write `feature_type`/`is_metabolite`.
   It currently works only because the Nextflow step adds `is_gene`. Make that
   dependency explicit or the first build that skips the pipeline step breaks.

---

## 5. Sizing — measured, not estimated

Two sections built through the real pipeline: `ven2_z1` (41,726 cells) stores in
**8 MB**; `GL0018_2` (351,578 cells) in **78 MB** — about 220 bytes per cell.

Across 7.15M cells that is **~1.6 GB for the whole cohort's cells**, plus ~700 MB
for ven2's MS planes: **~2.5 GB total**, against the ~20 GB extrapolated from the
pilot. The pilot stored a comparable plane in 127 MB; the cohort build does it in
8 MB, because the cells store carries 307 genes rather than 1,196 fused
gene+metabolite features, and float32 rather than float64.

The 100 GB volume request stands unchanged — it is now well over-provisioned for
this phase, which is the right direction, and Phase 8's tissue rasters will
consume it. Notably the cohort would fit on a trial instance's 30 GB root disk.

## 6. First cohort release — AGREED 2026-09-16

Proceeding without waiting on §3.1 (lu.t). Shipping:

- **65 sections** with cells, cell type, niche and gene expression
  (all but `GL0184_prim_1`, which is not in the cohort object);
- the MS layer for **ven2 only (8 planes)**. Correcting an earlier note: ven1's
  metabolomics is also raw pre-alignment, so it is in the same position as
  ven3–ven6. ven2 is the only patient with ST-frame-aligned coordinates today;
- ven1 and ven3–ven6 as ST-only until lu.t names the canonical aligned file;
- z3–z8 pairings applied only after §3.4 is confirmed.

That is a complete, honest cohort atlas that no longer depends on anyone else's
calendar, and the MS layer for four more patients drops in later as a data
change with no code change — the manifest already carries per-section modality.

---

*Phase 6 — scope, 2026-09-16.*


---

## 7. First cohort release — BUILT 2026-09-16

Built and validated end to end. Location:
`/vast/scratch/users/kriel.j/atlas_cohort/release` — **on scratch**, so sync it
to the Nectar VM before any purge window.

| | |
|---|---|
| Patients | 15 |
| Sections | **65** of 66 (`GL0184_prim_1` absent from the cohort object) |
| Cells | **7,063,837** |
| Sections with MS | 8 (ven2's full z-stack) |
| Size | **2.1 GB**, 14,224 objects |
| Legend | 27 cell types, 12 niches, all with biological identities |

Axis handling came out right across the cohort: nine patients as clinical
timepoint series, five as z-stacks, and **ven5 as `mixed`** — an 8-plane stack
plus two later `recurrent_vora` sections, which is a real property of that
patient rather than a defect.

Validation: served through real nginx, **16/16 smoke checks pass**, including
all 73 data URLs across all 65 configs resolving.

Build timings, for planning re-runs: export 4m14s for 65 sections (8.8 GB of
interchange files); build array ~15 min at 12-way concurrency; MS layers ~5 min.

### An alignment observation worth passing to lu.t

Every ven2 MS plane was validated against its own cells by median
nearest-neighbour distance. Seven of the eight sit at **20.8-22.6 um**. **z1 is
38.2 um** - nearly double.

The obvious hypothesis is the documented z1/z2 label swap, so it was tested
rather than assumed: pairing MS z1 against cells z2 gives **48.8 um**, which is
*worse*, and MS z2 fits cells z1 and z2 about equally (20.4 vs 22.3 um). So the
z1 outlier is **not** explained by the label inversion - it is an alignment
quality issue specific to that plane. It passes the 100 um build threshold and
ships, but it is the one plane in the release whose registration is measurably
weaker than its neighbours.

This does **not** resolve section 3.4; the z3-z8 pairing question stands.

### Next

1. Sync to Nectar once an instance exists:
   `deploy/sync_to_nectar.sh --host ubuntu@<vm> --src <release> --version v1`
2. Confirm Vitessce renders in a browser - the one thing never verified here.
3. lu.t on the ven3-ven6 aligned files (section 3.1), after which those patients'
   MS drops in as a data change with no code change.


---

## Sizing correction, 2026-09-16 (after the log1p fix)

The release grew from **2.1 GB to 3.6 GB** when `X` moved to `log1p(counts)`.
Raw counts are small integers and compress very well; log1p turns them into
floats with long mantissas that do not. The +71% is the price of a gene
expression map that is actually readable — with raw counts, p99 was 6 against a
max of 75, so a handful of extreme cells saturated the scale and every gene
looked the same.

3.6 GB is still an order of magnitude under the ~20 GB first extrapolated from
the pilot, still fits a trial instance's 30 GB root disk, and leaves the 100 GB
volume request comfortably over-provisioned for this phase.

If size ever matters more than fidelity, the lever is quantising the transformed
values (log1p output spans 0-4.4, so float16 or a scaled uint8 would be ample)
rather than reverting to counts.
