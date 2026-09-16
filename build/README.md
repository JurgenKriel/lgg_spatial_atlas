# Building a cohort release

From the cohort object on stornext to a release directory the Nectar VM can
serve. Every step is re-runnable; none of them write outside their own
section's paths.

Scratch workspace: `/vast/scratch/users/$USER/atlas_cohort/` — never the project
tree, which is inode-bound.

---

## 0. Once per cohort

```bash
# The section table: 66 sections, two axes, treatment labels, grades.
# Also the naming normaliser (the CSV says GX008/LGGA, the stores say
# GX0008/LGG-A1, the cohort object says LGGA1).
python3 build/make_sections_table.py \
    /vast/projects/BCRL_Multi_Omics/venture_ST/full_ven_cohort_annotations.csv \
    --out /vast/scratch/users/$USER/atlas_cohort/sections.csv      # ~23 s

# ONE palette over the union of all 30 centroids stores. Not optional: a
# per-sample palette gives the same cell type different colours in different
# patients, and pt2's palette alone is missing 4 cell types and 2 niches that
# exist elsewhere in the cohort.
spatialdata_env_2/bin/python3 build/make_cohort_palette.py \
    /vast/projects/BCRL_Multi_Omics/venture_ST/centroids \
    --out /vast/scratch/users/$USER/atlas_cohort/palettes.json
```

## 1. Export per-section matrices from the cohort object

```bash
sbatch build/export_cohort_sections.sh            # all sections
ONLY="ven2_z1 GL0018_2" sbatch build/export_cohort_sections.sh   # a subset
```

Loads the 7M-cell `SingleCellExperiment` **once** (~50 s) and slices it. Writes
three files per section to `$WORK/export/`:

| file | what |
|---|---|
| `<section>.X.f32` | raw float32, column-major, genes × cells |
| `<section>.obs.tsv` | annotation, niche, coordinates, sample |
| `<section>.json` | shape, gene names, array order |

**Why not h5ad.** `zellkonverter::writeH5AD` bridges to python via
basilisk/reticulate and begins installing a pyenv into `$HOME` — which on this
system is inode-constrained and has broken package installs before. Three plain
files need no bridge, and numpy reads the matrix with one `fromfile`.

Covers **65 of 66 sections**. `GL0184_prim_1` (2,900 cells) is not in the cohort
object and is reported, not silently skipped.

## 2. Build the release

```bash
sbatch build/build_cohort_release.sh              # array over all sections
sbatch --array=1-2 build/build_cohort_release.sh  # a couple, to check
```

One section per array task, throttled to 12 at a time — this is I/O bound, and
66 concurrent dense matrices would only thrash the filesystem. Each task writes
`venture_atlas-<section>-anndata.zarr` and its config into `$WORK/release/`.

The MS layer is picked up automatically where `ms_<section>-anndata.zarr`
already exists in the release directory; otherwise the config is built ST-only,
with a full-width cells panel rather than a dead empty one.

## 3. Manifest, then ship

```bash
python3 deploy/make_manifest.py $WORK/release v1 \
    --sections $WORK/sections.csv \
    --palettes $WORK/palettes.json > $WORK/release/manifest.json

deploy/sync_to_nectar.sh --host ubuntu@<vm> --src $WORK/release --version v1
deploy/smoke_test.sh https://<domain>/ reviewer:<pass>
```

## 4. Look at it before shipping it

No VM needed — serve the release from the HPC and tunnel to it:

```bash
# on the HPC (use a compute node for a big release: srun --pty bash)
deploy/preview_local.sh --release $WORK/release --port 8080

# on your laptop, in another terminal — the script prints this line for you
ssh -N -L 8080:localhost:8080 <you>@<node>
# then open http://localhost:8080/
```

It serves the app and the release from one origin, with the Zarr content types
the real host sets, so what you see is what a reviewer sees.

**It binds loopback only.** This is unpublished patient-derived data; on
`0.0.0.0` anyone able to reach that port on the node could read it with no
credentials. The SSH tunnel is the access path.

For a full dress rehearsal of the *production* config — basic auth, TLS, the
immutable cache headers — run nginx from a container against the same tree
instead; that path is what `deploy/smoke_test.sh` exercises. Note the preview
deliberately does **not** set immutable caching (you want rebuilds to show up),
so the smoke test's cache check is expected to fail against it and only that one.

---

## What the first release contains

- **65 sections** across 15 patients — cells, cell type, niche, 307-gene panel.
- **MS for ven2 only** (8 planes). ven1 and ven3–ven6 hold *raw pre-alignment*
  metabolite coordinates; only ven2 has ST-frame-aligned files today. They
  become ST-only in the viewer until lu.t names the canonical aligned file, at
  which point adding them is a data change with no code change — the manifest
  already carries per-section modality.
- Two axes: a depth slider for the ven z-stacks, a labelled timepoint list for
  the GL/GX/LGG clinical series.

## Gotchas worth keeping

- **`X` must be dense.** Sparse CSR gives Vitessce a `LoaderNotFoundError`.
- **`X` is float32, not float64.** Halves the atlas and halves the bytes a
  reviewer pulls per interaction, which is metered off-net on Nectar.
- **`var/is_gene` is written by the builder**, not by a Nextflow step. The pilot
  relied on the pipeline adding it, so a build that skipped that step produced a
  store the viewer could not read.
- **Consolidated metadata** (`.zmetadata`) is written per store; without it the
  viewer makes thousands of metadata requests per store.
- **`white` is not a niche.** It is a placeholder with no biological identity;
  the builder maps it to `unassigned` and the palette drops it.
