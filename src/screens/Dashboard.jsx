import { c, VERDICTS, YELLOW, MONO, Icon, hover, VerdictPill, eyebrow, h1, page, preventThen } from '../ui.jsx';

const STATS = [
  { label: 'Active cases', value: '6', unit: '', icon: 'folder_open', foot: '2 opened this week' },
  { label: 'Evidence analyzed', value: '48', unit: '', icon: 'inventory_2', foot: 'Image, video, audio and text' },
  { label: 'Findings awaiting review', value: '11', unit: '', icon: 'rate_review', foot: '4 in C-0007' },
  { label: 'Avg. analysis time', value: '42', unit: 's', icon: 'timer', foot: 'On this device, per case' },
];

const STEPS = [
  ['Ingest', 'Hash every file and keep the original read-only.'],
  ['Analyze', 'Run image, video, audio and text analyzers locally.'],
  ['Correlate', 'Check where findings agree or conflict across media.'],
  ['Review', 'Accept, reject or annotate each finding.'],
  ['Report', 'Export a reproducible report with hashes.'],
];

const CASES = [
  { id: 'C-0007', title: 'Viral clip: minister announces holiday', why: 'audio splice at 00:14.2 lines up with a motion break', types: ['movie', 'image', 'notes'], v: 'strong', updated: '12 min ago' },
  { id: 'C-0006', title: 'Flood photo from Chennai post', why: 'error-level pattern around the waterline', types: ['image', 'notes'], v: 'ind', updated: '2 h ago' },
  { id: 'C-0005', title: "Voice note from 'bank manager'", why: 'too little clean audio to decide', types: ['graphic_eq'], v: 'inc', updated: 'Yesterday' },
  { id: 'C-0004', title: 'Campus event poster', why: 'metadata and pixels are consistent', types: ['image'], v: 'none', updated: '17 Nov' },
  { id: 'C-0003', title: 'Product review video', why: '3 findings not yet reviewed', types: ['movie', 'graphic_eq'], v: 'review', updated: '16 Nov' },
];

const VAL = [['Noise-floor step', 0.83], ['Optical-flow discontinuity', 0.79], ['Error level inconsistency', 0.68], ['Lip-sync correlation', 0.57]];

export function TypeIcons({ types }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {types.map((ty) => (
        <span key={ty} style={{ width: 26, height: 26, borderRadius: 8, background: c.surface, display: 'flex', alignItems: 'center', justifyContent: 'center', color: c.ink2 }}><Icon name={ty} size={16} /></span>
      ))}
    </div>
  );
}

const card = { background: c.bg, border: `1px solid ${c.border}`, borderRadius: 16, boxShadow: '0 1px 2px rgba(17,17,17,.04)' };

export default function Dashboard({ go }) {
  return (
    <div style={{ ...page, gap: 28 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Overview · Thursday 19 Nov</div>
        <h1 style={h1}>Good evening, Priya.</h1>
        <p style={{ margin: 0, fontSize: 15, color: c.ink2 }}>You have 11 findings waiting for review across 6 active cases.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 14 }}>
        {STATS.map((s) => (
          <div key={s.label} style={{ background: c.surface, border: `1px solid ${c.border}`, borderRadius: 16, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: c.ink2 }}>{s.label}</span>
              <Icon name={s.icon} style={{ color: c.ink2 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
              <span style={{ fontSize: 40, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1 }}>{s.value}</span>
              <span style={{ fontSize: 18, fontWeight: 700, color: c.ink2 }}>{s.unit}</span>
            </div>
            <span style={{ fontSize: 12.5, color: c.ink2 }}>{s.foot}</span>
          </div>
        ))}
      </div>

      <section style={{ background: c.hero, color: '#fff', borderRadius: 20, padding: '28px 30px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 620 }}>
            <span style={{ ...eyebrow, color: YELLOW }}>How TruthLens works</span>
            <h2 style={{ margin: 0, fontSize: 28, lineHeight: 1.15, fontWeight: 800, letterSpacing: '-0.03em', textWrap: 'balance' }}>Every finding is evidence-linked and reviewable</h2>
          </div>
          <span style={{ fontSize: 13.5, color: '#B8B8B2', maxWidth: 360, lineHeight: 1.5 }}>Analyzers suggest. You decide. Nothing goes into a report until a reviewer has seen it.</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 10 }}>
          {STEPS.map(([name, desc], i) => (
            <div key={name} style={{ border: '1px solid #2C2C2A', borderRadius: 14, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontFamily: MONO, fontSize: 12, color: YELLOW }}>0{i + 1}</span>
                <Icon name={i < 4 ? 'arrow_forward' : 'check'} size={18} style={{ color: '#8A8A85' }} />
              </div>
              <span style={{ fontSize: 16, fontWeight: 800, letterSpacing: '-0.01em' }}>{name}</span>
              <span style={{ fontSize: 12.5, color: '#B8B8B2', lineHeight: 1.45 }}>{desc}</span>
            </div>
          ))}
        </div>
      </section>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'stretch' }}>
        <section style={{ ...card, flex: '2 1 560px', minWidth: 0, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px 12px' }}>
            <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>Recent cases</span>
            <a href="#" onClick={preventThen(() => go('cases'))} style={{ fontSize: 13, fontWeight: 700 }}>All cases</a>
          </div>
          {CASES.map((cs) => (
            <button key={cs.id} onClick={() => go('workspace')} {...hover({ bg: c.surface }, { width: '100%', display: 'grid', gridTemplateColumns: '72px minmax(0,1fr) auto auto 90px', alignItems: 'center', gap: 16, padding: '14px 20px', border: 'none', borderTop: `1px solid ${c.line}`, background: c.bg, fontFamily: 'inherit', color: c.ink, textAlign: 'left', cursor: 'pointer' })}>
              <span style={{ fontFamily: MONO, fontSize: 12, color: c.ink2 }}>{cs.id}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                <span style={{ fontSize: 14.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{cs.title}</span>
                <span style={{ fontSize: 12.5, color: c.ink2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Why: {cs.why}</span>
              </div>
              <TypeIcons types={cs.types} />
              <VerdictPill dot={VERDICTS[cs.v][1]} label={VERDICTS[cs.v][0]} />
              <span style={{ fontSize: 12, color: c.ink2, textAlign: 'right', whiteSpace: 'nowrap' }}>{cs.updated}</span>
            </button>
          ))}
        </section>

        <section style={{ ...card, flex: '1 1 300px', padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={eyebrow}>Validation snapshot · sample data</span>
            <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>Seeded test set · 160 items</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {VAL.map(([name, p]) => (
              <div key={name} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ fontWeight: 600 }}>{name}</span>
                  <span style={{ fontFamily: MONO, fontSize: 12, color: c.ink2 }}>precision {p.toFixed(2)}</span>
                </div>
                <div style={{ height: 6, borderRadius: 999, background: c.line }}>
                  <div style={{ height: '100%', width: p * 100 + '%', borderRadius: 999, background: c.ink }} />
                </div>
              </div>
            ))}
          </div>
          <span style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.45 }}>Results from our own seeded test set. Not a general accuracy claim.</span>
          <a href="#" onClick={preventThen(() => go('validation'))} style={{ fontSize: 13, fontWeight: 700, marginTop: 'auto' }}>Open validation →</a>
        </section>
      </div>
    </div>
  );
}
