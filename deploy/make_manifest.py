#!/usr/bin/env python3
"""Generate a release manifest for the Venture atlas (component D-3).

The viewer reads this to learn which planes exist and which layers each one
has, so nothing about samples or z-planes is hard-coded in the app. Phase 6
extends the same file across the cohort: add a `sample` dimension and the
selector follows, because the app already reads the shape rather than assuming
it (REQ-11).

Recognised filenames in a release directory:
    <prefix>-<sample>_z<N>-anndata.zarr    cells  (genes / cell type / niche)
    ms_<sample>_z<N>-anndata.zarr          MS ion density
    <prefix>-<sample>_z<N>-config.json     the Vitessce config for that plane

Usage:  make_manifest.py <release-dir> <version> [> manifest.json]
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys

CELLS = re.compile(r"^(?P<prefix>.+)-(?P<sample>[A-Za-z0-9]+)_z(?P<z>\d+)-anndata\.zarr$")
MS = re.compile(r"^ms_(?P<sample>[A-Za-z0-9]+)_z(?P<z>\d+)-anndata\.zarr$")
CONFIG = re.compile(r"^(?P<prefix>.+)-(?P<sample>[A-Za-z0-9]+)_z(?P<z>\d+)-config\.json$")


def build(release_dir: str, version: str) -> dict:
    try:
        names = sorted(os.listdir(release_dir))
    except FileNotFoundError:
        raise SystemExit(f"release directory not found: {release_dir}")

    planes: dict[tuple[str, int], dict] = {}

    def slot(sample: str, z: int) -> dict:
        return planes.setdefault((sample, z), {"sample": sample, "z": z})

    for name in names:
        m = MS.match(name)
        if m:
            slot(m["sample"], int(m["z"]))["ms_zarr"] = name
            continue
        m = CELLS.match(name)
        if m:
            slot(m["sample"], int(m["z"]))["cells_zarr"] = name
            continue
        m = CONFIG.match(name)
        if m:
            slot(m["sample"], int(m["z"]))["config"] = name

    ordered = [planes[k] for k in sorted(planes, key=lambda k: (k[0], k[1]))]

    # A plane with no config cannot be displayed; surface that rather than
    # letting the viewer fail on it silently.
    incomplete = [f"{p['sample']}_z{p['z']}" for p in ordered if "config" not in p]
    if incomplete:
        print(f"warning: no config for {', '.join(incomplete)}", file=sys.stderr)

    return {
        "version": version,
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "samples": sorted({p["sample"] for p in ordered}),
        "planes": ordered,
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    manifest = build(sys.argv[1], sys.argv[2])
    json.dump(manifest, sys.stdout, indent=2)
    sys.stdout.write("\n")
    n_ms = sum(1 for p in manifest["planes"] if "ms_zarr" in p)
    print(
        f"{len(manifest['planes'])} planes "
        f"({n_ms} with MS) across samples {manifest['samples']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
