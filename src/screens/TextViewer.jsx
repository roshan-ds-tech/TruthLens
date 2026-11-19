import { useEffect, useRef, useState } from 'react';
import { c, VERDICTS, YELLOW, MONO, Icon, eyebrow, h1, Muted, VerdictPill, fmtRange, preventThen } from '../ui.jsx';
import { useApi } from '../api/client.js';

const CLAIM_STATUS = {
  consistent: { label: 'Consistent', color: '#3E9B5F' },
  conflict: { label: 'Conflict', color: '#D64545' },
  unverifiable: { label: 'Not verified', color: '#8A8A85' },
};
const panel = { minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', background: c.bg };
const panelHeading = { margin: 0, padding: '14px 20px', borderBottom: `1px solid ${c.border}`, fontSize: 15, fontWeight: 700 };

export default function TextViewer({ go, active, caseId, evidenceId }) {
  const [focus, setFocus] = useState(null);
  const highlightRef = useRef(null);
  const caseQ = useApi(active && caseId ? `/cases/${caseId}` : null);
  const cs = caseQ.data?.id === caseId ? caseQ.data : null;
  const texts = cs?.evidence.filter((item) => item.kind === 'text') || [];
  // A sidebar click may still carry the ID of an image/audio item; choose text from this case instead.
  const id = active ? (texts.find((item) => item.id === evidenceId) || texts[0])?.id : null;
  const detailQ = useApi(id ? `/evidence/${id}` : null);
  const ev = detailQ.data?.id === id && detailQ.data?.kind === 'text' ? detailQ.data : null;

  useEffect(() => { setFocus(null); }, [id]);
  useEffect(() => { if (active && focus) highlightRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, [focus, active]);

  const back = <a href="#" onClick={preventThen(() => go('workspace', { caseId }))}
    style={{ display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none', fontSize: 13, fontWeight: 700 }}>
    <Icon name="arrow_back" size={18} />{caseId || 'Case'} workspace
  </a>;
  const rootStyle = { padding: '32px clamp(16px, 3vw, 40px) 56px', display: 'flex', flexDirection: 'column', gap: 22, minWidth: 0, color: c.ink };

  if (!ev) {
    const error = caseQ.error || detailQ.error;
    return <div style={rootStyle}>
      {back}<h1 style={h1}>Text evidence</h1>
      <Muted>{error ? `Could not load the text: ${error.message}` : caseQ.loading || (id && detailQ.loading) ? 'Loading…' : 'This case has no text evidence. Add a caption or text file from New case.'}</Muted>
    </div>;
  }

  const verdict = ev.verdict || { key: 'review', label: 'Not analyzed' };
  const claims = ev.claims || [];
  const findings = ev.findings || [];
  const text = ev.text || '';
  // Analyzer spans use Python character offsets, so preserve Unicode code points (including emoji).
  const chars = Array.from(text);
  const start = Math.max(0, Math.min(chars.length, Number(focus?.start) || 0));
  const end = Math.max(start, Math.min(chars.length, Number(focus?.end) || 0));
  const selection = end > start;
  const isCaption = ev.filename?.startsWith('Caption ·');

  return <div style={rootStyle}>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
      {back}
      <div style={eyebrow}>Evidence · {ev.case_id} · {ev.label} · Text</div>
      <h1 style={h1}>Text evidence</h1>
      <span style={{ fontSize: 16, color: c.ink2, overflowWrap: 'anywhere' }}>{ev.display_name}</span>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10 }}>
        <VerdictPill dot={VERDICTS[verdict.key]?.[1] || c.ink2} label={verdict.label} />
        {verdict.lo != null && <span style={{ fontFamily: MONO, fontSize: 13 }}>{fmtRange(verdict.lo, verdict.hi)}</span>}
        <span style={{ fontSize: 13, color: c.ink2 }}>{chars.length} characters · Original preserved read-only</span>
      </div>
      {verdict.why && <span style={{ fontSize: 14, color: c.ink2 }}><b style={{ color: c.ink }}>Why:</b> {verdict.why}</span>}
    </div>

    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: 20, minWidth: 0 }}>
      <section style={{ ...panel, flex: '2 1 520px' }}>
        <h2 style={panelHeading}>{isCaption ? 'Original caption' : 'Original text'}</h2>
        <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 18 }}>
          <p style={{ margin: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: 17, lineHeight: 1.8 }}>
            {selection ? <>{chars.slice(0, start).join('')}<mark ref={highlightRef} style={{ background: YELLOW, color: '#111', borderRadius: 3, padding: '2px 0' }}>{chars.slice(start, end).join('')}</mark>{chars.slice(end).join('')}</> : text || 'The text file is empty.'}
          </p>
          {selection && <button onClick={() => setFocus(null)} style={{ alignSelf: 'flex-start', border: 'none', background: 'none', color: c.ink, textDecoration: 'underline', fontFamily: 'inherit', cursor: 'pointer', padding: 0 }}>Clear highlight</button>}
          <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2, overflowWrap: 'anywhere' }}>sha256 {ev.sha256}</span>
        </div>
      </section>

      <aside style={{ display: 'flex', flexDirection: 'column', flex: '1 1 320px', minWidth: 0, gap: 20 }}>
        <section style={panel}>
          <h2 style={panelHeading}>Extracted claims · {claims.length}</h2>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {!claims.length && <Muted>{ev.status === 'analyzed' ? 'No checkable claims were extracted from this text.' : 'Run analysis from the workspace to extract and check claims.'}</Muted>}
            {claims.map((claim, i) => {
              const status = CLAIM_STATUS[claim.status] || CLAIM_STATUS.unverifiable;
              const selected = focus?.key === `claim-${i}`;
              return <button key={i} onClick={() => setFocus({ key: `claim-${i}`, start: claim.start, end: claim.end })}
                style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0, padding: 14, textAlign: 'left', border: `1px solid ${selected ? c.ink : c.border}`, borderRadius: 12, background: selected ? c.hl : c.bg, color: c.ink, fontFamily: 'inherit', cursor: 'pointer', overflowWrap: 'anywhere' }}>
                <span style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8, fontSize: 12, fontWeight: 700 }}>
                  <span style={{ textTransform: 'capitalize' }}>{claim.kind}</span><span style={{ color: status.color }}>{status.label}</span>
                </span>
                <span style={{ fontSize: 15, fontWeight: 600 }}>{claim.text}</span>
                {claim.detail && <span style={{ fontSize: 13, lineHeight: 1.5, color: c.ink2 }}>{claim.detail}</span>}
                {!!claim.evidence?.length && <span style={{ fontSize: 12, color: c.ink2 }}>Checked against: {claim.evidence.join(' · ')}</span>}
              </button>;
            })}
          </div>
        </section>
        <section style={{ ...panel, padding: 18, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Reading these results</h2>
          <Muted>A conflict means the caption disagrees with the available metadata or transcript. It does not establish which source is correct. Not verified means there was not enough information to check the claim.</Muted>
        </section>
      </aside>
    </div>

    <section style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
      <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Related findings · {findings.length}</h2>
      {!findings.length && <Muted>{ev.status === 'analyzed' ? 'No finding crossed its reporting threshold for this text.' : 'This text has not been analyzed yet. Return to the workspace to run analysis.'}</Muted>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(320px,100%),1fr))', gap: 12 }}>
        {findings.map((finding) => <article key={finding.id} style={{ ...panel, padding: 18, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 }}>
            <span style={{ fontFamily: MONO, fontSize: 12 }}>{finding.finding_id}</span>
            <span style={{ fontSize: 12, color: c.ink2 }}>{fmtRange(finding.conf_low, finding.conf_high)}</span>
          </div>
          <h3 style={{ margin: 0, fontSize: 16 }}>{finding.name}</h3>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: c.ink2 }}>{finding.explanation}</p>
          {!!finding.compare?.length && <dl style={{ display: 'flex', flexDirection: 'column', gap: 8, margin: 0, fontSize: 13 }}>
            {finding.compare.map((row) => <div key={row.k}><dt style={{ color: c.ink2 }}>{row.k}</dt><dd style={{ margin: '2px 0 0', overflowWrap: 'anywhere' }}>{row.v}</dd></div>)}
          </dl>}
          {!!finding.alternatives?.length && <details style={{ fontSize: 13, lineHeight: 1.6, color: c.ink2 }}><summary style={{ color: c.ink, cursor: 'pointer' }}>Alternative explanations</summary><ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>{finding.alternatives.map((item) => <li key={item}>{item}</li>)}</ul></details>}
          {finding.location?.type === 'text_span' && <button onClick={() => setFocus({ key: finding.finding_id, start: finding.location.start, end: finding.location.end })}
            style={{ alignSelf: 'flex-start', border: `1px solid ${c.border}`, borderRadius: 999, background: c.surface, color: c.ink, padding: '8px 12px', fontFamily: 'inherit', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Highlight in original text</button>}
        </article>)}
      </div>
    </section>
  </div>;
}
