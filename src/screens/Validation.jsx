import { c, YELLOW, MONO, Icon, eyebrow, h1, page } from '../ui.jsx';

const TILES = [
  { icon: 'graphic_eq', name: 'Noise-floor step', p: '0.83', r: '0.71', n: '30' },
  { icon: 'movie', name: 'Optical-flow discontinuity', p: '0.79', r: '0.68', n: '30' },
  { icon: 'image', name: 'Error level inconsistency', p: '0.68', r: '0.74', n: '40' },
  { icon: 'notes', name: 'Date conflict', p: '0.92', r: '0.88', n: '30' },
  { icon: 'join_inner', name: 'Lip-sync correlation', p: '0.57', r: '0.49', n: '30' },
];

const FPS = [
  { type: 'WhatsApp-recompressed JPEG', ind: 'Error level', fp: '7/40', cause: 'Platform recompression' },
  { type: 'Low-light phone video', ind: 'Lip-sync', fp: '6/30', cause: 'Mouth region too dark' },
  { type: 'Screen-recorded video', ind: 'Optical flow', fp: '4/30', cause: 'Dropped frames' },
  { type: 'Call recording', ind: 'Noise floor', fp: '3/30', cause: 'Noise suppression toggling' },
  { type: 'Old photo, new caption', ind: 'Date conflict', fp: '1/30', cause: 'Camera clock wrong' },
];

// Reliability diagram paths, computed once.
const CHART = (() => {
  const X = (p) => 50 + p * 350;
  const Y = (p) => 260 - p * 240;
  const obs = [0.06, 0.14, 0.27, 0.34, 0.43, 0.52, 0.66, 0.77, 0.88];
  const cnt = [6, 9, 14, 18, 22, 25, 24, 21, 15];
  let line = '', pts = '', hist = '';
  obs.forEach((o, i) => {
    const p = 0.1 + i * 0.1, x = X(p), y = Y(o);
    line += (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
    pts += `M${(x - 4).toFixed(1)} ${(y - 4).toFixed(1)}h8v8h-8z `;
    const h = cnt[i] * 3.2;
    hist += `M${(x - 15).toFixed(1)} 260v-${h.toFixed(1)}h30v${h.toFixed(1)}z `;
  });
  return { line, pts, hist };
})();

const FP_COLS = '1.3fr 1fr 64px 1.3fr';
const axisText = { fontSize: 10, fontFamily: 'JetBrains Mono', fill: '#8A8A85' };
const labelText = { fontSize: 11, fontFamily: 'Manrope', fill: '#5F5F5A', textAnchor: 'middle' };

export default function Validation() {
  return (
    <div style={page}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Validation · Self-made test set</div>
        <h1 style={h1}>How the analyzers behave on known samples</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, alignSelf: 'flex-start', padding: '10px 14px', borderRadius: 12, background: c.surface, border: `1px solid ${c.border}`, fontSize: 13.5 }}>
          <Icon name="info" size={19} />
          <span>Results from our own seeded test set. Not a general accuracy claim.</span>
          <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: YELLOW, color: '#111111' }}>SAMPLE DATA</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 12 }}>
        {TILES.map((t) => (
          <div key={t.name} style={{ border: `1px solid ${c.border}`, borderRadius: 16, padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 12, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Icon name={t.icon} size={19} style={{ color: c.ink2 }} />
              <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>n = {t.n}</span>
            </div>
            <span style={{ fontSize: 14, fontWeight: 700, minHeight: 38 }}>{t.name}</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[['Precision', t.p], ['Recall', t.r]].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: 11.5, color: c.ink2 }}>{k}</span>
                  <span style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.03em' }}>{v}</span>
                </div>
              ))}
            </div>
            <span style={{ fontFamily: MONO, fontSize: 10.5, color: '#8A8A85' }}>sample values</span>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'stretch' }}>
        <section style={{ flex: '1 1 440px', minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 17, fontWeight: 800, letterSpacing: '-0.02em' }}>Reliability</span>
            <span style={{ fontSize: 12.5, color: c.ink2 }}>Predicted confidence vs observed hit rate · all indicators</span>
          </div>
          <svg viewBox="0 0 420 300" style={{ width: '100%', height: 'auto', display: 'block' }}>
            <path d="M50 20 V260 H400" fill="none" style={{ stroke: c.border }} />
            <path d="M50 140 H400 M225 20 V260" fill="none" style={{ stroke: 'var(--tl-line,#F0F0EC)' }} />
            <path d={CHART.hist} style={{ fill: c.surface2 }} />
            <path d="M50 260 L400 20" fill="none" stroke="#8A8A85" strokeDasharray="4 4" />
            <path d={CHART.line} fill="none" style={{ stroke: c.ink }} strokeWidth="2" />
            <path d={CHART.pts} fill={YELLOW} stroke="#111111" strokeWidth="1.5" />
            <text x="50" y="278" textAnchor="middle" {...axisText}>0.0</text>
            <text x="225" y="278" textAnchor="middle" {...axisText}>0.5</text>
            <text x="400" y="278" textAnchor="middle" {...axisText}>1.0</text>
            <text x="225" y="296" {...labelText}>predicted confidence (range midpoint)</text>
            <text x="40" y="263" textAnchor="end" {...axisText}>0.0</text>
            <text x="40" y="143" textAnchor="end" {...axisText}>0.5</text>
            <text x="40" y="23" textAnchor="end" {...axisText}>1.0</text>
            <text x="14" y="140" transform="rotate(-90 14 140)" {...labelText}>observed hit rate</text>
          </svg>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12, color: c.ink2 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 18, height: 2, background: c.ink }} />observed</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 18, borderTop: '1.5px dashed #8A8A85' }} />perfect calibration</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 12, height: 10, background: c.surface2 }} />samples per bin</span>
          </div>
          <span style={{ fontSize: 12.5, color: c.ink2 }}>Mid-range findings are slightly overconfident, which is why ranges rather than single numbers are shown.</span>
        </section>

        <section style={{ flex: '1 1 440px', minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '18px 20px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 17, fontWeight: 800, letterSpacing: '-0.02em' }}>False positives</span>
            <span style={{ fontSize: 12.5, color: c.ink2 }}>Untouched samples that were flagged</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: FP_COLS, gap: 12, padding: '10px 20px', background: c.surface, borderTop: `1px solid ${c.border}`, borderBottom: `1px solid ${c.border}`, fontSize: 10.5, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: c.ink2 }}>
            <span>Sample type</span><span>Indicator</span><span>FP</span><span>Common cause</span>
          </div>
          {FPS.map((r) => (
            <div key={r.type} style={{ display: 'grid', gridTemplateColumns: FP_COLS, gap: 12, padding: '12px 20px', borderBottom: `1px solid ${c.line}`, fontSize: 13, alignItems: 'center' }}>
              <span style={{ fontWeight: 600 }}>{r.type}</span><span>{r.ind}</span><span style={{ fontFamily: MONO }}>{r.fp}</span><span style={{ color: c.ink2 }}>{r.cause}</span>
            </div>
          ))}
          <span style={{ padding: '12px 20px', fontFamily: MONO, fontSize: 10.5, color: '#8A8A85' }}>sample data · test set v0.3 · 160 items · seed 7</span>
        </section>
      </div>
    </div>
  );
}
