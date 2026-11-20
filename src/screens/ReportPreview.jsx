import { c, YELLOW, MONO, Icon, Logo, eyebrow, fmtRange, preventThen, PrimaryButton, SecondaryButton, Muted } from '../ui.jsx';
import { useState } from 'react';
import { useApi, fmtBytes, shortHash, download } from '../api/client.js';
import { AuthImg } from '../api/media.jsx';

// The report pages are print documents: they stay dark-on-white in both themes.
const DOT = { strong: '#D64545', indicators: '#E8A33D', inconclusive: '#8A8A85', none: '#3E9B5F' };

const mono = { fontFamily: MONO };
const paper = { width: 794, maxWidth: '100%', minHeight: 1123, background: '#fff', color: '#111', boxShadow: '0 1px 3px rgba(17,17,17,.08),0 12px 40px rgba(17,17,17,.06)', padding: '56px 60px 44px', display: 'flex', flexDirection: 'column', gap: 26, fontSize: 12.5, lineHeight: 1.5 };
const section = { display: 'flex', flexDirection: 'column', gap: 8 };
const label = { fontSize: 10, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: '#5F5F5A' };
const tableHead = { display: 'grid', gap: 10, padding: '8px 12px', background: '#F7F7F5', fontSize: 10, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: '#5F5F5A' };
const tableRow = { display: 'grid', gap: 10, padding: '8px 12px', borderTop: '1px solid #EFEFEB' };

const EV_COLS = '1.6fr .7fr .8fr 1.3fr';
const DEC_COLS = '90px 80px 110px 1fr';

export default function ReportPreview({ go, active, caseId }) {
  const rep = useApi(active && caseId ? `/cases/${caseId}/report` : null);
  const r = rep.data;
  const [dlError, setDlError] = useState('');
  const get = (path, ext) => download(path, `Vero_${r.case.id}_report.${ext}`).catch((e) => setDlError(e.message));

  if (!r) {
    return (
      <div style={{ color: c.ink, background: c.surface, minHeight: '100%' }}>
        <div style={{ padding: '28px 40px 20px', display: 'flex', flexDirection: 'column', gap: 10, background: c.bg, borderBottom: `1px solid ${c.border}` }}>
          <a href="#" onClick={preventThen(() => go('workspace'))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />{caseId || 'Case'} workspace</a>
          <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em' }}>Forensic report preview</h1>
          <Muted>{rep.loading ? 'Loading…' : 'No report yet for this case. Use Export report in the case workspace to build one.'}</Muted>
        </div>
      </div>
    );
  }

  const historicalAssessment = r.deepfake && r.deepfake.version !== 'ai-only-v3';
  const v = r.verdict;
  const ev = r.evidence;
  const half = Math.ceil(r.findings.length / 2);
  const generated = r.generated_at.slice(0, 16).replace('T', ' ');
  return (
    <div style={{ color: c.ink, background: c.surface, minHeight: '100%' }}>
      <div style={{ padding: '28px 40px 20px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, background: c.bg, borderBottom: `1px solid ${c.border}` }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <a href="#" onClick={preventThen(() => go('workspace', { caseId: r.case.id }))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />{r.case.id} workspace</a>
          <div style={eyebrow}>Report · <span style={mono}>{r.case.id}</span> · Draft {r.draft} · on-screen summary{r.pdf_pages ? ` · PDF: ${r.pdf_pages} A4 page${r.pdf_pages === 1 ? '' : 's'}` : ''}</div>
          <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em' }}>Forensic report preview</h1>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <SecondaryButton onClick={() => get(r.files.json, 'json')}><Icon name="data_object" size={19} />Export JSON</SecondaryButton>
          <PrimaryButton onClick={() => r.files.pdf && get(r.files.pdf, 'pdf')} style={{ height: 40, padding: '0 18px', opacity: r.files.pdf ? 1 : 0.55 }}>Download PDF<Icon name="arrow_forward" size={19} /></PrimaryButton>
          {!r.files.pdf && <Muted style={{ fontSize: 12 }}>PDF unavailable on this machine; <a href="#" onClick={(e) => { e.preventDefault(); get(r.files.html, 'html'); }}>download the HTML</a>.</Muted>}
          {dlError && <Muted style={{ fontSize: 12 }}>{dlError}</Muted>}
        </div>
      </div>

      <div style={{ padding: '32px 24px 64px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
        <article style={paper}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingBottom: 18, borderBottom: '2px solid #111' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <Logo lockup size={30} theme="light" />
                <span style={{ fontSize: 10.5, color: '#5F5F5A' }}>Forensic report</span>
              </div>
            </div>
            <div style={{ textAlign: 'right', ...mono, fontSize: 10.5, color: '#5F5F5A', lineHeight: 1.6 }}>{r.case.id} · draft {r.draft}<br />generated {generated} UTC<br />investigator {r.case.investigator}</div>
          </div>

          <div style={section}>
            <span style={label}>Summary</span>
            <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, letterSpacing: '-0.018em', lineHeight: 1.15 }}>{r.case.title}</h2>
            <p style={{ margin: 0, color: '#333', textWrap: 'pretty' }}>{r.summary}</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 20, padding: '18px 20px', borderRadius: 12, background: '#111', color: '#fff' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ ...label, color: YELLOW }}>Verdict</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 18, fontWeight: 700 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: DOT[v.band] || '#8A8A85' }} />{v.label}</span>
              {v.lo != null && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: '#333' }}>
                    <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${v.lo * 100}%`, width: `${(v.hi - v.lo) * 100}%`, background: YELLOW, borderRadius: 999 }} />
                  </div>
                  <span style={{ ...mono, fontSize: 11, color: YELLOW }}>{fmtRange(v.lo, v.hi)}</span>
                </div>
              )}
            </div>
            <p style={{ margin: 0, color: '#D8D8D2', fontSize: 12.5 }}><b style={{ color: '#fff' }}>Why:</b> {v.why}. The range reflects agreement between analyzers, not a probability of editing.</p>
          </div>

          {r.deepfake && <div style={section}>
            <span style={label}>AI-generation assessment</span>
            <strong>{historicalAssessment ? 'Historical assessment — re-run analysis and export a new report' : <>{r.deepfake.label}{r.deepfake.p != null ? ` · AI estimate ${Math.round(r.deepfake.p * 100)}%` : ''}</>}</strong>
            <span style={{ color: '#5F5F5A' }}>{historicalAssessment ? 'This report preserves a previous scoring method. Its original downloads remain unchanged.' : `${r.deepfake.why}. Editing indicators are separate; this is not proof.`}</span>
          </div>}

          <div style={section}>
            <span style={label}>Evidence</span>
            <div style={{ border: '1px solid #E8E8E4', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ ...tableHead, gridTemplateColumns: EV_COLS }}><span>File</span><span>Type</span><span>Size</span><span>SHA-256</span></div>
              {ev.map((e) => (
                <div key={e.label} style={{ ...tableRow, gridTemplateColumns: EV_COLS }}>
                  <span style={{ fontWeight: 600 }}>{e.label} · {e.name}</span><span>{e.type}</span><span>{fmtBytes(e.size)}</span><span style={{ ...mono, fontSize: 11 }}>{shortHash(e.sha256)}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={section}>
            <span style={label}>Findings · {r.findings.length}</span>
            {!r.findings.length && <span style={{ color: '#5F5F5A' }}>No analyzer produced a finding above its threshold.</span>}
            {r.findings.slice(0, half).map((f) => <ReportFinding key={f.finding_id} f={f} caseId={r.case.id} />)}
          </div>
          <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 10, color: '#8A8A85' }}><span>Vero {r.app_version} · generated {r.generated_where || 'on device'}</span><span>summary · part 1</span></div>
        </article>

        <article style={paper}>
          <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 12, borderBottom: '1px solid #E8E8E4', ...mono, fontSize: 10.5, color: '#5F5F5A' }}><span>{r.case.id} · {r.case.title}</span><span>draft {r.draft}</span></div>
          {r.findings.length > half && (
            <div style={section}>
              <span style={label}>Findings (continued)</span>
              {r.findings.slice(half).map((f) => <ReportFinding key={f.finding_id} f={f} caseId={r.case.id} />)}
            </div>
          )}
          <div style={section}>
            <span style={label}>Correlation summary</span>
            {!r.correlations.length && <span style={{ color: '#5F5F5A' }}>No cross-modal rule fired.</span>}
            {r.correlations.map((rule) => (
              <div key={rule.id + rule.links} style={{ display: 'grid', gridTemplateColumns: '48px 1fr auto', gap: 12, padding: '8px 0', borderBottom: '1px solid #EFEFEB' }}>
                <span style={{ ...mono, fontSize: 11, fontWeight: 600 }}>{rule.id}</span>
                <span><b>{rule.name}</b><br /><span style={{ ...mono, fontSize: 10.5, color: '#5F5F5A' }}>{rule.links}</span></span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 999, border: '1px solid #E8E8E4', alignSelf: 'start' }}>{rule.tag}</span>
              </div>
            ))}
          </div>
          <div style={section}>
            <span style={label}>Limitations</span>
            <ul style={{ margin: 0, paddingLeft: 18, color: '#333', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {r.limitations.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
          <div style={section}>
            <span style={label}>Recommended human checks</span>
            <ul style={{ margin: 0, paddingLeft: 18, color: '#333', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {r.recommended_checks.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
          <div style={section}>
            <span style={label}>Reviewer decisions</span>
            <div style={{ border: '1px solid #E8E8E4', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ ...tableHead, gridTemplateColumns: DEC_COLS }}><span>Finding</span><span>Decision</span><span>Time</span><span>Note</span></div>
              {r.review_decisions.map((d) => (
                <div key={d.finding_id} style={{ ...tableRow, gridTemplateColumns: DEC_COLS }}><span style={{ ...mono, fontSize: 11 }}>{d.finding_id}</span><span style={{ fontWeight: 700, textTransform: 'capitalize' }}>{d.decision === 'pending' ? 'Open' : d.decision}</span><span style={{ ...mono, fontSize: 11, color: '#5F5F5A' }}>{d.time ? d.time.slice(11, 19) : '—'}</span><span style={{ color: '#333' }}>{d.note || '—'}</span></div>
              ))}
            </div>
            <span style={{ color: '#5F5F5A' }}>Reviewed by {r.case.investigator}. Open findings are listed but carry no reviewer decision.</span>
          </div>
          {!!r.source_context?.length && <div style={section}>
            <span style={label}>Original text and context</span>
            {r.source_context.map((source) => <div key={source.evidence}>
              <b>{source.evidence} · {source.name}</b>
              <p style={{ margin: '4px 0', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{source.text}</p>
            </div>)}
          </div>}
          {r.analysis && <div style={section}>
            <span style={label}>Analysis coverage and history</span>
            <span>Run {r.analysis.run_count} · {r.analysis.status} · {r.analysis_history?.length || 0} recorded events before this export.</span>
            <span style={{ color: '#5F5F5A' }}>The PDF includes method coverage, model checkpoints, and custody history. The JSON also includes the complete job log and linked hashes.</span>
          </div>}

          <div style={section}>
            <span style={label}>Rerun command</span>
            <div style={{ background: '#F7F7F5', border: '1px solid #E8E8E4', borderRadius: 10, padding: '12px 14px', ...mono, fontSize: 11, lineHeight: 1.6, wordBreak: 'break-all' }}>{r.rerun_command}</div>
            <span style={{ color: '#5F5F5A' }}>Rerunning on the same originals and model lock reproduces these finding IDs and scores.</span>
          </div>
          <div style={{ marginTop: 'auto', paddingTop: 14, borderTop: '2px solid #111', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8, ...mono, fontSize: 10.5 }}>
            <span>report sha256 {shortHash(r.sha256)}</span><span style={{ color: '#8A8A85' }}>chain of custody: {r.custody.entries} entries{r.custody.chain_valid ? '' : ' · BROKEN'} · summary · part 2</span>
          </div>
        </article>
      </div>
    </div>
  );
}

function ReportFinding({ f, caseId }) {
  const [noThumb, setNoThumb] = useState(f.location.type === 'text_span');
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '96px 1fr 150px', gap: 14, alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #EFEFEB' }}>
      <div style={{ height: 56, borderRadius: 6, background: 'repeating-linear-gradient(135deg,#EFEFEB 0 6px,#F7F7F5 6px 12px)', display: 'flex', alignItems: 'center', justifyContent: 'center', ...mono, fontSize: 9, color: '#8A8A85', textAlign: 'center', overflow: 'hidden', position: 'relative' }}>
        {noThumb ? `${f.evidence_id} · ${f.modality === 'text' ? 'caption' : f.modality}`
          : <AuthImg path={`/api/cases/${caseId}/findings/${f.finding_id}/thumb`} alt={`${f.finding_id} evidence`} onError={() => setNoThumb(true)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span><span style={{ ...mono, fontSize: 11, fontWeight: 600 }}>{f.finding_id}</span> · <b>{f.name}</b></span>
        <span style={{ color: '#5F5F5A' }}>{f.loc_label} · <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: DOT[f.band] }} />{f.verdict.label}</span></span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ position: 'relative', height: 6, borderRadius: 999, background: '#EFEFEB' }}><div style={{ position: 'absolute', top: 0, bottom: 0, left: `${f.conf_low * 100}%`, width: `${(f.conf_high - f.conf_low) * 100}%`, borderRadius: 999, background: f.band === 'inconclusive' ? '#8A8A85' : '#111' }} /></div>
        <span style={{ ...mono, fontSize: 10.5, display: 'flex', justifyContent: 'space-between' }}><span>{fmtRange(f.conf_low, f.conf_high)}</span><span style={{ color: '#5F5F5A' }}>{f.review.status === 'pending' ? 'open' : f.review.status}</span></span>
      </div>
    </div>
  );
}
