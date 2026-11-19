// Shared tokens and primitives used across TruthLens screens.

export const YELLOW = '#FFD23F';
export const YELLOW_HOVER = '#F5C400';
export const MUTED = '#8A8A85';

export const c = {
  bg: 'var(--tl-bg,#fff)',
  surface: 'var(--tl-surface,#F7F7F5)',
  surface2: 'var(--tl-surface2,#F2F2EE)',
  border: 'var(--tl-border,#E8E8E4)',
  border2: 'var(--tl-border2,#CFCFC9)',
  line: 'var(--tl-line,#EFEFEB)',
  ink: 'var(--tl-ink,#111)',
  ink2: 'var(--tl-ink2,#5F5F5A)',
  hero: 'var(--tl-hero,#111)',
  hl: 'var(--tl-hl,#FFFBEA)',
  hlb: 'var(--tl-hlb,#F3E4A6)',
  hover: 'var(--tl-hover,#EEEEEA)',
};

export const VERDICTS = {
  strong: ['Strong indicators', '#D64545'],
  ind: ['Indicators', '#E8A33D'],
  inc: ['Inconclusive', MUTED],
  none: ['No indicators', '#3E9B5F'],
  review: ['Needs review', c.ink],
};

export const THEMES = {
  light: { '--tl-bg': '#FFFFFF', '--tl-surface': '#F7F7F5', '--tl-surface2': '#F2F2EE', '--tl-border': '#E8E8E4', '--tl-border2': '#CFCFC9', '--tl-line': '#EFEFEB', '--tl-ink': '#111111', '--tl-ink2': '#5F5F5A', '--tl-hero': '#111111', '--tl-hl': '#FFFBEA', '--tl-hlb': '#F3E4A6', '--tl-hover': '#EEEEEA' },
  dark: { '--tl-bg': '#0F0F0E', '--tl-surface': '#1A1A18', '--tl-surface2': '#21211F', '--tl-border': '#2E2E2B', '--tl-border2': '#3D3D39', '--tl-line': '#262624', '--tl-ink': '#F2F2EE', '--tl-ink2': '#A3A39C', '--tl-hero': '#1C1C1A', '--tl-hl': '#2A2512', '--tl-hlb': '#4D4219', '--tl-hover': '#242422' },
};

export const MONO = "'JetBrains Mono',monospace";

/** Material Symbols glyph. */
export function Icon({ name, size = 20, style, ...rest }) {
  return <span className="ms" style={{ fontSize: size, ...style }} {...rest}>{name}</span>;
}

/** Hover props: spread onto an element to swap background (and/or border color) on hover. */
export function hover({ bg, bc } = {}, style = {}) {
  const cls = [bg && 'hv-bg', bc && 'hv-bc'].filter(Boolean).join(' ');
  return { className: cls, style: { ...style, ...(bg ? { '--hv-bg': bg } : {}), ...(bc ? { '--hv-bc': bc } : {}) } };
}

export const fmtRange = (lo, hi) => lo.toFixed(2) + '–' + hi.toFixed(2);

/** Small rounded pill with a coloured dot, used for verdicts everywhere. */
export function VerdictPill({ dot, label, h = 24, fs = 12, pad = 10, dotSize = 7, style }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: h, padding: `0 ${pad}px`, borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: fs, fontWeight: 600, whiteSpace: 'nowrap', ...style }}>
      <span style={{ width: dotSize, height: dotSize, borderRadius: '50%', background: dot }} />{label}
    </span>
  );
}

/** Horizontal confidence-range bar. */
export function RangeBar({ lo, hi, color, h = 6, midline = false, track = c.line }) {
  return (
    <div style={{ position: 'relative', flex: 1, height: h, borderRadius: 999, background: track }}>
      {midline && <div style={{ position: 'absolute', left: '50%', top: -2, bottom: -2, width: 1, background: 'var(--tl-border2,#D5D5CF)' }} />}
      <div style={{ position: 'absolute', top: 0, bottom: 0, left: lo * 100 + '%', width: (hi - lo) * 100 + '%', borderRadius: 999, background: color }} />
    </div>
  );
}

export const eyebrow = { fontSize: 11, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: c.ink2 };
export const h1 = { margin: 0, fontSize: 36, lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.035em' };
export const page = { padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 24, color: c.ink };

/** Filter chip that inverts when active. */
export function chipStyle(on) {
  return { display: 'inline-flex', alignItems: 'center', gap: 8, height: 34, padding: '0 14px', borderRadius: 999, border: `1px solid ${on ? c.ink : c.border}`, background: on ? c.ink : c.bg, color: on ? c.bg : c.ink, fontFamily: 'inherit', fontSize: 13, fontWeight: 700, cursor: 'pointer' };
}

export const btnPrimary = { display: 'inline-flex', alignItems: 'center', gap: 8, height: 42, padding: '0 20px', borderRadius: 999, border: 'none', background: YELLOW, fontFamily: 'inherit', fontSize: 14, fontWeight: 700, color: '#111111', cursor: 'pointer' };
export const btnSecondary = { display: 'inline-flex', alignItems: 'center', gap: 8, height: 40, padding: '0 16px', borderRadius: 999, background: c.bg, border: `1px solid ${c.border}`, fontFamily: 'inherit', fontSize: 14, fontWeight: 700, color: c.ink, cursor: 'pointer' };

export function PrimaryButton({ style, children, ...rest }) {
  return <button {...rest} {...hover({ bg: YELLOW_HOVER }, { ...btnPrimary, ...style })}>{children}</button>;
}
export function SecondaryButton({ style, children, ...rest }) {
  return <button {...rest} {...hover({ bg: c.surface }, { ...btnSecondary, ...style })}>{children}</button>;
}

/** The yellow lens mark. */
export function Logo({ size = 38 }) {
  const inner = Math.round(size * 0.53);
  return (
    <div style={{ width: size, height: size, flex: 'none', borderRadius: size * 0.26, background: YELLOW, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: inner, height: inner, borderRadius: '50%', border: `${size >= 34 ? 3.5 : 3}px solid #111111`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {size >= 34 && <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#111111' }} />}
      </div>
    </div>
  );
}

export const preventThen = (fn) => (e) => { e.preventDefault(); fn(); };
