/**
 * Venture Atlas viewer — self-hosted Vitessce (component E-1).
 *
 * WHY THIS EXISTS
 * The previous viewer iframed `https://vitessce.io/?url=<our config>`, which
 * means a third-party origin fetched our data. That is incompatible with the
 * review gate: vitessce.io cannot send our basic-auth credentials, and a
 * cross-origin credentialed request will not pass. Bundling Vitessce and
 * serving it from our own origin makes app and data same-origin, so one nginx
 * auth block covers both and CORS disappears from the problem entirely.
 *
 * It also removes a runtime dependency on someone else's uptime and version.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Vitessce } from 'vitessce';

const DATA_ROOT = '/data';

/**
 * Built configs carry absolute URLs baked in for whichever host they were
 * generated against (originally GitHub Pages). Every store sits flat inside a
 * release directory, so rewriting each `url` to /data/<version>/<basename>
 * makes a single build deployable on any host without a rebuild — and keeps
 * every fetch same-origin.
 */
function rebaseConfig(node, version) {
  const rebase = (u) => {
    if (typeof u !== 'string' || !u) return u;
    let path = u;
    if (/^https?:\/\//i.test(u)) {
      try { path = new URL(u).pathname; } catch { return u; }
    }
    const name = path.split('/').filter(Boolean).pop();
    return name ? `${DATA_ROOT}/${version}/${name}` : u;
  };
  const walk = (n) => {
    if (Array.isArray(n)) return n.map(walk);
    if (n && typeof n === 'object') {
      const out = {};
      for (const [k, v] of Object.entries(n)) out[k] = k === 'url' ? rebase(v) : walk(v);
      return out;
    }
    return n;
  };
  return walk(node);
}

function Shell() {
  const [manifest, setManifest] = useState(null);
  const [z, setZ] = useState(null);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [height, setHeight] = useState(() => Math.max(420, window.innerHeight - 74));

  useEffect(() => {
    const onResize = () => setHeight(Math.max(420, window.innerHeight - 74));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // The manifest drives the plane list — nothing about samples or z-planes is
  // hard-coded here, which is what Phase 6's cohort selector will extend.
  useEffect(() => {
    fetch(`${DATA_ROOT}/current/manifest.json`, { cache: 'no-store' })
      .then((r) => {
        if (!r.ok) throw new Error(`manifest ${r.status}`);
        return r.json();
      })
      .then((m) => {
        setManifest(m);
        const first = m.planes?.find((p) => p.config) ?? m.planes?.[0];
        if (first) setZ(first.z);
        else setError('The manifest lists no planes with a config.');
      })
      .catch((e) => setError(`Could not load the release manifest (${e.message}). Has a release been synced?`));
  }, []);

  const plane = useMemo(
    () => manifest?.planes?.find((p) => p.z === z) ?? null,
    [manifest, z],
  );

  useEffect(() => {
    if (!manifest || !plane?.config) return;
    setConfig(null);
    fetch(`${DATA_ROOT}/${manifest.version}/${plane.config}`, { cache: 'force-cache' })
      .then((r) => {
        if (!r.ok) throw new Error(`config ${r.status}`);
        return r.json();
      })
      .then((c) => setConfig(rebaseConfig(c, manifest.version)))
      .catch((e) => setError(`Could not load the config for z${plane.z} (${e.message}).`));
  }, [manifest, plane]);

  const onSlide = useCallback((e) => setZ(Number(e.target.value)), []);

  const planes = manifest?.planes ?? [];
  const zs = planes.map((p) => p.z);
  const hasMS = Boolean(plane?.ms_zarr);

  return (
    <>
      <header className="bar">
        <h1>Venture Atlas — {plane?.sample ?? 'pt2'}</h1>
        {zs.length > 1 && (
          <div className="ctl">
            <label htmlFor="z">Z-plane</label>
            <input
              id="z" type="range" min={Math.min(...zs)} max={Math.max(...zs)}
              step={1} value={z ?? Math.min(...zs)} onChange={onSlide}
              list="zticks"
            />
            <datalist id="zticks">{zs.map((v) => <option key={v} value={v} />)}</datalist>
            <span className="zval">z{z}</span>
          </div>
        )}
        <span className="meta">
          left: cells (gene / cell type / niche)
          {hasMS ? ' · right: MS ion density (m/z)' : ' · no MS layer for this plane'}
        </span>
        <span className="meta rel">{manifest?.version}</span>
      </header>

      <main className="stage" style={{ height }}>
        {error && <div className="msg err"><strong>Problem loading the atlas.</strong><p>{error}</p></div>}
        {!error && !config && <div className="msg"><p>Loading z{z}…</p></div>}
        {!error && config && (
          <Vitessce config={config} theme="dark" height={height} />
        )}
      </main>
    </>
  );
}

const el = document.getElementById('root');
createRoot(el).render(<Shell />);
