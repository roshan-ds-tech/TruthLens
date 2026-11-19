import { useEffect, useRef, useState } from 'react';
import { c, YELLOW, MONO, Icon, eyebrow, fmtRange, preventThen } from '../ui.jsx';

const DURATION = 42;
const pct = (x) => (x / DURATION) * 100 + '%';
const fmt = (t) => '00:' + t.toFixed(1).padStart(4, '0');
const mono = { fontFamily: MONO };

// Deterministic PRNG so the waveform and spectrogram look the same on every render.
function rnd(seed) {
  let x = seed;
  return () => (x = (x * 16807) % 2147483647) / 2147483647;
}

const SPEECH = [[0.8, 5.6], [5.9, 13.8], [14.2, 19.0], [19.4, 27.0], [27.5, 41.2]];
function env(t) {
  const on = SPEECH.some(([a, b]) => t >= a && t <= b);
  return on ? 0.55 + 0.4 * Math.abs(Math.sin(t * 5.3) * Math.sin(t * 1.7)) : 0.02;
}

const BARS = (() => {
  const r = rnd(3);
  return Array.from({ length: 140 }, (_, i) => {
    const t = ((i + 0.5) / 140) * DURATION;
    const floor = t >= 14.2 ? 0.1 : 0.04;
    const h = Math.max(floor, env(t) * (0.5 + r() * 0.5));
    return { h: Math.round(h * 92) + '%', flagged: t >= 14 && t <= 19 };
  });
})();

function drawSpectrogram(canvas) {
  const ctx = canvas.getContext('2d'), W = canvas.width, H = canvas.height, r = rnd(7);
  const img = ctx.createImageData(W, H);
  for (let x = 0; x < W; x++) {
    const t = (x / W) * DURATION, speech = env(t), floor = t >= 14.2 ? 0.2 : 0.07;
    for (let y = 0; y < H; y++) {
      const f = 1 - y / H;
      let v = floor * (0.6 + r() * 0.8);
      if (speech > 0.2) {
        [0.08, 0.16, 0.27, 0.4].forEach((b, i) => { v += speech * Math.exp(-((f - b - 0.02 * Math.sin(t * 3 + i)) ** 2) / 0.0012) * (1 - i * 0.18); });
        v += speech * 0.15 * Math.exp(-f * 4) * r();
      }
      const g = Math.max(0, 247 - Math.min(1, v) * 210) | 0, i4 = (y * W + x) * 4;
      img.data[i4] = g; img.data[i4 + 1] = g; img.data[i4 + 2] = g - 2; img.data[i4 + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
}

const SEGMENTS = [
  { id: 'F-AUD-001', name: 'Noise-floor step (possible splice)', a: 14.2, b: 14.7, key: 's3', lo: 0.70, hi: 0.86, v: ['Strong indicators', '#D64545'], shade: 'rgba(255,210,63,.55)', shadeSoft: 'rgba(255,210,63,.4)', expl: 'Noise floor jumps 9 dB in under 20 ms with no change in speaker distance. Alternative: microphone gain change.' },
  { id: 'F-XM-001', name: 'Lip-sync weak correlation', a: 14.0, b: 19.0, key: 's3', lo: 0.40, hi: 0.62, v: ['Inconclusive', '#8A8A85'], shade: 'rgba(255,210,63,.22)', shadeSoft: 'rgba(255,210,63,.16)', inc: true, expl: 'Speech energy and mouth movement correlate weakly. The face is partly turned in this window.' },
];

const TRANSCRIPT = [
  ['s1', 0.8, 5.6, 'Good evening, everyone. Thank you for joining at short notice.'],
  ['s2', 5.9, 13.8, 'As you know, the state has seen heavy rain this week, and our teams are on the ground.'],
  ['s3', 14.2, 19.0, 'The government has decided to declare a three-day holiday from tomorrow.', true],
  ['s4', 19.4, 27.0, 'All schools and offices will remain closed during this period.'],
  ['s5', 27.5, 41.2, 'We request everyone to stay safe and follow only official channels for updates. Thank you.'],
];

const TICKS = [0, 5, 10, 15, 20, 25, 30, 35, 40];
const sideLabel = { width: 84, flex: 'none', fontSize: 11.5, fontWeight: 600, color: c.ink2 };

export default function AudioViewer({ go, active }) {
  const [t, setT] = useState(14.2);
  const [seg, setSeg] = useState('F-AUD-001');
  const specRef = useRef(null);
  const trRef = useRef(null);

  const scrollTo = (key, smooth = true) => {
    const box = trRef.current;
    const el = box?.querySelector(`[data-seg="${key}"]`);
    if (el) box.scrollTo({ top: el.offsetTop - 8, behavior: smooth ? 'smooth' : 'auto' });
  };

  useEffect(() => { if (specRef.current) drawSpectrogram(specRef.current); }, []);

  // The transcript box has no layout while hidden, so jump to the flagged line once visible.
  useEffect(() => {
    if (!active) return undefined;
    const id = setTimeout(() => scrollTo('s3', false), 30);
    return () => clearTimeout(id);
  }, [active]);

  const seek = (e) => {
    const rc = e.currentTarget.getBoundingClientRect();
    const nt = Math.max(0, Math.min(DURATION, ((e.clientX - rc.left) / rc.width) * DURATION));
    setT(nt);
    const ln = TRANSCRIPT.find(([, a, b]) => nt >= a - 0.3 && nt <= b + 0.3);
    if (ln) scrollTo(ln[0]);
  };

  const pickSeg = (s) => (e) => { e.stopPropagation(); setSeg(s.id); setT(s.a); scrollTo(s.key); };
  const playhead = { position: 'absolute', left: pct(t), width: 2, marginLeft: -1, background: c.ink, pointerEvents: 'none' };

  return (
    <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 22, color: c.ink }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <a href="#" onClick={preventThen(() => go('workspace'))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />C-0007 workspace</a>
        <div style={eyebrow}>Evidence · <span style={mono}>C-0007</span> · Audio track · sha256 <span style={mono}>5d81e0c2…07af</span></div>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.035em' }}>Audio track of minister_holiday_clip.mp4</h1>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 30, padding: '0 13px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 13, fontWeight: 700 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#D64545' }} />Strong indicators <span style={{ ...mono, fontWeight: 500, color: c.ink2 }}>0.70–0.86</span>
          </span>
          <span style={{ fontSize: 14, color: c.ink2 }}><b style={{ color: c.ink }}>Why:</b> the background noise steps up by 9 dB at 00:14.2, right where the holiday sentence begins.</span>
          <a href="#" onClick={(e) => e.preventDefault()} style={{ fontSize: 13.5, fontWeight: 700 }}>Limitations</a>
        </div>
      </div>

      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button aria-label="Play" style={{ width: 36, height: 36, borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer' }}><Icon name="play_arrow" size={22} /></button>
            <span style={{ ...mono, fontSize: 12.5 }}>{fmt(t)} / 00:42.0</span>
            <span style={{ fontSize: 12.5, color: c.ink2 }}>48 kHz · mono · 16-bit</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {SEGMENTS.map((s) => {
              const on = seg === s.id;
              return (
                <button key={s.id} onClick={pickSeg(s)} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 32, padding: '0 13px', borderRadius: 999, border: `1px solid ${on ? YELLOW : c.border}`, background: on ? YELLOW : c.bg, fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, color: on ? '#111111' : c.ink, cursor: 'pointer' }}>
                  <span style={{ ...mono, fontWeight: 600 }}>{s.id}</span>{fmt(s.a)}–{fmt(s.b)}
                </button>
              );
            })}
          </div>
        </div>
        <div style={{ padding: '16px 16px 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <span style={{ ...sideLabel, paddingTop: 6 }}>Waveform</span>
            <div onClick={seek} style={{ position: 'relative', flex: 1, height: 120, borderRadius: 10, background: c.surface, cursor: 'crosshair' }}>
              {SEGMENTS.map((s) => (
                <button key={s.id} title={s.id} onClick={pickSeg(s)} style={{ position: 'absolute', top: 0, bottom: 0, left: pct(s.a), width: pct(s.b - s.a), minWidth: 8, border: 'none', borderLeft: '1.5px solid #E0B400', borderRight: '1.5px solid #E0B400', background: s.shade, padding: 0, cursor: 'pointer', zIndex: 1 }} />
              ))}
              <div style={{ position: 'absolute', inset: '0 6px', display: 'flex', alignItems: 'center', gap: 1, pointerEvents: 'none', zIndex: 2 }}>
                {BARS.map((b, i) => <span key={i} style={{ flex: 1, height: b.h, background: b.flagged ? c.ink : c.ink2, borderRadius: 1 }} />)}
              </div>
              <div style={{ ...playhead, top: -4, bottom: -4, zIndex: 3 }} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ ...sideLabel, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '4px 0' }}>
              <span>Spectrogram</span>
              <span style={{ ...mono, fontWeight: 400, fontSize: 10 }}>8 kHz<br />0 Hz</span>
            </div>
            <div onClick={seek} style={{ position: 'relative', flex: 1, height: 150, borderRadius: 10, overflow: 'hidden', background: c.surface, cursor: 'crosshair' }}>
              <canvas ref={specRef} width={1000} height={150} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
              {SEGMENTS.map((s) => (
                <div key={s.id} style={{ position: 'absolute', top: 0, bottom: 0, left: pct(s.a), width: pct(s.b - s.a), minWidth: 8, borderLeft: '1.5px solid #E0B400', borderRight: '1.5px solid #E0B400', background: s.shadeSoft, pointerEvents: 'none' }} />
              ))}
              <span style={{ position: 'absolute', left: '34.5%', top: 8, ...mono, fontSize: 10.5, background: YELLOW, color: '#111111', padding: '2px 7px', borderRadius: 5, pointerEvents: 'none' }}>−62 → −53 dB</span>
              <div style={{ ...playhead, top: 0, bottom: 0 }} />
            </div>
          </div>
          <div style={{ position: 'relative', height: 16, marginLeft: 96 }}>
            {TICKS.map((s) => <span key={s} style={{ position: 'absolute', left: pct(s), transform: 'translateX(-50%)', ...mono, fontSize: 10, color: '#8A8A85' }}>00:{String(s).padStart(2, '0')}</span>)}
          </div>
        </div>
      </section>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-start' }}>
        <section style={{ flex: '2 1 560px', minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${c.border}`, background: c.surface }}>
            <span style={{ fontSize: 14, fontWeight: 800 }}>Transcript · word timestamps</span>
            <span style={{ ...mono, fontSize: 11.5, color: c.ink2 }}>whisper-small · 58 words · conf 0.91</span>
          </div>
          <div ref={trRef} style={{ position: 'relative', height: 300, overflow: 'auto', padding: '8px 16px 16px', scrollBehavior: 'smooth' }}>
            {TRANSCRIPT.map(([key, a, b, text, flagged]) => {
              const words = text.split(' '), step = (b - a) / words.length;
              const activeLine = t >= a && t <= b;
              return (
                <div key={key} data-seg={key} style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: 14, padding: 12, marginTop: 6, borderRadius: 12, background: flagged ? c.hl : c.bg, border: `1px solid ${activeLine ? c.ink : flagged ? c.hlb : c.line}` }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <span style={{ ...mono, fontSize: 12, fontWeight: 600 }}>{fmt(a)}–{fmt(b).slice(3)}</span>
                    {flagged && <span style={{ ...mono, fontSize: 10.5, color: c.ink2 }}>F-AUD-001 · F-XM-001</span>}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 4px' }}>
                    {words.map((w, i) => {
                      const wt = a + i * step;
                      const cur = t >= wt && t < wt + step;
                      return (
                        <button key={i} onClick={() => setT(wt)} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 1, border: 'none', padding: '2px 4px', borderRadius: 6, background: cur ? YELLOW : 'transparent', fontFamily: 'inherit', cursor: 'pointer', color: cur ? '#111111' : c.ink }}>
                          <span style={{ ...mono, fontSize: 9.5, color: '#8A8A85' }}>{wt.toFixed(1)}</span>
                          <span style={{ fontSize: 15, fontWeight: 500 }}>{w}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
        <aside style={{ flex: '1 1 320px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span style={eyebrow}>Findings in this track</span>
          {SEGMENTS.map((s) => {
            const on = seg === s.id;
            return (
              <button key={s.id} onClick={pickSeg(s)} style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 8, padding: '14px 16px', borderRadius: 14, border: `1px solid ${on ? c.ink : c.border}`, boxShadow: on ? '0 0 0 3px rgba(255,210,63,.55)' : 'none', background: c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                  <span style={{ ...mono, fontSize: 11.5, fontWeight: 600 }}>{s.id}</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 20, padding: '0 8px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 11, fontWeight: 600 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.v[1] }} />{s.v[0]}
                  </span>
                </div>
                <span style={{ fontSize: 14.5, fontWeight: 700 }}>{s.name}</span>
                <span style={{ ...mono, fontSize: 12 }}>{fmt(s.a)}–{fmt(s.b)}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                  <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: c.line }}>
                    <div style={{ position: 'absolute', top: 0, bottom: 0, left: s.lo * 100 + '%', width: (s.hi - s.lo) * 100 + '%', borderRadius: 999, background: s.inc ? '#8A8A85' : c.ink }} />
                  </div>
                  <span style={{ ...mono, fontSize: 11.5 }}>{fmtRange(s.lo, s.hi)}</span>
                </div>
                <span style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.45 }}>{s.expl}</span>
              </button>
            );
          })}
        </aside>
      </div>
    </div>
  );
}
