import { useEffect, useRef, useState } from 'react';
import { c, VERDICTS, YELLOW, MONO, Icon, eyebrow, fmtRange, preventThen, Muted } from '../ui.jsx';
import { useApi, fmtT } from '../api/client.js';

const fmt = fmtT;
const mono = { fontFamily: MONO };
const sideLabel = { width: 84, flex: 'none', fontSize: 11.5, fontWeight: 600, color: c.ink2 };

export default function AudioViewer({ go, active, caseId, evidenceId }) {
  const [t, setT] = useState(0);
  const [seg, setSeg] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [limOpen, setLimOpen] = useState(false);
  const specRef = useRef(null);
  const trRef = useRef(null);
  const audioRef = useRef(null);

  const caseQ = useApi(active && caseId ? `/cases/${caseId}` : null);
  const fallback = caseQ.data?.evidence.find((e) => e.kind === 'audio');
  const id = evidenceId && active ? evidenceId : fallback?.id;
  const evQ = useApi(active && id ? `/evidence/${id}` : null);
  const ev = evQ.data && evQ.data.kind === 'audio' ? evQ.data : null;
  const wfQ = useApi(ev ? `/evidence/${ev.id}/waveform` : null);
  const allF = useApi(ev ? `/cases/${ev.case_id}/findings` : null);
  const wf = wfQ.data;
  const duration = wf?.duration || ev?.duration || 1;
  const pct = (x) => `${Math.max(0, Math.min(100, (x / duration) * 100))}%`;

  useEffect(() => { setSeg(null); setT(0); }, [id]);
  useEffect(() => { if (!active) audioRef.current?.pause(); }, [active]);

  // the spectrogram is rendered server-side; draw it into the existing canvas
  useEffect(() => {
    const cv = specRef.current;
    if (!cv || !wf?.spectrogram_url) return;
    const img = new Image();
    img.onload = () => { const ctx = cv.getContext('2d'); ctx.clearRect(0, 0, cv.width, cv.height); ctx.drawImage(img, 0, 0, cv.width, cv.height); };
    img.src = wf.spectrogram_url;
  }, [wf?.spectrogram_url, active]);

  const scrollTo = (key, smooth = true) => {
    const box = trRef.current;
    const el = box?.querySelector(`[data-seg="${key}"]`);
    if (el) box.scrollTo({ top: el.offsetTop - 8, behavior: smooth ? 'smooth' : 'auto' });
  };

  if (!ev) {
    return (
      <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 10, color: c.ink }}>
        <a href="#" onClick={preventThen(() => go('workspace'))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />Case workspace</a>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.035em' }}>Audio evidence</h1>
        <Muted>{evQ.loading || caseQ.loading ? 'Loading…' : evQ.error ? `Could not load the audio: ${evQ.error.message}` : 'This case has no audio evidence.'}</Muted>
      </div>
    );
  }

  const own = ev.findings.filter((f) => f.location.type === 'time_range');
  const xm = (allF.data || []).filter((f) => f.modality === 'cross-modal' && f.extra?.audio === ev.label);
  const SEG = [...own, ...xm];
  const shaded = SEG.filter((s) => s.location.end - s.location.start < duration * 0.8);
  const selected = seg || shaded[0]?.finding_id || SEG[0]?.finding_id;
  const v = ev.verdict || { key: 'review', label: 'Not analyzed', why: 'run the analysis to see indicators' };
  const segments = wf?.transcript?.segments || [];
  const bars = (wf?.peaks || []).map((h, i) => {
    const tt = ((i + 0.5) / (wf.peaks.length || 1)) * duration;
    return { h: Math.round(Math.max(h, 0.02) * 92) + '%', flagged: shaded.some((s) => tt >= s.location.start - 0.3 && tt <= s.location.end + 0.3) };
  });
  const step = duration > 60 ? 15 : duration > 20 ? 5 : duration > 8 ? 2 : 1;
  const ticks = Array.from({ length: Math.floor(duration / step) + 1 }, (_, i) => i * step);
  const lineFor = (x) => segments.findIndex((sg) => x >= sg.start - 0.3 && x <= sg.end + 0.3);
  const seekTo = (x) => {
    const val = Math.max(0, Math.min(duration, x));
    setT(val);
    if (audioRef.current) audioRef.current.currentTime = val;
    const li = lineFor(val);
    if (li >= 0) scrollTo(`s${li}`);
  };
  const pick = (s) => (e) => { e.stopPropagation(); setSeg(s.finding_id); seekTo(s.location.start); };
  const seek = (e) => { const rc = e.currentTarget.getBoundingClientRect(); seekTo(((e.clientX - rc.left) / rc.width) * duration); };
  const toggle = () => { const a = audioRef.current; if (!a) return; if (a.paused) a.play(); else a.pause(); };

  return (
    <div style={{ padding: '32px 40px 56px', display: 'flex', flexDirection: 'column', gap: 22, color: c.ink }}>
      <audio ref={audioRef} src={ev.media_url} preload="metadata" onTimeUpdate={(e) => setT(e.currentTarget.currentTime)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <a href="#" onClick={preventThen(() => go('workspace', { caseId: ev.case_id }))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />{ev.case_id} workspace</a>
        <div style={eyebrow}>Evidence · <span style={mono}>{ev.case_id}</span> · {ev.label} · Audio{ev.derived_from ? ` track of ${ev.derived_from}` : ''} · sha256 <span style={mono}>{ev.sha_short}</span></div>
        <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.035em' }}>{ev.display_name}</h1>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 30, padding: '0 13px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 13, fontWeight: 700 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: VERDICTS[v.key][1] }} />{v.label} {v.lo != null && <span style={{ ...mono, fontWeight: 500, color: c.ink2 }}>{fmtRange(v.lo, v.hi)}</span>}
          </span>
          <span style={{ fontSize: 14, color: c.ink2 }}><b style={{ color: c.ink }}>Why:</b> {v.why}.</span>
          <a href="#" onClick={preventThen(() => setLimOpen((x) => !x))} style={{ fontSize: 13.5, fontWeight: 700 }}>Limitations</a>
        </div>
        {limOpen && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 760 }}>
            {[...(ev.extra?.metadata_notes || []), ev.extra?.bandlimit?.skipped ? `Band-limit check skipped: ${ev.extra.bandlimit.skipped}.` : null,
              'A splice between two recordings of the same room may leave no noise-floor step.', 'Cloned voices recorded at full bandwidth may pass the band-limit check.'].filter(Boolean).map((n) => <Muted key={n}>· {n}</Muted>)}
          </div>
        )}
      </div>

      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={toggle} aria-label={playing ? 'Pause' : 'Play'} style={{ width: 36, height: 36, borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer' }}><Icon name={playing ? 'pause' : 'play_arrow'} size={22} /></button>
            <span style={{ ...mono, fontSize: 12.5 }}>{fmt(t)} / {fmt(duration)}</span>
            <span style={{ fontSize: 12.5, color: c.ink2 }}>{ev.meta_label.split(' · ').slice(2).join(' · ') || 'mono'}{wf ? ` · analysed at ${wf.sr / 1000} kHz` : ''}</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {shaded.map((s) => {
              const on = selected === s.finding_id;
              return (
                <button key={s.finding_id} onClick={pick(s)} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 32, padding: '0 13px', borderRadius: 999, border: `1px solid ${on ? YELLOW : c.border}`, background: on ? YELLOW : c.bg, fontFamily: 'inherit', fontSize: 12.5, fontWeight: 700, color: on ? '#111111' : c.ink, cursor: 'pointer' }}>
                  <span style={{ ...mono, fontWeight: 600 }}>{s.finding_id}</span>{fmt(s.location.start)}–{fmt(s.location.end)}
                </button>
              );
            })}
          </div>
        </div>
        <div style={{ padding: '16px 16px 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <span style={{ ...sideLabel, paddingTop: 6 }}>Waveform</span>
            <div onClick={seek} style={{ position: 'relative', flex: 1, height: 120, borderRadius: 10, background: c.surface, cursor: 'crosshair' }}>
              {shaded.map((s) => (
                <button key={s.finding_id} title={s.finding_id} onClick={pick(s)} style={{ position: 'absolute', top: 0, bottom: 0, left: pct(s.location.start), width: pct(s.location.end - s.location.start), minWidth: 8, border: 'none', borderLeft: '1.5px solid #E0B400', borderRight: '1.5px solid #E0B400', background: s.modality === 'audio' ? 'rgba(255,210,63,.55)' : 'rgba(255,210,63,.22)', padding: 0, cursor: 'pointer', zIndex: 1 }} />
              ))}
              <div style={{ position: 'absolute', inset: '0 6px', display: 'flex', alignItems: 'center', gap: 1, pointerEvents: 'none', zIndex: 2 }}>
                {bars.map((b, i) => <span key={i} style={{ flex: 1, height: b.h, background: b.flagged ? c.ink : c.ink2, borderRadius: 1 }} />)}
                {!bars.length && <Muted style={{ fontSize: 12 }}>{wfQ.error ? 'Waveform appears after the analysis has run.' : 'Loading…'}</Muted>}
              </div>
              <div style={{ position: 'absolute', top: -4, bottom: -4, left: pct(t), width: 2, marginLeft: -1, background: c.ink, zIndex: 3, pointerEvents: 'none' }} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ ...sideLabel, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '4px 0' }}><span>Spectrogram</span><span style={{ ...mono, fontWeight: 400, fontSize: 10 }}>8 kHz<br />0 Hz</span></div>
            <div onClick={seek} style={{ position: 'relative', flex: 1, height: 150, borderRadius: 10, overflow: 'hidden', background: c.surface, cursor: 'crosshair' }}>
              <canvas ref={specRef} width={1000} height={150} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
              {shaded.map((s) => (
                <div key={s.finding_id} style={{ position: 'absolute', top: 0, bottom: 0, left: pct(s.location.start), width: pct(s.location.end - s.location.start), minWidth: 8, borderLeft: '1.5px solid #E0B400', borderRight: '1.5px solid #E0B400', background: s.modality === 'audio' ? 'rgba(255,210,63,.4)' : 'rgba(255,210,63,.16)', pointerEvents: 'none' }} />
              ))}
              {shaded.filter((s) => s.indicator === 'noise_floor_step').map((s) => (
                <span key={s.finding_id + 'db'} style={{ position: 'absolute', left: pct(s.location.start), marginLeft: 6, top: 8, ...mono, fontSize: 10.5, background: YELLOW, color: '#111111', padding: '2px 7px', borderRadius: 5, pointerEvents: 'none' }}>{s.extra.step_db > 0 ? '+' : ''}{s.extra.step_db} dB</span>
              ))}
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: pct(t), width: 2, marginLeft: -1, background: c.ink, pointerEvents: 'none' }} />
            </div>
          </div>
          <div style={{ position: 'relative', height: 16, marginLeft: 96 }}>
            {ticks.map((s) => <span key={s} style={{ position: 'absolute', left: pct(s), transform: 'translateX(-50%)', ...mono, fontSize: 10, color: '#8A8A85' }}>{fmt(s).slice(0, 5)}</span>)}
          </div>
        </div>
      </section>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-start' }}>
        <section style={{ flex: '2 1 560px', minWidth: 0, border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${c.border}`, background: c.surface }}>
            <span style={{ fontSize: 14, fontWeight: 800 }}>Transcript · word timestamps</span>
            <span style={{ ...mono, fontSize: 11.5, color: c.ink2 }}>{wf?.transcript ? `${wf.transcript.model} · ${wf.transcript.n_words} words · conf ${wf.transcript.mean_conf.toFixed(2)}` : 'no transcript'}</span>
          </div>
          <div ref={trRef} style={{ position: 'relative', height: 300, overflow: 'auto', padding: '8px 16px 16px', scrollBehavior: 'smooth' }}>
            {!segments.length && <div style={{ padding: 12 }}><Muted>{wf ? 'No speech was transcribed (or the transcript analyzer is turned off).' : 'The transcript appears after the analysis has run.'}</Muted></div>}
            {segments.map((sg, li) => {
              const hits = SEG.filter((s) => s.location.start <= sg.end && s.location.end >= sg.start && s.location.end - s.location.start < duration * 0.8);
              const flagged = hits.length > 0;
              const activeLine = t >= sg.start && t <= sg.end;
              return (
                <div key={li} data-seg={`s${li}`} style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: 14, padding: 12, marginTop: 6, borderRadius: 12, background: flagged ? c.hl : c.bg, border: `1px solid ${activeLine ? c.ink : flagged ? c.hlb : c.line}` }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <span style={{ ...mono, fontSize: 12, fontWeight: 600 }}>{fmt(sg.start)}–{fmt(sg.end).slice(3)}</span>
                    {flagged && <span style={{ ...mono, fontSize: 10.5, color: c.ink2 }}>{hits.map((h) => h.finding_id).join(' · ')}</span>}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 4px' }}>
                    {(sg.words.length ? sg.words : [{ w: sg.text, start: sg.start, end: sg.end }]).map((w, i) => {
                      const cur = t >= w.start && t < w.end;
                      return (
                        <button key={i} onClick={() => seekTo(w.start)} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 1, border: 'none', padding: '2px 4px', borderRadius: 6, background: cur ? YELLOW : 'transparent', fontFamily: 'inherit', cursor: 'pointer', color: cur ? '#111111' : c.ink }}>
                          <span style={{ ...mono, fontSize: 9.5, color: '#8A8A85' }}>{w.start.toFixed(1)}</span>
                          <span style={{ fontSize: 15, fontWeight: 500 }}>{w.w}</span>
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
          {!SEG.length && <Muted>{ev.status === 'analyzed' ? 'No indicator crossed its threshold on this track.' : 'Not analyzed yet.'}</Muted>}
          {SEG.map((s) => {
            const on = selected === s.finding_id;
            return (
              <button key={s.finding_id} onClick={pick(s)} style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 8, padding: '14px 16px', borderRadius: 14, border: `1px solid ${on ? c.ink : c.border}`, boxShadow: on ? '0 0 0 3px rgba(255,210,63,.55)' : 'none', background: c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                  <span style={{ ...mono, fontSize: 11.5, fontWeight: 600 }}>{s.finding_id}</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 20, padding: '0 8px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 11, fontWeight: 600 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: VERDICTS[s.verdict.key][1] }} />{s.verdict.label}
                  </span>
                </div>
                <span style={{ fontSize: 14.5, fontWeight: 700 }}>{s.name}</span>
                <span style={{ ...mono, fontSize: 12 }}>{s.loc_label}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                  <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: c.line }}>
                    <div style={{ position: 'absolute', top: 0, bottom: 0, left: s.conf_low * 100 + '%', width: (s.conf_high - s.conf_low) * 100 + '%', borderRadius: 999, background: s.verdict.key === 'inc' ? '#8A8A85' : c.ink }} />
                  </div>
                  <span style={{ ...mono, fontSize: 11.5 }}>{fmtRange(s.conf_low, s.conf_high)}</span>
                </div>
                <span style={{ fontSize: 12.5, color: c.ink2, lineHeight: 1.45 }}>{s.explanation}{s.alternatives[0] ? ` Alternative: ${s.alternatives[0].toLowerCase()}.` : ''}</span>
              </button>
            );
          })}
        </aside>
      </div>
    </div>
  );
}
