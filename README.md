# LGG Spatial Atlas

**Explore low-grade glioma in space: genes, metabolites, cell types and tissue
niches, measured on the same tissue and browsable in your web browser.**

<p>
  <a href="https://jurgenkriel.github.io/lgg_spatial_atlas/"><b>▶ Open the atlas</b></a>
  &nbsp;·&nbsp; <a href="#whats-inside">What's inside</a>
  &nbsp;·&nbsp; <a href="#repository-map">Repository map</a>
  &nbsp;·&nbsp; <a href="#paper-analysis">Paper analysis</a>
  &nbsp;·&nbsp; <a href="#citation">Cite</a>
</p>

---

Brain tumours are not uniform. Within a single specimen, neighbourhoods of
tumour, immune and glial cells sit side by side, each with its own gene
expression and its own metabolism. This atlas puts those layers on one map.
**Single-cell spatial transcriptomics** (10x Genomics Xenium) and **MALDI mass
spectrometry imaging** of metabolites were measured on serial sections of the
same tissue and registered into a shared coordinate frame. Pick a section,
choose a gene or a metabolite, and see where it is, which cells carry it, and
which tissue niche those cells belong to.

### At a glance

| | |
|---|---|
| **Disease** | IDH-mutant low-grade glioma |
| **Paper cohort** | 17 patients · 26 spatially profiled samples |
| **Atlas (cohort release)** | 65 tissue sections · ~7 million cells |
| **Modalities** | Xenium spatial transcriptomics · MALDI mass spectrometry imaging · H&E / IHC / immunofluorescence |
| **Raw data** | ~1.3 TB, to be deposited in the [BioImage Archive](https://www.ebi.ac.uk/bioimage-archive/) |

## What's inside

| Layer | What you see | Source |
|---|---|---|
| 🧬 **Transcriptomics** | Per-cell expression of any panel gene | Xenium spatial transcriptomics |
| ⚗️ **Metabolomics** | Ion intensity per *m/z*, with putative annotations | MS imaging, aligned to the ST section |
| 🔬 **Cell types** | Annotated cell identity for every cell | Clustering + marker-based annotation |
| 🗺️ **Niche analysis** | Recurring multicellular neighbourhoods | Spatial niche analysis |

**Two ways through the cohort:**

- **Depth.** For six patients, serial sections through one tissue block form a
  z-stack. A slider steps through the tissue plane by plane.
- **Time.** For the other patients, sections come from different clinical
  timepoints (primary and recurrent tumour after different treatments). These
  are shown as separate specimens, never as planes of one block.

> **Current release:** the public viewer shows the pilot patient (three paired
> ST + metabolite planes). The full-cohort release is in preparation.

## Using the viewer

1. **[Open the atlas](https://jurgenkriel.github.io/lgg_spatial_atlas/)**. It
   runs entirely in the browser; there's nothing to install.
2. Use the **Z-plane** slider to move through the tissue.
3. **Left panel:** cells, coloured by gene, cell type or niche. **Right panel:**
   the matching metabolite image.
4. Zoom and pan with the mouse; select a feature from the panel controls.

The viewer is built on [Vitessce](http://vitessce.io), and the data stores are
generated with the
[webatlas-pipeline](https://github.com/haniffalab/webatlas-pipeline).

## Repository map

This repository holds two things: the code that **builds the atlas** and the
code behind the **paper's analyses**.

| Folder | Purpose |
|---|---|
| [`analysis/`](analysis/) | Scripts that produce the figures and tables in the paper, one folder per figure |
| [`build/`](build/) | Assembles per-section AnnData: joins genes, metabolites, cell type, niche and coordinates (see [`JOIN_KEY.md`](build/JOIN_KEY.md)) |
| [`webatlas/`](webatlas/) | Runs the webatlas-pipeline and writes Vitessce view configs (data spec in [`PIPELINE_CONTRACT.md`](webatlas/PIPELINE_CONTRACT.md)) |
| [`docs/`](docs/) | The published static site (GitHub Pages): viewer page and zarr data stores |

## Building the atlas

The build runs on an HPC cluster with Nextflow and Apptainer. Tool versions are
pinned in [`webatlas/versions.env`](webatlas/versions.env).

```bash
source webatlas/env.sh            # load Nextflow / Apptainer, set paths
./webatlas/pull_containers.sh     # fetch pinned pipeline containers (once)
./webatlas/run_example.sh         # smoke test on synthetic data
```

The input data are not in this repository. Raw and processed data (~1.3 TB of
Xenium, MALDI-MSI and histology images) will be released through the
[BioImage Archive](https://www.ebi.ac.uk/bioimage-archive/) under a single
BioStudies accession when the paper is published. The accession will be added
here.

## Paper analysis

The code for every figure lives under [`analysis/`](analysis/). Each figure
folder has a README that lists its inputs and how to run it. Generated outputs
are not committed.

## Citation

A preprint is in preparation. Until it's out, please cite this repository and
contact the authors before reusing the data.

## Contact

Brain Cancer Research Lab, Walter and Eliza Hall Institute of Medical Research
(WEHI). Questions and bug reports: please
[open an issue](https://github.com/JurgenKriel/lgg_spatial_atlas/issues).
