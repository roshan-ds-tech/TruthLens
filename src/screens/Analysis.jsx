import { useEffect, useRef, useState } from 'react';
import { c, MONO, Icon, eyebrow, h1, page, PrimaryButton } from '../ui.jsx';

const ITEMS = [
  { icon: 'movie', name: 'minister_holiday_clip.mp4', meta: 'Video · 00:42', sha: '9f2c41a7…e81b', steps: ['Metadata', 'Keyframes', 'Optical flow', 'Face region', 'Lip-sync'], start: 3, t0: 31 },
  { icon: 'graphic_eq', name: 'Audio track (from clip)', meta: 'Audio · 00:42', sha: '5d81e0c2…07af', steps: ['Metadata', 'Noise floor', 'Spectral', 'Transcript'], start: 2, t0: 24 },
  { icon: 'image', name: 'podium_photo.jpg', meta: 'Image · 2.1 MB', sha: '3b7e0d19…a4c2', steps: ['Metadata', 'Error level analysis', 'Noise map', 'Copy-move', 'Regions'], start: 3, t0: 18 },
  { icon: 'notes', name: 'Caption · WhatsApp forward', meta: 'Text · 214 chars', sha: 'c41d9a3e…5f10', steps: ['Claim extraction', 'Date and entity check', 'Cross-check with EXIF'], start: 2, t0: 6 },
];

const BASE_LOG = [
  ['21:45:10.004', 'run', 'tl-analyze 0.9.1 · run 2 · --vfr · seed 7'],
  ['21:45:10.021', 'ingest', 'verified sha256 9f2c41a7…e81b (read-only)'],
  ['21:45:10.024', 'ingest', 'verified sha256 3b7e0d19…a4c2 (read-only)'],
  ['21:45:10.031', 'ingest', 'verified sha256 c41d9a3e…5f10'],
  ['21:45:10.412', 'video', 'metadata: h264 · 1280x720 · 29.97 fps (vfr)'],
  ['21:45:11.880', 'audio', 'extracted 48 kHz mono · sha256 5d81e0c2…07af'],
  ['21:45:12.106', 'image', 'EXIF DateTimeOriginal 2024:03:03 10:41:22'],
  ['21:45:12.110', 'text', 'claim date 12 Nov 2026 · entities: minister, state'],
  ['21:45:13.340', 'text', 'F-TXT-001 date conflict · range 0.80–0.94'],
  ['21:45:16.902', 'image', 'ELA q=90 · podium region delta 2.4σ'],
  ['21:45:17.215', 'audio', 'noise floor −62 → −53 dB at 00:14.2'],
  ['21:45:17.216', 'audio', 'F-AUD-001 noise-floor step · range 0.70–0.86'],
  ['21:45:21.660', 'video', 'flow residual spike frames 420–423'],
  ['21:45:21.662', 'video', 'F-VID-002 optical-flow discontinuity · range 0.64–0.81'],
];

// Lines revealed one per tick while the run progresses.
const MORE_LOG = [
  ['21:45:24.118', 'image', 'noise map: 3 regions above threshold'],
  ['21:45:26.540', 'audio', 'transcript: 58 words · mean conf 0.91'],
  ['21:45:28.003', 'video', 'face region tracked 94% of frames'],
  ['21:45:30.771', 'image', 'F-IMG-003 error level inconsistency · range 0.52–0.71'],
  ['21:45:33.290', 'image', 'copy-move: 1 weak match on banner'],
  ['21:45:36.415', 'xmodal', 'lip-sync 00:14–00:19 r=0.31 · face turned'],
  ['21:45:37.002', 'xmodal', 'F-XM-001 lip-sync weak correlation · inconclusive'],
  ['21:45:38.660', 'correl', 'rules fired: R-03 R-07 R-11 R-14'],
  ['21:45:39.120', 'correl', 'combined range 0.71–0.88'],
  ['21:45:39.480', 'custody', 'findings 2be1…48d7 appended to log'],
  ['21:45:39.501', 'run', 'complete · 7 findings · 0 errors'],
];

const LAST_TICK = MORE_LOG.length;
const pad2 = (n) => String(n).padStart(2, '0');

function StepChip({ label, isDone, isRun }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 28, padding: '0 12px 0 8px', borderRadius: 999, border: `1px solid ${isRun ? c.hlb : c.border}`, background: isRun ? c.hl : isDone ? c.bg : c.surface, fontSize: 12.5, fontWeight: 600, color: isDone || isRun ? c.ink : '#8A8A85' }}>
      {isDone && <Icon name="check" size={16} style={{ color: c.ink }} />}
      {isRun && <span style={{ width: 12, height: 12, margin: '0 2px', borderRadius: '50%', border: `2px solid ${c.border}`, borderTopColor: c.ink, animation: 'tlspin .9s linear infinite' }} />}
      {!isDone && !isRun && <span style={{ width: 12, height: 12, margin: '0 2px', borderRadius: '50%', border: '1.5px dashed #B8B8B2' }} />}
      {label}
    </span>
  );
}

export default function Analysis({ go, active }) {
  const [tick, setTick] = useState(0);
  const logRef = useRef(null);

  // Restart the simulated run each time the screen becomes active.
  useEffect(() => {
    if (!active) return undefined;
    setTick(0);
    const iv = setInterval(() => setTick((k) => (k >= LAST_TICK ? k : k + 1)), 1100);
    return () => clearInterval(iv);
  }, [active]);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [tick, active]);

  let totalSteps = 0, doneSteps = 0;
  const rows = ITEMS.map((r, i) => {
    const done = Math.min(r.steps.length, r.start + Math.floor((tick + i) / 3));
    totalSteps += r.steps.length;
    doneSteps += done;
    return { ...r, done, time: done === r.steps.length ? 'done' : '00:' + pad2(r.t0 + tick) };
  });
  const allDone = doneSteps === totalSteps;
  const log = [...BASE_LOG, ...MORE_LOG.slice(0, tick)];

  return (
    <div style={page}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={eyebrow}>Analysis · <span style={{ fontFamily: MONO }}>C-0007</span> · Run 2</div>
          <h1 style={h1}>{allDone ? 'Analysis complete · 7 findings' : 'Analyzing 4 evidence items'}</h1>
          <p style={{ margin: 0, fontSize: 14.5, color: c.ink2 }}>
            Elapsed <span style={{ fontFamily: MONO, color: c.ink }}>00:{pad2(28 + tick)}</span> · estimated <span style={{ fontFamily: MONO }}>00:42</span> · CPU, 8 threads · no network
          </p>
        </div>
        <PrimaryButton onClick={() => go('workspace')} style={{ opacity: allDone ? 1 : 0.55 }}>Open workspace<Icon name="arrow_forward" size={19} /></PrimaryButton>
      </div>
      <div style={{ height: 8, borderRadius: 999, background: c.line, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: Math.round((doneSteps / totalSteps) * 100) + '%', background: c.ink, borderRadius: 999, transition: 'width .6s ease' }} />
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-start' }}>
        <div style={{ flex: '3 1 560px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rows.map((r) => (
            <div key={r.name} style={{ border: `1px solid ${c.border}`, borderRadius: 14, padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ width: 38, height: 38, flex: 'none', borderRadius: 10, background: c.surface, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={r.icon} /></span>
                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 14.5, fontWeight: 700 }}>{r.name}</span>
                  <span style={{ fontSize: 12.5, color: c.ink2 }}>{r.meta} · <span style={{ fontFamily: MONO }}>{r.sha}</span></span>
                </div>
                <span style={{ fontFamily: MONO, fontSize: 12, color: c.ink2 }}>{r.done}/{r.steps.length} · {r.time}</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {r.steps.map((label, j) => <StepChip key={label} label={label} isDone={j < r.done} isRun={j === r.done} />)}
              </div>
            </div>
          ))}
        </div>
        <section style={{ flex: '2 1 380px', minWidth: 0, background: c.surface, border: `1px solid ${c.border}`, borderRadius: 14, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>
            <span style={eyebrow}>Live log</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: c.ink2 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: allDone ? '#3E9B5F' : '#E8A33D' }} />{allDone ? 'finished' : 'running'}
            </span>
          </div>
          <div ref={logRef} style={{ height: 440, overflow: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 3, fontFamily: MONO, fontSize: 11.5, lineHeight: 1.55 }}>
            {log.map(([t, src, msg]) => (
              <div key={t} style={{ display: 'grid', gridTemplateColumns: '92px 64px 1fr', gap: 8, color: /F-[A-Z]+-\d/.test(msg) ? c.ink : c.ink2 }}>
                <span style={{ color: '#8A8A85' }}>{t}</span><span>{src}</span><span style={{ wordBreak: 'break-all' }}>{msg}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
