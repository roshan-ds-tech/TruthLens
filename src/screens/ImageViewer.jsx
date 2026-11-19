import { useEffect, useState } from 'react';
import { c, VERDICTS, YELLOW, MONO, Icon, chipStyle, eyebrow, fmtRange, preventThen, Muted } from '../ui.jsx';
import { useApi } from '../api/client.js';
import { AuthImg } from '../api/media.jsx';

const LAYERS = [['ela', 'Error level', 'contrast'], ['noise', 'Noise map', 'grain'], ['copy', 'Copy-move', 'content_copy'], ['regions', 'Regions', 'crop_free']];
const ARTIFACT = { ela: 'ela.png', noise: 'noise.png', copy: 'copymove.png' };

const mono = { fontFamily: MONO };

export default function ImageViewer({ go, active, caseId, evidenceId }) {
  const [pos, setPos] = useState(46);
  const [sel, setSel] = useState(null);
  const [layers, setLayers] = useState({ ela: true, noise: false, copy: false, regions: true });
  const [limOpen, setLimOpen] = useState(false);
  const [missing, setMissing] = useState({});

  // Without an explicit item, show the first image of the open case.
  const caseQ = useApi(active && !evidenceId && caseId ? `/cases/${caseId}` : null);
  const fallback = caseQ.data?.evidence.find((e) => e.kind === 'image');
  const id = evidenceId && active ? evidenceId : fallback?.id;
  const evQ = useApi(active && id ? `/evidence/${id}` : null);
  const ev = evQ.data && evQ.data.kind === 'image' ? evQ.data : null;
  useEffect(() => { setSel(null); setMissing({}); }, [id]);

  if (!ev) {
    return (
      <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 10, color: c.ink }}>
        <a href="#" onClick={preventThen(() => go('workspace'))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />Case workspace</a>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em' }}>Image evidence</h1>
        <Muted>{evQ.loading || caseQ.loading ? 'Loading…' : evQ.error ? `Could not load the image: ${evQ.error.message}` : 'This case has no image evidence.'}</Muted>
      </div>
    );
  }

  const regionsF = ev.findings.filter((f) => f.location.type === 'bbox');
  // finding coordinates are in display orientation (EXIF rotation applied), so size the frame from them
  const W = regionsF[0]?.location.image_w || ev.width || 1, H = regionsF[0]?.location.image_h || ev.height || 1;
  const selected = sel || regionsF[0]?.finding_id;
  const v = ev.verdict || { key: 'review', label: 'Not analyzed', why: 'run the analysis to see indicators' };
  const layerLabel = LAYERS.filter(([k]) => layers[k] && k !== 'regions').map(([, l]) => l.toUpperCase()).join(' + ') || 'NONE';
  const posPct = pos + '%';
  const notes = [...(ev.extra?.metadata_notes || []), ...(ev.warnings || [])];
  const conflicts = (ev.exif_rows || []).filter((x) => x.conflict).length;
  const box = (L) => ({ left: `${(L.x / W) * 100}%`, top: `${(L.y / H) * 100}%`, width: `${(L.w / W) * 100}%`, height: `${(L.h / H) * 100}%` });

  return (
    <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 22, color: c.ink }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <a href="#" onClick={preventThen(() => go('workspace', { caseId: ev.case_id }))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />{ev.case_id} workspace</a>
        <div style={eyebrow}>Evidence · <span style={mono}>{ev.case_id}</span> · {ev.label} · Image · sha256 <span style={mono}>{ev.sha_short}</span></div>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em' }}>{ev.display_name}</h1>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 30, padding: '0 13px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 13, fontWeight: 700 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: VERDICTS[v.key][1] }} />{v.label} {v.lo != null && <span style={{ ...mono, fontWeight: 500, color: c.ink2 }}>{fmtRange(v.lo, v.hi)}</span>}
          </span>
          <span style={{ fontSize: 14, color: c.ink2 }}><b style={{ color: c.ink }}>Why:</b> {v.why}.</span>
          <a href="#" onClick={preventThen(() => setLimOpen((x) => !x))} style={{ fontSize: 13.5, fontWeight: 700 }}>Limitations</a>
        </div>
        {limOpen && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 760 }}>
            {[...notes, 'Error-level and noise maps react to sharp edges, text and platform recompression; read them with the region cards.', 'A fully AI-generated image without later editing may show no indicator at all.'].map((n) => <Muted key={n}>· {n}</Muted>)}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-start' }}>
        <section style={{ flex: '2 1 600px', minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {LAYERS.map(([k, label, icon]) => (
                <button key={k} onClick={() => setLayers((s) => ({ ...s, [k]: !s[k] }))} style={{ ...chipStyle(layers[k]), gap: 6, height: 32, padding: '0 13px', fontSize: 12.5 }}>
                  <Icon name={icon} size={16} />{label}
                </button>
              ))}
            </div>
            <span style={{ fontSize: 12, color: c.ink2 }}>Drag to compare · click a box to open its finding</span>
          </div>
          <div style={{ padding: 16 }}>
            <div style={{ position: 'relative', aspectRatio: `${W}/${H}`, maxHeight: '70vh', margin: '0 auto', borderRadius: 12, overflow: 'hidden', background: 'repeating-linear-gradient(135deg,#EFEFEB 0 12px,#F7F7F5 12px 24px)', userSelect: 'none' }}>
              <AuthImg path={ev.media_url} alt="original" draggable={false} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'fill' }} />
              <div style={{ position: 'absolute', inset: 0, clipPath: `inset(0 0 0 ${posPct})`, background: '#151515' }}>
                <AuthImg path={ev.media_url} alt="" draggable={false} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'fill', filter: 'grayscale(1) brightness(.35)' }} />
                {['ela', 'noise', 'copy'].map((k) => layers[k] && !missing[k] && (
                  <AuthImg key={k} path={`/api/evidence/${ev.id}/artifacts/${ARTIFACT[k]}`} alt="" draggable={false} onError={() => setMissing((m) => ({ ...m, [k]: true }))}
                    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'fill', mixBlendMode: 'screen' }} />
                ))}
                <span style={{ position: 'absolute', right: 12, bottom: 12, ...mono, fontSize: 10.5, color: '#fff', background: 'rgba(0,0,0,.55)', padding: '3px 8px', borderRadius: 6, whiteSpace: 'nowrap' }}>ANALYSIS · {layerLabel}{Object.keys(missing).length ? ' · run analysis for maps' : ''}</span>
              </div>
              <span style={{ position: 'absolute', left: 12, top: 12, ...mono, fontSize: 10.5, color: c.ink, background: c.bg, border: `1px solid ${c.border}`, padding: '3px 8px', borderRadius: 6 }}>ORIGINAL</span>
              <input type="range" min="0" max="100" value={pos} onChange={(e) => setPos(+e.target.value)} aria-label="Compare original and analysis" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', margin: 0, opacity: 0, cursor: 'ew-resize', zIndex: 2 }} />
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: posPct, width: 2, marginLeft: -1, background: YELLOW, zIndex: 1, pointerEvents: 'none' }}>
                <span style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: 34, height: 34, borderRadius: '50%', background: YELLOW, border: '2px solid #111111', color: '#111111', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name="code" size={18} /></span>
              </div>
              {layers.regions && regionsF.map((f, i) => {
                const on = selected === f.finding_id;
                return (
                  <button key={f.finding_id} title={f.finding_id} onClick={() => setSel(f.finding_id)} style={{ position: 'absolute', ...box(f.location), border: `2px solid ${on ? YELLOW : '#fefefe'}`, borderRadius: 6, background: on ? 'rgba(255,210,63,.12)' : 'transparent', zIndex: 3, cursor: 'pointer', padding: 0 }}>
                    <span style={{ position: 'absolute', left: -2, top: -2, width: 22, height: 22, borderRadius: '6px 0 6px 0', background: on ? YELLOW : '#fefefe', color: '#111111', ...mono, fontSize: 11.5, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{i + 1}</span>
                  </button>
                );
              })}
              {layers.regions && regionsF.filter((f) => f.location.pair).map((f) => (
                <div key={f.finding_id + 'pair'} style={{ position: 'absolute', ...box(f.location.pair), border: '1.5px dashed #fff', borderRadius: 4, zIndex: 3, pointerEvents: 'none' }} />
              ))}
            </div>
          </div>
        </section>

        <aside style={{ flex: '1 1 340px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={eyebrow}>Flagged regions · {regionsF.length}</span>
            {!regionsF.length && <Muted>{ev.status === 'analyzed' ? 'No region crossed its threshold.' : 'Not analyzed yet.'}</Muted>}
            {ev.findings.map((f) => {
              const n = regionsF.indexOf(f) + 1;
              const on = selected === f.finding_id;
              return (
                <button key={f.finding_id} onClick={() => setSel(f.finding_id)} style={{ textAlign: 'left', display: 'flex', gap: 12, padding: '12px 14px', borderRadius: 14, border: `1px solid ${on ? c.ink : c.border}`, background: c.bg, boxShadow: on ? '0 0 0 3px rgba(255,210,63,.55)' : 'none', fontFamily: 'inherit', color: c.ink, cursor: 'pointer' }}>
                  <span style={{ width: 24, height: 24, flex: 'none', borderRadius: 7, background: on ? YELLOW : c.bg, color: on ? '#111111' : c.ink, border: `1.5px solid ${c.ink}`, ...mono, fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{n > 0 ? n : <Icon name={f.loc_icon} size={14} />}</span>
                  <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                      <span style={{ ...mono, fontSize: 11.5, fontWeight: 600 }}>{f.finding_id}</span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 20, padding: '0 8px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 11, fontWeight: 600 }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: VERDICTS[f.verdict.key][1] }} />{f.verdict.label}
                      </span>
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 700 }}>{f.name} · {f.loc_label}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: c.line }}>
                        <div style={{ position: 'absolute', top: 0, bottom: 0, left: f.conf_low * 100 + '%', width: (f.conf_high - f.conf_low) * 100 + '%', borderRadius: 999, background: f.verdict.key === 'inc' ? '#8A8A85' : c.ink }} />
                      </div>
                      <span style={{ ...mono, fontSize: 11.5 }}>{fmtRange(f.conf_low, f.conf_high)}</span>
                    </div>
                    {on && (
                      <>
                        <span style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.45 }}>{f.explanation}</span>
                        {f.alternatives[0] && <span style={{ fontSize: 12.5, lineHeight: 1.45 }}><b>Alternative:</b> <span style={{ color: c.ink2 }}>{f.alternatives[0]}</span></span>}
                      </>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          <section style={{ border: `1px solid ${c.border}`, borderRadius: 14, overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', background: c.surface, borderBottom: `1px solid ${c.border}` }}>
              <span style={{ fontSize: 14, fontWeight: 700 }}>Metadata · EXIF</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: c.ink2 }}><span style={{ width: 7, height: 7, borderRadius: '50%', background: conflicts ? '#E8A33D' : '#3E9B5F' }} />{conflicts} conflict{conflicts === 1 ? '' : 's'}</span>
            </div>
            {(ev.exif_rows || []).map(({ k, v: val, note, conflict }) => (
              <div key={k} style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 10, padding: '9px 14px', borderBottom: `1px solid ${c.line}`, background: conflict ? c.hl : c.bg }}>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>{k}</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                  <span style={{ ...mono, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, wordBreak: 'break-all' }}>
                    {conflict && <span style={{ width: 7, height: 7, flex: 'none', borderRadius: '50%', background: '#E8A33D' }} />}{val}
                  </span>
                  {conflict && <span style={{ fontSize: 11.5, color: c.ink2 }}>{note}</span>}
                </div>
              </div>
            ))}
          </section>
        </aside>
      </div>
    </div>
  );
}
