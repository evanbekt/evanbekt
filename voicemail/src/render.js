// ONE NEW VOICEMAIL — renderer. Every frame is a pure function of time.
// WebGL2: light, dust, glows, peephole lens, motion-blur accumulation. Canvas 2D: type, UI, set.

import * as TL from './timeline.js';
import { LINES, WAVE_RATE, WAVE_B64 } from './voice_data.js';
import { createGL } from './gl.js';

const Q = new URLSearchParams(location.search);
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
const L9 = LINES.find((l) => l.id === 'l9');
// what the phone is playing: the voice, plus the beep; never the whisper (that one isn't on the phone)
function phoneSample(t) {
  if (t >= L9.t0 - 1.2 && t <= L9.t1 + 0.3) return 0;
  const i = Math.floor(t * WAVE_RATE);
  let v = i >= 0 && i < WAVE.length ? WAVE[i] : 0;
  const bt = t - TL.timeOf(TL.EVENTS.beep);
  if (bt > 0 && bt < 0.42) v += 0.55 * Math.sin(bt * 2 * Math.PI * 1000) * Math.min(1, bt / 0.01, (0.42 - bt) / 0.02);
  return v;
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
function dust(P, b, n, seed, region, sizeR, alphaFn, col = COLD, cam = null, fall = 0) {
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
  const sys = l.fx === 'sys', wh = l.fx === 'whisper';
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
function drawPhone(ctx, b, t, on, mode) {
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 60; ctx.shadowOffsetY = 20;
  rrect(ctx, -PW / 2, -PH / 2, PW, PH, 72); ctx.fillStyle = '#0a0b0e'; ctx.fill();
  ctx.restore();
  rrect(ctx, -PW / 2, -PH / 2, PW, PH, 72);
  ctx.lineWidth = 3; ctx.strokeStyle = `rgba(150,170,205,${0.08 + 0.28 * on})`; ctx.stroke();
  const sx = -PW / 2 + 16, sy = -PH / 2 + 16, sw = PW - 32, sh = PH - 32;
  ctx.save();
  rrect(ctx, sx, sy, sw, sh, 58); ctx.clip();
  const g = ctx.createLinearGradient(0, sy, 0, sy + sh);
  g.addColorStop(0, `rgba(${14 + 18 * on},${18 + 28 * on},${26 + 48 * on},1)`);
  g.addColorStop(1, `rgba(${4 + 5 * on},${5 + 7 * on},${8 + 12 * on},1)`);
  ctx.fillStyle = g; ctx.fillRect(sx, sy, sw, sh);
  rrect(ctx, -60, sy + 22, 120, 34, 17); ctx.fillStyle = '#020203'; ctx.fill();
  if (on > 0.01) {
    ctx.globalAlpha = on;
    ctx.textAlign = 'center';
    if (mode === 'lock') {
      ctx.fillStyle = 'rgba(214,226,250,0.72)'; ctx.font = `500 24px ${UI}`;
      ctx.fillText('Wednesday, 13 November', 0, -330);
      ctx.font = `200 156px ${UI}`; ctx.fillStyle = 'rgba(232,240,255,0.94)';
      ctx.fillText('3:13', 0, -175);
      const n = ease(ramp(b, TL.EVENTS.notify, TL.EVENTS.notify + 0.9));
      if (n > 0.001) {
        ctx.save(); ctx.globalAlpha *= n; ctx.translate(0, (1 - n) * -26);
        const cw = 412, cx = -cw / 2, cy = -90, ch = 170;
        rrect(ctx, cx, cy, cw, ch, 30); ctx.fillStyle = 'rgba(36,44,60,0.9)'; ctx.fill();
        ctx.textAlign = 'left';
        ctx.font = `600 17px ${UI}`; ctx.letterSpacing = '3px'; ctx.fillStyle = 'rgba(200,215,240,0.62)';
        ctx.fillText('VOICEMAIL', cx + 26, cy + 42);
        ctx.letterSpacing = '0px'; ctx.textAlign = 'right'; ctx.font = `400 18px ${UI}`;
        ctx.fillText('now', cx + cw - 24, cy + 42);
        ctx.textAlign = 'left'; ctx.font = `600 27px ${UI}`; ctx.fillStyle = 'rgba(240,244,255,0.98)';
        ctx.fillText('1 new voicemail from You', cx + 26, cy + 88);
        ctx.font = `400 23px ${UI}`; ctx.fillStyle = 'rgba(205,216,238,0.85)';
        ctx.fillText('Received: Tomorrow, 3:14 AM', cx + 26, cy + 126);
        ctx.restore();
      }
    } else {
      // the voicemail player
      ctx.font = `600 30px ${UI}`; ctx.fillStyle = 'rgba(236,241,252,0.95)';
      ctx.fillText('Voicemail', 0, -330);
      rrect(ctx, -195, -280, 390, 128, 26); ctx.fillStyle = 'rgba(36,44,60,0.85)'; ctx.fill();
      ctx.textAlign = 'left'; ctx.font = `600 30px ${UI}`; ctx.fillStyle = 'rgba(240,244,255,0.98)';
      ctx.fillText('You', -170, -228);
      ctx.font = `400 21px ${UI}`; ctx.fillStyle = 'rgba(205,216,238,0.8)';
      ctx.fillText('Tomorrow, 3:14 AM  ·  0:41', -170, -188);
      ctx.save(); ctx.translate(-200, 40);
      waveStrip(ctx, t, 0, 0, 400, 90, { bar: 4, gap: 3, span: 2.2 });
      ctx.restore();
      const el = t - TL.timeOf(TL.EVENTS.play);
      ctx.fillStyle = 'rgba(205,216,238,0.25)'; ctx.fillRect(-195, 190, 390, 4);
      ctx.fillStyle = 'rgba(236,241,252,0.9)'; ctx.fillRect(-195, 190, 390 * clamp(el / 41), 4);
      ctx.font = `400 19px ${UI}`; ctx.fillStyle = 'rgba(205,216,238,0.7)';
      ctx.textAlign = 'left'; ctx.fillText(mmss(el), -195, 230);
      ctx.textAlign = 'right'; ctx.fillText('-' + mmss(41 - el), 195, 230);
      // pause glyph
      ctx.fillStyle = 'rgba(236,241,252,0.95)';
      ctx.fillRect(-26, 290, 16, 56); ctx.fillRect(10, 290, 16, 56);
    }
    ctx.globalAlpha = 1;
  }
  ctx.restore();
}

// ---------------------------------------------------------------- the front door (flat set)
const DOOR = { x0: -200, x1: 200, y0: -430, y1: 400 };
function feet(b) {
  // two shadows arrive, one after the other; they never leave
  return [smooth(ramp(b, TL.EVENTS.feet, TL.EVENTS.feet + 0.8)), smooth(ramp(b, TL.EVENTS.feet + 0.7, TL.EVENTS.feet + 1.5))];
}
function knockShake(b) {
  let x = 0, y = 0;
  for (const k of TL.EVENTS.knocks) {
    const u = b - k;
    if (u > 0 && u < 0.5) { const e = Math.exp(-u * 10); x += Math.sin(u * 90) * 5 * e; y += Math.cos(u * 70) * 2.5 * e; }
  }
  return [x, y];
}
function gapLight(b) {
  // the light under the door; dies just before the cut to the title
  const k = TL.EVENTS.knocks.reduce((m, kb) => m + (b > kb && b < kb + 0.25 ? 0.35 : 0), 0);
  return (1 - k) * (1 - smooth(ramp(b, 85.1, 85.35)));
}
function drawDoor(ctx, b) {
  const { x0, x1, y0, y1 } = DOOR;
  const gl = gapLight(b);
  const [sx, sy] = b >= 76 ? knockShake(b) : [0, 0];
  // floor
  const fg = ctx.createLinearGradient(0, y1, 0, y1 + 500);
  fg.addColorStop(0, `rgba(${30 * gl + 8},${36 * gl + 9},${30 * gl + 9},1)`); fg.addColorStop(1, '#050607');
  ctx.fillStyle = fg; ctx.fillRect(-2000, y1, 4000, 800);
  // light spilling across the floor
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  const sp = ctx.createRadialGradient(0, y1 + 4, 10, 0, y1 + 4, 520);
  sp.addColorStop(0, css(HALL, 0.20 * gl)); sp.addColorStop(1, css(HALL, 0));
  ctx.fillStyle = sp; ctx.save(); ctx.scale(1, 0.32); ctx.fillRect(-700, (y1 - 40) / 0.32, 1400, 600 / 0.32); ctx.restore();
  ctx.restore();
  // wall
  const wg = ctx.createRadialGradient(0, y1, 50, 0, y1 - 200, 1300);
  wg.addColorStop(0, `rgb(${Math.round(20 + 16 * gl)},${Math.round(22 + 20 * gl)},${Math.round(22 + 16 * gl)})`); wg.addColorStop(1, '#0a0b0d');
  ctx.fillStyle = wg; ctx.fillRect(-2000, -1200, 4000, 1200 + y1);
  // coat on a hook, keys on a small shelf
  ctx.fillStyle = '#08090b';
  ctx.beginPath(); ctx.moveTo(-560, -170); ctx.quadraticCurveTo(-640, 60, -600, 250); ctx.lineTo(-470, 250); ctx.quadraticCurveTo(-450, 40, -520, -170); ctx.closePath(); ctx.fill();
  ctx.fillRect(-548, -190, 16, 26);
  ctx.fillStyle = '#101216'; ctx.fillRect(420, -40, 220, 14);
  // frame
  ctx.fillStyle = '#1c1f24'; ctx.fillRect(x0 - 34, y0 - 34, x1 - x0 + 68, y1 - y0 + 34);
  ctx.fillStyle = 'rgba(190,210,195,0.10)'; ctx.fillRect(x0 - 34, y0 - 34, x1 - x0 + 68, 3); ctx.fillRect(x0 - 34, y0 - 34, 3, y1 - y0 + 34);
  // door (it trembles on the knocks)
  ctx.save(); ctx.translate(sx, sy);
  const dg = ctx.createLinearGradient(x0, 0, x1, 0);
  dg.addColorStop(0, '#16181c'); dg.addColorStop(1, '#101215');
  ctx.fillStyle = dg; ctx.fillRect(x0, y0, x1 - x0, y1 - y0 - 6);
  ctx.strokeStyle = 'rgba(200,220,205,0.07)'; ctx.lineWidth = 3;
  ctx.strokeRect(x0 + 40, y0 + 50, x1 - x0 - 80, 300); ctx.strokeRect(x0 + 40, y0 + 400, x1 - x0 - 80, 330);
  // knob, chain
  ctx.beginPath(); ctx.arc(x1 - 52, 20, 15, 0, Math.PI * 2); ctx.fillStyle = '#1d2026'; ctx.fill();
  ctx.beginPath(); ctx.arc(x1 - 56, 16, 5, 0, Math.PI * 2); ctx.fillStyle = 'rgba(200,220,200,0.18)'; ctx.fill();
  ctx.strokeStyle = 'rgba(160,170,160,0.16)'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(x1 - 40, -100); ctx.quadraticCurveTo(x1 - 10, -40, x1 + 18, -96); ctx.stroke();
  ctx.restore();
  // the gap under the door, and whatever is standing in it
  ctx.fillStyle = css(HALL, 0.95 * gl); ctx.fillRect(x0, y1 - 6, x1 - x0, 7);
  const [fl, fr] = feet(b);
  ctx.fillStyle = 'rgba(4,5,6,0.96)';
  if (fl > 0) ctx.fillRect(-92, y1 - 6, 70 * fl, 7);
  if (fr > 0) ctx.fillRect(22, y1 - 6, 70 * fr, 7);
}

// ---------------------------------------------------------------- the corridor (through the peephole)
const F = 560;
const proj = (X, Y, Z) => [CX + X / Z * F, CY - 40 + Y / Z * F];
function quad(ctx, pts, fill) {
  ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
  ctx.fillStyle = fill; ctx.fill();
}
function drawCorridor(ctx, b, P) {
  const L = TL.lightOn(b);
  const hum = L * (0.9 + 0.1 * Math.sin(b * 37.1) * Math.sin(b * 11.3));
  const Zn = 0.9, Zf = 14, Xw = 1.05, Yf = 1, Yc = -0.85;
  const sh = (v) => Math.round(v);
  const wall = (a) => `rgb(${sh(14 + 46 * a * hum)},${sh(16 + 56 * a * hum)},${sh(14 + 44 * a * hum)})`;
  // end wall, ceiling, floor, side walls
  ctx.fillStyle = '#020303'; ctx.fillRect(0, 0, W, H);
  const fogTo = (z) => 1 - 0.75 * (z - Zn) / (Zf - Zn);
  for (let z = Zn; z < Zf; z += 0.5) {
    const z2 = z + 0.5, f = fogTo(z);
    quad(ctx, [proj(-Xw, Yf, z), proj(Xw, Yf, z), proj(Xw, Yf, z2), proj(-Xw, Yf, z2)], wall(0.55 * f));      // floor
    quad(ctx, [proj(-Xw, Yc, z), proj(Xw, Yc, z), proj(Xw, Yc, z2), proj(-Xw, Yc, z2)], wall(0.35 * f));      // ceiling
    quad(ctx, [proj(-Xw, Yc, z), proj(-Xw, Yf, z), proj(-Xw, Yf, z2), proj(-Xw, Yc, z2)], wall(0.8 * f));     // left wall
    quad(ctx, [proj(Xw, Yc, z), proj(Xw, Yf, z), proj(Xw, Yf, z2), proj(Xw, Yc, z2)], wall(0.75 * f));        // right wall
  }
  quad(ctx, [proj(-Xw, Yc, Zf), proj(Xw, Yc, Zf), proj(Xw, Yf, Zf), proj(-Xw, Yf, Zf)], wall(0.3));
  // carpet runner
  quad(ctx, [proj(-0.32, Yf, Zn), proj(0.32, Yf, Zn), proj(0.32, Yf, Zf), proj(-0.32, Yf, Zf)], `rgba(10,12,10,${0.55})`);
  // doors along the walls
  for (const [side, z] of [[-1, 2.6], [1, 4.4], [-1, 6.8], [1, 9.2], [-1, 11.6]]) {
    const X = side * Xw;
    quad(ctx, [proj(X, -0.55, z), proj(X, Yf, z), proj(X, Yf, z + 0.85), proj(X, -0.55, z + 0.85)], `rgb(${sh(8 + 22 * hum * fogTo(z))},${sh(9 + 24 * hum * fogTo(z))},${sh(9 + 20 * hum * fogTo(z))})`);
    const [nx, ny] = proj(X, -0.38, z + 0.42);
    ctx.fillStyle = `rgba(200,210,190,${0.25 * hum * fogTo(z)})`; ctx.fillRect(nx - 6 / z * 3, ny, 12 / z * 3, 8 / z * 3);
  }
  // ceiling panels
  for (let z = 1.6; z < Zf; z += 2.1) {
    quad(ctx, [proj(-0.32, Yc, z), proj(0.32, Yc, z), proj(0.32, Yc, z + 0.7), proj(-0.32, Yc, z + 0.7)],
      css(HALL, (0.08 + 0.92 * hum) * fogTo(z)));
    const [gx, gy] = proj(0, Yc + 0.02, z + 0.35);
    P.push(gx, gy, 260 / z, 0, HALL, 0.25 * hum * fogTo(z), 0.03, 0.8);   // core must be > 0
  }
  // exit sign: the only light that never goes out
  const [ex0, ey0] = proj(-0.2, -0.72, Zf), [ex1, ey1] = proj(0.2, -0.6, Zf);
  ctx.fillStyle = 'rgba(190,40,30,0.95)'; ctx.fillRect(ex0, ey0, ex1 - ex0, ey1 - ey0);
  P.push((ex0 + ex1) / 2, (ey0 + ey1) / 2, 46, 0, RED, 0.35, 0.03, 0.5);
  // the figure
  const d = TL.figureDepth(b);
  if (d !== null) {
    const Z = lerp(1.0, 13.4, d);
    const [fx0, fy0] = proj(-0.26, -0.7, Z), [fx1, fy1] = proj(0.26, Yf, Z);
    const [hx, hy] = proj(0, -0.79, Z);
    const hr = 0.115 / Z * F;
    const lit = 0.2 + 0.8 * L;
    ctx.fillStyle = `rgba(1,1,1,${0.97})`;
    // shoulders to feet, a little too narrow at the waist, perfectly still
    ctx.beginPath();
    const w = fx1 - fx0, h = fy1 - fy0;
    ctx.moveTo(fx0 + w * 0.06, fy0 + h * 0.06);
    ctx.quadraticCurveTo(fx0 + w * 0.5, fy0 - h * 0.02, fx1 - w * 0.06, fy0 + h * 0.06);
    ctx.lineTo(fx1 - w * 0.2, fy0 + h * 0.5); ctx.lineTo(fx1 - w * 0.28, fy1);
    ctx.lineTo(fx0 + w * 0.28, fy1); ctx.lineTo(fx0 + w * 0.2, fy0 + h * 0.5);
    ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.ellipse(hx, hy + hr * 0.1, hr * 0.86, hr, 0, 0, Math.PI * 2); ctx.fill();
    // a rim of light on the edge facing the panels, so the shape reads even in the dark
    ctx.strokeStyle = css(L > 0.5 ? HALL : RED, 0.10 * lit + (L > 0.5 ? 0 : 0.10)); ctx.lineWidth = Math.max(1, 3 / Z);
    ctx.beginPath(); ctx.ellipse(hx, hy + hr * 0.1, hr * 0.86, hr, 0, Math.PI * 1.05, Math.PI * 1.95); ctx.stroke();
  }
  // dark wash when the light is out
  if (L < 1) { ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillRect(0, 0, W, H); }
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

function timestamp(ov, b, a = 1) {
  const s = b >= TL.EVENTS.minute ? '3:14 AM' : '3:13 AM';
  const pop = b >= TL.EVENTS.minute ? Math.exp(-(b - TL.EVENTS.minute) * 2) : 0;
  label(ov, s, PORTRAIT ? 70 : 90, PORTRAIT ? 230 : 96, 26, `rgba(${Math.round(lerp(200, 255, pop))},${Math.round(lerp(214, 255, pop))},${Math.round(lerp(236, 255, pop))},0.85)`, a, 'left', 0.12, 300);
}
function bottomBar(ov, t, b, a = 1) {
  // the message is still playing in your hand: a thin strip of it at the bottom
  const w = PORTRAIT ? 700 : 760, y = PORTRAIT ? 1495 : 1000;
  waveStrip(ov, t, CX - w / 2, y, w, 22, { bar: 3, gap: 3, span: 3, alpha: 0.75 * a, playhead: false });
}

function shotPhone(b, t, S, set, ov, P) {
  const u = ramp(b, 0, 16);
  const z = (PORTRAIT ? 1.18 : 0.92) + (PORTRAIT ? 0.14 : 0.22) * sine(u);
  const cam = camera(0, (PORTRAIT ? 150 : 70) - 50 * sine(u), z);
  const on = smooth(ramp(b, TL.EVENTS.screenOn, TL.EVENTS.screenOn + 0.3));
  const [gx, gy] = cam.s(0, 0);
  S.bg.glow = [gx, gy, 760 * z, 0.28 * on + 0.01];
  S.bg.glowCol = [0.55, 0.68, 0.95];
  cam.apply(set);
  set.save();
  set.strokeStyle = '#08090c'; set.lineWidth = 12; set.lineCap = 'round';
  set.beginPath(); set.moveTo(0, PH / 2); set.bezierCurveTo(0, PH / 2 + 160, -380, PH / 2 + 60, -520, PH / 2 + 300); set.stroke();
  set.rotate(0.03);
  const playing = b >= TL.EVENTS.play;
  drawPhone(set, b, t, on, playing ? 'player' : 'lock');
  set.restore();
  dust(P, b, 120, 11, [-700, -700, 700, 700], 2.2, (x, y) => (0.03 + 0.5 * on) * Math.exp(-(x * x + y * y) / 300000), COLD, cam);
  caption(ov, t, CX, PORTRAIT ? 1480 : 1040, { size: PORTRAIT ? 40 : 32, maxW: PORTRAIT ? 820 : 1300 });
}

function shotWave(b, t, S, set, ov, P) {
  S.bg.glow = [CX, CY - 40, PORTRAIT ? 900 : 1000, 0.07 + 0.10 * peakAround(t - 0.05, 0.1)];
  S.bg.glowCol = [0.5, 0.6, 0.85];
  const el = t - TL.timeOf(TL.EVENTS.play);
  const top = PORTRAIT ? 250 : 110;
  label(ov, 'VOICEMAIL  ·  FROM: YOU', PORTRAIT ? 70 : 110, top, 20, 'rgba(200,214,240,0.7)', 1, 'left', 0.25);
  label(ov, 'RECEIVED: TOMORROW, 3:14 AM', PORTRAIT ? 70 : 110, top + 38, 20, 'rgba(200,214,240,0.45)', 1, 'left', 0.25);
  label(ov, `${mmss(el)} / 0:41`, PORTRAIT ? W - 70 : W - 110, top, 22, 'rgba(200,214,240,0.7)', 1, 'right', 0.12, 400);
  const ww = PORTRAIT ? 960 : 1640;
  waveStrip(ov, t, CX - ww / 2, CY - (PORTRAIT ? 160 : 70), ww, PORTRAIT ? 200 : 230, { bar: 5, gap: 4, span: 3.2, playhead: true });
  caption(ov, t, CX, CY + (PORTRAIT ? 260 : 300), { maxW: PORTRAIT ? 900 : 1500, size: PORTRAIT ? 66 : 70 });
  dust(P, b, 90, 21, [0, 0, W, H], 1.6, () => 0.10);
}

function doorShot(b, t, S, set, ov, P, second) {
  const u = second ? ramp(b, 76, 86) : ramp(b, 32, 52);
  const z = second ? lerp(1.16, 1.3, sine(u)) * (PORTRAIT ? 1.15 : 1) : lerp(0.92, 1.1, sine(u)) * (PORTRAIT ? 1.1 : 1);
  const cam = camera(0, PORTRAIT ? 170 : -20, z);
  const gl = gapLight(b);
  const [lx, ly] = cam.s(0, DOOR.y1);
  S.bg.glow = [lx, ly, 640 * z, 0.22 * gl];
  S.bg.glow2 = [CX - 500, CY - 300, 900, 0.035]; S.bg.glow2Col = [0.5, 0.58, 0.75];   // the faintest street light, somewhere left
  S.bg.glowCol = HALL;
  const [px, py] = cam.s(0, -140);
  cam.apply(set);
  drawDoor(set, b);
  // the peephole: a pinprick of the hallway's light
  P.push(px, py, 26 * z, 0, HALL, 0.9 * gl, 0.12, 0.6);
  // dust shaken loose by the knocks
  if (second) {
    for (const k of TL.EVENTS.knocks) {
      const kt = b - k;
      if (kt < 0 || kt > 6) continue;
      for (let i = 0; i < 26; i++) {
        const h1 = hash2(i, k), h2 = hash2(i, k + 1);
        const x = DOOR.x0 - 30 + h1 * (DOOR.x1 - DOOR.x0 + 60);
        const y = DOOR.y0 - 30 + kt * (60 + 90 * h2) + Math.sin(kt * 2 + i) * 6;
        const [sx, sy] = cam.s(x, y);
        P.push(sx, sy, 7 * z, 0, [0.6, 0.65, 0.62], 0.35 * (1 - kt / 6), 0.25, 0.2);
      }
    }
    S.shake = knockShake(b).map((v) => v * 0.6);
  }
  dust(P, b, 140, 31, [-900, -600, 900, 600], 2.0, (x, y) => gl * 0.5 * Math.exp(-((x * x) / 160000 + ((y - DOOR.y1) ** 2) / 50000)), HALL, cam);
  timestamp(ov, b);
  if (!second || b < 81) bottomBar(ov, t, b);
  else bottomBar(ov, t, b, 1 - smooth(ramp(b, 85, 86)));     // flat: the whisper isn't coming from the phone
  caption(ov, t, CX, PORTRAIT ? 1400 : 900, { maxW: PORTRAIT ? 900 : 1300, size: PORTRAIT ? 60 : 58 });
}

function shotPeep(b, t, S, set, ov, P) {
  const r = PORTRAIT ? 500 : 470;
  S.lens = [CX, CY - 20, r, 1.12];
  set.setTransform(1, 0, 0, 1, 0, 0);
  drawCorridor(set, b, P);
  dust(P, b, 110, 41, [CX - 600, CY - 500, CX + 600, CY + 500], 1.8, () => 0.25 * TL.lightOn(b), HALL);
  timestamp(ov, b, 0.7);
  bottomBar(ov, t, b);
  caption(ov, t, CX, PORTRAIT ? 1340 : 970, { maxW: PORTRAIT ? 900 : 1400, size: PORTRAIT ? 62 : 54 });
  S.grain = 0.04;
}

function shotTitle(b, t, S, set, ov, P) {
  S.bg.glow = [CX, CY, PORTRAIT ? 800 : 900, 0.05];
  S.bg.glowCol = [0.5, 0.6, 0.55];
  const a = smooth(ramp(b, 86, 86.6));
  ov.save();
  ov.textAlign = 'center'; ov.globalAlpha = a;
  ov.font = `${PORTRAIT ? 104 : 150}px ${SERIF}`; ov.letterSpacing = `${PORTRAIT ? 8 : 18}px`;
  ov.fillStyle = 'rgba(232,237,240,0.97)';
  ov.fillText('ONE NEW VOICEMAIL', CX + (PORTRAIT ? 4 : 9), CY);
  ov.restore();
  label(ov, 'RECEIVED TOMORROW, 3:14 A.M.', CX, CY + (PORTRAIT ? 90 : 100), PORTRAIT ? 24 : 24, 'rgba(200,214,226,0.65)', smooth(ramp(b, 87, 87.6)), 'center', 0.3, 500);
  dust(P, b, 80, 51, [0, 0, W, H], 1.6, () => 0.10);
}

function shotRecord(b, t, S, set, ov, P) {
  if (PORTRAIT) { ov.translate(CX, CY); ov.scale(1.45, 1.45); ov.translate(-CX, -CY); }
  const K = PORTRAIT ? 1.45 : 1, kx = (x) => CX + (x - CX) * K, ky = (y) => CY + (y - CY) * K;
  const el = t - TL.timeOf(TL.EVENTS.record);
  const a = smooth(ramp(b, 91, 91.5));
  const y0 = CY - 110;
  label(ov, 'NEW VOICEMAIL', CX, y0 - 110, 20, 'rgba(200,214,240,0.6)', a, 'center', 0.3);
  label(ov, 'To: You', CX, y0 - 50, 40, 'rgba(236,240,250,0.95)', a, 'center', 0, 500);
  label(ov, 'Deliver: Yesterday, 3:14 AM', CX, y0 - 6, 24, 'rgba(205,216,238,0.7)', a, 'center', 0, 400);
  // the red dot, breathing
  const pulse = 0.75 + 0.25 * Math.sin(el * 4.2);
  P.push(kx(CX - 92), ky(y0 + 92), 46 * K, 5, [RED[0] * 1.5, RED[1] * 1.5, RED[2] * 1.5], a, 0.24, 0.5 * pulse);
  label(ov, 'Recording', CX - 62, y0 + 101, 28, 'rgba(240,244,250,0.95)', a, 'left', 0, 500);
  label(ov, mmss(el), CX + 110, y0 + 101, 28, 'rgba(240,244,250,0.6)', a, 'left', 0, 300);
  // the mic hears almost nothing. Then one breath.
  const bw = PORTRAIT ? 620 : 900, by = y0 + 220;
  ov.save(); ov.globalAlpha = a;
  const n = Math.floor(bw / 7);
  for (let i = 0; i < n; i++) {
    const tt = t + (i / n - 1) * 2.4;
    const br = TL.timeOf(TL.EVENTS.breath);
    const e = tt > br && tt < br + 1.1 ? Math.sin(Math.PI * (tt - br) / 1.1) * (0.6 + 0.4 * hash2(i, 9)) : 0;
    const amp = 1.5 + 2 * hash2(i, Math.floor(tt * 30)) + e * 70;
    ov.fillStyle = 'rgba(240,244,250,0.75)';
    ov.fillRect(CX - bw / 2 + i * 7, by - amp, 4, amp * 2);
  }
  ov.restore();
  S.bg.glow = [kx(CX - 92), ky(y0 + 92), 500, 0.05 * a];
  S.bg.glowCol = RED;
}

function shotBlack(b, t, S) { S.grain = 0.0; }

const SHOT_FN = {
  phone: shotPhone, wave: shotWave, door: (b, t, S, s, o, P) => doorShot(b, t, S, s, o, P, false),
  peephole: shotPeep, door2: (b, t, S, s, o, P) => doorShot(b, t, S, s, o, P, true),
  title: shotTitle, record: shotRecord, black: shotBlack,
};

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
    // the peephole flicker is a hard cut too: no blending light into dark
    const b = TL.beatOf(tc), bt = TL.beatOf(t);
    if (TL.lightOn(b) !== TL.lightOn(bt)) t = tc;
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
  G.endFrame(Math.floor(seedT * TL.FPS) % 9973, grain, pixels);
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
