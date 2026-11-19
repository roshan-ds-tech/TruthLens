import { c, VERDICTS, YELLOW, MONO, Icon, hover, VerdictPill, eyebrow, h1, page, preventThen, Muted } from '../ui.jsx';
import { DeepfakePill } from '../Deepfake.jsx';
import { useApi, relTime, useServerMode, PRIVACY } from '../api/client.js';

const STEPS = [
  ['Ingest', 'Hash every file and keep the original read-only.'],
  ['Analyze', null],
  ['Correlate', 'Check where findings agree or conflict across media.'],
  ['Review', 'Accept, reject or annotate each finding.'],
  ['Report', 'Export a reproducible report with hashes.'],
];

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

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

export default function Dashboard({ go, active, investigator }) {
  const stats = useApi(active ? '/stats' : null);
  const privacy = PRIVACY[useServerMode()];
  const cases = useApi(active ? '/cases' : null);
  const metrics = useApi(active ? '/validation/metrics' : null);
  const st = stats.data;
  const today = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' });
  const retry = (e) => { e.preventDefault(); stats.reload(); cases.reload(); metrics.reload(); };
  const STATS = !st ? [
    ['Active cases', 'folder_open'], ['Evidence analyzed', 'inventory_2'], ['Findings awaiting review', 'rate_review'], ['Avg. analysis time', 'timer'],
  ].map(([label, icon]) => ({ label, icon, value: '—', unit: '', foot: stats.error ? 'Unavailable' : 'Loading…' })) : [
    { label: 'Active cases', value: String(st.active_cases), unit: '', icon: 'folder_open', foot: `${st.opened_this_week} opened this week` },
    { label: 'Evidence analyzed', value: String(st.evidence_count), unit: '', icon: 'inventory_2',
      foot: st.evidence_stored > st.evidence_count ? `${st.evidence_stored - st.evidence_count} more uploaded, not analyzed yet`
        : st.evidence_kinds.length ? st.evidence_kinds.map((k) => k[0].toUpperCase() + k.slice(1)).join(', ') : 'No evidence yet' },
    { label: 'Findings awaiting review', value: String(st.pending_review), unit: '', icon: 'rate_review', foot: st.top_pending_case.count ? `${st.top_pending_case.count} in ${st.top_pending_case.id}` : 'Nothing pending' },
    { label: 'Avg. analysis time', value: st.avg_analysis_seconds == null ? '—' : String(st.avg_analysis_seconds), unit: st.avg_analysis_seconds == null ? '' : 's', icon: 'timer', foot: `${privacy.where[0].toUpperCase()}${privacy.where.slice(1)}, per case` },
  ];
  const CASES = (cases.data || []).slice(0, 5);
  const VAL = (metrics.data?.indicators || []).filter((v) => v.precision != null && v.n_findings >= 6)
    .sort((x, y) => y.n_findings - x.n_findings).slice(0, 4);
  return (
    <div style={{ ...page, gap: 28 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Overview · {today}</div>
        <h1 style={h1}>{greeting()}{investigator ? `, ${investigator.split(' ')[0]}` : ''}.</h1>
        <p style={{ margin: 0, fontSize: 15, color: c.ink2 }}>
          {st ? `You have ${st.pending_review} finding${st.pending_review === 1 ? '' : 's'} waiting for review across ${st.active_cases} active case${st.active_cases === 1 ? '' : 's'}.`
            : stats.error ? <>{stats.error.message} <a href="#" onClick={retry} style={{ fontWeight: 700 }}>Retry</a></> : 'Loading…'}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 14 }}>
        {STATS.map((s) => (
          <div key={s.label} style={{ background: c.surface, border: `1px solid ${c.border}`, borderRadius: 16, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: c.ink2 }}>{s.label}</span>
              <Icon name={s.icon} style={{ color: c.ink2 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
              <span style={{ fontSize: 40, fontWeight: 700, letterSpacing: '-0.024em', lineHeight: 1 }}>{s.value}</span>
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
            <h2 style={{ margin: 0, fontSize: 28, lineHeight: 1.15, fontWeight: 700, letterSpacing: '-0.018em', textWrap: 'balance' }}>Every finding is evidence-linked and reviewable</h2>
          </div>
          <span style={{ fontSize: 13.5, color: '#B8B8B2', maxWidth: 360, lineHeight: 1.5 }}>Analyzers suggest. You decide. Every report marks each finding as accepted, rejected or not yet reviewed.</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 10 }}>
          {STEPS.map(([name, desc], i) => (
            <div key={name} style={{ border: '1px solid #2C2C2A', borderRadius: 14, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontFamily: MONO, fontSize: 12, color: YELLOW }}>0{i + 1}</span>
                <Icon name={i < 4 ? 'arrow_forward' : 'check'} size={18} style={{ color: '#8A8A85' }} />
              </div>
              <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.01em' }}>{name}</span>
              <span style={{ fontSize: 12.5, color: '#B8B8B2', lineHeight: 1.45 }}>{desc || privacy.analyzeStep}</span>
            </div>
          ))}
        </div>
      </section>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'stretch' }}>
        <section style={{ ...card, flex: '2 1 560px', minWidth: 0, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px 12px' }}>
            <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.012em' }}>Recent cases</span>
            <a href="#" onClick={preventThen(() => go('cases'))} style={{ fontSize: 13, fontWeight: 700 }}>All cases</a>
          </div>
          {cases.data && !CASES.length && <div style={{ padding: '6px 20px 18px' }}><Muted>No cases yet. Use New case to add evidence.</Muted></div>}
          {cases.error && !cases.data && <div style={{ padding: '6px 20px 18px' }}><Muted>Couldn’t load cases. <a href="#" onClick={retry} style={{ fontWeight: 700 }}>Retry</a></Muted></div>}
          {!cases.data && !cases.error && <div style={{ padding: '6px 20px 18px' }}><Muted>Loading cases…</Muted></div>}
          {CASES.map((cs) => (
            <button key={cs.id} onClick={() => go('workspace', { caseId: cs.id })} {...hover({ bg: c.surface }, { width: '100%', display: 'grid', gridTemplateColumns: '72px minmax(0,1fr) auto auto 90px', alignItems: 'center', gap: 16, padding: '14px 20px', border: 'none', borderTop: `1px solid ${c.line}`, background: c.bg, fontFamily: 'inherit', color: c.ink, textAlign: 'left', cursor: 'pointer' })}>
              <span style={{ fontFamily: MONO, fontSize: 12, color: c.ink2 }}>{cs.id}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                <span style={{ fontSize: 14.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{cs.title}</span>
                <span style={{ fontSize: 12.5, color: c.ink2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Why: {cs.why}</span>
              </div>
              <TypeIcons types={cs.types} />
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
                <VerdictPill dot={VERDICTS[cs.verdict.key][1]} label={cs.verdict.label} />
                <DeepfakePill d={cs.deepfake} h={24} fs={12} style={{ padding: '0 10px' }} />
              </div>
              <span style={{ fontSize: 12, color: c.ink2, textAlign: 'right', whiteSpace: 'nowrap' }}>{relTime(cs.updated_at)}</span>
            </button>
          ))}
        </section>

        <section style={{ ...card, flex: '1 1 300px', padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={eyebrow}>Validation snapshot · {metrics.data ? `test set ${metrics.data.version}` : 'not run'}</span>
            <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.012em' }}>{metrics.data ? `Seeded test set · ${metrics.data.n_items} items` : 'No validation results yet'}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {metrics.error && <Muted>Run <span style={{ fontFamily: MONO }}>make validate</span> to measure the analyzers on the seeded test set.</Muted>}
            {VAL.map(({ name, precision: p }) => (
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
