import { useEffect, useRef, useState } from 'react';
import { c, VERDICTS, YELLOW, MONO, Icon, eyebrow, fmtRange, preventThen, Muted } from '../ui.jsx';
import { useApi, useMediaUrl, fmtT } from '../api/client.js';
import { AuthImg } from '../api/media.jsx';
import { DeepfakeCard, DeepfakePill } from '../Deepfake.jsx';

const fmt = fmtT;
const mono = { fontFamily: MONO };
const sideLabel = { width: 92, flex: 'none', fontSize: 11.5, fontWeight: 600, color: c.ink2 };
const W = 1000, H = 90;

export default function VideoViewer({ go, active, caseId, evidenceId }) {
  const [t, setT] = useState(0);
  const [sel, setSel] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [rate, setRate] = useState(1);
  const [limOpen, setLimOpen] = useState(false);
  const videoRef = useRef(null);

  const caseQ = useApi(active && caseId ? `/cases/${caseId}` : null);
  const fallback = caseQ.data?.evidence.find((e) => e.kind === 'video');
  // the shared evidenceId may point at another kind (an image or audio item); fall back to the case's first video
  const id = (active && caseQ.data?.evidence.find((e) => e.id === evidenceId && e.kind === 'video')?.id) || fallback?.id
    || (active && !caseId ? evidenceId : null);
  const evQ = useApi(active && id ? `/evidence/${id}` : null);
  const ev = evQ.data && evQ.data.kind === 'video' ? evQ.data : null;
  const allF = useApi(ev ? `/cases/${ev.case_id}/findings` : null);
  const siblings = useApi(ev ? `/cases/${ev.case_id}` : null).data?.evidence || [];
  const src = useMediaUrl(ev ? ev.media_url : null).url;
  const duration = ev?.duration || 1;
  const fps = ev?.fps || 25;
  const pct = (x) => `${Math.max(0, Math.min(100, (x / duration) * 100))}%`;

  useEffect(() => { setSel(null); setT(0); }, [id]);
  useEffect(() => { if (!active) videoRef.current?.pause(); }, [active]);
  useEffect(() => { if (videoRef.current) videoRef.current.playbackRate = rate; }, [rate, src]);

  if (!ev) {
    return (
      <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 10, color: c.ink }}>
        <a href="#" onClick={preventThen(() => go('workspace'))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />Case workspace</a>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em' }}>Video evidence</h1>
        <Muted>{evQ.loading || caseQ.loading ? 'Loading…' : evQ.error ? `Could not load the video: ${evQ.error.message}` : 'This case has no video evidence.'}</Muted>
      </div>
    );
  }

  const audioTrack = siblings.find((e) => e.derived_from === ev.label);
  const own = ev.findings.filter((f) => ['frame_range', 'time_range', 'bbox'].includes(f.location.type) || f.modality === 'video');
  const xm = (allF.data || []).filter((f) => f.modality === 'cross-modal' && (f.extra?.video === ev.label || (f.extra?.members || []).includes(ev.label)));
  const SEG = [...own, ...xm];
  const timed = SEG.filter((s) => s.location.start != null && s.location.end != null);
  const marks = timed.filter((s) => s.location.end - s.location.start < duration * 0.8);
  const selected = sel || marks[0]?.finding_id || SEG[0]?.finding_id;
  const v = ev.verdict || { key: 'review', label: 'Not analyzed', why: 'run the analysis to see indicators' };
  const curve = ev.extra?.suspicion_curve || [];
  const ai = ev.extra?.ai_detector;
  const aiFrames = ai?.frames || [];
  const hit = marks.find((s) => t >= s.location.start - 0.15 && t <= s.location.end + 0.35);

  const seekTo = (x) => {
    const val = Math.max(0, Math.min(duration, x));
    setT(val);
    if (videoRef.current) videoRef.current.currentTime = val;
  };
  const pick = (s) => (e) => { e?.stopPropagation(); setSel(s.finding_id); if (s.location.start != null) seekTo(Math.max(0, s.location.start - 0.5)); };
  const seek = (e) => { const rc = e.currentTarget.getBoundingClientRect(); seekTo(((e.clientX - rc.left) / rc.width) * duration); };
  const toggle = () => { const a = videoRef.current; if (!a) return; if (a.paused) a.play(); else a.pause(); };
  const step = (n) => { videoRef.current?.pause(); seekTo(t + n / fps); };

  const tickStep = duration > 60 ? 15 : duration > 20 ? 5 : duration > 8 ? 2 : 1;
  const ticks = Array.from({ length: Math.floor(duration / tickStep) + 1 }, (_, i) => i * tickStep);
  const line = curve.map((y, i) => `${i ? 'L' : 'M'}${((Math.min(i + 0.5, duration) / duration) * W).toFixed(1)},${(H - 4 - Math.min(y, 1) * (H - 10)).toFixed(1)}`).join(' ');

  return (
    <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 22, color: c.ink }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <a href="#" onClick={preventThen(() => go('workspace', { caseId: ev.case_id }))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />{ev.case_id} workspace</a>
        <div style={eyebrow}>Evidence · <span style={mono}>{ev.case_id}</span> · {ev.label} · Video · sha256 <span style={mono}>{ev.sha_short}</span></div>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 700, letterSpacing: '-0.022em' }}>{ev.display_name}</h1>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
          <DeepfakePill d={ev.deepfake} dark />
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 30, padding: '0 13px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 13, fontWeight: 700 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: VERDICTS[v.key][1] }} />{v.label} {v.lo != null && <span style={{ ...mono, fontWeight: 500, color: c.ink2 }}>{fmtRange(v.lo, v.hi)}</span>}
          </span>
          <span style={{ fontSize: 14, color: c.ink2 }}><b style={{ color: c.ink }}>Why:</b> {v.why}{v.why?.endsWith('.') ? '' : '.'}</span>
          {audioTrack && <a href="#" onClick={preventThen(() => go('audio', { evidenceId: audioTrack.id }))} style={{ fontSize: 13.5, fontWeight: 700 }}>Audio track ({audioTrack.label})</a>}
          <a href="#" onClick={preventThen(() => setLimOpen((x) => !x))} style={{ fontSize: 13.5, fontWeight: 700 }}>Limitations</a>
        </div>
        {limOpen && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 760 }}>
            {[...(ev.extra?.metadata_notes || []), ...(ev.warnings || []),
              'Re-encoding and platform compression can hide frame-level edits.',
              'A cut on a static shot, or a cut that matches the motion, may leave no optical-flow jump.',
              'The AI-frames detector scores sampled frames with image classifiers; new video generators can go either way.'].filter(Boolean).map((n) => <Muted key={n}>· {n}</Muted>)}
          </div>
        )}
      </div>

      <DeepfakeCard d={ev.deepfake} subject={ev.label} />

      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
        <div style={{ position: 'relative', background: '#111111', display: 'flex', justifyContent: 'center' }}>
          <video ref={videoRef} src={src || undefined} preload="metadata" playsInline onClick={toggle}
            onTimeUpdate={(e) => setT(e.currentTarget.currentTime)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
            style={{ display: 'block', width: '100%', maxHeight: 520, objectFit: 'contain', cursor: 'pointer', outline: hit ? `4px solid ${YELLOW}` : 'none', outlineOffset: -4 }} />
          {hit && (
            <span style={{ position: 'absolute', left: 14, top: 14, display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 10px', borderRadius: 8, background: YELLOW, color: '#111111', fontSize: 12.5, fontWeight: 700 }}>
              <span style={mono}>{hit.finding_id}</span>{hit.name}
            </span>
          )}
          {!src && <span style={{ position: 'absolute', top: '45%', color: '#ddd', fontSize: 13 }}>Loading video…</span>}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={() => step(-1)} aria-label="Previous frame" title="Previous frame" style={ctl}><Icon name="skip_previous" size={20} /></button>
            <button onClick={toggle} aria-label={playing ? 'Pause' : 'Play'} style={ctl}><Icon name={playing ? 'pause' : 'play_arrow'} size={22} /></button>
            <button onClick={() => step(1)} aria-label="Next frame" title="Next frame" style={ctl}><Icon name="skip_next" size={20} /></button>
            <span style={{ ...mono, fontSize: 12.5 }}>{fmt(t)} / {fmt(duration)} · frame {Math.round(t * fps)}</span>
            <select value={rate} onChange={(e) => setRate(Number(e.target.value))} aria-label="Playback speed" style={{ height: 30, borderRadius: 8, border: `1px solid ${c.border}`, background: c.bg, color: c.ink, fontFamily: 'inherit', fontSize: 12.5 }}>
              {[0.25, 0.5, 1].map((r) => <option key={r} value={r}>{r}×</option>)}
            </select>
            <span style={{ fontSize: 12.5, color: c.ink2 }}>{ev.meta_label}</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {marks.map((s) => {
              const on = selected === s.finding_id;
              return (
                <button key={s.finding_id} onClick={pick(s)} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 32, padding: '0 13px', borderRadius: 999, border: `1px solid ${on ? YELLOW : c.border}`, background: on ? YELLOW : c.bg, fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, color: on ? '#111111' : c.ink, cursor: 'pointer' }}>
                  <span style={{ ...mono, fontWeight: 600 }}>{s.finding_id}</span>{fmt(s.location.start)}
                </button>
              );
            })}
          </div>
        </div>
        <div style={{ padding: '16px 16px 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <span style={{ ...sideLabel, paddingTop: 4 }}>Suspicion<br /><span style={{ fontWeight: 400, fontSize: 10.5 }}>per second</span></span>
            <div onClick={seek} style={{ position: 'relative', flex: 1, height: H, borderRadius: 10, background: c.surface, cursor: 'crosshair', overflow: 'hidden' }}>
              {marks.map((s) => (
                <button key={s.finding_id} title={`${s.finding_id} · ${s.name}`} onClick={pick(s)} style={{ position: 'absolute', top: 0, bottom: 0, left: pct(s.location.start), width: pct(s.location.end - s.location.start), minWidth: 8, border: 'none', borderLeft: '1.5px solid #E0B400', borderRight: '1.5px solid #E0B400', background: s.modality === 'video' ? 'rgba(255,210,63,.5)' : 'rgba(255,210,63,.22)', padding: 0, cursor: 'pointer', zIndex: 1 }} />
              ))}
              <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 2, color: c.ink }}>
                {line && <path d={`${line} L${W},${H} L0,${H} Z`} fill="currentColor" fillOpacity={0.08} />}
                {line && <path d={line} fill="none" stroke="currentColor" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />}
              </svg>
              {!curve.length && <Muted style={{ position: 'absolute', left: 12, top: 10, fontSize: 12 }}>{ev.status === 'analyzed' ? 'No suspicion curve was recorded.' : 'The curve appears after the analysis has run.'}</Muted>}
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: pct(t), width: 2, marginLeft: -1, background: c.ink, zIndex: 3, pointerEvents: 'none' }} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <span style={{ ...sideLabel, paddingTop: 4 }}>AI-frames<br /><span style={{ fontWeight: 400, fontSize: 10.5 }}>detector score</span></span>
            <div onClick={seek} style={{ position: 'relative', flex: 1, height: 56, borderRadius: 10, background: c.surface, cursor: 'crosshair' }}>
              <div style={{ position: 'absolute', left: 0, right: 0, top: '50%', borderTop: `1px dashed ${c.border}` }} />
              {aiFrames.map((f) => (
                <span key={f.t} title={`${fmt(f.t)} · AI-likeness ${Math.round(f.p * 100)}%`} style={{ position: 'absolute', left: pct(f.t), bottom: 4, width: 10, marginLeft: -5, height: `${Math.max(f.p, 0.04) * 48}px`, borderRadius: 3, background: f.p >= 0.5 ? '#D64545' : '#3E9B5F', opacity: 0.85 }} />
              ))}
              {!aiFrames.length && <Muted style={{ position: 'absolute', left: 12, top: 18, fontSize: 12 }}>{ev.status === 'analyzed' ? 'The AI-frames detector did not run on this video.' : 'Appears after the analysis has run.'}</Muted>}
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: pct(t), width: 2, marginLeft: -1, background: c.ink, pointerEvents: 'none' }} />
            </div>
          </div>
          <div style={{ position: 'relative', height: 16, marginLeft: 104 }}>
            {ticks.map((s) => <span key={s} style={{ position: 'absolute', left: pct(s), transform: 'translateX(-50%)', ...mono, fontSize: 10, color: '#8A8A85' }}>{fmt(s).slice(0, 5)}</span>)}
          </div>
        </div>
      </section>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <span style={eyebrow}>Findings in this video</span>
        {!SEG.length && <Muted>{ev.status === 'analyzed' ? 'No indicator crossed its threshold in this video.' : 'Not analyzed yet.'}</Muted>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
          {SEG.map((s) => {
            const on = selected === s.finding_id;
            return (
              <button key={s.finding_id} onClick={pick(s)} style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 8, padding: '14px 16px', borderRadius: 14, border: `1px solid ${on ? c.ink : c.border}`, boxShadow: on ? '0 0 0 3px rgba(255,210,63,.55)' : 'none', background: c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer', minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                  <span style={{ ...mono, fontSize: 11.5, fontWeight: 600 }}>{s.finding_id} · {s.mod_label}</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 20, padding: '0 8px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 11, fontWeight: 600 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: VERDICTS[s.verdict.key][1] }} />{s.verdict.label}
                  </span>
                </div>
                {s.location.type !== 'file' && s.location.start != null && (
                  <AuthImg path={`/cases/${ev.case_id}/findings/${s.finding_id}/thumb`} alt="" style={{ width: '100%', aspectRatio: '16 / 9', objectFit: 'cover', borderRadius: 10, background: c.surface }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                )}
                <span style={{ fontSize: 14.5, fontWeight: 700 }}>{s.name}</span>
                <span style={{ ...mono, fontSize: 12 }}>{s.loc_label}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                  <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: c.line }}>
                    <div style={{ position: 'absolute', top: 0, bottom: 0, left: s.conf_low * 100 + '%', width: (s.conf_high - s.conf_low) * 100 + '%', borderRadius: 999, background: s.verdict.key === 'inc' ? '#8A8A85' : c.ink }} />
                  </div>
                  <span style={{ ...mono, fontSize: 11.5 }}>{fmtRange(s.conf_low, s.conf_high)}</span>
                </div>
                <span style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.45 }}>{s.explanation}{s.alternatives[0] ? ` Alternative: ${s.alternatives[0].toLowerCase()}.` : ''}</span>
                <span style={{ fontSize: 11.5, color: c.ink2 }}>{s.method}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const ctl = { width: 36, height: 36, borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' };
