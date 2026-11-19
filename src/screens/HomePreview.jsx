// Home page sample case: plays a short press-briefing clip and replays TruthLens's real analysis of it in time.
// The clip and its analysis come from samples/make_home_demo.py (public/media/home-demo.{mp4,json}).
import { useEffect, useRef, useState } from 'react';
import { c, VERDICTS, YELLOW, MONO, Icon, fmtRange } from '../ui.jsx';
import { DeepfakePill } from '../Deepfake.jsx';

const pad = (n) => String(n).padStart(2, '0');
const clock = (t) => `${pad(Math.floor(t / 60))}:${(t % 60).toFixed(1).padStart(4, '0')}`;

function useDemo() {
  const [data, setData] = useState(null);
  useEffect(() => {
    let alive = true;
    fetch('/media/home-demo.json').then((r) => (r.ok ? r.json() : null)).then((d) => { if (alive) setData(d); }, () => {});
    return () => { alive = false; };
  }, []);
  return data;
}

/** Video time, sampled every animation frame (timeupdate fires only ~4× a second). */
function useVideoClock(ref) {
  const [t, setT] = useState(0);
  useEffect(() => {
    let raf;
    const tick = () => { if (ref.current) setT(ref.current.currentTime); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [ref]);
  return t;
}

function Card({ on, icon, eyebrow, children }) {
  return (
    <div style={{ background: c.bg, border: `1px solid ${on ? c.ink : c.border}`, boxShadow: on ? '0 0 0 3px rgba(255,210,63,.45)' : 'none', borderRadius: 14, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8, transition: 'border-color .3s, box-shadow .3s' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: c.ink2 }}>
        <Icon name={icon} size={16} />{eyebrow}
      </div>
      {children}
    </div>
  );
}

function Pending({ label, meter, detail }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, fontWeight: 600 }}>
        <span style={{ width: 12, height: 12, borderRadius: '50%', border: `2px solid ${c.border}`, borderTopColor: c.ink, animation: 'tlspin .9s linear infinite' }} />{label}
      </span>
      <div style={{ height: 6, borderRadius: 999, background: c.line, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${Math.round(Math.min(1, meter) * 100)}%`, background: c.ink2, borderRadius: 999, transition: 'width .15s linear' }} />
      </div>
      <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>{detail}</span>
    </div>
  );
}

function Found({ f }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 600 }}>{f.id}</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 20, padding: '0 8px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 11, fontWeight: 600 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: VERDICTS[f.key][1] }} />{f.label}
        </span>
      </div>
      <span style={{ fontSize: 14, fontWeight: 700 }}>{f.name}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: c.line }}>
          <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${f.lo * 100}%`, width: `${(f.hi - f.lo) * 100}%`, borderRadius: 999, background: c.ink }} />
        </div>
        <span style={{ fontFamily: MONO, fontSize: 11 }}>{fmtRange(f.lo, f.hi)}</span>
      </div>
      <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>{f.loc}</span>
    </div>
  );
}

export default function HomePreview() {
  const data = useDemo();
  const video = useRef(null);
  const t = useVideoClock(video);
  const [muted, setMuted] = useState(true);
  const [playing, setPlaying] = useState(false);

  // Browsers only autoplay muted video; sound is one click away. Respect reduced-motion settings.
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    v.muted = true;
    if (!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) v.play().catch(() => {});
  }, [data]);

  const vid = data?.findings.find((f) => f.modality === 'video' && f.key !== 'none' && f.key !== 'inc');
  const aud = data?.findings.find((f) => f.modality === 'audio' && f.key !== 'none' && f.key !== 'inc');
  const rule = data?.rules.find((r) => r.id === 'R-03') || data?.rules[0];
  const seenV = vid && t >= vid.start, seenA = aud && t >= aud.start;
  const flash = vid && t >= vid.start - 0.15 && t <= vid.start + 1.4;
  const dur = data?.duration || 16;
  const pct = (x) => `${(x / dur) * 100}%`;
  const peaks = (data?.waveform || []).filter((_, i) => i % 2 === 0);
  const peakAt = (x) => { const w = data?.waveform || []; return w.length ? w[Math.min(w.length - 1, Math.floor((x / dur) * w.length))] : 0; };
  const motion = data?.curve?.length ? data.curve[Math.min(data.curve.length - 1, Math.floor(t))] : 0;
  const words = (data?.words || []).filter((w) => w.start <= t + 1.6 && w.end >= t - 2.2);

  const toggleSound = () => { const v = video.current; if (!v) return; v.muted = !v.muted; setMuted(v.muted); if (v.paused) v.play().catch(() => {}); };
  const togglePlay = () => { const v = video.current; if (!v) return; if (v.paused) v.play().catch(() => {}); else v.pause(); };
  const btn = { width: 32, height: 32, borderRadius: '50%', border: 'none', background: 'rgba(17,17,17,.6)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' };

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
      <div style={{ flex: '3 1 420px', minWidth: 0, background: c.bg, border: `1px solid ${c.border}`, borderRadius: 14, padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ position: 'relative', aspectRatio: '16/9', borderRadius: 10, overflow: 'hidden', background: '#1A1A1A' }}>
          <video ref={video} src="/media/home-demo.mp4" loop playsInline muted preload="auto" aria-label="Sample press briefing clip being analysed"
            onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
          <div style={{ position: 'absolute', inset: 0, border: `3px solid ${YELLOW}`, borderRadius: 10, opacity: flash ? 1 : 0, transition: 'opacity .2s', pointerEvents: 'none' }} />
          {flash && (
            <span style={{ position: 'absolute', left: 12, top: 44, background: YELLOW, color: '#111111', fontFamily: MONO, fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 5 }}>
              {vid.id} · motion break · {clock(vid.start)}
            </span>
          )}
          <span style={{ position: 'absolute', left: 12, top: 12, fontFamily: MONO, fontSize: 10.5, color: '#fff', background: 'rgba(17,17,17,.6)', padding: '3px 8px', borderRadius: 5 }}>
            frame {Math.round(t * (data?.fps || 25))} · {clock(t)}
          </span>
          <div style={{ position: 'absolute', right: 10, top: 10, display: 'flex', gap: 6 }}>
            <button onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'} style={btn}><Icon name={playing ? 'pause' : 'play_arrow'} size={19} /></button>
            <button onClick={toggleSound} aria-label={muted ? 'Turn sound on' : 'Mute'} style={btn}><Icon name={muted ? 'volume_off' : 'volume_up'} size={18} /></button>
          </div>
          <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '28px 14px 10px', background: 'linear-gradient(transparent, rgba(0,0,0,.65))', display: 'flex', flexWrap: 'wrap', gap: '2px 5px', minHeight: 54 }}>
            {words.map((w, i) => {
              const now = t >= w.start && t < w.end + 0.05;
              return <span key={`${w.start}-${i}`} style={{ fontSize: 14, fontWeight: 600, color: now ? '#111111' : 'rgba(255,255,255,.9)', background: now ? YELLOW : 'transparent', borderRadius: 4, padding: '0 3px' }}>{w.w}</span>;
            })}
          </div>
        </div>
        <div style={{ position: 'relative', height: 40, borderRadius: 8, background: c.surface, overflow: 'hidden' }}>
          {aud && seenA && (
            <div style={{ position: 'absolute', left: pct(aud.start), right: 0, top: 0, bottom: 0, background: 'rgba(255,210,63,.28)', borderLeft: `1.5px solid ${YELLOW}` }} />
          )}
          <div style={{ position: 'absolute', inset: '0 4px', display: 'flex', alignItems: 'center', gap: 2 }}>
            {peaks.map((h, i) => {
              const x = ((i + 0.5) / peaks.length) * dur;
              return <span key={i} style={{ flex: 1, height: `${Math.max(h, 0.04) * 90}%`, background: c.ink, borderRadius: 1, opacity: x <= t ? 0.85 : 0.25 }} />;
            })}
          </div>
          <div style={{ position: 'absolute', top: 0, bottom: 0, left: pct(t), width: 2, marginLeft: -1, background: c.ink }} />
        </div>
      </div>

      <div style={{ flex: '2 1 280px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Card on={seenV} icon="movie" eyebrow="Video · optical flow">
          {seenV ? <Found f={vid} /> : <Pending label="Watching frames" meter={motion} detail={`frame ${Math.round(t * (data?.fps || 25))} · motion ${(motion * 100).toFixed(0)}%`} />}
        </Card>
        <Card on={seenA} icon="graphic_eq" eyebrow="Audio · noise floor">
          {seenA ? <Found f={aud} /> : <Pending label="Listening to background noise" meter={peakAt(t)} detail={`level ${(20 * Math.log10(Math.max(peakAt(t), 0.001))).toFixed(0)} dB re. peak`} />}
        </Card>
        <Card on={seenV && seenA} icon="join_inner" eyebrow="Cross-modal">
          {seenV && seenA && rule ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              <span style={{ fontSize: 14, fontWeight: 700 }}><span style={{ fontFamily: MONO, fontSize: 11 }}>{rule.id}</span> · {rule.name}</span>
              <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2 }}>{rule.links}</span>
              <span style={{ display: 'inline-flex', alignSelf: 'flex-start', alignItems: 'center', gap: 7, height: 26, padding: '0 11px', borderRadius: 999, background: c.hero, color: '#fff', fontSize: 12.5, fontWeight: 700 }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: VERDICTS[data.verdict.key][1] }} />{data.verdict.label}
                <span style={{ fontFamily: MONO, fontWeight: 500, color: YELLOW }}>{fmtRange(data.verdict.lo, data.verdict.hi)}</span>
              </span>
              {data.deepfake?.p != null && <DeepfakePill d={data.deepfake} h={26} fs={12.5} style={{ alignSelf: 'flex-start' }} />}
            </div>
          ) : <Pending label={seenV || seenA ? 'Waiting for an independent second signal' : 'Cross-checking video and audio'} meter={(seenV ? 0.5 : 0) + (seenA ? 0.5 : 0)} detail="a finding counts as corroborated only when two methods agree" />}
        </Card>
        <span style={{ fontSize: 11.5, color: c.ink2, lineHeight: 1.45 }}>
          Demo clip made for this page: we cut it at {clock(data?.ground_truth?.video_cut_s ?? 8)} and joined speech from a noisier room at{' '}
          {clock(data?.ground_truth?.audio_splice_s ?? 8.2)}. The footage is genuine stock video; the narration is computer-generated
          speech, which the voice detector recognises. The cards replay TruthLens's actual analysis of it.
        </span>
      </div>
    </div>
  );
}
