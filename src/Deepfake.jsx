// Evidence assessment: editing status and AI-generation signal are separate questions, shown separately.
import { c, MONO, MUTED } from './ui.jsx';

export const DF_COLORS = { deepfake: '#D64545', authentic: '#4A7FB0', uncertain: MUTED };
export const ED_COLORS = { edited: '#D64545', possible: '#E8A33D', metadata: '#B58A2E', none: '#3E9B5F', unavailable: MUTED };
const pct = (x) => `${Math.round(x * 100)}%`;
const hasEstimate = (d) => d?.p != null && d.calibrated !== false && d.key !== 'uncertain';
const short = { edited: 'Edited', possible: 'Possible editing', metadata: 'Metadata changed', none: 'No editing indicators', unavailable: 'Editing unavailable' };
const aiShort = (d) => (d.key === 'deepfake' ? 'AI signal strong' : d.key === 'authentic' ? 'AI signal low' : 'AI check inconclusive');

const dot = (color, size = 6) => <span style={{ width: size, height: size, flex: 'none', borderRadius: '50%', background: color }} />;

/** Compact pill: editing status first, AI-generation signal second. */
export function DeepfakePill({ d, h = 30, fs = 13, dark = false, style }) {
  if (!d) return null;
  const ed = d.editing;
  return <span title={[ed?.label, d.label, d.why].filter(Boolean).join(' · ')} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: h, padding: '0 11px', borderRadius: 6, background: dark ? c.hero : c.surface, color: dark ? '#fff' : c.ink, border: `1px solid ${c.border}`, fontSize: fs, fontWeight: 600, whiteSpace: 'nowrap', ...style }}>
    {ed && <>{dot(ED_COLORS[ed.key])}{short[ed.key]}<span style={{ opacity: 0.4 }}>·</span></>}
    {dot(DF_COLORS[d.key])}{aiShort(d)}{hasEstimate(d) && <span style={{ fontFamily: MONO, fontSize: fs - 1 }}>{pct(d.p)}</span>}
  </span>;
}

function Row({ title, color, status, detail, children }) {
  return <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
    <span style={{ fontSize: 11.5, color: c.ink2, fontWeight: 600 }}>{title}</span>
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 18, fontWeight: 650, letterSpacing: '-.01em' }}>{dot(color, 8)}{status}</span>
    {detail && <span style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.5 }}>{detail}</span>}
    {children}
  </div>;
}

export function DeepfakeCard({ d, title = 'Assessment', subject, onDriver }) {
  if (!d) return null;
  const ed = d.editing;
  const estimated = hasEstimate(d);
  const diagnostic = d.ai?.diagnostic_only || d.diagnostic_only;
  const aiTitle = d.kind === 'audio' ? 'Synthetic-speech assessment' : d.kind === 'text' ? 'AI-writing assessment' : 'AI-generation assessment';
  return <section style={{ minWidth: 0, padding: '16px 20px', border: `1px solid ${c.border}`, borderRadius: 12, background: c.bg, display: 'flex', flexDirection: 'column', gap: 12, overflowWrap: 'anywhere' }}>
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
      <span style={{ fontSize: 12, color: c.ink2, fontWeight: 600 }}>{title}{subject ? ` · ${subject}` : ''}</span>
      {d.driver && (onDriver
        ? <button onClick={onDriver} style={{ border: 'none', padding: 0, background: 'none', fontFamily: 'inherit', fontSize: 12, color: c.ink2, textDecoration: 'underline', cursor: 'pointer' }}>AI signal from {d.driver}</button>
        : <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>AI signal from {d.driver}</span>)}
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
      {ed && <Row title="Editing assessment" color={ED_COLORS[ed.key]} status={ed.label}
        detail={(ed.types?.length && ed.key !== 'none' ? `Detected: ${ed.types.join(', ')}. ` : '') + (ed.items?.length ? `${ed.note}` : ed.note)} />}
      <Row title={aiTitle} color={DF_COLORS[d.key]} status={d.label}
        detail={estimated ? `Estimate ${pct(d.p)} (range ${pct(d.lo)}–${pct(d.hi)}). ${d.why}` : d.why} />
    </div>
    <details style={{ borderTop: `1px solid ${c.border}`, paddingTop: 9, fontSize: 12, color: c.ink2, lineHeight: 1.6 }}>
      <summary style={{ cursor: 'pointer', color: c.ink, fontWeight: 600 }}>What these results mean</summary>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, paddingTop: 9 }}>
        <span><b style={{ color: c.ink }}>Editing</b> asks whether parts of the file were changed (pasted or copied regions, cuts, splices, metadata). <b style={{ color: c.ink }}>AI generation</b> asks whether the content looks machine-made. They are different questions: an edited photo can have a low AI signal.</span>
        {diagnostic && <span>Video frame scores are experimental diagnostics, not a percentage of authenticity.</span>}
        {d.ai?.calibration_note && <span>{d.ai.calibration_note}</span>}
        <span>"No editing indicators" and "low AI signal" do not prove a file is original. Check the source and the flagged locations.</span>
      </div>
    </details>
  </section>;
}
