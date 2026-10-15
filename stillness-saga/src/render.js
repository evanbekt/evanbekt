// THE STILLNESS, PARTS 4-6 — renderer (`?part=4|5|6`). Every frame is a pure function of time.
// Shares its sets and helpers with Part 2 (voicemail/) and Part 3 (seven-minutes/).
// WebGL2: light, dust, glows, peephole lens, motion-blur accumulation. Canvas 2D: type, UI, set.

import { make } from './timelines.js';
import { createGL } from './gl.js';

const Q = new URLSearchParams(location.search);
const PART = +(Q.get('part') || 4);
const TL = make(PART);
const { LINES, WAVE_RATE, WAVE_B64 } = await import(`./voice_data${PART}.js`);
const W = +(Q.get('w') || 1920), H = +(Q.get('h') || 1080);
const SUB = +(Q.get('sub') || 8);
const SHUTTER = 0.5;
const PORTRAIT = H > W;
const CX = W / 2, CY = H / 2;

// ---------------------------------------------------------------- palette
const HALL = [0.80, 0.93, 0.78];      // hallway fluorescent: sick, pale green-white
const COLD = [0.70, 0.80, 1.0];       // phone light
const RED = [1.0, 0.16, 0.12];        // recording
const INK = '#e2e7ee';
const UI = '"Inter", sans-serif';
const SERIF = '"Instrument Serif", serif';
const css = (c, a = 1) => `rgba(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)},${a})`;

// ---------------------------------------------------------------- math
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const ramp = (x, a, b) => clamp((x - a) / (b - a));
const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const ease = (x) => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const sine = (x) => 0.5 - 0.5 * Math.cos(Math.PI * clamp(x));
const fract = (x) => x - Math.floor(x);
const hash = (n) => fract(Math.sin(n * 127.1 + 311.7) * 43758.5453);
const hash2 = (n, m) => hash(n * 17.13 + m * 101.7);

// ---------------------------------------------------------------- the voice, as data
const WAVE = (() => {
  const bin = atob(WAVE_B64);
  const a = new Float32Array(bin.length);
  for (let i = 0; i < bin.length; i++) { const v = bin.charCodeAt(i); a[i] = (v > 127 ? v - 256 : v) / 127; }
  return a;
})();
// what the phone is playing: every line except the ones that come from the room (the whisper, the child)
const OFF_PHONE = LINES.filter((l) => l.fx === 'whisper' || l.fx === 'child');
function phoneSample(t) {
  for (const l of OFF_PHONE) if (t >= l.t0 - 0.3 && t <= l.t1 + 0.3) return 0;
  const i = Math.floor(t * WAVE_RATE);
  return i >= 0 && i < WAVE.length ? WAVE[i] : 0;
}
function peakAround(t, span) {
  let m = 0;
  const n = Math.max(1, Math.round(span * WAVE_RATE));
  const step = Math.max(1, Math.floor(n / 24));
  for (let k = 0; k < n; k += step) m = Math.max(m, Math.abs(phoneSample(t + k / WAVE_RATE)));
  return m;
}

// ---------------------------------------------------------------- particles
const MAXP = 4000;
class Parts {
  constructor() { this.a = new Float32Array(MAXP * 12); this.n = 0; }
  reset() { this.n = 0; }
  push(x, y, size, type, c, alpha, p0 = 0, p1 = 0, p2 = 0, p3 = 0) {
    if (this.n >= MAXP || alpha <= 0.001) return;
    const o = this.n++ * 12, a = this.a;
    a[o] = x; a[o + 1] = y; a[o + 2] = size; a[o + 3] = type;
    a[o + 4] = c[0]; a[o + 5] = c[1]; a[o + 6] = c[2]; a[o + 7] = alpha;
    a[o + 8] = p0; a[o + 9] = p1; a[o + 10] = p2; a[o + 11] = p3;
  }
}
function camera(x, y, z) {
  return {
    x, y, z,
    s: (wx, wy) => [CX + (wx - x) * z, CY + (wy - y) * z],
    apply: (ctx) => ctx.setTransform(z, 0, 0, z, CX - x * z, CY - y * z),
  };
}
function dust(P, bReal, n, seed, region, sizeR, alphaFn, col = COLD, cam = null, fall = 0) {
  const b = TL.worldBeats(bReal);          // dust belongs to the world: it freezes with it
  const [x0, y0, x1, y1] = region;
  for (let i = 0; i < n; i++) {
    const h1 = hash2(i, seed), h2 = hash2(i, seed + 1), h3 = hash2(i, seed + 2), h4 = hash2(i, seed + 3);
    const x = x0 + fract(h1 + b * 0.003 * (h3 - 0.4)) * (x1 - x0) + Math.sin(b * 0.3 + h4 * 6.28) * 12;
    const y = y0 + fract(h2 + b * (0.002 + fall) * (0.4 + h4)) * (y1 - y0) + Math.cos(b * 0.23 + h3 * 6.28) * 9;
    const a = alphaFn(x, y, i);
    if (a <= 0.003) continue;
    let sx = x, sy = y, z = 1;
    if (cam) { [sx, sy] = cam.s(x, y); z = cam.z; }
    P.push(sx, sy, (1.2 + h3 * h3 * sizeR) * Math.max(z, 0.4) * 4, 0, col, a, 0.25, 0.35);
  }
}

// ---------------------------------------------------------------- 2D helpers
function wrap(ctx, text, maxW) {
  const words = text.split(' '); const lines = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { lines.push(cur); cur = w; } else cur = t; }
  if (cur) lines.push(cur);
  return lines;
}
function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function label(ctx, text, x, y, size, color, a, align = 'left', spacing = 0.22, weight = 600) {
  if (a <= 0.002) return;
  ctx.save();
  ctx.font = `${weight} ${size}px ${UI}`; ctx.letterSpacing = `${size * spacing}px`;
  ctx.textAlign = align; ctx.fillStyle = color; ctx.globalAlpha = a;
  ctx.fillText(text, x, y);
  ctx.restore();
}

// Caption: words arrive as they are spoken. Holds until the next line, or CAPTION_HOLD beats after.
function currentLine(t) {
  let cur = null;
  for (let i = 0; i < LINES.length; i++) {
    const l = LINES[i], next = LINES[i + 1];
    const end = Math.min(next ? next.t0 - 0.05 : 1e9, l.v1 + TL.timeOf(TL.CAPTION_HOLD));
    if (t >= l.v0 - 0.05 && t < end) cur = { l, end };
  }
  return cur;
}
function caption(ctx, t, x, y, o = {}) {
  const c = currentLine(t);
  if (!c) return;
  const { l, end } = c;
  const sys = l.fx === 'sys' || l.fx === 'op', wh = l.fx === 'whisper' || l.fx === 'child';
  const size = o.size || (sys ? 34 : wh ? 56 : 60);
  ctx.save();
  ctx.font = sys ? `400 ${size}px ${UI}` : `${wh ? 'italic ' : ''}${size}px ${SERIF}`;
  ctx.textBaseline = 'alphabetic';
  const full = l.words.map((w) => w.w).join(' ');
  const lines = wrap(ctx, full, o.maxW || (PORTRAIT ? 900 : 1300));
  const lh = size * 1.18;
  const out = 1 - smooth(ramp(t, end - 0.35, end));
  let wi = 0;
  lines.forEach((ln, li) => {
    const ws = ln.split(' ');
    const tw = ctx.measureText(ln).width;
    let cx = x - tw / 2;
    for (const w of ws) {
      const wt = l.words[wi++].t;
      const a = smooth(ramp(t, wt - 0.02, wt + 0.18)) * out;
      // glitch line: words jitter as they land
      const jx = l.fx === 'glitch' ? (hash2(wi, Math.floor(t * 24)) - 0.5) * 8 * Math.exp(-(t - wt) * 3) : 0;
      ctx.globalAlpha = a * (wh ? 0.86 : 1);
      ctx.fillStyle = sys ? 'rgba(200,212,232,0.92)' : wh ? 'rgba(232,236,242,1)' : INK;
      ctx.fillText(w, cx + jx, y + li * lh + (1 - smooth(ramp(t, wt, wt + 0.3))) * 6);
      cx += ctx.measureText(w + ' ').width;
    }
  });
  ctx.restore();
}

// A strip of the phone's waveform (what is playing right now), as bars.
function waveStrip(ctx, t, x, y, w, h, o = {}) {
  const bar = o.bar || 4, gap = o.gap || 3, span = o.span || 2.4;
  const n = Math.floor(w / (bar + gap));
  ctx.save();
  for (let i = 0; i < n; i++) {
    const u = i / (n - 1);                   // 0 = oldest, 0.5 = now, 1 = what's coming
    const tt = t + (u - 0.5) * span;
    const p = peakAround(tt, span / n);
    const amp = Math.max(1.5, p * h);
    const future = u > 0.5;
    ctx.globalAlpha = (o.alpha ?? 1) * (future ? 0.22 : 0.55 + 0.45 * u * 2);
    ctx.fillStyle = o.color || INK;
    ctx.fillRect(x + i * (bar + gap), y - amp, bar, amp * 2);
  }
  if (o.playhead) {
    ctx.globalAlpha = (o.alpha ?? 1) * 0.6;
    ctx.fillStyle = o.color || INK;
    ctx.fillRect(x + w / 2 - 1, y - h - 30, 2, h * 2 + 60);
  }
  ctx.restore();
}
const mmss = (s) => `${Math.floor(Math.max(0, s) / 60)}:${String(Math.floor(Math.max(0, s) % 60)).padStart(2, '0')}`;

// ---------------------------------------------------------------- phone
const PW = 470, PH = 960;
function phoneShell(ctx, on, tint = [1, 1, 1]) {
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 60; ctx.shadowOffsetY = 20;
  rrect(ctx, -PW / 2, -PH / 2, PW, PH, 72); ctx.fillStyle = '#0a0b0e'; ctx.fill();
  ctx.restore();
  rrect(ctx, -PW / 2, -PH / 2, PW, PH, 72);
  ctx.lineWidth = 3; ctx.strokeStyle = `rgba(150,170,205,${0.08 + 0.28 * on})`; ctx.stroke();
  const sx = -PW / 2 + 16, sy = -PH / 2 + 16, sw = PW - 32, sh = PH - 32;
  rrect(ctx, sx, sy, sw, sh, 58); ctx.clip();
  const g = ctx.createLinearGradient(0, sy, 0, sy + sh);
  g.addColorStop(0, `rgba(${(14 + 18 * on) * tint[0]},${(18 + 28 * on) * tint[1]},${(26 + 48 * on) * tint[2]},1)`);
  g.addColorStop(1, `rgba(${4 + 5 * on},${5 + 7 * on},${8 + 12 * on},1)`);
  ctx.fillStyle = g; ctx.fillRect(sx, sy, sw, sh);
  rrect(ctx, -60, sy + 22, 120, 34, 17); ctx.fillStyle = '#020203'; ctx.fill();
}
function notif(ctx, y, head, title, body, a, right = 'now') {
  if (a <= 0.001) return 0;
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(0, (1 - a) * -24);
  const cw = 412, cx = -cw / 2, ch = body ? 150 : 112;
  rrect(ctx, cx, y, cw, ch, 28); ctx.fillStyle = 'rgba(36,44,60,0.9)'; ctx.fill();
  ctx.textAlign = 'left';
  ctx.font = `600 16px ${UI}`; ctx.letterSpacing = '3px'; ctx.fillStyle = 'rgba(200,215,240,0.62)';
  ctx.fillText(head, cx + 24, y + 38);
  ctx.letterSpacing = '0px'; ctx.textAlign = 'right'; ctx.font = `400 17px ${UI}`;
  ctx.fillText(right, cx + cw - 22, y + 38);
  ctx.textAlign = 'left'; ctx.font = `600 25px ${UI}`; ctx.fillStyle = 'rgba(240,244,255,0.98)';
  ctx.fillText(title, cx + 24, y + 78);
  if (body) { ctx.font = `400 21px ${UI}`; ctx.fillStyle = 'rgba(205,216,238,0.85)'; ctx.fillText(body, cx + 24, y + 114); }
  ctx.restore();
  return ch + 14;
}
function lockScreen(ctx, b, notes) {
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(214,226,250,0.72)'; ctx.font = `500 24px ${UI}`;
  ctx.fillText(PART === 6 ? 'Thursday, 14 November' : 'Wednesday, 13 November', 0, -330);
  ctx.font = `200 156px ${UI}`; ctx.fillStyle = 'rgba(232,240,255,0.94)';
  ctx.fillText(TL.clockText(b), 0, -175);
  let y = -110;
  for (const n of notes) y += notif(ctx, y, n.head, n.title, n.body, ease(ramp(b, n.at, n.at + 0.8)), n.right);
}
function chatScreen(ctx, b) {
  ctx.textAlign = 'center';
  ctx.font = `600 26px ${UI}`; ctx.fillStyle = 'rgba(236,241,252,0.95)';
  ctx.fillText('Building 3', 0, -360);
  ctx.font = `400 17px ${UI}`; ctx.fillStyle = 'rgba(190,205,232,0.6)';
  ctx.fillText('41 members', 0, -332);
  ctx.fillStyle = 'rgba(190,205,232,0.12)'; ctx.fillRect(-205, -310, 410, 1.5);
  // messages stack upward from the composer; the newest pushes the rest up
  const shown = TL.CHAT.filter(([mb]) => b >= mb - 0.7);
  let y = 360;
  for (let i = shown.length - 1; i >= 0; i--) {
    const [mb, apt, name, text] = shown[i];
    const typing = b < mb;
    const a = typing ? 1 : ease(ramp(b, mb, mb + 0.35));
    ctx.save(); ctx.globalAlpha *= Math.max(0.0, Math.min(1, (y + 300) / 120));
    if (!name) {
      ctx.textAlign = 'center'; ctx.font = `italic 400 19px ${UI}`; ctx.fillStyle = 'rgba(190,205,232,0.6)';
      ctx.globalAlpha *= a; ctx.fillText(text, 0, y - 10); y -= 50; ctx.restore(); continue;
    }
    ctx.font = `400 23px ${UI}`;
    const lines = typing ? ['• • •'] : wrap(ctx, text, 300);
    const bh = 30 + lines.length * 30 + 26;
    const bw = typing ? 90 : Math.max(...lines.map((l) => ctx.measureText(l).width)) + 36;
    const x = -200;
    ctx.globalAlpha *= a;
    rrect(ctx, x, y - bh, bw, bh, 22); ctx.fillStyle = 'rgba(44,52,70,0.95)'; ctx.fill();
    ctx.textAlign = 'left';
    ctx.font = `600 16px ${UI}`; ctx.fillStyle = name === 'Lily' ? 'rgba(255,190,150,0.9)' : 'rgba(170,200,255,0.85)';
    ctx.fillText(`${name} · ${apt}`, x + 18, y - bh + 26);
    ctx.font = `400 23px ${UI}`; ctx.fillStyle = 'rgba(240,244,255,0.97)';
    lines.forEach((l, k) => ctx.fillText(l, x + 18, y - bh + 58 + k * 30));
    y -= bh + 14;
    ctx.restore();
  }
  rrect(ctx, -205, 385, 410, 52, 26); ctx.fillStyle = 'rgba(36,44,60,0.8)'; ctx.fill();
  ctx.textAlign = 'left'; ctx.font = `400 19px ${UI}`; ctx.fillStyle = 'rgba(190,205,232,0.4)';
  ctx.fillText('Message', -180, 418);
}
function ringing(b) {
  for (const [a, c] of TL.EVENTS.rings || []) if (b >= a && b < c) return b - a;
  return -1;
}
function callScreen(ctx, b, t) {
  const r = ringing(b);
  const answered = TL.EVENTS.answered !== undefined && b >= TL.EVENTS.answered;
  ctx.textAlign = 'center';
  // avatar: no photo, just a letter
  const pulse = r >= 0 ? 1 + 0.06 * Math.sin(r * Math.PI * 2) : 1;
  ctx.beginPath(); ctx.arc(0, -250, 70 * pulse, 0, Math.PI * 2); ctx.fillStyle = 'rgba(60,70,92,0.9)'; ctx.fill();
  ctx.font = `300 64px ${UI}`; ctx.fillStyle = 'rgba(236,241,252,0.95)'; ctx.fillText('Y', 0, -228);
  ctx.font = `500 46px ${UI}`; ctx.fillText('You', 0, -120);
  ctx.font = `400 22px ${UI}`; ctx.fillStyle = 'rgba(205,216,238,0.75)';
  if (answered) {
    const el = t - TL.timeOf(TL.EVENTS.answered);
    ctx.fillText(mmss(el), 0, -80);
    ctx.save(); ctx.translate(-190, 60); waveStrip(ctx, t, 0, 0, 380, 70, { bar: 4, gap: 3, span: 2.2 }); ctx.restore();
    rrect(ctx, -45, 300, 90, 90, 45); ctx.fillStyle = 'rgba(235,70,60,0.95)'; ctx.fill();
  } else {
    ctx.fillText(r >= 0 ? 'mobile · calling…' : 'Missed call', 0, -80);
    // slide to answer; on the last call the knob moves without anyone touching it
    const auto = TL.EVENTS.answered !== undefined ? ease(ramp(b, TL.EVENTS.answered - 1.6, TL.EVENTS.answered)) : 0;
    rrect(ctx, -190, 300, 380, 90, 45); ctx.fillStyle = 'rgba(255,255,255,0.12)'; ctx.fill();
    ctx.font = `400 22px ${UI}`; ctx.fillStyle = `rgba(236,241,252,${0.6 * (1 - auto)})`; ctx.fillText('slide to answer', 20, 353);
    const kx = -145 + auto * 290;
    ctx.beginPath(); ctx.arc(kx, 345, 38, 0, Math.PI * 2); ctx.fillStyle = 'rgba(80,200,110,0.95)'; ctx.fill();
  }
  const mc = TL.missedCalls(b);
  if (mc > 0 && !answered) { ctx.font = `600 19px ${UI}`; ctx.fillStyle = 'rgba(255,120,110,0.9)'; ctx.fillText(`${mc} missed call${mc > 1 ? 's' : ''} from You`, 0, 250); }
}
function dialScreen(ctx, b, t) {
  ctx.textAlign = 'center';
  ctx.font = `300 72px ${UI}`; ctx.fillStyle = 'rgba(236,241,252,0.95)'; ctx.fillText('911', 0, -250);
  const el = t - TL.timeOf(TL.EVENTS.dial) - 1.2;
  ctx.font = `400 22px ${UI}`; ctx.fillStyle = 'rgba(205,216,238,0.75)';
  ctx.fillText(el < 0 ? 'calling…' : mmss(el), 0, -200);
  ctx.save(); ctx.translate(-190, -60); waveStrip(ctx, t, 0, 0, 380, 60, { bar: 4, gap: 3, span: 2.2 }); ctx.restore();
  for (let k = 0; k < 9; k++) {
    const x = (k % 3 - 1) * 120, y = 60 + Math.floor(k / 3) * 105;
    ctx.beginPath(); ctx.arc(x, y, 42, 0, Math.PI * 2); ctx.fillStyle = 'rgba(255,255,255,0.08)'; ctx.fill();
  }
  rrect(ctx, -45, 380, 90, 90, 45); ctx.fillStyle = 'rgba(235,70,60,0.95)'; ctx.fill();
}
function holderScreen(ctx, b) {
  ctx.textAlign = 'center';
  ctx.font = `600 17px ${UI}`; ctx.letterSpacing = '5px'; ctx.fillStyle = 'rgba(200,215,240,0.6)';
  ctx.fillText('THE STILLNESS', 0, -330); ctx.letterSpacing = '0px';
  ctx.font = `48px ${SERIF}`; ctx.fillStyle = 'rgba(236,241,252,0.96)';
  ctx.fillText('Holder: You', 0, -230);
  ctx.font = `400 22px ${UI}`; ctx.fillStyle = 'rgba(190,205,232,0.7)';
  ctx.fillText('99 of 99 released at sunrise', 0, -185);
  const k = smooth(ramp(b, TL.EVENTS.freeze + 0.8, TL.EVENTS.freeze + 1.6));
  ctx.globalAlpha *= 1;
  ctx.font = `600 18px ${UI}`; ctx.letterSpacing = '3px'; ctx.fillStyle = `rgba(255,160,90,${0.9 * k})`;
  ctx.fillText('NEXT OFFER: 3:07 AM', 0, -110); ctx.letterSpacing = '0px';
  ctx.font = `400 21px ${UI}`; ctx.fillStyle = `rgba(205,216,238,${0.8 * k})`;
  ctx.fillText('99 new recipients', 0, -78);
  const press = smooth(ramp(b, TL.EVENTS.hold - 0.4, TL.EVENTS.hold));
  rrect(ctx, -170, 170, 340, 84, 42);
  ctx.fillStyle = `rgba(226,236,255,${0.12 + 0.82 * press})`; ctx.fill();
  ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(210,222,245,0.5)'; ctx.stroke();
  ctx.font = `600 26px ${UI}`; ctx.fillStyle = press > 0.5 ? '#0b0f17' : 'rgba(226,236,255,0.9)';
  ctx.fillText(press > 0.5 ? 'Holding' : 'Hold to stop', 0, 222);
}
function playerScreen(ctx, b, t, from) {
  ctx.textAlign = 'center';
  ctx.font = `600 30px ${UI}`; ctx.fillStyle = 'rgba(236,241,252,0.95)'; ctx.fillText('Voicemail', 0, -330);
  rrect(ctx, -195, -280, 390, 128, 26); ctx.fillStyle = 'rgba(36,44,60,0.85)'; ctx.fill();
  ctx.textAlign = 'left'; ctx.font = `600 30px ${UI}`; ctx.fillStyle = 'rgba(240,244,255,0.98)';
  ctx.fillText('You', -170, -228);
  ctx.font = `400 21px ${UI}`; ctx.fillStyle = 'rgba(205,216,238,0.8)'; ctx.fillText(from, -170, -188);
  ctx.save(); ctx.translate(-200, 40); waveStrip(ctx, t, 0, 0, 400, 90, { bar: 4, gap: 3, span: 2.2 }); ctx.restore();
  ctx.fillStyle = 'rgba(236,241,252,0.95)'; ctx.fillRect(-26, 290, 16, 56); ctx.fillRect(10, 290, 16, 56);
}
function drawPhone(ctx, b, t, on, screen, tint) {
  ctx.save();
  phoneShell(ctx, on, tint);
  if (on > 0.01) { ctx.globalAlpha = on; screen(ctx, b, t); ctx.globalAlpha = 1; }
  ctx.restore();
}

// ---------------------------------------------------------------- the front door (Part 2's set)
const DOOR = { x0: -200, x1: 200, y0: -430, y1: 400 };
function knockShake(b, knocks) {
  let x = 0, y = 0;
  for (const k of knocks) {
    const u = b - k;
    if (u > 0 && u < 0.5) { const e = Math.exp(-u * 10); x += Math.sin(u * 90 + k) * 5 * e; y += Math.cos(u * 70 + k) * 2.5 * e; }
  }
  return [x, y];
}
// light: color of what's under the door; feet: number of pairs; open: 0..1
function drawDoor(ctx, b, { light = HALL, gl = 1, feet = 0, open = 0, shake = [0, 0], dawn = 0 } = {}) {
  const { x0, x1, y0, y1 } = DOOR;
  const fg = ctx.createLinearGradient(0, y1, 0, y1 + 500);
  fg.addColorStop(0, `rgba(${Math.round(30 * gl + 8 + 30 * dawn)},${Math.round(36 * gl + 9 + 20 * dawn)},${Math.round(30 * gl + 9 + 8 * dawn)},1)`); fg.addColorStop(1, '#050607');
  ctx.fillStyle = fg; ctx.fillRect(-2000, y1, 4000, 800);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const sp = ctx.createRadialGradient(0, y1 + 4, 10, 0, y1 + 4, 520);
  sp.addColorStop(0, css(light, 0.20 * gl)); sp.addColorStop(1, css(light, 0));
  ctx.fillStyle = sp; ctx.save(); ctx.scale(1, 0.32); ctx.fillRect(-700, (y1 - 40) / 0.32, 1400, 600 / 0.32); ctx.restore();
  ctx.restore();
  const wg = ctx.createRadialGradient(0, y1, 50, 0, y1 - 200, 1300);
  wg.addColorStop(0, `rgb(${Math.round(20 + 16 * gl + 30 * dawn)},${Math.round(22 + 20 * gl + 20 * dawn)},${Math.round(22 + 16 * gl + 8 * dawn)})`); wg.addColorStop(1, '#0a0b0d');
  ctx.fillStyle = wg; ctx.fillRect(-2000, -1200, 4000, 1200 + y1);
  ctx.fillStyle = '#08090b';
  ctx.beginPath(); ctx.moveTo(-560, -170); ctx.quadraticCurveTo(-640, 60, -600, 250); ctx.lineTo(-470, 250); ctx.quadraticCurveTo(-450, 40, -520, -170); ctx.closePath(); ctx.fill();
  ctx.fillRect(-548, -190, 16, 26);
  ctx.fillStyle = '#1c1f24'; ctx.fillRect(x0 - 34, y0 - 34, x1 - x0 + 68, y1 - y0 + 34);
  if (open > 0) {
    ctx.fillStyle = css(light, 0.92); ctx.fillRect(x0, y0, (x1 - x0) * open, y1 - y0);
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    const s2 = ctx.createLinearGradient(0, y1, 0, y1 + 420);
    s2.addColorStop(0, css(light, 0.35 * open)); s2.addColorStop(1, css(light, 0));
    ctx.fillStyle = s2;
    ctx.beginPath(); ctx.moveTo(x0, y1); ctx.lineTo(x0 + (x1 - x0) * open, y1); ctx.lineTo(x0 + (x1 - x0) * open * 1.9 + 120, y1 + 420); ctx.lineTo(x0 - 120, y1 + 420); ctx.fill();
    ctx.restore();
  }
  ctx.save(); ctx.translate(shake[0], shake[1]);
  const w = (x1 - x0) * (1 - open * 0.86), px = x1 - w;
  const dg = ctx.createLinearGradient(px, 0, x1, 0);
  dg.addColorStop(0, '#16181c'); dg.addColorStop(1, '#101215');
  ctx.fillStyle = dg;
  ctx.beginPath(); ctx.moveTo(px, y0 - open * 30); ctx.lineTo(x1, y0); ctx.lineTo(x1, y1 - 6); ctx.lineTo(px, y1 - 6 + open * 30); ctx.closePath(); ctx.fill();
  if (open < 0.3) {
    ctx.strokeStyle = 'rgba(200,220,205,0.07)'; ctx.lineWidth = 3;
    ctx.strokeRect(x0 + 40, y0 + 50, x1 - x0 - 80, 300); ctx.strokeRect(x0 + 40, y0 + 400, x1 - x0 - 80, 330);
    ctx.beginPath(); ctx.arc(x1 - 52, 20, 15, 0, Math.PI * 2); ctx.fillStyle = '#1d2026'; ctx.fill();
    ctx.strokeStyle = 'rgba(160,170,160,0.16)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(x1 - 40, -100); ctx.quadraticCurveTo(x1 - 10, -40, x1 + 18, -96); ctx.stroke();
  }
  ctx.restore();
  if (open < 0.02) {
    ctx.fillStyle = css(light, 0.95 * gl); ctx.fillRect(x0, y1 - 6, x1 - x0, 7);
    // feet: pairs of shadows across the gap; with enough of them the light is gone
    ctx.fillStyle = 'rgba(4,5,6,0.97)';
    for (let k = 0; k < feet; k++) {
      const c = feet === 1 ? 0 : -150 + 300 * (k / Math.max(1, feet - 1)) + (hash2(k, 3) - 0.5) * 30;
      const wv = 34 + 10 * hash2(k, 4);
      ctx.fillRect(c - wv - 6, y1 - 6, wv, 7); ctx.fillRect(c + 6, y1 - 6, wv, 7);
    }
  }
}

// ---------------------------------------------------------------- the corridor
const F = 560;
let VPY = 0;
const proj = (X, Y, Z) => [CX + X / Z * F, VPY + Y / Z * F];
function quad(ctx, pts, fill) {
  ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
  ctx.fillStyle = fill; ctx.fill();
}
function figure(ctx, X, Z, hgt, Yf, rim) {
  // Part 2's figure: too narrow at the waist, perfectly still, facing us. hgt < 1 = a child.
  const top = Yf - 1.7 * hgt;
  const [fx0, fy0] = proj(X - 0.26 * Math.sqrt(hgt), top + 0.1, Z), [fx1, fy1] = proj(X + 0.26 * Math.sqrt(hgt), Yf, Z);
  const [hx, hy] = proj(X, top, Z);
  const hr = 0.115 * Math.sqrt(hgt) / Z * F;
  const w = fx1 - fx0, h = fy1 - fy0;
  ctx.fillStyle = 'rgba(1,1,1,0.97)';
  ctx.beginPath();
  ctx.moveTo(fx0 + w * 0.06, fy0 + h * 0.06);
  ctx.quadraticCurveTo(fx0 + w * 0.5, fy0 - h * 0.02, fx1 - w * 0.06, fy0 + h * 0.06);
  ctx.lineTo(fx1 - w * 0.2, fy0 + h * 0.5); ctx.lineTo(fx1 - w * 0.28, fy1);
  ctx.lineTo(fx0 + w * 0.28, fy1); ctx.lineTo(fx0 + w * 0.2, fy0 + h * 0.5);
  ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.ellipse(hx, hy + hr * 0.1, hr * 0.86, hr, 0, 0, Math.PI * 2); ctx.fill();
  if (rim) { ctx.strokeStyle = rim; ctx.lineWidth = Math.max(1, 3 / Z); ctx.beginPath(); ctx.ellipse(hx, hy + hr * 0.1, hr * 0.86, hr, 0, Math.PI * 1.05, Math.PI * 1.95); ctx.stroke(); }
}
// mode: 'night' (Part 2's corridor, flickering) or 'day' (empty, every door open)
function drawCorridor(ctx, b, P, { mode = 'night', crowd = 0, cam = 0, endPhone = 0 } = {}) {
  const day = mode === 'day';
  const L = day ? 1 : TL.lightOn(b);
  const hum = day ? 1 : L * (0.9 + 0.1 * Math.sin(b * 37.1) * Math.sin(b * 11.3));
  const Zn = day ? 0.62 : 0.9, Zf = 14, Xw = 1.05, Yf = 1, Yc = -0.85;
  const sh = (v) => Math.round(v);
  const z0 = cam;                      // the camera walks forward in daylight
  const P3 = (X, Y, Z) => proj(X, Y, Math.max(0.05, Z - z0));
  const wall = day
    ? (a) => `rgb(${sh(40 + 120 * a)},${sh(36 + 104 * a)},${sh(30 + 82 * a)})`
    : (a) => `rgb(${sh(14 + 46 * a * hum)},${sh(16 + 56 * a * hum)},${sh(14 + 44 * a * hum)})`;
  ctx.fillStyle = day ? '#2a2620' : '#020303'; ctx.fillRect(0, 0, W, H);
  const fogTo = (z) => 1 - 0.7 * (z - Zn) / (Zf - Zn);
  for (let z = Math.max(Zn, z0 + 0.3); z < Zf; z += 0.5) {
    const z2 = z + 0.5, f = fogTo(z);
    quad(ctx, [P3(-Xw, Yf, z), P3(Xw, Yf, z), P3(Xw, Yf, z2), P3(-Xw, Yf, z2)], wall(0.55 * f));
    quad(ctx, [P3(-Xw, Yc, z), P3(Xw, Yc, z), P3(Xw, Yc, z2), P3(-Xw, Yc, z2)], wall(0.35 * f));
    quad(ctx, [P3(-Xw, Yc, z), P3(-Xw, Yf, z), P3(-Xw, Yf, z2), P3(-Xw, Yc, z2)], wall(0.8 * f));
    quad(ctx, [P3(Xw, Yc, z), P3(Xw, Yf, z), P3(Xw, Yf, z2), P3(Xw, Yc, z2)], wall(0.75 * f));
  }
  quad(ctx, [P3(-Xw, Yc, Zf), P3(Xw, Yc, Zf), P3(Xw, Yf, Zf), P3(-Xw, Yf, Zf)], wall(0.3));
  quad(ctx, [P3(-0.32, Yf, Math.max(Zn, z0 + 0.3)), P3(0.32, Yf, Math.max(Zn, z0 + 0.3)), P3(0.32, Yf, Zf), P3(-0.32, Yf, Zf)], day ? 'rgba(70,40,30,0.5)' : 'rgba(10,12,10,0.55)');
  for (const [side, z] of [[-1, 2.6], [1, 4.4], [-1, 6.8], [1, 9.2], [-1, 11.6]]) {
    if (z < z0 + 0.4) continue;
    const X = side * Xw, f = fogTo(z);
    if (day) {
      // every door stands open; the apartments behind them are dark
      quad(ctx, [P3(X, -0.55, z), P3(X, Yf, z), P3(X, Yf, z + 0.85), P3(X, -0.55, z + 0.85)], 'rgb(22,20,18)');
      // Lily, just inside her doorway, while she asks
      if (PART === 6 && side === 1 && z === 9.2 && b >= 36.8 && b < 44.5) {
        const k = smooth(ramp(b, 36.8, 37.6)) * (1 - smooth(ramp(b, 43.5, 44.5)));
        ctx.save(); ctx.globalAlpha = k; figure(ctx, X - 0.3, z + 0.5, 0.6, Yf, null); ctx.restore();   // in the hall, by her door
      }
      quad(ctx, [P3(X, -0.55, z), P3(X, Yf, z), P3(X - side * 0.5, Yf, z + 0.05), P3(X - side * 0.5, -0.55, z + 0.05)], `rgb(${sh(60 * f + 20)},${sh(54 * f + 18)},${sh(44 * f + 16)})`);
    } else {
      quad(ctx, [P3(X, -0.55, z), P3(X, Yf, z), P3(X, Yf, z + 0.85), P3(X, -0.55, z + 0.85)], `rgb(${sh(8 + 22 * hum * f)},${sh(9 + 24 * hum * f)},${sh(9 + 20 * hum * f)})`);
    }
  }
  for (let z = 1.6; z < Zf; z += 2.1) {
    if (z < z0 + 0.3) continue;
    quad(ctx, [P3(-0.32, Yc, z), P3(0.32, Yc, z), P3(0.32, Yc, z + 0.7), P3(-0.32, Yc, z + 0.7)], day ? 'rgba(200,190,170,0.35)' : css(HALL, (0.08 + 0.92 * hum) * fogTo(z)));
    if (!day) { const [gx, gy] = P3(0, Yc + 0.02, z + 0.35); P.push(gx, gy, 260 / Math.max(0.3, z - z0), 0, HALL, 0.25 * hum * fogTo(z), 0.03, 0.8); }
  }
  // daylight comes from a window at the far end
  if (day) {
    const [wx0, wy0] = P3(-0.5, -0.6, Zf), [wx1, wy1] = P3(0.5, 0.3, Zf);
    ctx.fillStyle = 'rgba(255,236,200,0.9)'; ctx.fillRect(wx0, wy0, wx1 - wx0, wy1 - wy0);
    P.push((wx0 + wx1) / 2, (wy0 + wy1) / 2, 420, 0, [1, 0.85, 0.6], 0.25, 0.03, 0.6);
  } else {
    const [ex0, ey0] = P3(-0.2, -0.72, Zf), [ex1, ey1] = P3(0.2, -0.6, Zf);
    ctx.fillStyle = 'rgba(190,40,30,0.95)'; ctx.fillRect(ex0, ey0, ex1 - ex0, ey1 - ey0);
    P.push((ex0 + ex1) / 2, (ey0 + ey1) / 2, 46, 0, RED, 0.35, 0.03, 0.5);
  }
  // a phone on the floor at the far end, face up, lit
  if (endPhone > 0) {
    const [px, py] = P3(0.05, Yf, 12.6);
    P.push(px, py, 220 / Math.max(0.4, 12.6 - z0), 0, COLD, 1.4 * endPhone, 0.05, 0.9);
  }
  // the crowd: everyone in the building, standing where the light can find them. Far first.
  const n = crowd;
  const order = [];
  for (let k = 0; k < n; k++) {
    // the first one stands at the far end; every blackout adds more of them, closer
    const lane = (hash2(k, 21) - 0.5) * (k === 0 ? 0 : 1.3);
    const z = 12.8 - 10.6 * Math.pow(k / 30, 0.65) + (hash2(k, 22) - 0.5) * 0.8;
    const hgt = hash2(k, 23) < 0.12 ? 0.62 : 0.92 + 0.16 * hash2(k, 24);        // some of them are children
    order.push([z, lane, hgt]);
  }
  order.sort((a, c) => c[0] - a[0]);
  for (const [z, lane, hgt] of order) figure(ctx, lane, z, hgt, Yf, css(HALL, 0.10 * L));
  if (!day && L < 1) { ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(0, 0, W, H); }
}

// ---------------------------------------------------------------- shots
function baseState() {
  return {
    bg: {
      base: [0.008, 0.009, 0.011], base2: [0.004, 0.004, 0.006],
      glow: [CX, CY, 400, 0], glowCol: COLD, glow2: [CX, CY, 400, 0], glow2Col: HALL,
      beam: [0, 0, 1, 1], beamP: [1, 1, 0, 0], beamCol: HALL, vig: 1.0, lift: 0,
    },
    freeze: 0, setAlpha: 1, ripple: [CX, CY, 0, 0], shake: [0, 0], clip: [0, 0, W, H], lens: [0, 0, 0, 1],
    grain: 0.034,
  };
}
const CAP_Y = 1420;
function partTag(ov, b) {
  const a = smooth(ramp(b, 0.3, 1.2)) * (1 - smooth(ramp(b, 5, 6)));
  label(ov, `THE STILLNESS  ·  PART ${PART}`, CX, 210, 20, 'rgba(200,214,232,0.75)', a, 'center', 0.3);
}
function timestamp(ov, b, a = 1) {
  label(ov, TL.clockText(b) + ' AM', 70, 290, 26, 'rgba(200,214,236,0.85)', a, 'left', 0.12, 300);
}
function bottomBar(ov, t, a = 1) { waveStrip(ov, t, CX - 350, 1495, 700, 22, { bar: 3, gap: 3, span: 3, alpha: 0.75 * a }); }
function phoneCam(b, b0, b1, set) {
  const u = ramp(b, b0, b1);
  const z = 1.2 + 0.1 * sine(u);
  const cam = camera(0, 130 - 30 * sine(u), z);
  cam.apply(set);
  set.rotate(0.03);
  return cam;
}
function phoneShot(b, t, S, set, ov, P, screen, { on = 1, tint, cap = true } = {}) {
  const sh = TL.shotAt(b);
  const cam = phoneCam(b, sh.b0, sh.b1, set);
  const [gx, gy] = cam.s(0, 0);
  S.bg.glow = [gx, gy, 760 * cam.z, 0.28 * on + 0.01];
  S.bg.glowCol = [0.55, 0.68, 0.95];
  drawPhone(set, b, t, on, screen, tint);
  set.setTransform(1, 0, 0, 1, 0, 0);
  dust(P, b, 110, 11, [-700, -700, 700, 700], 2.2, (x, y) => (0.03 + 0.45 * on) * Math.exp(-(x * x + y * y) / 300000), COLD, cam);
  if (cap) caption(ov, t, CX, CAP_Y + 40, { maxW: 880, size: 56 });
}
function doorShot(b, t, S, set, ov, P, opts, z0 = 1.1, z1 = 1.22) {
  const sh = TL.shotAt(b);
  const z = lerp(z0, z1, sine(ramp(b, sh.b0, sh.b1)));
  const cam = camera(0, 170, z);
  const light = opts.light || HALL;
  const [lx, ly] = cam.s(0, DOOR.y1);
  S.bg.glow = [lx, ly, 640 * z, 0.22 * (opts.gl ?? 1) + 0.4 * (opts.open || 0)];
  S.bg.glowCol = light;
  cam.apply(set);
  drawDoor(set, b, opts);
  set.setTransform(1, 0, 0, 1, 0, 0);
  if (!opts.open) { const [px, py] = cam.s(0, -140); P.push(px, py, 26 * z, 0, light, 0.9 * (opts.gl ?? 1), 0.12, 0.6); }
  dust(P, b, 140, 31, [-900, -600, 900, 900], 2.0, (x, y) => 0.45 * Math.exp(-((x * x) / 160000 + ((y - DOOR.y1) ** 2) / 60000)), light, cam);
  S.shake = (opts.shake || [0, 0]).map((v) => v * 0.6);
  return cam;
}
function titleCard(ov, P, b, b0, lines) {
  const a = smooth(ramp(b, b0, b0 + 0.6));
  label(ov, `THE STILLNESS  ·  PART ${PART}`, CX, CY - 150, 24, 'rgba(200,214,232,0.7)', a, 'center', 0.4);
  ov.save(); ov.textAlign = 'center'; ov.globalAlpha = a;
  ov.font = `${lines.length > 1 ? 112 : 104}px ${SERIF}`; ov.letterSpacing = '5px'; ov.fillStyle = 'rgba(232,237,240,0.97)';
  lines.forEach((l, i) => ov.fillText(l, CX + 2, CY + i * 116));
  ov.restore();
  dust(P, b, 80, 51, [0, 0, W, H], 1.6, () => 0.10);
}
function waveShot(b, t, S, ov, P, header, sub, dense = 0) {
  S.bg.glow = [CX, CY - 40, 900, 0.07 + 0.10 * peakAround(t - 0.05, 0.1)];
  S.bg.glowCol = [0.5, 0.6, 0.85];
  label(ov, header, 70, 250, 20, 'rgba(200,214,240,0.7)', 1, 'left', 0.25);
  label(ov, sub, 70, 288, 20, 'rgba(200,214,240,0.45)', 1, 'left', 0.25);
  waveStrip(ov, t, CX - 480, CY - 160, 960, 200 + 60 * dense, { bar: 5, gap: 4, span: 3.2, playhead: true });
  dust(P, b, 90, 21, [0, 0, W, H], 1.6, () => 0.10);
}

// --- PART 4
function p4lock(b, t, S, set, ov, P) {
  const [n1, n2] = TL.EVENTS.notify;
  phoneShot(b, t, S, set, ov, P, (c) => lockScreen(c, b, [
    { at: n1, head: 'BUILDING 3', title: '41 new messages', body: 'Marta: is anyone else’s phone…' },
    { at: n2, head: 'VOICEMAIL', title: '99 new voicemails from You', body: 'Received: Tomorrow — in 99 nights' },
  ]));
  partTag(ov, b);
}
function p4chat(b, t, S, set, ov, P) { phoneShot(b, t, S, set, ov, P, (c) => chatScreen(c, b), { cap: false }); timestamp(ov, b, 0.7); }
function p4wave(b, t, S, set, ov, P) {
  const n = b < 34 ? 1 : b < 41 ? 2 : 3;
  waveShot(b, t, S, ov, P, 'VOICEMAIL  ·  FROM: YOU', `RECEIVED: IN ${[99, 98, 97][n - 1]} NIGHTS  ·  ${n} OF 99`);
  caption(ov, t, CX, CY + 260, { maxW: 900, size: 64 });
}
function p4chorus(b, t, S, set, ov, P) {
  waveShot(b, t, S, ov, P, 'PLAYING ALL  ·  99 VOICEMAILS', 'FROM: YOU  ·  YOU  ·  YOU  ·  YOU', 1);
  // every night's warning at once: the same words, everywhere, out of step
  const [c0] = TL.EVENTS.chorus;
  for (let k = 0; k < 26; k++) {
    const at = c0 + 0.2 + k * 0.42 + hash2(k, 7) * 0.3;
    const a = smooth(ramp(b, at, at + 0.3)) * (1 - smooth(ramp(b, at + 2.2, at + 3.2)));
    if (a <= 0.01) continue;
    ov.save(); ov.globalAlpha = a * (0.35 + 0.6 * hash2(k, 8));
    ov.font = `${hash2(k, 9) < 0.3 ? 'italic ' : ''}${Math.round(34 + 40 * hash2(k, 10))}px ${SERIF}`;
    ov.textAlign = 'center'; ov.fillStyle = INK;
    ov.fillText('Don’t open the door.', 160 + 760 * hash2(k, 11), 420 + 1050 * hash2(k, 12) - (b - at) * 8);
    ov.restore();
  }
}
function p4peep(b, t, S, set, ov, P) {
  S.lens = [CX, CY - 20, 500, 1.12];
  set.setTransform(1, 0, 0, 1, 0, 0);
  VPY = CY - 40;
  drawCorridor(set, b, P, { crowd: TL.crowd(b) });
  dust(P, b, 110, 41, [CX - 600, CY - 500, CX + 600, CY + 500], 1.8, () => 0.25 * TL.lightOn(b), HALL);
  timestamp(ov, b, 0.7); bottomBar(ov, t);
  caption(ov, t, CX, 1360, { maxW: 900, size: 60 });
  S.grain = 0.04;
}
function p4knock(b, t, S, set, ov, P) {
  // the whole hallway knocks at once; their feet fill the light under the door
  const ks = []; for (let k = 0; k < 30; k++) ks.push(TL.EVENTS.knocks + 0.1 + k * 0.11 + hash2(k, 31) * 0.08);
  doorShot(b, t, S, set, ov, P, { feet: 9, gl: 1.2, shake: knockShake(b, ks) }, 1.25, 1.35);
  timestamp(ov, b, 0.7);
}

// --- PART 5
function p5call(b, t, S, set, ov, P) {
  const r = ringing(b);
  const on = r >= 0 ? 0.85 + 0.15 * Math.cos(r * Math.PI * 2) : 0.75;
  phoneShot(b, t, S, set, ov, P, (c) => callScreen(c, b, t), { on });
  partTag(ov, b); timestamp(ov, b, 0.7);
}
function p5dial(b, t, S, set, ov, P) { phoneShot(b, t, S, set, ov, P, (c) => dialScreen(c, b, t)); timestamp(ov, b, 0.7); }
function p5chat(b, t, S, set, ov, P) { phoneShot(b, t, S, set, ov, P, (c) => chatScreen(c, b), { cap: false }); timestamp(ov, b, 0.7); }
function p5door(b, t, S, set, ov, P) {
  const cam = doorShot(b, t, S, set, ov, P, { feet: TL.feetPairs(b), gl: 1 });
  // the phone on the floor lights the room every time it rings
  const ph = 0.5 + 0.5 * Math.sin(b * Math.PI * 1.5);
  const [px, py] = cam.s(330, 560);
  P.push(px, py, 160, 0, COLD, 0.35 * ph, 0.04, 0.8);
  timestamp(ov, b); bottomBar(ov, t);
  caption(ov, t, CX, 1400, { maxW: 880, size: 58 });
}
function p5clock(b, t, S, set, ov, P) {
  S.bg.glow = [CX, CY, 900, 0.06]; S.bg.glowCol = [0.5, 0.6, 0.85];
  const k = (b - 64) % 3;
  const a = smooth(ramp(k, 0, 0.4));
  ov.save(); ov.textAlign = 'center'; ov.globalAlpha = a;
  ov.font = `200 220px ${UI}`; ov.fillStyle = 'rgba(232,240,255,0.95)'; ov.fillText(TL.clockText(b), CX, CY - 60);
  ov.font = `600 24px ${UI}`; ov.letterSpacing = '6px'; ov.fillStyle = 'rgba(255,120,110,0.9)';
  ov.fillText(`${TL.missedCalls(b)} MISSED CALLS FROM YOU`, CX, CY + 40);
  ov.letterSpacing = '4px'; ov.fillStyle = 'rgba(200,214,236,0.6)'; ov.font = `500 20px ${UI}`;
  ov.fillText('SUNRISE 6:41 AM', CX, CY + 90);
  ov.restore();
  caption(ov, t, CX, CAP_Y, { maxW: 880, size: 62 });
  dust(P, b, 80, 61, [0, 0, W, H], 1.6, () => 0.12);
}
function p5call2(b, t, S, set, ov, P) {
  const r = ringing(b);
  const on = r >= 0 ? 0.85 + 0.15 * Math.cos(r * Math.PI * 2) : 0.9;
  phoneShot(b, t, S, set, ov, P, (c) => callScreen(c, b, t), { on });
  timestamp(ov, b, 0.7);
}

// --- PART 6
const DAWN = [1.0, 0.82, 0.58];
function p6dawn(b, t, S, set, ov, P) {
  const d = smooth(ramp(b, 0, 10));
  const light = [lerp(HALL[0], DAWN[0], d), lerp(HALL[1], DAWN[1], d), lerp(HALL[2], DAWN[2], d)];
  const cam = doorShot(b, t, S, set, ov, P, { light, gl: 1 + 0.4 * d, dawn: d });
  const [px, py] = cam.s(330, 560);
  P.push(px, py, 160, 0, COLD, 0.3, 0.04, 0.8);
  // the call never hung up
  const el = 3 * 3600 + 22 * 60 + 41 + t;
  label(ov, `CALL IN PROGRESS  ·  YOU  ·  ${Math.floor(el / 3600)}:${String(Math.floor(el / 60) % 60).padStart(2, '0')}:${String(Math.floor(el % 60)).padStart(2, '0')}`, CX, 1500, 20, 'rgba(120,230,150,0.85)', 1, 'center', 0.2);
  partTag(ov, b); timestamp(ov, b, 0.8);
}
function p6open(b, t, S, set, ov, P) {
  const open = ease(ramp(b, TL.EVENTS.doorOpen, TL.EVENTS.doorOpen + 3.5));
  doorShot(b, t, S, set, ov, P, { light: DAWN, gl: 1.4, dawn: 1, open }, 1.15, 1.3);
  timestamp(ov, b, 0.8);
}
function p6hall(b, t, S, set, ov, P) {
  set.setTransform(1, 0, 0, 1, 0, 0);
  VPY = CY - 80;
  const walk = lerp(0, 6.5, sine(ramp(b, 26, 48)));
  drawCorridor(set, b, P, { mode: 'day', cam: walk, endPhone: smooth(ramp(b, 30, 32)) });
  S.bg.vig = 1.2;
  dust(P, b, 150, 71, [0, 0, W, H], 2.0, () => 0.3, [1, 0.88, 0.7]);
  timestamp(ov, b, 0.8);
  caption(ov, t, CX, 1400, { maxW: 880, size: 62 });
}
function p6floorphone(b, t, S, set, ov, P) {
  const playing = b >= TL.EVENTS.tapPlay;
  phoneShot(b, t, S, set, ov, P, (c, bb, tt) => (playing
    ? playerScreen(c, bb, tt, 'Yesterday, 3:07 AM  ·  the first night')
    : lockScreen(c, bb, [{ at: TL.EVENTS.notify, head: 'VOICEMAIL', title: '1 new voicemail from You', body: 'Received: Yesterday, 3:07 AM' }])), { tint: [1.15, 1.0, 0.85] });
  S.bg.base = [0.05, 0.04, 0.03];
}
function p6holder(b, t, S, set, ov, P) {
  S.freeze = smooth(ramp(b, TL.EVENTS.freeze, TL.EVENTS.freeze + 0.6));
  if (b >= TL.EVENTS.freeze && b < TL.EVENTS.freeze + 4) {
    const u = (b - TL.EVENTS.freeze) / 4;
    S.ripple = [CX, CY, u * 2600, 0.9 * (1 - smooth(u))];
  }
  phoneShot(b, t, S, set, ov, P, (c) => holderScreen(c, b));
}
function p6final(b, t, S, set, ov, P) {
  const ks = TL.EVENTS.knocks;
  S.shake = knockShake(b, ks).map((v) => v * 0.8);
  const a1 = smooth(ramp(b, 82.5, 83.5)), a2 = smooth(ramp(b, 85, 86));
  ov.save(); ov.textAlign = 'center';
  ov.globalAlpha = a1; ov.font = `76px ${SERIF}`; ov.fillStyle = 'rgba(236,240,246,0.97)';
  ov.fillText('It has been', CX, CY - 80); ov.fillText('offered to you.', CX, CY + 10);
  ov.globalAlpha = a2; ov.font = `italic 46px ${SERIF}`; ov.fillStyle = 'rgba(200,210,226,0.85)';
  ov.fillText('Accept or decline by sunrise.', CX, CY + 110);
  ov.restore();
  label(ov, 'THE STILLNESS  ·  PART 6', CX, CY - 230, 22, 'rgba(200,214,232,0.65)', a1, 'center', 0.4);
  dust(P, b, 80, 81, [0, 0, W, H], 1.6, () => 0.10);
}
function shotBlack(b, t, S) { S.grain = 0.0; }

const SHOT_FN = {
  4: { lock: p4lock, chat: p4chat, wave: p4wave, chorus: p4chorus, peep: p4peep, knock: p4knock,
       title: (b, t, S, s, o, P) => titleCard(o, P, b, TL.EVENTS.title, ['99 NEW', 'VOICEMAILS']), black: shotBlack },
  5: { call: p5call, dial: p5dial, chat: p5chat, door: p5door, clock: p5clock, call2: p5call2,
       title: (b, t, S, s, o, P) => titleCard(o, P, b, TL.EVENTS.title, ['DON’T', 'ANSWER']), black: shotBlack },
  6: { dawn: p6dawn, open: p6open, hall: p6hall, floorphone: p6floorphone, holder: p6holder, final: p6final, black: shotBlack },
}[PART];

// ---------------------------------------------------------------- frame assembly
const glCanvas = document.getElementById('gl');
glCanvas.width = W; glCanvas.height = H;
const setCv = document.createElement('canvas'); setCv.width = W; setCv.height = H;
const ovCv = document.createElement('canvas'); ovCv.width = W; ovCv.height = H;
const setCtx = setCv.getContext('2d', { willReadFrequently: true });   // CPU-backed: GPU canvases upload one draw stale
const ovCtx = ovCv.getContext('2d', { willReadFrequently: true });
const G = createGL(glCanvas, W, H);
const parts = new Parts();
const pixels = new Uint8Array(W * H * 4);
const rgb = new Uint8Array(W * H * 3);

function compose(t) {
  const b = TL.beatOf(t);
  const shot = TL.shotAt(b);
  const S = baseState();
  for (const c of [setCtx, ovCtx]) { c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, W, H); c.globalAlpha = 1; }
  parts.reset();
  SHOT_FN[shot.name](b, t, S, setCtx, ovCtx, parts);
  setCtx.setTransform(1, 0, 0, 1, 0, 0);
  return S;
}
function subTimes(f) {
  const tc = f / TL.FPS, out = [];
  for (let s = 0; s < SUB; s++) {
    let t = tc + ((s + hash2(f, s + 0.5)) / SUB - 0.5) * SHUTTER / TL.FPS;
    for (const cb of TL.CUTS) {
      const ct = TL.timeOf(cb);
      if (tc >= ct && t < ct) t = ct;
      if (tc < ct && t >= ct) t = ct - 1e-4;
    }
    out.push(Math.max(0, Math.min(TL.DURATION - 1e-4, t)));
  }
  return out;
}
function renderAt(times, seedT) {
  G.beginFrame();
  let grain = 0.03;
  for (const t of times) {
    const S = compose(t);
    grain = S.grain;
    G.subFrame(S, setCv, ovCv, parts.a, parts.n, 1 / times.length);
  }
  // grain is seeded by the world clock (Part 1): when the world stops, so does the film
  G.endFrame(Math.floor(TL.worldBeats(TL.beatOf(seedT)) * TL.BEAT * TL.FPS + 0.5) % 9973, grain, pixels);
  for (let i = 0, j = 0; i < pixels.length; i += 4, j += 3) { rgb[j] = pixels[i]; rgb[j + 1] = pixels[i + 1]; rgb[j + 2] = pixels[i + 2]; }
}
window.renderFrame = (f) => { renderAt(subTimes(f), f / TL.FPS); return true; };
window.renderStill = (t, sub = SUB) => {
  const times = [];
  for (let s = 0; s < sub; s++) times.push(Math.min(TL.DURATION - 1e-4, t + ((s + 0.5) / sub - 0.5) * SHUTTER / TL.FPS));
  renderAt(times, t);
  return true;
};
const ROWS = Math.max(1, Math.floor(720000 / (W * 3)));
window.sliceCount = Math.ceil(H / ROWS);
window.getSlice = (k) => {
  const a = k * ROWS * W * 3, e = Math.min(H, (k + 1) * ROWS) * W * 3;
  let s = '';
  for (let i = a; i < e; i += 0x8000) s += String.fromCharCode.apply(null, rgb.subarray(i, Math.min(e, i + 0x8000)));
  return btoa(s);
};
window.READY = true;
