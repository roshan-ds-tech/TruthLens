import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { c, VERDICTS, YELLOW, MONO, Icon, hover, VerdictPill, RangeBar, eyebrow, fmtRange, preventThen, PrimaryButton, SecondaryButton, Muted } from '../ui.jsx';
import { api, useApi, useMediaUrl, fmtT, fmtDate, shortHash } from '../api/client.js';
import { AuthImg, EvidencePreview } from '../api/media.jsx';

const fmt = fmtT;

/** API finding → the shape the finding card renders. */
function toCard(f) {
  return {
    id: f.finding_id, dbId: f.id, name: f.name, mod: f.mod_label, icon: f.icon, loc: f.loc_label, locIcon: f.loc_icon,
    t: f.t, lo: f.conf_low, hi: f.conf_high, v: f.verdict.key, label: f.verdict.label, expl: f.explanation,
    alts: f.alternatives, compare: f.compare, go: f.goto, evidenceDbId: f.evidence_db_id, evidence: f.evidence_id,
    modality: f.modality, location: f.location, review: f.review, weakened: f.weakened, calibrated: f.calibrated,
  };
}

function CorrelationGraph({ selected, rules, nodes }) {
  const pos = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const selR = rules.find((r) => r.id === selected);
  const active = new Set();
  (selR ? selR.edges : []).forEach(([a, b]) => { active.add(a); active.add(b); });
  return (
    <svg viewBox="0 0 420 230" style={{ width: '100%', height: '100%', display: 'block', color: c.ink }}>
      {rules.flatMap((r) => r.edges.map(([a, b]) => {
        if (!pos[a] || !pos[b]) return null;
        const on = r.id === selected;
        const conflict = r.relation === 'weakens';
        return <line key={`${r.id}${a}${b}`} x1={pos[a].x} y1={pos[a].y} x2={pos[b].x} y2={pos[b].y} stroke={conflict ? '#E8A33D' : 'currentColor'} strokeWidth={on ? 3 : 1.5} strokeDasharray={conflict ? '5 4' : r.weak ? '2 3' : undefined} opacity={selR && !on ? 0.3 : 1} />;
      }))}
      {nodes.map((n) => {
        const prf = n.kind === 'profile';
        const ev = n.kind === 'evidence';
        return (
          <g key={n.id}>
            <circle cx={n.x} cy={n.y} r={prf || ev ? 16 : 22} style={{ fill: active.has(n.id) ? YELLOW : c.bg }} stroke={prf || ev ? '#8A8A85' : 'currentColor'} strokeWidth={1.5} strokeDasharray={prf || ev ? '3 3' : undefined} />
            <text x={n.x} y={n.y + 4} textAnchor="middle" fontSize={11} fontWeight={700} fontFamily="Inter, sans-serif" style={{ fill: active.has(n.id) ? '#111111' : c.ink }}>{n.abbr}</text>
            <text x={n.x} y={n.y + (prf || ev ? 32 : 38)} textAnchor="middle" fontSize={10} fontFamily="IBM Plex Mono, monospace" style={{ fill: c.ink2 }}>{n.label}</text>
          </g>
        );
      })}
    </svg>
  );
}

const smallBtn = { display: 'inline-flex', alignItems: 'center', gap: 4, height: 30, padding: '0 12px', borderRadius: 999, fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, cursor: 'pointer' };
const linkBtn = { border: 'none', background: 'none', padding: 0, cursor: 'pointer', color: c.ink, textDecoration: 'underline', textDecorationColor: YELLOW, textDecorationThickness: 2, textUnderlineOffset: 3 };

function FindingCard({ f, selected, decision, altOpen, note, noteOpen, draft, decidedAt, onSelect, onJump, onToggleAlt, onDecide, onToggleNote, onDraft, onSaveNote, reviewer }) {
  const dot = VERDICTS[f.v][1];
  const stop = (fn) => (e) => { e.stopPropagation(); fn(); };
  const accepted = decision === 'accepted', rejected = decision === 'rejected';
  return (
    <article onClick={onSelect} style={{ background: c.bg, border: `1px solid ${selected ? c.ink : c.border}`, boxShadow: selected ? '0 0 0 3px rgba(255,210,63,.55)' : '0 1px 2px rgba(17,17,17,.04)', borderRadius: 14, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10, cursor: 'pointer' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: MONO, fontSize: 11.5, fontWeight: 600 }}>{f.id}</span>
        <Icon name={f.icon} size={17} title={f.mod} style={{ color: c.ink2 }} />
        <span style={{ flex: 1 }} />
        <VerdictPill dot={dot} label={f.label} h={22} fs={11.5} pad={9} dotSize={6} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em' }}>{f.name}</span>
        <button onClick={stop(onJump)} style={{ ...linkBtn, alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: MONO, fontSize: 12, textAlign: 'left' }}>
          <Icon name={f.locIcon} size={15} />{f.loc}
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: c.ink2 }}>
          <span>Confidence range{f.calibrated ? '' : ' · uncalibrated'}{f.weakened ? ' · weakened by R-14' : ''}</span>
          <span style={{ fontFamily: MONO, color: c.ink, fontWeight: 600 }}>{fmtRange(f.lo, f.hi)}</span>
        </div>
        <div style={{ display: 'flex' }}><RangeBar lo={f.lo} hi={f.hi} h={8} midline color={f.v === 'inc' ? '#8A8A85' : c.ink} /></div>
      </div>
      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: c.ink2, textWrap: 'pretty' }}>{f.expl}</p>
      {f.compare && (
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', padding: '10px 12px', borderRadius: 10, background: c.surface, fontSize: 12 }}>
          {f.compare.map((row) => [
            <span key={row.k + 'k'} style={{ color: c.ink2 }}>{row.k}</span>,
            <span key={row.k + 'v'} style={{ fontFamily: MONO, display: 'flex', alignItems: 'center', gap: 6 }}>{row.conflict && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#E8A33D' }} />}{row.v}</span>,
          ])}
        </div>
      )}
      <div style={{ borderTop: `1px solid ${c.line}`, paddingTop: 8 }}>
        <button onClick={stop(onToggleAlt)} style={{ display: 'flex', alignItems: 'center', gap: 4, border: 'none', background: 'none', padding: 0, cursor: 'pointer', fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, color: c.ink }}>
          <Icon name={altOpen ? 'expand_less' : 'expand_more'} size={18} />Alternative explanations ({f.alts.length})
        </button>
        {altOpen && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '6px 0 0 22px' }}>
            {f.alts.map((a) => <span key={a} style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.45 }}>· {a}</span>)}
          </div>
        )}
      </div>
      {note && !noteOpen && (
        <div style={{ fontSize: 12.5, lineHeight: 1.45, padding: '8px 10px', borderRadius: 10, background: c.hl, border: `1px solid ${c.hlb}` }}><b>Note · {reviewer}</b> {note}</div>
      )}
      {noteOpen && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <textarea onClick={(e) => e.stopPropagation()} value={draft} onChange={(e) => onDraft(e.target.value)} placeholder="Add a reviewer note" style={{ minHeight: 60, resize: 'vertical', border: `1px solid ${c.border}`, borderRadius: 10, padding: '8px 10px', fontFamily: 'inherit', fontSize: 13, outline: 'none', background: c.bg }} />
          <button onClick={stop(onSaveNote)} style={{ alignSelf: 'flex-end', height: 30, padding: '0 14px', borderRadius: 999, border: `1px solid ${c.ink}`, background: c.hero, color: '#fff', fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, cursor: 'pointer' }}>Save note</button>
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <button onClick={stop(() => onDecide('accepted'))} style={{ ...smallBtn, border: `1px solid ${accepted ? c.ink : c.border}`, background: accepted ? c.ink : c.bg, color: accepted ? c.bg : c.ink }}><Icon name="check" size={16} />Accept</button>
        <button onClick={stop(() => onDecide('rejected'))} style={{ ...smallBtn, border: `1px solid ${rejected ? c.ink : c.border}`, background: rejected ? c.surface : c.bg, color: c.ink }}><Icon name="close" size={16} />Reject</button>
        <button onClick={stop(onToggleNote)} style={{ ...smallBtn, border: `1px solid ${c.border}`, background: c.bg, color: c.ink }}><Icon name="edit_note" size={16} />Add note</button>
        <span style={{ flex: 1 }} />
        <span style={{ fontFamily: MONO, fontSize: 10.5, color: c.ink2 }}>{accepted || rejected ? `${decision} · ${decidedAt ? new Date(decidedAt + (decidedAt.endsWith('Z') || decidedAt.includes('+') ? '' : 'Z')).toTimeString().slice(0, 5) : ''}` : 'needs review'}</span>
      </div>
    </article>
  );
}

function CustodyDrawer({ caseId, onClose }) {
  const cust = useApi(`/cases/${caseId}/custody`);
  const rows = cust.data?.entries || [];
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(17,17,17,.28)', zIndex: 50 }} />
      <aside style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(480px,92%)', background: c.bg, zIndex: 51, boxShadow: '-12px 0 40px rgba(17,17,17,.12)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '22px 24px 18px', borderBottom: `1px solid ${c.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={eyebrow}>Chain of custody · <span style={{ fontFamily: MONO }}>{caseId}</span></span>
            <span style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.018em' }}>{rows.length} recorded actions</span>
            <span style={{ fontSize: 13, color: c.ink2 }}>Append-only log. Each entry records the input and output hash of the step{cust.data ? (cust.data.chain_valid ? ' · hash chain verified' : ' · HASH CHAIN BROKEN') : ''}.</span>
          </div>
          <button onClick={onClose} style={{ width: 36, height: 36, borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer', flex: 'none' }}><Icon name="close" /></button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px 28px' }}>
          {cust.error && <Muted>Could not load the custody log: {cust.error.message}</Muted>}
          {rows.map((e, i) => (
            <div key={e.id} style={{ display: 'grid', gridTemplateColumns: '28px 1fr', gap: '0 14px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ width: 28, height: 28, borderRadius: '50%', background: i === rows.length - 1 ? YELLOW : c.bg, color: i === rows.length - 1 ? '#111111' : c.ink, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}><Icon name={custodyIcon(e.action)} size={16} /></span>
                <span style={{ flex: 1, width: 1, background: c.border, minHeight: 16 }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, padding: '3px 0 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 14, fontWeight: 700 }}>{e.action}</span>
                  <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>{fmtDate(e.ts)} · {e.ts.slice(11, 19)}</span>
                </div>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>{e.actor} · <span style={{ fontFamily: MONO }}>{e.tool}</span></span>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2px 10px', padding: '8px 10px', borderRadius: 10, background: c.surface, fontFamily: MONO, fontSize: 11 }}>
                  <span style={{ color: '#8A8A85' }}>in</span><span>{hashLabel(e.input_hash)}</span>
                  <span style={{ color: '#8A8A85' }}>out</span><span>{hashLabel(e.output_hash)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}

const hashLabel = (s) => s.replace(/[0-9a-f]{40,64}/g, (h) => shortHash(h));

function custodyIcon(action) {
  if (action.startsWith('Case')) return 'folder_open';
  if (action.includes('ingested')) return 'lock';
  if (action.includes('Audio track')) return 'graphic_eq';
  if (action.startsWith('Analysis')) return 'motion_photos_on';
  if (action.startsWith('Report')) return 'description';
  if (action.includes('accepted')) return 'check';
  if (action.includes('rejected')) return 'close';
  return 'edit_note';
}

function curvePaths(curve, duration) {
  if (!curve || !curve.length || !duration) return { line: '', area: '' };
  let line = '', area = 'M0,60 ';
  curve.forEach((v, i) => {
    const X = ((Math.min(i + 0.5, duration) / duration) * 420).toFixed(1), Y = (58 - Math.min(v, 1) * 54).toFixed(1);
    line += (line ? 'L' : 'M') + X + ',' + Y + ' ';
    area += 'L' + X + ',' + Y + ' ';
  });
  return { line, area: area + 'L420,60 Z' };
}

export default function CaseWorkspace({ go, active, compact, caseId }) {
  const [sel, setSel] = useState(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [alt, setAlt] = useState({});
  const [drafts, setDrafts] = useState({});
  const [noteOpen, setNoteOpen] = useState(null);
  const [drawer, setDrawer] = useState(false);
  const [limOpen, setLimOpen] = useState(false);
  const [rule, setRule] = useState(null);
  const [mode, setMode] = useState('wide');
  const [busy, setBusy] = useState('');
  const [viewId, setViewId] = useState(null);
  const rootRef = useRef(null);
  const videoRef = useRef(null);

  const path = active && caseId ? caseId : null;
  const caseQ = useApi(path && `/cases/${path}`);
  const findQ = useApi(path && `/cases/${path}/findings`);
  const graphQ = useApi(path && `/cases/${path}/graph`);
  const cs = caseQ.data;
  const evidence = cs?.evidence || [];
  const primary = evidence.find((e) => e.id === viewId) || evidence.find((e) => e.kind === 'video') || evidence.find((e) => e.kind === 'image') || null;
  const primaryQ = useApi(active && primary ? `/evidence/${primary.id}` : null);
  const isVideo = primary?.kind === 'video';
  const videoSrc = useMediaUrl(isVideo ? primary.media_url : null).url;
  const duration = primary?.duration || 1;
  const pct = (x) => `${Math.max(0, Math.min(100, (x / duration) * 100))}%`;

  const F = useMemo(() => (findQ.data || []).map(toCard), [findQ.data]);
  const byId = useMemo(() => Object.fromEntries(F.map((f) => [f.id, f])), [F]);
  const rules = graphQ.data?.rules || [];
  const nodes = graphQ.data?.nodes || [];
  useEffect(() => { if (rules.length && !rules.some((r) => r.id === rule)) setRule(rules[0].id); }, [rules, rule]);
  // Finding IDs repeat across cases (every case has an F-VID-001), so all per-finding UI state is per case.
  useEffect(() => {
    setSel(null); setViewId(null); setT(0); setAlt({}); setDrafts({}); setNoteOpen(null); setLimOpen(false); setRule(null); setErrLine('');
  }, [caseId]);

  // Lay out by the component's own width (not the window), since the sidebar can collapse.
  const measure = useCallback(() => {
    const root = rootRef.current;
    if (!root) return;
    const style = getComputedStyle(root);
    const w = root.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    if (!w) return;
    setMode(w < 760 ? 'stack' : w < 1100 ? 'mid' : 'wide');
  }, []);
  useEffect(() => {
    measure();
    window.addEventListener('resize', measure);
    const ro = window.ResizeObserver && rootRef.current ? new ResizeObserver(measure) : null;
    ro?.observe(rootRef.current);
    return () => { window.removeEventListener('resize', measure); ro?.disconnect(); };
  }, [measure]);
  useEffect(() => { if (active) requestAnimationFrame(measure); else videoRef.current?.pause(); }, [active, measure]);

  const seekTo = (x) => {
    const v = Math.max(0, Math.min(duration, x));
    setT(v);
    if (videoRef.current) videoRef.current.currentTime = v;
  };
  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { if (v.ended) v.currentTime = 0; v.play(); } else v.pause();
  };

  // timeline lanes: this video, its derived audio track, and cross-modal findings on the same clock
  const derived = evidence.filter((e) => e.derived_from === primary?.label).map((e) => e.label);
  const onClock = (f) => f.location && ['frame_range', 'time_range'].includes(f.location.type) && f.location.start != null
    && (f.evidence === primary?.label || derived.includes(f.evidence));
  const tracks = [
    { label: 'Video', marks: F.filter((f) => onClock(f) && f.modality === 'video') },
    { label: 'Audio', marks: F.filter((f) => onClock(f) && f.modality === 'audio' && f.location.end - f.location.start < duration * 0.8) },
    { label: 'Lip-sync', marks: F.filter((f) => onClock(f) && f.modality === 'cross-modal') },
  ];
  const timed = F.filter((f) => onClock(f) && f.v !== 'none' && f.location.end - f.location.start < duration * 0.8);
  const focus = (sel && byId[sel] && onClock(byId[sel]) ? byId[sel] : null) || [...timed].sort((a, b) => b.hi - a.hi)[0];
  const band = focus ? { a: focus.location.start, b: Math.max(focus.location.end, focus.location.start + duration * 0.02) } : null;
  const boxes = F.filter((f) => onClock(f) && f.location.w && t >= f.location.start - 0.25 && t <= f.location.end + 0.25);
  const curve = curvePaths(primaryQ.data?.extra?.suspicion_curve, duration);
  const step = duration > 40 ? 10 : duration > 20 ? 5 : duration > 8 ? 2 : 1;
  const ticks = Array.from({ length: Math.floor(duration / step) + 1 }, (_, i) => i * step);
  const openCount = F.filter((f) => !['accepted', 'rejected'].includes(f.review.status)).length;

  const selectF = (f) => { setSel(f.id); if (f.t != null && onClock(f)) seekTo(f.t); };
  const updateFinding = (updated) => findQ.setData((list) => list.map((x) => (x.id === updated.id ? updated : x)));
  const review = (f, body) => api.patch(`/findings/${f.dbId}/review`, body).then(updateFinding, (e) => alertLine(e));
  const [errLine, setErrLine] = useState('');
  const alertLine = (e) => setErrLine(e.message);
  const decide = (f, d) => review(f, { decision: f.review.status === d ? 'pending' : d });
  const jump = (f) => {
    if (f.go === 'image' || f.go === 'audio') go(f.go, { evidenceId: f.evidenceDbId });
    else if (f.modality === 'text') go('text', { caseId, evidenceId: f.evidenceDbId });
    else selectF(f);
  };

  const rerun = () => { setBusy('rerun'); api.post(`/cases/${caseId}/analyze`).then((j) => go('analysis', { caseId, jobId: j.job_id }), alertLine).finally(() => setBusy('')); };
  const exportReport = () => { setBusy('report'); api.post(`/cases/${caseId}/report`).then(() => go('report', { caseId, refresh: true }), alertLine).finally(() => setBusy('')); };

  const stacked = compact || mode === 'stack';
  const wide = !stacked && mode !== 'mid';
  const gridCols = stacked ? 'minmax(0,1fr)' : mode === 'mid' ? '220px minmax(0,1fr)' : '248px minmax(0,1fr)';
  const workspacePadding = compact ? '24px 24px 48px' : '32px clamp(16px, 3vw, 40px) 56px';
  const trackLabel = { position: 'absolute', left: -76, fontSize: 11.5, fontWeight: 600, color: c.ink2 };
  const v = cs?.verdict;
  const combined = graphQ.data?.combined;

  if (!caseId || (!cs && (caseQ.error || !caseQ.loading))) {
    return (
      <div ref={rootRef} style={{ padding: workspacePadding, display: 'flex', flexDirection: 'column', gap: 10, color: c.ink }}>
        <div style={eyebrow}>Case workspace</div>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em' }}>No case open</h1>
        <Muted>{caseQ.error ? `Could not load the case: ${caseQ.error.message}` : 'Open a case from Cases, or start one with New case.'}</Muted>
      </div>
    );
  }
  if (!cs) return <div ref={rootRef} style={{ padding: workspacePadding }}><Muted>Loading case…</Muted></div>;

  return (
    <div ref={rootRef} style={{ padding: workspacePadding, display: 'flex', flexDirection: 'column', gap: 24, minWidth: 0, color: c.ink }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0, flex: '1 1 520px' }}>
          <div style={eyebrow}>Case · <span style={{ fontFamily: MONO, letterSpacing: '.02em' }}>{cs.id}</span> · Opened {fmtDate(cs.created_at)}</div>
          <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em', textWrap: 'balance' }}>{cs.title}</h1>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 32, padding: '0 14px', borderRadius: 999, background: c.hero, color: '#fff', fontSize: 13.5, fontWeight: 700 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: VERDICTS[v.key][1] === c.ink ? '#fff' : VERDICTS[v.key][1] }} />{v.label} {v.lo != null && <span style={{ fontFamily: MONO, fontWeight: 500, color: YELLOW }}>{fmtRange(v.lo, v.hi)}</span>}
            </span>
            <span style={{ fontSize: 14, color: c.ink2, textWrap: 'pretty' }}>
              <b style={{ color: c.ink, fontWeight: 700 }}>Why:</b> {cs.why}{cs.why.endsWith('.') ? '' : '.'}
            </span>
            <button onClick={() => setLimOpen((x) => !x)} style={{ ...linkBtn, fontFamily: 'inherit', fontSize: 13.5, fontWeight: 700 }}>Limitations</button>
          </div>
          {limOpen && (
            <div style={{ background: c.surface, border: `1px solid ${c.border}`, borderRadius: 14, padding: '14px 18px', maxWidth: 760, display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13.5, color: c.ink2, lineHeight: 1.5 }}>
              <span style={{ ...eyebrow, color: c.ink }}>Limitations of this verdict</span>
              {(cs.limitations || []).map((l) => <span key={l}>· {l}</span>)}
              <span>· Analyzers were calibrated on our own seeded test set. <a href="#" onClick={preventThen(() => go('validation'))}>See validation</a>.</span>
            </div>
          )}
          {errLine && <Muted>{errLine}</Muted>}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          <SecondaryButton onClick={() => setDrawer(true)}><Icon name="history" size={19} />Chain of custody</SecondaryButton>
          <SecondaryButton onClick={rerun} disabled={!!busy}><Icon name="refresh" size={19} />{busy === 'rerun' ? 'Starting…' : 'Re-run analysis'}</SecondaryButton>
          <PrimaryButton onClick={exportReport} disabled={!!busy || cs.status !== 'analyzed'} style={{ height: 40, padding: '0 18px', opacity: cs.status === 'analyzed' ? 1 : 0.55 }}>{busy === 'report' ? 'Building report…' : 'Export report'}<Icon name="arrow_forward" size={19} /></PrimaryButton>
        </div>
      </div>

      {/* Keep the findings column independent so its height cannot stretch the evidence rows. */}
      <div style={{ display: 'grid', gridTemplateColumns: wide ? 'minmax(0,1fr) 384px' : 'minmax(0,1fr)', gap: 20, alignItems: 'start', minWidth: 0 }}>
      <div style={{ display: 'grid', gridTemplateColumns: gridCols, gap: 20, alignItems: 'start', minWidth: 0 }}>
        <section style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: 20, padding: '0 2px' }}>
            <span style={eyebrow}>Evidence · {evidence.length}</span>
            <span style={{ fontSize: 12, color: c.ink2 }}>originals read-only</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {evidence.map((e) => {
              const on = primary && e.id === primary.id;
              const ev = e.verdict || { key: 'review', label: 'Not analyzed' };
              const open = () => {
                if (e.kind === 'video') { setViewId(e.id); setT(0); } else if (e.kind === 'image') go('image', { evidenceId: e.id });
                else if (e.kind === 'audio') go('audio', { evidenceId: e.id });
                else if (e.kind === 'text') go('text', { caseId, evidenceId: e.id });
              };
              return (
                <button key={e.id} onClick={open} {...hover({ bc: c.ink }, { flex: '1 1 200px', minWidth: 0, maxWidth: '100%', boxSizing: 'border-box', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 8, padding: 12, borderRadius: 14, border: `1px solid ${on ? c.ink : c.border}`, background: on ? c.surface : c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer' })}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', minWidth: 0, width: '100%' }}>
                    <span style={{ width: 34, height: 34, flex: 'none', borderRadius: 9, background: on ? YELLOW : c.surface, color: on ? '#111111' : c.ink, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={e.icon} size={19} /></span>
                    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                      <span style={{ fontSize: 13.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.display_name}</span>
                      <span style={{ fontSize: 12, color: c.ink2 }}>{e.label} · {e.meta_label}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '6px 8px', width: '100%', minWidth: 0 }}>
                    <VerdictPill dot={VERDICTS[ev.key][1]} label={ev.label} h={22} fs={11.5} pad={9} dotSize={6} style={{ background: c.bg }} />
                    <span style={{ fontFamily: MONO, fontSize: 10.5, color: c.ink2 }}>{e.sha_short}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, minWidth: 0 }}>
        <section style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span style={{ ...eyebrow, display: 'flex', alignItems: 'center', minHeight: 20, padding: '0 2px' }}>Evidence viewer</span>
          <div style={{ minWidth: 0, background: c.bg, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '14px 18px', borderBottom: `1px solid ${c.border}` }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px 10px', minWidth: 0, maxWidth: '100%' }}>
              <Icon name={primary?.icon || 'movie'} />
              <span style={{ fontSize: 14, fontWeight: 700, minWidth: 0, overflowWrap: 'anywhere' }}>{primary ? primary.display_name : 'No video or image in this case'}</span>
              <span style={{ fontSize: 12.5, color: c.ink2 }}>{primary ? primary.meta_label.split(' · ').slice(1).join(' · ') : ''}</span>
            </div>
            <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>{primary ? `sha256 ${primary.sha_short}` : ''}</span>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ position: 'relative', aspectRatio: '16/9', borderRadius: 12, overflow: 'hidden', background: 'repeating-linear-gradient(135deg,#1A1A1A 0 12px,#202020 12px 24px)' }}>
              {isVideo && (
                <video key={primary.id} ref={videoRef} src={videoSrc || undefined} preload="metadata" playsInline
                  onTimeUpdate={(e) => setT(e.currentTarget.currentTime)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', background: '#151515' }} />
              )}
              {primary?.kind === 'image' && <AuthImg path={primary.media_url} alt="" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', background: '#151515' }} />}
              {!primary && <EvidencePreview ev={evidence.find((e) => e.kind === 'audio') || evidence.find((e) => e.kind === 'text')} dark lines={6} />}
              {!primary && <div style={{ position: 'absolute', left: 16, top: 14, fontFamily: MONO, fontSize: 11, color: '#8A8A85' }}>no video or image · showing {evidence.some((e) => e.kind === 'audio') ? 'the audio waveform' : 'the caption'}</div>}
              {isVideo && <div style={{ position: 'absolute', right: 16, top: 14, fontFamily: MONO, fontSize: 11, color: '#fff', background: 'rgba(17,17,17,.7)', padding: '3px 8px', borderRadius: 6 }}>frame {Math.round(t * (primary.fps || 25))}</div>}
              {boxes.map((f) => {
                const L = f.location;
                return (
                  <div key={f.id} style={{ position: 'absolute', left: `${(L.x / L.image_w) * 100}%`, top: `${(L.y / L.image_h) * 100}%`, width: `${(L.w / L.image_w) * 100}%`, height: `${(L.h / L.image_h) * 100}%`, border: `2px solid ${YELLOW}`, borderRadius: 6, pointerEvents: 'none' }}>
                    <span style={{ position: 'absolute', left: -2, top: -26, background: YELLOW, color: '#111111', fontFamily: MONO, fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: '6px 6px 6px 0', whiteSpace: 'nowrap' }}>{f.id} · {f.name.toLowerCase()}</span>
                  </div>
                );
              })}
              {isVideo && (
                <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, background: 'linear-gradient(transparent,rgba(0,0,0,.55))' }}>
                  <button onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'} style={{ width: 36, height: 36, borderRadius: '50%', border: 'none', background: c.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: c.ink }}>
                    <Icon name={playing ? 'pause' : 'play_arrow'} size={22} />
                  </button>
                  <span style={{ fontFamily: MONO, fontSize: 12, color: '#fff' }}>{fmt(t)} / {fmt(duration)}</span>
                  <div onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); seekTo(((e.clientX - r.left) / r.width) * duration); }} style={{ flex: 1, height: 4, borderRadius: 999, background: 'rgba(255,255,255,.25)', position: 'relative', cursor: 'pointer' }}>
                    <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: pct(t), background: c.bg, borderRadius: 999 }} />
                    {band && <div style={{ position: 'absolute', left: pct(band.a), width: pct(band.b - band.a), top: -2, bottom: -2, background: YELLOW, borderRadius: 2, opacity: 0.9 }} />}
                  </div>
                  <Icon name="volume_up" style={{ color: '#fff' }} />
                </div>
              )}
            </div>

            {isVideo && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 12px', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={eyebrow}>Timeline · suspicion</span>
                  <span style={{ fontSize: 12, color: c.ink2 }}>Click any track to seek{band ? <> · flagged <span style={{ fontFamily: MONO, color: c.ink }}>{fmt(band.a)}–{fmt(band.b)}</span></> : ' · nothing flagged on this clip'}</span>
                </div>
                <div onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); const x = (e.clientX - r.left - 76) / (r.width - 76); if (x >= 0) seekTo(x * duration); }} style={{ position: 'relative', cursor: 'crosshair', display: 'flex', flexDirection: 'column', gap: 4, paddingLeft: 76 }}>
                  <div style={{ position: 'absolute', left: 76, right: 0, top: 0, bottom: 0, pointerEvents: 'none' }}>
                    {band && <div style={{ position: 'absolute', left: pct(band.a), width: pct(band.b - band.a), top: 0, bottom: 0, background: 'rgba(255,210,63,.28)', borderLeft: `1.5px solid ${YELLOW}`, borderRight: `1.5px solid ${YELLOW}` }} />}
                    <div style={{ position: 'absolute', left: pct(t), top: -4, bottom: -4, width: 2, marginLeft: -1, background: c.ink, zIndex: 2 }} />
                  </div>
                  <div style={{ position: 'relative', height: 64, borderRadius: 8, background: c.surface }}>
                    <span style={{ ...trackLabel, top: 24 }}>Suspicion</span>
                    <svg viewBox="0 0 420 60" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', color: c.ink }}>
                      <path d={curve.area} fill="currentColor" fillOpacity={0.08} />
                      <path d={curve.line} fill="none" stroke="currentColor" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
                    </svg>
                  </div>
                  {tracks.map((tr) => (
                    <div key={tr.label} style={{ position: 'relative', height: 26, borderRadius: 6, background: c.surface }}>
                      <span style={{ ...trackLabel, top: 5 }}>{tr.label}</span>
                      {tr.marks.map((f) => (
                        <button key={f.id} title={`${f.id} · ${f.name}`} onClick={(e) => { e.stopPropagation(); setSel(f.id); seekTo(f.location.start); }} style={{ position: 'absolute', left: pct(f.location.start), width: pct(f.location.end - f.location.start), minWidth: 10, top: 4, bottom: 4, borderRadius: 4, border: `1.5px solid ${c.ink}`, background: sel === f.id ? YELLOW : c.bg, cursor: 'pointer', padding: 0, zIndex: 3 }} />
                      ))}
                    </div>
                  ))}
                  <div style={{ position: 'relative', height: 16 }}>
                    {ticks.map((s) => (
                      <span key={s} style={{ position: 'absolute', left: pct(s), transform: 'translateX(-50%)', fontFamily: MONO, fontSize: 10, color: '#8A8A85' }}>{fmt(s).slice(0, 5)}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
          </div>
        </section>

        <section style={{ minWidth: 0, background: c.bg, border: `1px solid ${c.border}`, borderRadius: 16, padding: 18, display: 'flex', flexDirection: 'column', gap: 14, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 10 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={eyebrow}>Cross-modal correlations · {rules.length} rule{rules.length === 1 ? '' : 's'} fired</span>
              <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.012em' }}>How findings support or weaken each other</span>
            </div>
            {combined && combined.lo != null && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, maxWidth: '100%', flex: '0 1 240px' }}>
                <span style={{ fontSize: 12, color: c.ink2, whiteSpace: 'nowrap' }}>Combined</span>
                <RangeBar lo={combined.lo} hi={combined.hi} h={8} color={c.ink} />
                <span style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600 }}>{fmtRange(combined.lo, combined.hi)}</span>
              </div>
            )}
          </div>
          {!rules.length && <Muted>No cross-modal rule fired. Rules need findings from at least two sources that share a time, place or claim.</Muted>}
          {!!rules.length && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
              <div style={{ flex: '1 1 300px', minWidth: 0, background: c.surface, borderRadius: 12, padding: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ aspectRatio: '420/230' }}><CorrelationGraph selected={rule} rules={rules} nodes={nodes} /></div>
                <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 11.5, color: c.ink2, padding: '0 6px 4px' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 18, height: 2, background: c.ink }} />supports</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 18, borderTop: '2px dashed #E8A33D' }} />weakens</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: YELLOW, border: `1.5px solid ${c.ink}` }} />selected rule</span>
                </div>
              </div>
              <div style={{ flex: '2 1 340px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {rules.map((r) => {
                  const on = rule === r.id;
                  const conflict = r.relation === 'weakens';
                  return (
                    <button key={r.id + (r.weak ? 'w' : '')} onClick={() => setRule(r.id)} {...hover({ bc: c.ink }, { textAlign: 'left', display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-start', padding: '12px 14px', borderRadius: 12, border: `1px solid ${on ? c.ink : c.border}`, background: on ? c.hl : c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer' })}>
                      <span style={{ fontFamily: MONO, fontSize: 11.5, fontWeight: 600, paddingTop: 2, flex: 'none' }}>{r.id}</span>
                      <div style={{ flex: '1 1 120px', display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
                        <span style={{ fontSize: 13.5, fontWeight: 700, textWrap: 'pretty' }}>{r.name}</span>
                        <span style={{ fontSize: 12, color: c.ink2, fontFamily: MONO }}>{r.links}</span>
                        <span style={{ fontSize: 12.5, color: c.ink2, textWrap: 'pretty' }}>{r.detail}</span>
                      </div>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 22, padding: '0 9px', borderRadius: 999, border: `1px solid ${c.border}`, background: c.bg, fontSize: 11.5, fontWeight: 700, flex: 'none' }}>
                        <Icon name={conflict ? 'remove' : 'add'} size={14} style={{ color: conflict ? '#E8A33D' : c.ink }} />{r.tag}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </section>
        </div>
      </div>

        <section style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: 20, padding: '0 2px' }}>
            <span style={eyebrow}>Findings · {F.length} <span style={{ color: '#8A8A85' }}>· {openCount} awaiting review</span></span>
          </div>
          {cs.status !== 'analyzed' && <Muted>{cs.status === 'draft' ? 'Not analyzed yet. Use Re-run analysis to start.' : cs.status === 'failed' ? 'The last analysis failed; see the run log.' : 'Analysis in progress…'}</Muted>}
          {cs.status === 'analyzed' && !F.length && <Muted>No analyzer flagged anything above its threshold. See Limitations for what was not checked.</Muted>}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(min(300px,100%),1fr))', gap: 10 }}>
            {F.map((f) => (
              <FindingCard
                key={f.id}
                f={f}
                selected={sel === f.id}
                decision={f.review.status}
                decidedAt={f.review.decided_at}
                reviewer={f.review.reviewer || cs.investigator}
                altOpen={!!alt[f.id]}
                note={f.review.note}
                noteOpen={noteOpen === f.id}
                draft={drafts[f.id] ?? f.review.note ?? ''}
                onSelect={() => selectF(f)}
                onJump={() => jump(f)}
                onToggleAlt={() => setAlt((s) => ({ ...s, [f.id]: !s[f.id] }))}
                onDecide={(d) => decide(f, d)}
                onToggleNote={() => setNoteOpen((cur) => (cur === f.id ? null : f.id))}
                onDraft={(val) => setDrafts((s) => ({ ...s, [f.id]: val }))}
                onSaveNote={() => { review(f, { note: drafts[f.id] ?? f.review.note ?? '' }); setNoteOpen(null); }}
              />
            ))}
          </div>
        </section>

      </div>

      {drawer && <CustodyDrawer caseId={caseId} onClose={() => setDrawer(false)} />}
    </div>
  );
}
