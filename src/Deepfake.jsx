// Evidence assessment: calibrated estimates and explicit abstention on unsupported inputs.
import { c, MONO, MUTED } from './ui.jsx';

export const DF_COLORS = { deepfake: '#D64545', authentic: '#3E9B5F', uncertain: MUTED };
const pct = (x) => `${Math.round(x * 100)}%`;
const hasEstimate = (d) => d?.p != null && d.calibrated !== false && d.key !== 'uncertain';
const status = (d) => d.key === 'uncertain' ? 'Inconclusive' : d.label;

export function DeepfakePill({ d, h = 30, fs = 13, dark = false, style }) {
  if (!d) return null;
  return <span title={d.why} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: h, padding: '0 11px', borderRadius: 6, background: dark ? c.hero : c.surface, color: dark ? '#fff' : c.ink, border: `1px solid ${c.border}`, fontSize: fs, fontWeight: 600, whiteSpace: 'nowrap', ...style }}>
    <span style={{ width: 6, height: 6, borderRadius: '50%', background: DF_COLORS[d.key] }} />
    {status(d)}{hasEstimate(d) && <span style={{ fontFamily: MONO, fontSize: fs - 1 }}>AI {pct(d.p)}</span>}
  </span>;
}

export function DeepfakeCard({ d, title = 'Authenticity assessment', subject, onDriver }) {
  if (!d) return null;
  const estimated = hasEstimate(d);
  const diagnostic = d.ai?.diagnostic_only || d.ai?.calibration_scope === 'unvalidated-video';
  return <section style={{ minWidth: 0, padding: '16px 20px', border: `1px solid ${c.border}`, borderRadius: 12, background: c.bg, display: 'flex', flexDirection: 'column', gap: 10, overflowWrap: 'anywhere' }}>
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
      <span style={{ fontSize: 12, color: c.ink2, fontWeight: 600 }}>{title}{subject ? ` · ${subject}` : ''}</span>
      {d.driver && (onDriver
        ? <button onClick={onDriver} style={{ border: 'none', padding: 0, background: 'none', fontFamily: 'inherit', fontSize: 12, color: c.ink2, textDecoration: 'underline', cursor: 'pointer' }}>Evidence {d.driver}</button>
        : <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>Evidence {d.driver}</span>)}
    </div>
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '6px 16px' }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 20, fontWeight: 650, letterSpacing: '-.015em' }}>
        <span style={{ width: 7, height: 7, borderRadius: '50%', background: DF_COLORS[d.key] }} />{status(d)}
      </span>
      {estimated ? <span style={{ fontSize: 12, color: c.ink2 }}>AI-generation estimate <b style={{ fontFamily: MONO, color: c.ink }}>{pct(d.p)}</b> · range {pct(d.lo)}–{pct(d.hi)}</span>
        : <span style={{ fontSize: 12, color: c.ink2 }}>A reliable probability is not available</span>}
    </div>
    <p style={{ margin: 0, color: c.ink2, fontSize: 13, lineHeight: 1.55 }}>{d.why}</p>
    <details style={{ borderTop: `1px solid ${c.border}`, paddingTop: 9, fontSize: 12, color: c.ink2, lineHeight: 1.6 }}>
      <summary style={{ cursor: 'pointer', color: c.ink, fontWeight: 600 }}>Evidence and limitations</summary>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, paddingTop: 9 }}>
        {d.ai && <span><b style={{ color: c.ink }}>{diagnostic ? 'Experimental frame analysis: ' : 'Detector coverage: '}</b>{d.ai.calibration_note || (d.ai.short_text ? 'The text is too short for a reliable estimate.' : d.ai.calibrated ? 'Calibrated on a small labelled sample.' : 'No labelled calibration is available.')}</span>}
        {diagnostic && <span>Frame appearance scores are diagnostic signals, not percentages of video authenticity. Compression and scene content can cause false alarms.</span>}
        {d.manipulation && <span><b style={{ color: c.ink }}>Editing indicators:</b> assessed separately. Ordinary editing does not establish AI generation.</span>}
        <span>Review the source, flagged locations and alternative explanations. A low AI estimate does not rule out editing or misleading context; no automated result establishes authenticity.</span>
      </div>
    </details>
  </section>;
}
