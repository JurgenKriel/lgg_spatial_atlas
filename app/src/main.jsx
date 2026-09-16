/**
 * Venture Atlas viewer — self-hosted Vitessce, cohort-scale (E-1, REQ-09/10/11).
 *
 * WHY SELF-HOSTED
 * The original viewer iframed `https://vitessce.io/?url=<our config>`, so a
 * third-party origin fetched our data. That is incompatible with the review
 * gate: vitessce.io cannot send our basic-auth credentials. Bundling Vitessce
 * and serving it same-origin means one nginx auth block covers app and data
 * alike, and CORS leaves the problem entirely.
 *
 * WHY TWO AXES
 * The cohort has two genuinely different shapes. The ven series are serial
 * z-stacks of one tissue block — the axis is DEPTH, and a slider is right. The
 * GL/GX/LGG patients are flat sections taken at different CLINICAL TIMEPOINTS
 * (primary vs recurrent, split by treatment), frequently different specimens —
 * the axis is TIME, and a slider would imply a spatial relationship that does
 * not exist. The manifest carries the axis; this component honours it.
 *
 * One Vitessce config per section, fetched lazily — never a single
 * multi-dataset config, which would make Vitessce instantiate a loader for
 * every section in the cohort to display one.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Vitessce } from 'vitessce';

const DATA_ROOT = '/data';

/**
 * Built configs carry absolute URLs for whichever host they were generated
 * against. Every store sits flat inside a release directory, so rewriting each
 * `url` to /data/<version>/<basename> makes one build deployable on any host
 * without a rebuild — and keeps every fetch same-origin.
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

/** Tolerate an older manifest rather than render a blank page. */
function normalise(m) {
  if (!m) return null;
  if (Array.isArray(m.patients)) return m;
  const src = Array.isArray(m.samples) && typeof m.samples[0] === 'object'
    ? m.samples
    : [];
  const patients = src.map((s) => ({
    id: s.id,
    label: s.label ?? s.id,
    axis: 'z',
    modalities: s.modalities ?? [],
    n_sections: (s.planes ?? []).length,
    sections: (s.planes ?? []).map((p) => ({
      id: `${s.id}_z${p.z}`, label: `z${p.z}`, axis: 'z', order: p.z, ...p,
    })),
  }));
  return { ...m, patients, legend: m.legend ?? {} };
}

const readUrl = () => {
  const q = new URLSearchParams(window.location.search);
  return { patient: q.get('patient'), section: q.get('section') };
};

function writeUrl(patient, section) {
  const q = new URLSearchParams(window.location.search);
  if (patient) q.set('patient', patient); else q.delete('patient');
  if (section) q.set('section', section); else q.delete('section');
  window.history.replaceState(null, '', `${window.location.pathname}?${q}`);
}

function NicheKey({ legend, onClose }) {
  const entries = Object.entries(legend?.niche ?? {}).filter(([, v]) => v?.identity);
  if (!entries.length) return null;
  return (
    <div className="keypanel" role="dialog" aria-label="Niche key">
      <div className="keyhead">
        <strong>Spatial niches</strong>
        <button type="button" onClick={onClose} aria-label="Close niche key">×</button>
      </div>
      <ul>
        {entries.map(([code, v]) => (
          <li key={code}>
            <span className="sw" style={{ background: v.color }} aria-hidden="true" />
            <b>{code}</b>
            <span className="id">{v.identity}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Shell() {
  const [manifest, setManifest] = useState(null);
  const [patientId, setPatientId] = useState(null);
  const [sectionId, setSectionId] = useState(null);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [showKey, setShowKey] = useState(false);
  const [height, setHeight] = useState(() => Math.max(420, window.innerHeight - 74));

  useEffect(() => {
    const onResize = () => setHeight(Math.max(420, window.innerHeight - 74));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    fetch(`${DATA_ROOT}/current/manifest.json`, { cache: 'no-store' })
      .then((r) => { if (!r.ok) throw new Error(`manifest ${r.status}`); return r.json(); })
      .then((raw) => {
        const m = normalise(raw);
        if (!m?.patients?.length) throw new Error('manifest lists no patients');
        setManifest(m);
        const want = readUrl();
        const p = m.patients.find((x) => x.id === want.patient) ?? m.patients[0];
        setPatientId(p.id);
        const s = p.sections.find((x) => x.id === want.section) ?? p.sections[0];
        setSectionId(s ? s.id : null);
      })
      .catch((e) => setError(
        `Could not load the release manifest (${e.message}). Has a release been synced?`,
      ));
  }, []);

  const patient = useMemo(
    () => manifest?.patients.find((p) => p.id === patientId) ?? null,
    [manifest, patientId],
  );
  const sections = patient?.sections ?? [];
  const section = useMemo(
    () => sections.find((s) => s.id === sectionId) ?? null,
    [sections, sectionId],
  );

  useEffect(() => { if (patientId && sectionId) writeUrl(patientId, sectionId); },
    [patientId, sectionId]);

  useEffect(() => {
    if (!manifest || !section?.config) return;
    let cancelled = false;
    setConfig(null);
    fetch(`${DATA_ROOT}/${manifest.version}/${section.config}`, { cache: 'force-cache' })
      .then((r) => { if (!r.ok) throw new Error(`config ${r.status}`); return r.json(); })
      .then((c) => { if (!cancelled) setConfig(rebaseConfig(c, manifest.version)); })
      .catch((e) => { if (!cancelled) setError(`Could not load ${section.id} (${e.message}).`); });
    return () => { cancelled = true; };
  }, [manifest, section]);

  const onPatient = useCallback((e) => {
    const next = manifest.patients.find((p) => p.id === e.target.value);
    if (!next) return;
    setError(null);
    setPatientId(next.id);
    setSectionId(next.sections[0]?.id ?? null);
  }, [manifest]);

  const onSection = useCallback((e) => setSectionId(e.target.value), []);
  const onSlide = useCallback((e) => {
    const s = sections[Number(e.target.value)];
    if (s) setSectionId(s.id);
  }, [sections]);

  const idx = Math.max(0, sections.findIndex((s) => s.id === sectionId));
  const isDepth = patient?.axis === 'z';
  const many = sections.length > 1;
  const hasMS = Boolean(section?.ms_zarr);
  const patientHasMS = (patient?.modalities ?? []).includes('ms');

  return (
    <>
      <header className="bar">
        <h1>Venture Atlas</h1>

        {manifest && (
          <div className="ctl">
            <label htmlFor="patient">Patient</label>
            <select id="patient" value={patientId ?? ''} onChange={onPatient}>
              {manifest.patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                  {p.grade ? ` (${p.grade})` : ''}
                  {` · ${p.n_sections} ${p.axis === 'z' ? 'planes' : 'sections'}`}
                  {(p.modalities ?? []).includes('ms') ? ' · +MS' : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* A depth slider only where depth is real. Clinical timepoints get a
            list: sliding between a primary and a recurrent specimen would imply
            a spatial continuity that does not exist. */}
        {many && isDepth && (
          <div className="ctl">
            <label htmlFor="z">Z-plane</label>
            <input
              id="z" type="range" min={0} max={sections.length - 1} step={1}
              value={idx} onChange={onSlide}
            />
            <span className="zval">{section?.label}</span>
          </div>
        )}
        {many && !isDepth && (
          <div className="ctl">
            <label htmlFor="section">Section</label>
            <select id="section" value={sectionId ?? ''} onChange={onSection}>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </div>
        )}

        <span className="meta">
          {section?.n_cells ? `${section.n_cells.toLocaleString()} cells · ` : ''}
          {hasMS ? 'cells + MS ion density' : 'cells only'}
          {patientHasMS && !hasMS ? ' (no MS for this section)' : ''}
        </span>

        {manifest?.legend?.niche && (
          <button type="button" className="keybtn" onClick={() => setShowKey((v) => !v)}>
            Niche key
          </button>
        )}
        <span className="meta rel">{manifest?.version}</span>
      </header>

      <main className="stage" style={{ height }}>
        {error && <div className="msg err"><strong>Problem loading the atlas.</strong><p>{error}</p></div>}
        {!error && !config && <div className="msg"><p>Loading {section?.id ?? '…'}…</p></div>}
        {!error && config && <Vitessce config={config} theme="dark" height={height} />}
        {showKey && <NicheKey legend={manifest.legend} onClose={() => setShowKey(false)} />}
      </main>
    </>
  );
}

createRoot(document.getElementById('root')).render(<Shell />);
