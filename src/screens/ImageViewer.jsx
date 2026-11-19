import { useState } from 'react';
import { c, YELLOW, MONO, Icon, chipStyle, eyebrow, fmtRange, preventThen } from '../ui.jsx';

const LAYERS = [['ela', 'Error level', 'contrast'], ['noise', 'Noise map', 'grain'], ['copy', 'Copy-move', 'content_copy'], ['regions', 'Regions', 'crop_free']];

const V = { ind: ['Indicators', '#E8A33D'], inc: ['Inconclusive', '#8A8A85'] };

const REGIONS = [
  { n: 1, id: 'F-IMG-003', name: 'Error level inconsistency', where: 'podium', x: '40%', y: '46%', w: '22%', h: '40%', lo: 0.52, hi: 0.71, v: 'ind', expl: 'The podium area recompresses at a different level from the surrounding frame.', alt: 'Recompression by social platform.' },
  { n: 2, id: 'F-IMG-004', name: 'Copy-move match', where: 'banner logo', x: '64%', y: '12%', w: '14%', h: '16%', lo: 0.38, hi: 0.55, v: 'inc', expl: 'A patch of the banner matches another area at the top left.', alt: 'Repeating logo printed on the banner itself.' },
  { n: 3, id: 'F-IMG-005', name: 'Noise map discontinuity', where: 'left of podium', x: '24%', y: '38%', w: '14%', h: '30%', lo: 0.48, hi: 0.66, v: 'ind', expl: 'Sensor noise in this patch is finer than in the rest of the photo.', alt: 'Local denoising applied by the phone camera.' },
];

const EXIF = [
  ['Make / Model', 'samsung SM-A525F'],
  ['DateTimeOriginal', '2024:03:03 10:41:22', 'Caption says 12 Nov 2026 (F-TXT-001)'],
  ['Software', 'Adobe Photoshop 25.1 (Windows)', 'Editor tag on a phone photo'],
  ['Image size', '1280 × 720'],
  ['Thumbnail', '160 × 120 · differs from main image', 'Thumbnail shows an empty podium'],
  ['JPEG quality (est.)', '≈82 · two quantization passes'],
  ['GPS', 'not present'],
  ['Color space', 'sRGB'],
  ['File modified', '2026:11:12 21:36:04'],
];

const mono = { fontFamily: MONO };

export default function ImageViewer({ go }) {
  const [pos, setPos] = useState(46);
  const [sel, setSel] = useState('F-IMG-003');
  const [layers, setLayers] = useState({ ela: true, noise: false, copy: false, regions: true });

  const layerLabel = LAYERS.filter(([k]) => layers[k] && k !== 'regions').map(([, l]) => l.toUpperCase()).join(' + ') || 'NONE';
  const posPct = pos + '%';

  return (
    <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 22, color: c.ink }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <a href="#" onClick={preventThen(() => go('workspace'))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />C-0007 workspace</a>
        <div style={eyebrow}>Evidence · <span style={mono}>C-0007</span> · Image · sha256 <span style={mono}>3b7e0d19…a4c2</span></div>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.035em' }}>podium_photo.jpg</h1>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 30, padding: '0 13px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 13, fontWeight: 700 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#E8A33D' }} />Indicators <span style={{ ...mono, fontWeight: 500, color: c.ink2 }}>0.52–0.71</span>
          </span>
          <span style={{ fontSize: 14, color: c.ink2 }}><b style={{ color: c.ink }}>Why:</b> the podium recompresses differently from the rest of the photo, and the capture date conflicts with the caption.</span>
          <a href="#" onClick={(e) => e.preventDefault()} style={{ fontSize: 13.5, fontWeight: 700 }}>Limitations</a>
        </div>
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
            <div style={{ position: 'relative', aspectRatio: '16/9', borderRadius: 12, overflow: 'hidden', background: 'repeating-linear-gradient(135deg,#EFEFEB 0 12px,#F7F7F5 12px 24px)', userSelect: 'none' }}>
              <span style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', ...mono, fontSize: 11.5, color: '#8A8A85' }}>original photo · speaker at podium, banner behind</span>
              <div style={{ position: 'absolute', inset: 0, clipPath: `inset(0 0 0 ${posPct})`, background: '#151515' }}>
                <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(90deg,rgba(255,255,255,.035) 0 2px,transparent 2px 5px),repeating-linear-gradient(0deg,rgba(255,255,255,.03) 0 2px,transparent 2px 6px)' }} />
                {layers.ela && <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 14% 22% at 51% 66%,rgba(255,210,63,.9),rgba(255,210,63,.25) 55%,transparent 75%),radial-gradient(ellipse 8% 7% at 71% 21%,rgba(255,210,63,.45),transparent 80%),radial-gradient(ellipse 30% 20% at 30% 90%,rgba(255,255,255,.08),transparent)' }} />}
                {layers.noise && (
                  <>
                    <div style={{ position: 'absolute', left: '24%', top: '38%', width: '14%', height: '30%', background: 'repeating-linear-gradient(45deg,rgba(255,255,255,.22) 0 1px,transparent 1px 3px)', borderRadius: 4 }} />
                    <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0 1px,transparent 1px 4px)' }} />
                  </>
                )}
                {layers.copy && [['64%', '12%', 'A'], ['16%', '10%', 'A′']].map(([left, top, tag]) => (
                  <div key={tag} style={{ position: 'absolute', left, top, width: '14%', height: '16%', border: '1.5px dashed #fff', borderRadius: 4 }}>
                    <span style={{ position: 'absolute', right: 4, top: 2, ...mono, fontSize: 10, color: '#fff' }}>{tag}</span>
                  </div>
                ))}
                <span style={{ position: 'absolute', right: 12, bottom: 12, ...mono, fontSize: 10.5, color: '#fff', background: 'rgba(0,0,0,.55)', padding: '3px 8px', borderRadius: 6, whiteSpace: 'nowrap' }}>ANALYSIS · {layerLabel}</span>
              </div>
              <span style={{ position: 'absolute', left: 12, top: 12, ...mono, fontSize: 10.5, color: c.ink, background: c.bg, border: `1px solid ${c.border}`, padding: '3px 8px', borderRadius: 6 }}>ORIGINAL</span>
              <input type="range" min="0" max="100" value={pos} onChange={(e) => setPos(+e.target.value)} aria-label="Compare original and analysis" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', margin: 0, opacity: 0, cursor: 'ew-resize', zIndex: 2 }} />
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: posPct, width: 2, marginLeft: -1, background: YELLOW, zIndex: 1, pointerEvents: 'none' }}>
                <span style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: 34, height: 34, borderRadius: '50%', background: YELLOW, border: '2px solid #111111', color: '#111111', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name="code" size={18} /></span>
              </div>
              {layers.regions && REGIONS.map((r) => {
                const on = sel === r.id;
                return (
                  <button key={r.id} title={r.id} onClick={() => setSel(r.id)} style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, border: `2px solid ${on ? YELLOW : '#fefefe'}`, borderRadius: 6, background: on ? 'rgba(255,210,63,.12)' : 'transparent', zIndex: 3, cursor: 'pointer', padding: 0 }}>
                    <span style={{ position: 'absolute', left: -2, top: -2, width: 22, height: 22, borderRadius: '6px 0 6px 0', background: on ? YELLOW : '#fefefe', color: '#111111', ...mono, fontSize: 11.5, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{r.n}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        <aside style={{ flex: '1 1 340px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={eyebrow}>Flagged regions · {REGIONS.length}</span>
            {REGIONS.map((r) => {
              const on = sel === r.id;
              const [verdict, dot] = V[r.v];
              return (
                <button key={r.id} onClick={() => setSel(r.id)} style={{ textAlign: 'left', display: 'flex', gap: 12, padding: '12px 14px', borderRadius: 14, border: `1px solid ${on ? c.ink : c.border}`, background: c.bg, boxShadow: on ? '0 0 0 3px rgba(255,210,63,.55)' : 'none', fontFamily: 'inherit', color: c.ink, cursor: 'pointer' }}>
                  <span style={{ width: 24, height: 24, flex: 'none', borderRadius: 7, background: on ? YELLOW : c.bg, color: on ? '#111111' : c.ink, border: `1.5px solid ${c.ink}`, ...mono, fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{r.n}</span>
                  <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                      <span style={{ ...mono, fontSize: 11.5, fontWeight: 600 }}>{r.id}</span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 20, padding: '0 8px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 11, fontWeight: 600 }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: dot }} />{verdict}
                      </span>
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 700 }}>{r.name} · {r.where}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: c.line }}>
                        <div style={{ position: 'absolute', top: 0, bottom: 0, left: r.lo * 100 + '%', width: (r.hi - r.lo) * 100 + '%', borderRadius: 999, background: r.v === 'inc' ? '#8A8A85' : c.ink }} />
                      </div>
                      <span style={{ ...mono, fontSize: 11.5 }}>{fmtRange(r.lo, r.hi)}</span>
                    </div>
                    {on && (
                      <>
                        <span style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.45 }}>{r.expl}</span>
                        <span style={{ fontSize: 12.5, lineHeight: 1.45 }}><b>Alternative:</b> <span style={{ color: c.ink2 }}>{r.alt}</span></span>
                      </>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          <section style={{ border: `1px solid ${c.border}`, borderRadius: 14, overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', background: c.surface, borderBottom: `1px solid ${c.border}` }}>
              <span style={{ fontSize: 14, fontWeight: 800 }}>Metadata · EXIF</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: c.ink2 }}><span style={{ width: 7, height: 7, borderRadius: '50%', background: '#E8A33D' }} />3 conflicts</span>
            </div>
            {EXIF.map(([k, v, note]) => (
              <div key={k} style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 10, padding: '9px 14px', borderBottom: `1px solid ${c.line}`, background: note ? c.hl : c.bg }}>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>{k}</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                  <span style={{ ...mono, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, wordBreak: 'break-all' }}>
                    {note && <span style={{ width: 7, height: 7, flex: 'none', borderRadius: '50%', background: '#E8A33D' }} />}{v}
                  </span>
                  {note && <span style={{ fontSize: 11.5, color: c.ink2 }}>{note}</span>}
                </div>
              </div>
            ))}
          </section>
        </aside>
      </div>
    </div>
  );
}
