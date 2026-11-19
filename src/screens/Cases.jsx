import { useState } from 'react';
import { c, VERDICTS, MONO, Icon, hover, VerdictPill, chipStyle, eyebrow, h1, page, Muted } from '../ui.jsx';
import { useApi, relTime } from '../api/client.js';
import { TypeIcons } from './Dashboard.jsx';

const TESTS = {
  all: () => true,
  review: (r) => r.verdict.key === 'review' || r.needs_review,
  strong: (r) => r.verdict.key === 'strong',
  inc: (r) => r.verdict.key === 'inc',
  closed: (r) => r.closed,
};

const FILTERS = [['all', 'All'], ['review', 'Needs review', c.ink], ['strong', 'Strong indicators', '#D64545'], ['inc', 'Inconclusive', '#8A8A85'], ['closed', 'Closed']];

const COLS = '80px minmax(240px,1fr) 110px 170px 80px 130px 100px 24px';

export default function Cases({ go, active }) {
  const [f, setF] = useState('all');
  const list = useApi(active ? '/cases' : null);
  const ALL = list.data || [];
  const rows = ALL.filter(TESTS[f]);
  const open = ALL.filter((r) => !r.closed).length;

  return (
    <div style={page}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Cases · {open} active · {ALL.length - open} closed</div>
        <h1 style={h1}>Cases</h1>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {FILTERS.map(([k, label, dot]) => (
          <button key={k} onClick={() => setF(k)} style={chipStyle(f === k)}>
            {dot && <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot }} />}
            {label}
            <span style={{ fontFamily: MONO, fontSize: 11.5, fontWeight: 500, opacity: 0.7 }}>{ALL.filter(TESTS[k]).length}</span>
          </button>
        ))}
      </div>
      <div style={{ border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'auto', boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
        <div style={{ minWidth: 980 }}>
          <div style={{ display: 'grid', gridTemplateColumns: COLS, gap: 16, padding: '12px 20px', background: c.surface, borderBottom: `1px solid ${c.border}`, fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: c.ink2 }}>
            <span>ID</span><span>Title</span><span>Evidence</span><span>Verdict</span><span>Findings</span><span>Investigator</span><span>Updated</span><span />
          </div>
          {list.error && <div style={{ padding: '14px 20px' }}><Muted>Could not load cases: {list.error.message}</Muted></div>}
          {list.data && !rows.length && <div style={{ padding: '14px 20px' }}><Muted>{ALL.length ? 'No cases match this filter.' : 'No cases yet. Use New case to add evidence.'}</Muted></div>}
          {rows.map((r) => (
            <button key={r.id} onClick={() => go(r.status === 'draft' ? 'newcase' : 'workspace', { caseId: r.id })} {...hover({ bg: c.surface }, { width: '100%', display: 'grid', gridTemplateColumns: COLS, gap: 16, alignItems: 'center', padding: '14px 20px', border: 'none', borderBottom: `1px solid ${c.line}`, background: c.bg, fontFamily: 'inherit', color: c.ink, textAlign: 'left', cursor: 'pointer' })}>
              <span style={{ fontFamily: MONO, fontSize: 12 }}>{r.id}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                <span style={{ fontSize: 14.5, fontWeight: 700 }}>{r.title}</span>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>Why: {r.why}</span>
              </div>
              <TypeIcons types={r.types} />
              <VerdictPill dot={VERDICTS[r.verdict.key][1]} label={r.verdict.label} style={{ justifySelf: 'start' }} />
              <span style={{ fontFamily: MONO, fontSize: 13 }}>{r.status === 'analyzed' ? r.findings_count : '—'}</span>
              <span style={{ fontSize: 13 }}>{r.investigator}</span>
              <span style={{ fontSize: 12.5, color: c.ink2 }}>{relTime(r.updated_at)}</span>
              <Icon name="chevron_right" size={18} style={{ color: '#8A8A85' }} />
            </button>
          ))}
        </div>
      </div>
      <span style={{ fontSize: 12.5, color: c.ink2 }}>Showing {rows.length} of {ALL.length} cases. Verdicts describe indicators found, not whether content is authentic.</span>
    </div>
  );
}
