import { useState } from 'react';
import { c, VERDICTS, MONO, Icon, hover, VerdictPill, chipStyle, eyebrow, h1, page } from '../ui.jsx';
import { TypeIcons } from './Dashboard.jsx';

const ALL = [
  { id: 'C-0008', title: 'Toll plaza CCTV still', why: 'analysis queued, 1 image', types: ['image'], v: 'review', findings: '—', who: 'Arjun M.', updated: '5 min ago' },
  { id: 'C-0007', title: 'Viral clip: minister announces holiday', why: 'audio splice at 00:14.2 lines up with a motion break', types: ['movie', 'image', 'notes'], v: 'strong', findings: '7', who: 'Priya S.', updated: '12 min ago', review: true },
  { id: 'C-0006', title: 'Flood photo from Chennai post', why: 'error-level pattern around the waterline', types: ['image', 'notes'], v: 'ind', findings: '3', who: 'Priya S.', updated: '2 h ago' },
  { id: 'C-0005', title: "Voice note from 'bank manager'", why: 'too little clean audio to decide', types: ['graphic_eq'], v: 'inc', findings: '2', who: 'Nikhil R.', updated: 'Yesterday' },
  { id: 'C-0004', title: 'Campus event poster', why: 'metadata and pixels are consistent', types: ['image'], v: 'none', findings: '0', who: 'Priya S.', updated: '17 Nov' },
  { id: 'C-0003', title: 'Product review video', why: '3 findings not yet reviewed', types: ['movie', 'graphic_eq'], v: 'review', findings: '3', who: 'Arjun M.', updated: '16 Nov' },
  { id: 'C-0002', title: 'Hospital donation screenshot', why: 'font and layout match the source app', types: ['image', 'notes'], v: 'none', findings: '0', who: 'Nikhil R.', updated: '09 Nov', closed: true },
  { id: 'C-0001', title: 'Election rally audio', why: 'crowd noise masks splice analysis', types: ['graphic_eq'], v: 'inc', findings: '1', who: 'Priya S.', updated: '02 Nov', closed: true },
];

const TESTS = {
  all: () => true,
  review: (r) => r.v === 'review' || r.review,
  strong: (r) => r.v === 'strong',
  inc: (r) => r.v === 'inc',
  closed: (r) => r.closed,
};

const FILTERS = [['all', 'All'], ['review', 'Needs review', c.ink], ['strong', 'Strong indicators', '#D64545'], ['inc', 'Inconclusive', '#8A8A85'], ['closed', 'Closed']];

const COLS = '80px minmax(240px,1fr) 110px 170px 80px 130px 100px 24px';

export default function Cases({ go }) {
  const [f, setF] = useState('all');
  const rows = ALL.filter(TESTS[f]);

  return (
    <div style={page}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Cases · 6 active · 2 closed</div>
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
          {rows.map((r) => (
            <button key={r.id} onClick={() => go('workspace')} {...hover({ bg: c.surface }, { width: '100%', display: 'grid', gridTemplateColumns: COLS, gap: 16, alignItems: 'center', padding: '14px 20px', border: 'none', borderBottom: `1px solid ${c.line}`, background: c.bg, fontFamily: 'inherit', color: c.ink, textAlign: 'left', cursor: 'pointer' })}>
              <span style={{ fontFamily: MONO, fontSize: 12 }}>{r.id}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                <span style={{ fontSize: 14.5, fontWeight: 700 }}>{r.title}</span>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>Why: {r.why}</span>
              </div>
              <TypeIcons types={r.types} />
              <VerdictPill dot={VERDICTS[r.v][1]} label={VERDICTS[r.v][0]} style={{ justifySelf: 'start' }} />
              <span style={{ fontFamily: MONO, fontSize: 13 }}>{r.findings}</span>
              <span style={{ fontSize: 13 }}>{r.who}</span>
              <span style={{ fontSize: 12.5, color: c.ink2 }}>{r.updated}</span>
              <Icon name="chevron_right" size={18} style={{ color: '#8A8A85' }} />
            </button>
          ))}
        </div>
      </div>
      <span style={{ fontSize: 12.5, color: c.ink2 }}>Showing {rows.length} of 8 cases. Verdicts describe indicators found, not whether content is authentic.</span>
    </div>
  );
}
