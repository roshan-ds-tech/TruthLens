import { useEffect, useRef } from 'react';
import { c, MONO, Icon, eyebrow, h1, page, PrimaryButton, Muted } from '../ui.jsx';
import { useApi, useServerMode, PRIVACY } from '../api/client.js';

const pad2 = (n) => String(n).padStart(2, '0');

function StepChip({ label, status }) {
  const isDone = status === 'done', isRun = status === 'running';
  if (status === 'failed' || status === 'skipped') label = `${label} · ${status}`;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 28, padding: '0 12px 0 8px', borderRadius: 999, border: `1px solid ${isRun ? c.hlb : c.border}`, background: isRun ? c.hl : isDone ? c.bg : c.surface, fontSize: 12.5, fontWeight: 600, color: isDone || isRun ? c.ink : '#8A8A85' }}>
      {isDone && <Icon name="check" size={16} style={{ color: c.ink }} />}
      {isRun && <span style={{ width: 12, height: 12, margin: '0 2px', borderRadius: '50%', border: `2px solid ${c.border}`, borderTopColor: c.ink, animation: 'tlspin .9s linear infinite' }} />}
      {!isDone && !isRun && <span style={{ width: 12, height: 12, margin: '0 2px', borderRadius: '50%', border: '1.5px dashed #B8B8B2' }} />}
      {label}
    </span>
  );
}

export default function Analysis({ go, active, caseId, jobId }) {
  const logRef = useRef(null);
  const privacy = PRIVACY[useServerMode()];
  const path = !active ? null : jobId ? `/jobs/${jobId}` : caseId ? `/cases/${caseId}/jobs/latest` : null;
  const job = useApi(path, { poll: 1000 });
  const j = job.data;
  const running = j && (j.status === 'queued' || j.status === 'running');

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [j?.log?.length, active]);

  const rows = (j?.items || []).map((r) => {
    const done = r.steps.filter((x) => ['done', 'failed', 'skipped'].includes(x.status)).length;
    const t = r.finished != null && r.started != null ? r.finished - r.started : r.started != null ? Math.max(0, (j.elapsed_s || 0) - r.started) : null;
    return { ...r, done, time: r.finished != null ? 'done' : t == null ? 'queued' : `00:${pad2(Math.round(t))}` };
  });
  const allDone = j?.status === 'done';
  const failed = j?.status === 'failed';
  const log = (j?.log || []).map((l) => [l.t, l.src, l.msg]);
  const elapsed = j ? `${pad2(Math.floor(j.elapsed_s / 60))}:${pad2(Math.round(j.elapsed_s % 60))}` : '00:00';
  const headline = !j ? 'No analysis yet' : allDone ? `Analysis complete · ${j.findings_count} finding${j.findings_count === 1 ? '' : 's'}`
    : failed ? 'Analysis stopped' : `Analyzing ${rows.length} evidence item${rows.length === 1 ? '' : 's'}`;

  return (
    <div style={page}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={eyebrow}>Analysis · <span style={{ fontFamily: MONO }}>{j?.case_id || caseId || '—'}</span>{j ? ` · Job ${j.id}` : ''}</div>
          <h1 style={h1}>{headline}</h1>
          <p style={{ margin: 0, fontSize: 14.5, color: c.ink2 }}>
            {j ? <>Elapsed <span style={{ fontFamily: MONO, color: c.ink }}>{elapsed}</span> · {privacy.worker}{failed ? ` · ${j.error}` : ''}</>
              : job.error ? 'No analysis has run for this case yet. Start one from New case or Re-run analysis.' : 'Loading…'}
          </p>
        </div>
        <PrimaryButton onClick={() => go('workspace', { caseId: j?.case_id || caseId, refresh: true })} style={{ opacity: allDone ? 1 : 0.55 }}>Open workspace<Icon name="arrow_forward" size={19} /></PrimaryButton>
      </div>
      <div style={{ height: 8, borderRadius: 999, background: c.line, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: Math.round((j?.progress || 0) * 100) + '%', background: c.ink, borderRadius: 999, transition: 'width .6s ease' }} />
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-start' }}>
        <div style={{ flex: '3 1 560px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rows.map((r) => (
            <div key={r.evidence} style={{ border: `1px solid ${c.border}`, borderRadius: 14, padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ width: 38, height: 38, flex: 'none', borderRadius: 10, background: c.surface, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={r.icon} /></span>
                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 14.5, fontWeight: 700 }}>{r.name}</span>
                  <span style={{ fontSize: 12.5, color: c.ink2 }}>{r.evidence} · {r.meta} · <span style={{ fontFamily: MONO }}>{r.sha}</span></span>
                </div>
                <span style={{ fontFamily: MONO, fontSize: 12, color: c.ink2 }}>{r.done}/{r.steps.length} · {r.time}</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {r.steps.map((st) => <StepChip key={st.key} label={st.label} status={st.status} />)}
              </div>
            </div>
          ))}
        </div>
        <section style={{ flex: '2 1 380px', minWidth: 0, background: c.surface, border: `1px solid ${c.border}`, borderRadius: 14, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>
            <span style={eyebrow}>Live log</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: c.ink2 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: allDone ? '#3E9B5F' : failed ? '#D64545' : '#E8A33D' }} />{allDone ? 'finished' : failed ? 'stopped' : running ? 'running' : 'idle'}
            </span>
          </div>
          <div ref={logRef} style={{ height: 440, overflow: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 3, fontFamily: MONO, fontSize: 11.5, lineHeight: 1.55 }}>
            {!log.length && <Muted style={{ fontFamily: MONO, fontSize: 11.5 }}>No log yet.</Muted>}
            {log.map(([t, src, msg], i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '92px 64px 1fr', gap: 8, color: /F-[A-Z]+-\d/.test(msg) ? c.ink : c.ink2 }}>
                <span style={{ color: '#8A8A85' }}>{t}</span><span>{src}</span><span style={{ wordBreak: 'break-all' }}>{msg}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
