// Deepfake assessment UI: "Likely deepfake / Likely authentic / Uncertain" with a detector estimate and range.
import { c, MONO, MUTED, eyebrow } from './ui.jsx';

export const DF_COLORS = { deepfake: '#D64545', authentic: '#3E9B5F', uncertain: MUTED };
const pct = (x) => `${Math.round(x * 100)}%`;

/** Compact pill for lists and headers. */
export function DeepfakePill({ d, h = 30, fs = 13, dark = false, style }) {
  if (!d) return null;
  return (
    <span title={d.why} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: h, padding: '0 13px', borderRadius: 999, background: dark ? c.hero : c.surface, color: dark ? '#fff' : c.ink, border: `1px solid ${dark ? c.hero : c.border}`, fontSize: fs, fontWeight: 700, whiteSpace: 'nowrap', ...style }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: DF_COLORS[d.key] }} />
      {d.label}
      {d.p != null && <span style={{ fontFamily: MONO, fontWeight: 600 }}>AI {pct(d.p)}</span>}
    </span>
  );
}

/** Full card: the answer, the model estimate with its range on a 0–100 scale, and what it was built from. */
export function DeepfakeCard({ d, title = 'AI-generation assessment', subject, onDriver }) {
  if (!d) return null;
  const col = DF_COLORS[d.key];
  const parts = [
    d.ai && { k: 'AI-generation detector', p: d.ai.p, lo: d.ai.lo, hi: d.ai.hi,
              note: d.ai.calibration_note || (d.ai.calibrated ? `calibrated${d.ai.auc != null ? ` · validation AUC ${d.ai.auc.toFixed(2)}` : ''}` : 'raw model score, not calibrated'),
              warn: d.ai.short_text ? 'short text: low reliability' : null },
    d.manipulation && { k: 'Manipulation evidence', p: d.manipulation.p, lo: d.manipulation.lo, hi: d.manipulation.hi, note: 'separate indicators; not added to the AI estimate' },
  ].filter(Boolean);
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0, overflowWrap: 'anywhere', padding: '18px 20px', borderRadius: 16, border: `1px solid ${c.border}`, borderLeft: `5px solid ${col}`, background: c.bg, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'baseline', gap: '6px 16px' }}>
        <span style={eyebrow}>{title}{subject ? ` · ${subject}` : ''}</span>
        {d.driver && (onDriver
          ? <button onClick={onDriver} style={{ border: 'none', background: 'none', padding: 0, fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, color: c.ink, textDecoration: 'underline', cursor: 'pointer' }}>Highest estimate: {d.driver}</button>
          : <span style={{ fontSize: 12.5, color: c.ink2 }}>Highest estimate: {d.driver}</span>)}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px 18px' }}>
        <span style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em', color: col }}>{d.label}</span>
        {d.p != null && (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ fontFamily: MONO, fontSize: 26, fontWeight: 600 }}>{pct(d.p)}</span>
            <span style={{ fontSize: 13, color: c.ink2 }}>AI-generation estimate · range <span style={{ fontFamily: MONO }}>{pct(d.lo)}–{pct(d.hi)}</span></span>
          </span>
        )}
      </div>
      {d.p != null && <Scale p={d.p} lo={d.lo} hi={d.hi} col={col} />}
      {d.why && <span style={{ fontSize: 13.5, color: c.ink2, lineHeight: 1.5 }}><b style={{ color: c.ink }}>Based on:</b> {d.why}.</span>}
      {parts.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(220px, 100%), 1fr))', gap: 10 }}>
          {parts.map((x) => (
            <div key={x.k} style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 12px', borderRadius: 12, background: c.surface }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ fontSize: 12.5, fontWeight: 700 }}>{x.k}</span>
                <span style={{ fontFamily: MONO, fontSize: 12.5, fontWeight: 600 }}>{pct(x.p)}</span>
              </div>
              <Bar lo={x.lo} hi={x.hi} p={x.p} />
              <span style={{ fontSize: 11.5, color: c.ink2 }}>{x.note}{x.warn ? ` · ${x.warn}` : ''}</span>
            </div>
          ))}
        </div>
      )}
      <span style={{ fontSize: 12, color: c.ink2, lineHeight: 1.5 }}>
        Likely deepfake means 65% or more with the low end of the range at 50% or more; likely authentic means 35% or less with the high end at 50% or less. Anything between is reported as uncertain. A low AI estimate does not rule out editing or misleading context. Results can be wrong; use the evidence and alternatives for human review, not as proof.
      </span>
    </section>
  );
}

function Scale({ p, lo, hi, col }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ position: 'relative', height: 14, borderRadius: 999, background: `linear-gradient(90deg, ${DF_COLORS.authentic}33 0 35%, ${c.line} 35% 65%, ${DF_COLORS.deepfake}33 65% 100%)` }}>
        <div style={{ position: 'absolute', top: 3, bottom: 3, left: `${lo * 100}%`, width: `${Math.max(hi - lo, 0.01) * 100}%`, borderRadius: 999, background: col, opacity: 0.55 }} />
        <div style={{ position: 'absolute', top: -3, bottom: -3, left: `${p * 100}%`, width: 3, marginLeft: -1.5, borderRadius: 2, background: c.ink }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: c.ink2, fontFamily: MONO }}>
        <span>0% AI score</span><span>35%</span><span>65%</span><span>100% AI score</span>
      </div>
    </div>
  );
}

function Bar({ lo, hi, p }) {
  return (
    <div style={{ position: 'relative', height: 6, borderRadius: 999, background: c.line }}>
      <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${lo * 100}%`, width: `${Math.max(hi - lo, 0.01) * 100}%`, borderRadius: 999, background: MUTED }} />
      <div style={{ position: 'absolute', top: -2, bottom: -2, left: `${p * 100}%`, width: 2, background: c.ink }} />
    </div>
  );
}
