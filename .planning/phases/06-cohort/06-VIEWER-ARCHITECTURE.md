# Phase 6 — cohort viewer: architecture decisions

Settled design for taking the atlas from one patient to the whole cohort.
Data-inventory findings live in `06-SCOPE.md`; this file is the shape of the thing.

---

## A-1. One config per (sample, plane), fetched lazily

**Decision.** Keep the existing pattern: each (sample, z-plane) gets its own
Vitessce config JSON, and the app fetches exactly one at a time.

**Why not a single multi-dataset config.** Vitessce configs do support multiple
datasets with a shared coordination space, and it is tempting to express the whole
cohort as one config with a dataset-selection coordination scope. That would be a
mistake at this scale: Vitessce instantiates a data loader per dataset in the
config, so a cohort config would spin up loaders for every sample and plane on
page load, fetch every store's metadata, and hold it all resident — to display
one plane. The lazy pattern keeps first paint proportional to what is on screen.

**Consequence.** The number of configs is the number of (sample, plane) pairs, so
config generation must be a loop, not a hand-authored file. This is already how
`build_config_v8.py` behaves (it takes the two store URLs as arguments); what is
missing is the driver that calls it across the cohort.

## A-2. The manifest is the only place the cohort is enumerated

**Decision.** Nothing in the app, the nginx config, or the deploy scripts may
contain a sample list. The manifest generated at release time is the single
source of truth, and the UI is built from it (REQ-11).

This already half-holds: `deploy/make_manifest.py` emits a `samples` list and a
per-plane `sample` field, and `app/src/main.jsx` builds its z-slider from
`manifest.planes`. What it lacks is nesting — planes are currently a flat list
keyed only incidentally by sample.

**Manifest v2 schema:**

```json
{
  "version": "v3-20260916-abc1234",
  "generated": "2026-09-16T04:00:00Z",
  "cohort": "venture",
  "legend": {
    "cell_type": {"Astrocyte": "#f8c7c6", "...": "..."},
    "niche":     {"T-LE": {"color": "#9fcf86", "identity": "Leading edge"}}
  },
  "samples": [
    {
      "id": "ven2",
      "label": "Venture 2",
      "modalities": ["cells", "ms"],
      "planes": [
        {"z": 1, "config": "...-ven2_z1-config.json",
         "cells_zarr": "...", "ms_zarr": "...", "n_cells": 41726}
      ]
    },
    {
      "id": "GL0018",
      "label": "GL0018",
      "modalities": ["cells"],
      "planes": [{"z": 0, "config": "...", "cells_zarr": "...", "n_cells": 12345}]
    }
  ]
}
```

Three things this buys:

- **`modalities`** lets the app decide layout before fetching a config, so an
  ST-only sample never renders a dead metabolite panel (REQ-10).
- **`legend` is cohort-wide**, hoisted out of per-sample palettes — see A-3.
- **`n_cells`** lets the app warn before loading an unusually heavy plane.

## A-3. One cohort-wide palette, not per-sample palettes

**Decision.** Cell-type and niche colours are computed once over the **union** of
labels across all samples, and stored in the manifest. Every config references
the same colours.

**Why this is correctness, not cosmetics.** Palettes are currently sourced
per-sample from that sample's `uns/Anno_colors`. If sample A lacks a cell type
that sample B has, a per-sample palette silently shifts every subsequent colour,
and two samples viewed in sequence use different colours for the same cell type.
A reader comparing samples would draw false conclusions. The union palette fixes
the label→colour map once for the cohort.

This is the same class of bug as the known napari failure where a z-plane missing
a cell type broke the colour zip; the fix there was to stop dropping unused
categories, and the principle is identical.

**Label normalisation.** The canonical niche key uses underscore codes (`T_LE`)
while figures and the existing palette use hyphens (`T-LE`). The builder must
normalise to one form and map to the other for display. The legend should carry
the **biological identity** ("T-LE — Leading edge"), not the bare code: a reader
outside the lab cannot interpret `T_AMN`.

## A-4. Two viewer modes, chosen by the manifest

The cohort is not homogeneous, and the UI must not pretend otherwise.

| Mode | Applies to | Layout |
|---|---|---|
| **Multi-plane, multimodal** | samples with a real z-stack and MS | sample selector + z slider + cells panel + MS panel |
| **Single-plane, cells only** | single-section samples | sample selector only; one full-width cells panel |

The z slider hides entirely when a sample has one plane — a disabled slider with
one position is noise. The MS panel is absent, not empty, when `modalities` lacks
`ms`, and the cells panel takes the full width.

## A-5. URL state

**Decision.** The selected sample and plane live in the query string
(`?sample=ven2&z=3`), read on load and written on change via `history.replaceState`.

Cheap to implement and it buys three things: a colleague can be sent an exact
view, a manuscript can cite one (the beginning of REQ-16 curated views), and a
reviewer's browser back button behaves.

## A-6. Roll our own selector; revisit webatlas-app later

**Decision.** Add a sample selector to the existing lightweight shell rather than
adopting `haniffalab/webatlas-app` now.

webatlas-app is the study/dataset browser that cellatlas.io runs and remains the
right long-term answer for REQ-12 — but it is a full React application with its
own build and deployment, and its documentation does not clearly specify its input
contract. Adopting it now would put an unfamiliar build step on the critical path
for a cohort release. The shell already renders Vitessce same-origin and is
manifest-driven; a selector is a small addition to it. Phase 7 can still replace
the shell wholesale, and the manifest survives that change.

## A-7. What stays out of scope here

- Tissue image (H&E/IF) raster layers and segmentation polygons — Phase 8.
- Side-by-side comparison of two samples — Phase 9. Note A-1 makes this cheap
  later: two configs, two Vitessce instances, linked coordination.
- Named curated views beyond what A-5's URL state gives for free — Phase 9.

---

*Phase 6 — companion to `06-SCOPE.md`.*
