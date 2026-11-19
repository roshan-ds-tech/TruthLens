import { useCallback, useEffect, useRef, useState } from 'react';
import { c, VERDICTS, YELLOW, MONO, Icon, hover, VerdictPill, RangeBar, eyebrow, fmtRange, preventThen, PrimaryButton, SecondaryButton } from '../ui.jsx';

const DURATION = 42;
const pct = (x) => (x / DURATION) * 100 + '%';
const fmt = (t) => '00:' + t.toFixed(1).padStart(4, '0');

const FINDINGS = [
  { id: 'F-VID-002', name: 'Optical-flow discontinuity', mod: 'Video', icon: 'movie', loc: '00:14.0 · frames 420–423', locIcon: 'schedule', t: 14.0, lo: 0.64, hi: 0.81, v: 'strong', expl: 'Motion vectors break across three frames while the camera is static. This pattern is consistent with a cut or an inserted segment.', alts: ['Dropped frames during screen recording', 'Variable frame-rate re-encode by the uploading app'] },
  { id: 'F-AUD-001', name: 'Noise-floor step (possible splice)', mod: 'Audio', icon: 'graphic_eq', loc: '00:14.2 · +9 dB jump', locIcon: 'schedule', t: 14.2, lo: 0.70, hi: 0.86, v: 'strong', expl: 'Background noise rises 9 dB in under 20 ms, with no matching change in room tone before or after.', alts: ['Microphone gain change by an operator', 'Noise suppression switching on or off'], go: 'audio' },
  { id: 'F-IMG-003', name: 'Error level inconsistency', mod: 'Image', icon: 'image', loc: 'Podium region · podium_photo.jpg', locIcon: 'crop_free', t: null, lo: 0.52, hi: 0.71, v: 'ind', expl: 'The podium area recompresses differently from the rest of the photo.', alts: ['Recompression by social platform', 'Sharpening applied around text and logos'], go: 'image' },
  { id: 'F-TXT-001', name: 'Date conflict', mod: 'Text', icon: 'notes', loc: 'Caption ↔ EXIF of podium_photo.jpg', locIcon: 'data_object', t: null, lo: 0.80, hi: 0.94, v: 'ind', expl: 'The caption dates the event to 12 Nov 2026. The photo was captured on 03 Mar 2024 according to its metadata.', alts: ['Camera clock set incorrectly', 'Metadata carried over from a template file'], compare: true, go: 'image' },
  { id: 'F-XM-001', name: 'Lip-sync weak correlation', mod: 'Cross-modal', icon: 'join_inner', loc: '00:14.0–00:19.0', locIcon: 'schedule', t: 14.0, lo: 0.40, hi: 0.62, v: 'inc', expl: 'Mouth movement and speech energy correlate weakly in this window. The face is partly turned, which limits the measurement.', alts: ['Head turned away from camera', 'Low mouth-region resolution at 720p'] },
];

const TRACKS = [
  { label: 'Video', marks: [['F-VID-002', 14.0, 14.3]] },
  { label: 'Audio', marks: [['F-AUD-001', 14.2, 14.5]] },
  { label: 'Lip-sync', marks: [['F-XM-001', 14.0, 19.0]] },
];

const TICKS = [0, 5, 10, 15, 20, 25, 30, 35, 40];

const RULES = [
  { id: 'R-03', name: 'Audio splice within 0.5 s of a motion break', links: 'F-AUD-001 ↔ F-VID-002 · Δ 0.2 s', detail: 'Two independent analyzers point at the same moment.', tag: 'Supports', edges: ['VID-AUD'] },
  { id: 'R-07', name: 'Lip-sync drop overlaps a flagged segment', links: 'F-XM-001 ↔ F-VID-002, F-AUD-001', detail: 'Weak on its own. Adds little weight because the face is turned.', tag: 'Supports (weak)', edges: ['XM-VID', 'XM-AUD'] },
  { id: 'R-11', name: 'Claimed date differs from capture metadata', links: 'F-TXT-001 ↔ F-IMG-003', detail: 'Caption date is 2 years after the photo’s EXIF date.', tag: 'Supports', edges: ['TXT-IMG'] },
  { id: 'R-14', name: 'Error-level pattern matches platform recompression', links: 'F-IMG-003 ↔ profile: WhatsApp JPEG q≈82', detail: 'Lowers the weight of F-IMG-003 in the combined range.', tag: 'Conflicts', edges: ['IMG-PRF'], conflict: true },
];

const CUSTODY = [
  { action: 'Case opened', time: '19 Nov 2026 · 21:38:02', actor: 'Priya S.', tool: 'truthlens 0.9.1', inH: '—', outH: 'case c7a0…11de', icon: 'folder_open' },
  { action: 'Video ingested and sealed', time: '19 Nov 2026 · 21:39:47', actor: 'Priya S.', tool: 'tl-ingest 0.4.2', inH: 'upload stream', outH: 'sha256 9f2c41a7…e81b', icon: 'lock' },
  { action: 'Image ingested and sealed', time: '19 Nov 2026 · 21:39:51', actor: 'Priya S.', tool: 'tl-ingest 0.4.2', inH: 'upload stream', outH: 'sha256 3b7e0d19…a4c2', icon: 'lock' },
  { action: 'Caption recorded', time: '19 Nov 2026 · 21:40:12', actor: 'Priya S.', tool: 'tl-ingest 0.4.2', inH: 'clipboard text', outH: 'sha256 c41d9a3e…5f10', icon: 'notes' },
  { action: 'Audio track extracted', time: '19 Nov 2026 · 21:40:19', actor: 'system', tool: 'ffmpeg 6.1 (pinned)', inH: 'sha256 9f2c41a7…e81b', outH: 'sha256 5d81e0c2…07af', icon: 'graphic_eq' },
  { action: 'Analysis run 1', time: '19 Nov 2026 · 21:40:23', actor: 'system', tool: 'tl-analyze 0.9.1 · models.lock e0b2…', inH: '4 evidence hashes', outH: 'findings 7a3f…c902', icon: 'motion_photos_on' },
  { action: 'Analysis run 2 (frame-rate fix)', time: '19 Nov 2026 · 21:45:10', actor: 'Priya S.', tool: 'tl-analyze 0.9.1 · --vfr', inH: '4 evidence hashes', outH: 'findings 2be1…48d7', icon: 'refresh' },
  { action: 'F-AUD-001 accepted', time: '19 Nov 2026 · 21:48:33', actor: 'Priya S.', tool: 'review ui', inH: 'findings 2be1…48d7', outH: 'review 91c0…3a6e', icon: 'check' },
  { action: 'Report draft generated', time: '19 Nov 2026 · 21:51:05', actor: 'Priya S.', tool: 'tl-report 0.3.0', inH: 'review 91c0…3a6e', outH: 'sha256 4ae09c3b…7d21', icon: 'description' },
];

// Synthetic suspicion curve over the clip, peaking at the 00:14.2 splice.
const CURVE = (() => {
  let line = '', area = 'M0,60 ';
  for (let x = 0; x <= DURATION; x += 0.25) {
    const s = 0.1 + 0.04 * Math.sin(x * 1.3) + 0.03 * Math.sin(x * 3.7) + 0.68 * Math.exp(-((x - 14.2) ** 2) / 0.35) + 0.3 / (1 + Math.exp(-(x - 14) * 4)) / (1 + Math.exp((x - 19) * 4));
    const X = (x * 10).toFixed(1), Y = (58 - Math.min(s, 1) * 54).toFixed(1);
    line += (line ? 'L' : 'M') + X + ',' + Y + ' ';
    area += 'L' + X + ',' + Y + ' ';
  }
  return { line, area: area + 'L420,60 Z' };
})();

const NODES = { VID: [70, 60, 'F-VID-002'], AUD: [70, 175, 'F-AUD-001'], XM: [190, 118, 'F-XM-001'], IMG: [300, 60, 'F-IMG-003'], TXT: [300, 175, 'F-TXT-001'], PRF: [392, 118, 'platform'] };

function CorrelationGraph({ selected }) {
  const selR = RULES.find((r) => r.id === selected);
  const active = new Set();
  (selR ? selR.edges : []).forEach((e) => e.split('-').forEach((n) => active.add(n)));
  return (
    <svg viewBox="0 0 420 230" style={{ width: '100%', height: '100%', display: 'block', color: c.ink }}>
      {RULES.flatMap((r) => r.edges.map((e) => {
        const [a, b] = e.split('-');
        const on = r.id === selected;
        return <line key={e} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} stroke={r.conflict ? '#E8A33D' : 'currentColor'} strokeWidth={on ? 3 : 1.5} strokeDasharray={r.conflict ? '5 4' : undefined} opacity={selR && !on ? 0.3 : 1} />;
      }))}
      {Object.entries(NODES).map(([k, [x, y, lab]]) => {
        const prf = k === 'PRF';
        return (
          <g key={k}>
            <circle cx={x} cy={y} r={prf ? 16 : 22} style={{ fill: active.has(k) ? YELLOW : c.bg }} stroke={prf ? '#8A8A85' : 'currentColor'} strokeWidth={1.5} strokeDasharray={prf ? '3 3' : undefined} />
            <text x={x} y={y + 4} textAnchor="middle" fontSize={11} fontWeight={700} fontFamily="Manrope, sans-serif" style={{ fill: active.has(k) ? '#111111' : c.ink }}>{prf ? 'WA' : k}</text>
            <text x={x} y={y + (prf ? 32 : 38)} textAnchor="middle" fontSize={10} fontFamily="JetBrains Mono, monospace" style={{ fill: c.ink2 }}>{lab}</text>
          </g>
        );
      })}
    </svg>
  );
}

const smallBtn = { display: 'inline-flex', alignItems: 'center', gap: 4, height: 30, padding: '0 12px', borderRadius: 999, fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, cursor: 'pointer' };
const linkBtn = { border: 'none', background: 'none', padding: 0, cursor: 'pointer', color: c.ink, textDecoration: 'underline', textDecorationColor: YELLOW, textDecorationThickness: 2, textUnderlineOffset: 3 };

function FindingCard({ f, selected, decision, altOpen, note, noteOpen, draft, onSelect, onJump, onToggleAlt, onDecide, onToggleNote, onDraft, onSaveNote }) {
  const [verdict, dot] = VERDICTS[f.v];
  const stop = (fn) => (e) => { e.stopPropagation(); fn(); };
  const accepted = decision === 'accepted', rejected = decision === 'rejected';
  return (
    <article onClick={onSelect} style={{ background: c.bg, border: `1px solid ${selected ? c.ink : c.border}`, boxShadow: selected ? '0 0 0 3px rgba(255,210,63,.55)' : '0 1px 2px rgba(17,17,17,.04)', borderRadius: 14, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10, cursor: 'pointer' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: MONO, fontSize: 11.5, fontWeight: 600 }}>{f.id}</span>
        <Icon name={f.icon} size={17} title={f.mod} style={{ color: c.ink2 }} />
        <span style={{ flex: 1 }} />
        <VerdictPill dot={dot} label={verdict} h={22} fs={11.5} pad={9} dotSize={6} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em' }}>{f.name}</span>
        <button onClick={stop(onJump)} style={{ ...linkBtn, alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: MONO, fontSize: 12 }}>
          <Icon name={f.locIcon} size={15} />{f.loc}
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: c.ink2 }}>
          <span>Confidence range</span>
          <span style={{ fontFamily: MONO, color: c.ink, fontWeight: 600 }}>{fmtRange(f.lo, f.hi)}</span>
        </div>
        <div style={{ display: 'flex' }}><RangeBar lo={f.lo} hi={f.hi} h={8} midline color={f.v === 'inc' ? '#8A8A85' : c.ink} /></div>
      </div>
      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: c.ink2, textWrap: 'pretty' }}>{f.expl}</p>
      {f.compare && (
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', padding: '10px 12px', borderRadius: 10, background: c.surface, fontSize: 12 }}>
          <span style={{ color: c.ink2 }}>Caption</span><span style={{ fontFamily: MONO }}>12 Nov 2026</span>
          <span style={{ color: c.ink2 }}>EXIF DateTimeOriginal</span>
          <span style={{ fontFamily: MONO, display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: '#E8A33D' }} />03 Mar 2024</span>
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
        <div style={{ fontSize: 12.5, lineHeight: 1.45, padding: '8px 10px', borderRadius: 10, background: c.hl, border: `1px solid ${c.hlb}` }}><b>Note · Priya S.</b> {note}</div>
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
        <span style={{ fontFamily: MONO, fontSize: 10.5, color: c.ink2 }}>{accepted ? 'accepted · 21:48' : rejected ? 'rejected · 21:49' : 'needs review'}</span>
      </div>
    </article>
  );
}

function CustodyDrawer({ onClose }) {
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(17,17,17,.28)', zIndex: 50 }} />
      <aside style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(480px,92%)', background: c.bg, zIndex: 51, boxShadow: '-12px 0 40px rgba(17,17,17,.12)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '22px 24px 18px', borderBottom: `1px solid ${c.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={eyebrow}>Chain of custody · <span style={{ fontFamily: MONO }}>C-0007</span></span>
            <span style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.03em' }}>{CUSTODY.length} recorded actions</span>
            <span style={{ fontSize: 13, color: c.ink2 }}>Append-only log. Each entry records the input and output hash of the step.</span>
          </div>
          <button onClick={onClose} style={{ width: 36, height: 36, borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer', flex: 'none' }}><Icon name="close" /></button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px 28px' }}>
          {CUSTODY.map((e, i) => (
            <div key={e.time} style={{ display: 'grid', gridTemplateColumns: '28px 1fr', gap: '0 14px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ width: 28, height: 28, borderRadius: '50%', background: i === CUSTODY.length - 1 ? YELLOW : c.bg, color: i === CUSTODY.length - 1 ? '#111111' : c.ink, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}><Icon name={e.icon} size={16} /></span>
                <span style={{ flex: 1, width: 1, background: c.border, minHeight: 16 }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, padding: '3px 0 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 14, fontWeight: 700 }}>{e.action}</span>
                  <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>{e.time}</span>
                </div>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>{e.actor} · <span style={{ fontFamily: MONO }}>{e.tool}</span></span>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2px 10px', padding: '8px 10px', borderRadius: 10, background: c.surface, fontFamily: MONO, fontSize: 11 }}>
                  <span style={{ color: '#8A8A85' }}>in</span><span>{e.inH}</span>
                  <span style={{ color: '#8A8A85' }}>out</span><span>{e.outH}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}

export default function CaseWorkspace({ go, active, compact }) {
  const [sel, setSel] = useState('F-VID-002');
  const [t, setT] = useState(14.0);
  const [playing, setPlaying] = useState(false);
  const [decisions, setDecisions] = useState({ 'F-AUD-001': 'accepted' });
  const [alt, setAlt] = useState({ 'F-IMG-003': true });
  const [notes, setNotes] = useState({ 'F-TXT-001': 'Reverse image search pending. Earliest copy found is a 2024 news post.' });
  const [drafts, setDrafts] = useState({});
  const [noteOpen, setNoteOpen] = useState(null);
  const [drawer, setDrawer] = useState(false);
  const [limOpen, setLimOpen] = useState(false);
  const [rule, setRule] = useState('R-03');
  const [mode, setMode] = useState('wide');
  const rootRef = useRef(null);
  const ivRef = useRef(null);

  // Lay out by the component's own width (not the window), since the sidebar can collapse.
  const measure = useCallback(() => {
    const w = rootRef.current?.offsetWidth;
    if (!w) return;
    setMode(w < 760 ? 'stack' : w < 1100 ? 'mid' : 'wide');
  }, []);

  useEffect(() => {
    measure();
    window.addEventListener('resize', measure);
    const ro = window.ResizeObserver && rootRef.current ? new ResizeObserver(measure) : null;
    ro?.observe(rootRef.current);
    return () => { window.removeEventListener('resize', measure); ro?.disconnect(); clearInterval(ivRef.current); };
  }, [measure]);

  useEffect(() => { if (active) requestAnimationFrame(measure); }, [active, measure]);

  const togglePlay = () => {
    if (playing) { clearInterval(ivRef.current); setPlaying(false); return; }
    setPlaying(true);
    setT((cur) => (cur >= DURATION ? 0 : cur));
    ivRef.current = setInterval(() => {
      setT((cur) => {
        const next = cur + 0.1;
        if (next >= DURATION) { clearInterval(ivRef.current); setPlaying(false); return DURATION; }
        return next;
      });
    }, 100);
  };

  const selectF = (f) => { setSel(f.id); if (f.t != null) setT(f.t); };
  const decide = (id, d) => setDecisions((s) => ({ ...s, [id]: s[id] === d ? undefined : d }));
  const openCount = FINDINGS.filter((f) => !decisions[f.id]).length;

  const seek = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - r.left - 76) / (r.width - 76);
    if (x >= 0) setT(Math.min(DURATION, x * DURATION));
  };

  const stacked = compact || mode === 'stack';
  const gridCols = stacked ? 'minmax(0,1fr)' : mode === 'mid' ? '220px minmax(0,1fr)' : '248px minmax(0,1fr) 384px';
  const gridAreas = stacked ? "'list' 'viewer' 'findings' 'corr'" : mode === 'mid' ? "'list viewer' 'findings findings' 'corr corr'" : "'list viewer findings' 'corr corr findings'";

  const evidence = [
    { name: 'minister_holiday_clip.mp4', meta: 'Video · 00:42 · 18.4 MB', icon: 'movie', v: 'strong', sha: '9f2c41a7…e81b', on: true, onClick: () => { setSel('F-VID-002'); setT(14); } },
    { name: 'Audio track (from clip)', meta: 'Audio · 00:42 · 48 kHz', icon: 'graphic_eq', v: 'strong', sha: '5d81e0c2…07af', onClick: () => go('audio') },
    { name: 'podium_photo.jpg', meta: 'Image · 1280×720 · 2.1 MB', icon: 'image', v: 'ind', sha: '3b7e0d19…a4c2', onClick: () => go('image') },
    { name: 'Caption · WhatsApp forward', meta: 'Text · 214 characters', icon: 'notes', v: 'ind', sha: 'c41d9a3e…5f10', onClick: () => setSel('F-TXT-001') },
  ];

  const inFlag = t >= 14 && t <= 19;
  const trackLabel = { position: 'absolute', left: -76, fontSize: 11.5, fontWeight: 600, color: c.ink2 };

  return (
    <div ref={rootRef} style={{ padding: compact ? '24px 24px 48px' : '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 24, minWidth: 0, color: c.ink }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0, flex: '1 1 520px' }}>
          <div style={eyebrow}>Case · <span style={{ fontFamily: MONO, letterSpacing: '.02em' }}>C-0007</span> · Opened 19 Nov 2026</div>
          <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.035em', textWrap: 'balance' }}>Viral clip: minister announces holiday</h1>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 32, padding: '0 14px', borderRadius: 999, background: c.hero, color: '#fff', fontSize: 13.5, fontWeight: 700 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#D64545' }} />Strong indicators <span style={{ fontFamily: MONO, fontWeight: 500, color: YELLOW }}>0.71–0.88</span>
            </span>
            <span style={{ fontSize: 14, color: c.ink2, textWrap: 'pretty' }}>
              <b style={{ color: c.ink, fontWeight: 700 }}>Why:</b> an audio splice at 00:14.2 lines up with a motion break at 00:14.0, and the caption date conflicts with the photo's metadata.
            </span>
            <button onClick={() => setLimOpen((v) => !v)} style={{ ...linkBtn, fontFamily: 'inherit', fontSize: 13.5, fontWeight: 700 }}>Limitations</button>
          </div>
          {limOpen && (
            <div style={{ background: c.surface, border: `1px solid ${c.border}`, borderRadius: 14, padding: '14px 18px', maxWidth: 760, display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13.5, color: c.ink2, lineHeight: 1.5 }}>
              <span style={{ ...eyebrow, color: c.ink }}>Limitations of this verdict</span>
              <span>· Ranges describe how strongly analyzers agree. They are not the probability that the clip was edited.</span>
              <span>· 720p input limits face-region and lip-sync measurements.</span>
              <span>· Social-platform recompression can produce error-level patterns similar to editing.</span>
              <span>· Analyzers were tuned on our own seeded test set. <a href="#" onClick={preventThen(() => go('validation'))}>See validation</a>.</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          <SecondaryButton onClick={() => setDrawer(true)}><Icon name="history" size={19} />Chain of custody</SecondaryButton>
          <SecondaryButton onClick={() => go('analysis')}><Icon name="refresh" size={19} />Re-run analysis</SecondaryButton>
          <PrimaryButton onClick={() => go('report')} style={{ height: 40, padding: '0 18px' }}>Export report<Icon name="arrow_forward" size={19} /></PrimaryButton>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: gridCols, gridTemplateAreas: gridAreas, gap: 20, alignItems: 'start' }}>
        <section style={{ gridArea: 'list', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '0 2px' }}>
            <span style={eyebrow}>Evidence · 4</span>
            <span style={{ fontSize: 12, color: c.ink2 }}>originals read-only</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {evidence.map((e) => (
              <button key={e.name} onClick={e.onClick} {...hover({ bc: c.ink }, { flex: '1 1 200px', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 8, padding: 12, borderRadius: 14, border: `1px solid ${e.on ? c.ink : c.border}`, background: e.on ? c.surface : c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer' })}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', minWidth: 0, width: '100%' }}>
                  <span style={{ width: 34, height: 34, flex: 'none', borderRadius: 9, background: e.on ? YELLOW : c.surface, color: e.on ? '#111111' : c.ink, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={e.icon} size={19} /></span>
                  <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                    <span style={{ fontSize: 13.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.name}</span>
                    <span style={{ fontSize: 12, color: c.ink2 }}>{e.meta}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, width: '100%' }}>
                  <VerdictPill dot={VERDICTS[e.v][1]} label={VERDICTS[e.v][0]} h={22} fs={11.5} pad={9} dotSize={6} style={{ background: c.bg }} />
                  <span style={{ fontFamily: MONO, fontSize: 10.5, color: c.ink2 }}>{e.sha}</span>
                </div>
              </button>
            ))}
          </div>
        </section>

        <section style={{ gridArea: 'viewer', background: c.bg, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '14px 18px', borderBottom: `1px solid ${c.border}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
              <Icon name="movie" />
              <span style={{ fontSize: 14, fontWeight: 700 }}>minister_holiday_clip.mp4</span>
              <span style={{ fontSize: 12.5, color: c.ink2 }}>00:42 · 1280×720 · 30 fps</span>
            </div>
            <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>sha256 9f2c41a7…e81b</span>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ position: 'relative', aspectRatio: '16/9', borderRadius: 12, overflow: 'hidden', background: 'repeating-linear-gradient(135deg,#1A1A1A 0 12px,#202020 12px 24px)' }}>
              <div style={{ position: 'absolute', left: 16, top: 14, fontFamily: MONO, fontSize: 11, color: '#8A8A85' }}>video frame · press briefing, podium, single speaker</div>
              <div style={{ position: 'absolute', right: 16, top: 14, fontFamily: MONO, fontSize: 11, color: '#fff', background: 'rgba(17,17,17,.7)', padding: '3px 8px', borderRadius: 6 }}>frame {Math.round(t * 30)}</div>
              {inFlag && (
                <div style={{ position: 'absolute', left: '39%', top: '16%', width: '22%', height: '44%', border: `2px solid ${YELLOW}`, borderRadius: 6 }}>
                  <span style={{ position: 'absolute', left: -2, top: -26, background: YELLOW, color: '#111111', fontFamily: MONO, fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: '6px 6px 6px 0', whiteSpace: 'nowrap' }}>F-VID-002 · F-XM-001 · face region</span>
                </div>
              )}
              <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, background: 'linear-gradient(transparent,rgba(0,0,0,.55))' }}>
                <button onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'} style={{ width: 36, height: 36, borderRadius: '50%', border: 'none', background: c.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: c.ink }}>
                  <Icon name={playing ? 'pause' : 'play_arrow'} size={22} />
                </button>
                <span style={{ fontFamily: MONO, fontSize: 12, color: '#fff' }}>{fmt(t)} / 00:42.0</span>
                <div style={{ flex: 1, height: 4, borderRadius: 999, background: 'rgba(255,255,255,.25)', position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: pct(t), background: c.bg, borderRadius: 999 }} />
                  <div style={{ position: 'absolute', left: '33.3%', width: '11.9%', top: -2, bottom: -2, background: YELLOW, borderRadius: 2, opacity: 0.9 }} />
                </div>
                <Icon name="volume_up" style={{ color: '#fff' }} />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={eyebrow}>Timeline · suspicion</span>
                <span style={{ fontSize: 12, color: c.ink2 }}>Click any track to seek · flagged <span style={{ fontFamily: MONO, color: c.ink }}>00:14–00:19</span></span>
              </div>
              <div onClick={seek} style={{ position: 'relative', cursor: 'crosshair', display: 'flex', flexDirection: 'column', gap: 4, paddingLeft: 76 }}>
                <div style={{ position: 'absolute', left: 76, right: 0, top: 0, bottom: 0, pointerEvents: 'none' }}>
                  <div style={{ position: 'absolute', left: '33.33%', width: '11.9%', top: 0, bottom: 0, background: 'rgba(255,210,63,.28)', borderLeft: `1.5px solid ${YELLOW}`, borderRight: `1.5px solid ${YELLOW}` }} />
                  <div style={{ position: 'absolute', left: pct(t), top: -4, bottom: -4, width: 2, marginLeft: -1, background: c.ink, zIndex: 2 }} />
                </div>
                <div style={{ position: 'relative', height: 64, borderRadius: 8, background: c.surface }}>
                  <span style={{ ...trackLabel, top: 24 }}>Suspicion</span>
                  <svg viewBox="0 0 420 60" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', color: c.ink }}>
                    <path d={CURVE.area} fill="currentColor" fillOpacity={0.08} />
                    <path d={CURVE.line} fill="none" stroke="currentColor" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
                  </svg>
                </div>
                {TRACKS.map((tr) => (
                  <div key={tr.label} style={{ position: 'relative', height: 26, borderRadius: 6, background: c.surface }}>
                    <span style={{ ...trackLabel, top: 5 }}>{tr.label}</span>
                    {tr.marks.map(([id, a, b]) => (
                      <button key={id} title={id} onClick={(e) => { e.stopPropagation(); setSel(id); setT(a); }} style={{ position: 'absolute', left: pct(a), width: pct(b - a), minWidth: 10, top: 4, bottom: 4, borderRadius: 4, border: `1.5px solid ${c.ink}`, background: sel === id ? YELLOW : c.bg, cursor: 'pointer', padding: 0, zIndex: 3 }} />
                    ))}
                  </div>
                ))}
                <div style={{ position: 'relative', height: 16 }}>
                  {TICKS.map((s) => (
                    <span key={s} style={{ position: 'absolute', left: pct(s), transform: 'translateX(-50%)', fontFamily: MONO, fontSize: 10, color: '#8A8A85' }}>00:{String(s).padStart(2, '0')}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section style={{ gridArea: 'findings', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 2px' }}>
            <span style={eyebrow}>Findings · {FINDINGS.length} <span style={{ color: '#8A8A85' }}>· {openCount} awaiting review</span></span>
            <a href="#" onClick={preventThen(() => go('image'))} style={{ fontSize: 12, fontWeight: 600 }}>+2 in image</a>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 10 }}>
            {FINDINGS.map((f) => (
              <FindingCard
                key={f.id}
                f={f}
                selected={sel === f.id}
                decision={decisions[f.id]}
                altOpen={!!alt[f.id]}
                note={notes[f.id]}
                noteOpen={noteOpen === f.id}
                draft={drafts[f.id] ?? notes[f.id] ?? ''}
                onSelect={() => selectF(f)}
                onJump={() => (f.go ? go(f.go) : selectF(f))}
                onToggleAlt={() => setAlt((s) => ({ ...s, [f.id]: !s[f.id] }))}
                onDecide={(d) => decide(f.id, d)}
                onToggleNote={() => setNoteOpen((cur) => (cur === f.id ? null : f.id))}
                onDraft={(v) => setDrafts((s) => ({ ...s, [f.id]: v }))}
                onSaveNote={() => { setNotes((s) => ({ ...s, [f.id]: drafts[f.id] ?? s[f.id] })); setNoteOpen(null); }}
              />
            ))}
          </div>
        </section>

        <section style={{ gridArea: 'corr', background: c.bg, border: `1px solid ${c.border}`, borderRadius: 16, padding: 18, display: 'flex', flexDirection: 'column', gap: 14, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 10 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={eyebrow}>Cross-modal correlations · {RULES.length} rules fired</span>
              <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>How findings support or weaken each other</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 240 }}>
              <span style={{ fontSize: 12, color: c.ink2, whiteSpace: 'nowrap' }}>Combined</span>
              <RangeBar lo={0.71} hi={0.88} h={8} color={c.ink} />
              <span style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600 }}>0.71–0.88</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
            <div style={{ flex: '1 1 300px', background: c.surface, borderRadius: 12, padding: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ aspectRatio: '420/230' }}><CorrelationGraph selected={rule} /></div>
              <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 11.5, color: c.ink2, padding: '0 6px 4px' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 18, height: 2, background: c.ink }} />supports</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 18, borderTop: '2px dashed #E8A33D' }} />conflicts</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: YELLOW, border: `1.5px solid ${c.ink}` }} />selected rule</span>
              </div>
            </div>
            <div style={{ flex: '2 1 340px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {RULES.map((r) => {
                const on = rule === r.id;
                return (
                  <button key={r.id} onClick={() => setRule(r.id)} {...hover({ bc: c.ink }, { textAlign: 'left', display: 'flex', gap: 12, alignItems: 'flex-start', padding: '12px 14px', borderRadius: 12, border: `1px solid ${on ? c.ink : c.border}`, background: on ? c.hl : c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer' })}>
                    <span style={{ fontFamily: MONO, fontSize: 11.5, fontWeight: 600, paddingTop: 2, flex: 'none' }}>{r.id}</span>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
                      <span style={{ fontSize: 13.5, fontWeight: 700, textWrap: 'pretty' }}>{r.name}</span>
                      <span style={{ fontSize: 12, color: c.ink2, fontFamily: MONO }}>{r.links}</span>
                      <span style={{ fontSize: 12.5, color: c.ink2, textWrap: 'pretty' }}>{r.detail}</span>
                    </div>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 22, padding: '0 9px', borderRadius: 999, border: `1px solid ${c.border}`, background: c.bg, fontSize: 11.5, fontWeight: 700, flex: 'none' }}>
                      <Icon name={r.conflict ? 'remove' : 'add'} size={14} style={{ color: r.conflict ? '#E8A33D' : c.ink }} />{r.tag}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </section>
      </div>

      {drawer && <CustodyDrawer onClose={() => setDrawer(false)} />}
    </div>
  );
}
