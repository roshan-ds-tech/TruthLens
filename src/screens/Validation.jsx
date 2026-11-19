import { c, YELLOW, MONO, Icon, eyebrow, h1, page, Muted } from '../ui.jsx';
import { useApi } from '../api/client.js';

// Reliability diagram paths from metrics.reliability (cross-validated predicted vs observed hit rate).
function chart(rel) {
  const X = (p) => 50 + p * 350;
  const Y = (p) => 260 - p * 240;
  const bins = rel.filter((b) => b.count > 0 && b.observed != null);
  const maxCount = Math.max(1, ...rel.map((b) => b.count));
  let line = '', pts = '', hist = '';
  bins.forEach((b, i) => {
    const x = X(b.predicted ?? b.mid), y = Y(b.observed);
    line += (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
    pts += `M${(x - 4).toFixed(1)} ${(y - 4).toFixed(1)}h8v8h-8z `;
  });
  rel.forEach((b) => {
    if (!b.count) return;
    const h = (b.count / maxCount) * 90;
    hist += `M${(X(b.mid) - 15).toFixed(1)} 260v-${h.toFixed(1)}h30v${h.toFixed(1)}z `;
  });
  return { line, pts, hist };
}

const fmt = (v) => (v == null ? '—' : v.toFixed(2));

const FP_COLS = '1.3fr 1fr 64px 1.3fr';
const axisText = { fontSize: 10, fontFamily: 'IBM Plex Mono', fill: '#8A8A85' };
const labelText = { fontSize: 11, fontFamily: 'Inter', fill: '#5F5F5A', textAnchor: 'middle' };

export default function Validation({ active }) {
  const m = useApi(active ? '/validation/metrics' : null);
  const data = m.data;
  const TILES = (data?.indicators || []).filter((t) => t.n_targets > 0);
  const FPS = (data?.false_positives || []).slice(0, 6);
  const CHART = chart(data?.reliability || []);
  if (!data) {
    return (
      <div style={page}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={eyebrow}>Validation · Self-made test set</div>
          <h1 style={h1}>How the analyzers behave on known samples</h1>
          <Muted>{m.error ? 'No validation run yet. Run make validate to build the seeded test set and measure every analyzer; results appear here.' : 'Loading…'}</Muted>
        </div>
      </div>
    );
  }
  return (
    <div style={page}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Validation · Self-made test set</div>
        <h1 style={h1}>How the analyzers behave on known samples</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, alignSelf: 'flex-start', padding: '10px 14px', borderRadius: 12, background: c.surface, border: `1px solid ${c.border}`, fontSize: 13.5 }}>
          <Icon name="info" size={19} />
          <span>Results from our own seeded test set. Not a general accuracy claim.</span>
          <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: YELLOW, color: '#111111' }}>TEST SET {data.version} · {data.n_items} ITEMS</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 12 }}>
        {TILES.map((t) => (
          <div key={t.key} style={{ border: `1px solid ${c.border}`, borderRadius: 16, padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 12, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Icon name={t.icon} size={19} style={{ color: c.ink2 }} />
              <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>n = {t.n_targets}</span>
            </div>
            <span style={{ fontSize: 14, fontWeight: 700, minHeight: 38 }}>{t.name}</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[['Precision', fmt(t.precision)], ['Recall', fmt(t.recall)]].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: 11.5, color: c.ink2 }}>{k}</span>
                  <span style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.018em' }}>{v}</span>
                </div>
              ))}
            </div>
            <span style={{ fontFamily: MONO, fontSize: 10.5, color: '#8A8A85' }}>FPR {t.fpr == null ? '—' : `${t.false_positives}/${t.n_negatives}`} · {t.n_findings} findings</span>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'stretch' }}>
        <section style={{ flex: '1 1 440px', minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.012em' }}>Reliability</span>
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
          <span style={{ fontSize: 12.5, color: c.ink2 }}>Points are 5-fold cross-validated Platt predictions; the dashed line is perfect calibration. Ranges, not single numbers, are shown because the set is small.</span>
        </section>

        <section style={{ flex: '1 1 440px', minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '18px 20px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.012em' }}>False positives</span>
            <span style={{ fontSize: 12.5, color: c.ink2 }}>Untouched samples that were flagged</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: FP_COLS, gap: 12, padding: '10px 20px', background: c.surface, borderTop: `1px solid ${c.border}`, borderBottom: `1px solid ${c.border}`, fontSize: 10.5, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: c.ink2 }}>
            <span>Sample type</span><span>Indicator</span><span>FP</span><span>Common cause</span>
          </div>
          {!FPS.length && <div style={{ padding: '12px 20px' }}><Muted>No untouched sample was flagged.</Muted></div>}
          {FPS.map((r) => (
            <div key={r.type + r.indicator} style={{ display: 'grid', gridTemplateColumns: FP_COLS, gap: 12, padding: '12px 20px', borderBottom: `1px solid ${c.line}`, fontSize: 13, alignItems: 'center' }}>
              <span style={{ fontWeight: 600 }}>{r.type}</span><span>{r.indicator}</span><span style={{ fontFamily: MONO }}>{r.label}</span><span style={{ color: c.ink2 }}>{r.cause}</span>
            </div>
          ))}
          <span style={{ padding: '12px 20px', fontFamily: MONO, fontSize: 10.5, color: '#8A8A85' }}>test set {data.version} · {data.n_items} items · seed {data.seed} · {data.generated_at.slice(0, 10)}</span>
        </section>
      </div>
    </div>
  );
}
