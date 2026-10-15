// THE STILLNESS, PART 3: THE SEVEN MINUTES — renderer. Every frame is a pure function of time.
// Shares its sets and helpers with Part 2 (voicemail/) and its world clock with Part 1 (the-offer/).
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
const AMBER = [1.0, 0.56, 0.17];      // you (Part 1)
const ICE = [0.60, 0.86, 1.0];        // the others (Part 1)
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
// what the recording hears: you, from the moment it starts
function phoneSample(t) {
  if (t < TL.timeOf(TL.EVENTS.record)) return 0;
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
  const sys = false, wh = l.fx === 'p2w';
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

// ---------------------------------------------------------------- you (Part 1's amber dot)
function pushAmber(P, x, y, b, scale = 1, alpha = 1, trailFn = null) {
  const breath = 0.85 + 0.15 * Math.sin(b * Math.PI * 0.5);
  if (trailFn) {
    for (let k = 10; k >= 1; k--) {
      const [tx, ty] = trailFn(b - k * 0.07);
      P.push(tx, ty, 26 * scale, 0, AMBER, alpha * 0.22 * (1 - k / 11), 0.18, 0.4);
    }
  }
  P.push(x, y, 70 * scale, 5, [AMBER[0] * 1.7, AMBER[1] * 1.7, AMBER[2] * 1.7], alpha, 0.11, 0.5 * breath);
}
function path(pts, b) {
  if (b <= pts[0][0]) return [pts[0][1], pts[0][2]];
  const n = pts.length;
  if (b >= pts[n - 1][0]) return [pts[n - 1][1], pts[n - 1][2]];
  let i = 0;
  while (b > pts[i + 1][0]) i++;
  const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(n - 1, i + 2)];
  const dt = p2[0] - p1[0], u = (b - p1[0]) / dt;
  const tan = (a, c) => [(c[1] - a[1]) / Math.max(1e-6, c[0] - a[0]) * dt, (c[2] - a[2]) / Math.max(1e-6, c[0] - a[0]) * dt];
  const m1 = i === 0 ? [0, 0] : tan(p0, p2), m2 = i + 2 >= n ? [0, 0] : tan(p1, p3);
  const u2 = u * u, u3 = u2 * u;
  const h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
  return [h00 * p1[1] + h10 * m1[0] + h01 * p2[1] + h11 * m2[0], h00 * p1[2] + h10 * m1[1] + h01 * p2[2] + h11 * m2[1]];
}

// ---------------------------------------------------------------- phone
const PW = 470, PH = 960;
function drawPhone(ctx, b, on) {
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
  ctx.globalAlpha = on;
  ctx.textAlign = 'center';
  // Part 1's app, at the moment after: accepted
  ctx.font = `600 17px ${UI}`; ctx.letterSpacing = '5px'; ctx.fillStyle = 'rgba(200,215,240,0.6)';
  ctx.fillText('THE STILLNESS', 0, -320);
  ctx.letterSpacing = '0px';
  ctx.font = `200 132px ${UI}`; ctx.fillStyle = 'rgba(232,240,255,0.94)';
  ctx.fillText(TL.clockText(b), 0, -170);
  const k = smooth(ramp(b, TL.EVENTS.accepted, TL.EVENTS.accepted + 0.8));
  ctx.globalAlpha = on * k;
  ctx.font = `48px ${SERIF}`; ctx.fillStyle = 'rgba(236,241,252,0.95)';
  ctx.fillText('Offer accepted.', 0, -60);
  ctx.font = `400 22px ${UI}`; ctx.fillStyle = 'rgba(190,205,232,0.7)';
  ctx.fillText('100 of 100 holders', 0, -14);
  ctx.globalAlpha = on;
  // the hold-to-freeze button, pressed on "stopped"
  const press = smooth(ramp(b, TL.FREEZE - 0.4, TL.FREEZE));
  rrect(ctx, -170, 170, 340, 84, 42);
  ctx.fillStyle = `rgba(226,236,255,${0.12 + 0.82 * press})`; ctx.fill();
  ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(210,222,245,0.5)'; ctx.stroke();
  ctx.font = `600 26px ${UI}`; ctx.fillStyle = press > 0.5 ? '#0b0f17' : 'rgba(226,236,255,0.9)';
  ctx.fillText(press > 0.5 ? 'Holding' : 'Hold to stop', 0, 222);
  rrect(ctx, -70, 430, 140, 7, 4); ctx.fillStyle = 'rgba(220,230,250,0.5)'; ctx.fill();
  ctx.globalAlpha = 1;
  ctx.restore();
}

// ---------------------------------------------------------------- your door, from inside (Part 2's set, frozen)
const DOOR = { x0: -200, x1: 200, y0: -430, y1: 400 };
function drawDoorInside(ctx, b) {
  const { x0, x1, y0, y1 } = DOOR;
  const open = ease(ramp(b, TL.EVENTS.doorOpen, TL.EVENTS.doorOpen + 3));
  const fg = ctx.createLinearGradient(0, y1, 0, y1 + 500);
  fg.addColorStop(0, 'rgb(38,45,39)'); fg.addColorStop(1, '#050607');
  ctx.fillStyle = fg; ctx.fillRect(-2000, y1, 4000, 800);
  const wg = ctx.createRadialGradient(0, y1, 50, 0, y1 - 200, 1300);
  wg.addColorStop(0, 'rgb(36,42,38)'); wg.addColorStop(1, '#0a0b0d');
  ctx.fillStyle = wg; ctx.fillRect(-2000, -1200, 4000, 1200 + y1);
  ctx.fillStyle = '#08090b';
  ctx.beginPath(); ctx.moveTo(-560, -170); ctx.quadraticCurveTo(-640, 60, -600, 250); ctx.lineTo(-470, 250); ctx.quadraticCurveTo(-450, 40, -520, -170); ctx.closePath(); ctx.fill();
  ctx.fillRect(-548, -190, 16, 26);
  ctx.fillStyle = '#1c1f24'; ctx.fillRect(x0 - 34, y0 - 34, x1 - x0 + 68, y1 - y0 + 34);
  // the opening: hallway light pours in through the widening gap
  if (open > 0) {
    ctx.fillStyle = css(HALL, 0.9); ctx.fillRect(x0, y0, (x1 - x0) * open, y1 - y0);
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    const sp = ctx.createLinearGradient(0, y1, 0, y1 + 420);
    sp.addColorStop(0, css(HALL, 0.35 * open)); sp.addColorStop(1, css(HALL, 0));
    ctx.fillStyle = sp;
    ctx.beginPath(); ctx.moveTo(x0, y1); ctx.lineTo(x0 + (x1 - x0) * open, y1); ctx.lineTo(x0 + (x1 - x0) * open * 1.9 + 120, y1 + 420); ctx.lineTo(x0 - 120, y1 + 420); ctx.fill();
    ctx.restore();
  }
  // the door panel swings in (foreshortened as it turns toward us)
  const w = (x1 - x0) * (1 - open * 0.86);
  const px = x1 - w;
  const dg = ctx.createLinearGradient(px, 0, x1, 0);
  dg.addColorStop(0, '#16181c'); dg.addColorStop(1, '#101215');
  ctx.fillStyle = dg;
  ctx.beginPath();
  ctx.moveTo(px, y0 - open * 30); ctx.lineTo(x1, y0); ctx.lineTo(x1, y1 - 6); ctx.lineTo(px, y1 - 6 + open * 30); ctx.closePath(); ctx.fill();
  if (open < 0.5) {
    ctx.strokeStyle = 'rgba(200,220,205,0.07)'; ctx.lineWidth = 3;
    ctx.strokeRect(px + 40 * (w / 400), y0 + 50, w - 80 * (w / 400), 300); ctx.strokeRect(px + 40 * (w / 400), y0 + 400, w - 80 * (w / 400), 330);
    ctx.beginPath(); ctx.arc(px + w - 52 * (w / 400), 20, 15, 0, Math.PI * 2); ctx.fillStyle = '#1d2026'; ctx.fill();
  }
  // the gap under the door: frozen, no feet yet (they're yours, later)
  if (open < 0.02) { ctx.fillStyle = css(HALL, 0.95); ctx.fillRect(x0, y1 - 6, x1 - x0, 7); }
}

// ---------------------------------------------------------------- the hallway, frozen, full of the others
const F = 560;
let VPY = 0;
const proj = (X, Y, Z) => [CX + X / Z * F, VPY + Y / Z * F];
function quad(ctx, pts, fill) {
  ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
  ctx.fillStyle = fill; ctx.fill();
}
function silhouette(ctx, X, Z, turn, Yf) {
  // the Part 2 figure: too narrow at the waist, perfectly still. `turn` slides the head toward us.
  const [fx0, fy0] = proj(X - 0.24, -0.7, Z), [fx1, fy1] = proj(X + 0.24, Yf, Z);
  const [hx, hy] = proj(X - Math.sign(X) * 0.06 * turn, -0.79, Z);
  const hr = 0.11 / Z * F;
  const w = fx1 - fx0, h = fy1 - fy0;
  ctx.fillStyle = 'rgba(2,2,2,0.97)';
  ctx.beginPath();
  ctx.moveTo(fx0 + w * 0.06, fy0 + h * 0.06);
  ctx.quadraticCurveTo(fx0 + w * 0.5, fy0 - h * 0.02, fx1 - w * 0.06, fy0 + h * 0.06);
  ctx.lineTo(fx1 - w * 0.2, fy0 + h * 0.5); ctx.lineTo(fx1 - w * 0.28, fy1);
  ctx.lineTo(fx0 + w * 0.28, fy1); ctx.lineTo(fx0 + w * 0.2, fy0 + h * 0.5);
  ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.ellipse(hx, hy + hr * 0.1, hr * 0.86, hr, 0, 0, Math.PI * 2); ctx.fill();
  return [hx, hy + hr * 2.6, hr];
}
function drawHall(ctx, b, P) {
  VPY = CY - 80;
  const Zn = 0.62, Zf = 26, Xw = 1.05, Yf = 1, Yc = -0.85;   // starts close enough to fill 9:16
  const sh = (v) => Math.round(v);
  const fogTo = (z) => Math.max(0, 1 - 0.9 * (z - Zn) / (Zf - Zn));
  const wall = (a) => `rgb(${sh(12 + 40 * a)},${sh(14 + 48 * a)},${sh(12 + 38 * a)})`;
  ctx.fillStyle = '#020303'; ctx.fillRect(0, 0, W, H);
  for (let z = Zn; z < Zf; z += 0.5) {
    const z2 = z + 0.5, f = fogTo(z);
    quad(ctx, [proj(-Xw, Yf, z), proj(Xw, Yf, z), proj(Xw, Yf, z2), proj(-Xw, Yf, z2)], wall(0.55 * f));
    quad(ctx, [proj(-Xw, Yc, z), proj(Xw, Yc, z), proj(Xw, Yc, z2), proj(-Xw, Yc, z2)], wall(0.3 * f));
    quad(ctx, [proj(-Xw, Yc, z), proj(-Xw, Yf, z), proj(-Xw, Yf, z2), proj(-Xw, Yc, z2)], wall(0.8 * f));
    quad(ctx, [proj(Xw, Yc, z), proj(Xw, Yf, z), proj(Xw, Yf, z2), proj(Xw, Yc, z2)], wall(0.75 * f));
  }
  quad(ctx, [proj(-0.32, Yf, Zn), proj(0.32, Yf, Zn), proj(0.32, Yf, Zf), proj(-0.32, Yf, Zf)], 'rgba(10,12,10,0.55)');
  // the lights froze mid-flicker: some on, some off, forever
  for (let z = 1.6, k = 0; z < Zf; z += 2.1, k++) {
    const on = [1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0][k % 12];
    quad(ctx, [proj(-0.32, Yc, z), proj(0.32, Yc, z), proj(0.32, Yc, z + 0.7), proj(-0.32, Yc, z + 0.7)], css(HALL, (0.06 + 0.9 * on) * fogTo(z)));
    if (on) { const [gx, gy] = proj(0, Yc + 0.02, z + 0.35); P.push(gx, gy, 240 / z, 0, HALL, 0.22 * fogTo(z), 0.03, 0.8); }
  }
  // doors, each with someone standing at it, facing it
  const turn = smooth(ramp(b, TL.EVENTS.turn, TL.EVENTS.turn + 1.2));
  const others = [...TL.OTHERS].sort((a, c) => c[1] - a[1]);      // far to near
  for (const [side, z] of others) {
    const X = side * Xw, f = fogTo(z);
    quad(ctx, [proj(X, -0.55, z), proj(X, Yf, z), proj(X, Yf, z + 0.85), proj(X, -0.55, z + 0.85)], `rgb(${sh(8 + 20 * f)},${sh(9 + 22 * f)},${sh(9 + 18 * f)})`);
    const [nx, ny] = proj(X, -0.38, z + 0.42);
    ctx.fillStyle = `rgba(200,210,190,${0.25 * f})`; ctx.fillRect(nx - 9 / z, ny, 18 / z, 12 / z);
    const [dx, dy, hr] = silhouette(ctx, side * 0.72, z + 0.42, turn, Yf);
    // their light: Part 1's ice blue, at the chest. On the turn, every one of them flares at once.
    const flare = Math.exp(-Math.max(0, b - TL.EVENTS.turn) * 1.5) * (b >= TL.EVENTS.turn ? 1 : 0);
    P.push(dx, dy, Math.max(6, hr * 2.2), 3, [ICE[0] * 0.85, ICE[1] * 0.92, ICE[2]], f * (0.75 + 0.6 * flare), 1, 0.4 + 1.6 * flare, 1 / 4.5, 0.05);
  }
}

// ---------------------------------------------------------------- your door, from the hallway (Part 2's other side)
function drawDoorOutside(ctx, b) {
  const { x0, x1, y0, y1 } = DOOR;
  const live = b >= TL.RESUME;
  const hum = live ? 0.9 + 0.1 * Math.sin(b * 37.1) * Math.sin(b * 11.3) : 0.75;
  const wg = ctx.createLinearGradient(0, -1200, 0, y1);
  wg.addColorStop(0, `rgb(${Math.round(46 * hum)},${Math.round(56 * hum)},${Math.round(46 * hum)})`); wg.addColorStop(1, `rgb(${Math.round(24 * hum)},${Math.round(29 * hum)},${Math.round(25 * hum)})`);
  ctx.fillStyle = wg; ctx.fillRect(-2000, -1200, 4000, 1200 + y1);
  ctx.fillStyle = `rgb(${Math.round(20 * hum)},${Math.round(24 * hum)},${Math.round(20 * hum)})`; ctx.fillRect(-2000, y1, 4000, 800);
  ctx.fillStyle = 'rgba(10,12,10,0.6)'; ctx.fillRect(-260, y1, 520, 800);
  ctx.fillStyle = '#23272b'; ctx.fillRect(x0 - 34, y0 - 34, x1 - x0 + 68, y1 - y0 + 34);
  const [sx, sy] = knockShake(b);
  ctx.save(); ctx.translate(sx * 0.5, sy * 0.5);
  const dg = ctx.createLinearGradient(x0, 0, x1, 0);
  dg.addColorStop(0, '#2a2e33'); dg.addColorStop(1, '#22262a');
  ctx.fillStyle = dg; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.strokeStyle = 'rgba(220,235,220,0.08)'; ctx.lineWidth = 3;
  ctx.strokeRect(x0 + 40, y0 + 50, x1 - x0 - 80, 300); ctx.strokeRect(x0 + 40, y0 + 400, x1 - x0 - 80, 330);
  // 307
  ctx.fillStyle = 'rgba(205,190,150,0.75)'; ctx.font = `500 44px ${UI}`; ctx.textAlign = 'center';
  ctx.fillText('307', 0, y0 + 220);
  ctx.beginPath(); ctx.arc(x0 + 52, 20, 15, 0, Math.PI * 2); ctx.fillStyle = '#3a3e44'; ctx.fill();
  // the peephole: dark until someone inside comes to look
  const look = smooth(ramp(b, 86.4, 86.9));
  ctx.beginPath(); ctx.arc(0, -140, 9, 0, Math.PI * 2); ctx.fillStyle = look > 0 ? `rgba(4,5,6,${0.9})` : 'rgba(60,70,80,0.9)'; ctx.fill();
  ctx.restore();
}
function knockShake(b) {
  let x = 0, y = 0;
  for (const k of TL.EVENTS.knocks) {
    const u = b - k;
    if (u > 0 && u < 0.5) { const e = Math.exp(-u * 10); x += Math.sin(u * 90) * 5 * e; y += Math.cos(u * 70) * 2.5 * e; }
  }
  return [x, y];
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
function partTag(ov, a = 0.6) { label(ov, 'THE STILLNESS  ·  PART 3', CX, 210, 20, 'rgba(200,214,232,0.75)', a, 'center', 0.3); }
function clockTag(ov, b, a = 1) {
  const pop = b >= TL.RESUME ? Math.exp(-(b - TL.RESUME) * 1.5) : 0;
  label(ov, TL.clockText(b) + ' AM', 70, 290, 26, `rgba(${Math.round(lerp(200, 255, pop))},${Math.round(lerp(214, 255, pop))},${Math.round(lerp(236, 255, pop))},0.85)`, a, 'left', 0.12, 300);
}
const CAP_Y = 1420;

function shotPhone(b, t, S, set, ov, P) {
  const u = ramp(b, 0, 14);
  const z = 1.18 + 0.12 * sine(u);
  const cam = camera(0, 150 - 40 * sine(u), z);
  const [gx, gy] = cam.s(0, 0);
  S.bg.glow = [gx, gy, 760 * z, 0.28];
  S.bg.glowCol = [0.55, 0.68, 0.95];
  cam.apply(set);
  set.rotate(0.03);
  drawPhone(set, b, smooth(ramp(b, 0.2, 0.6)));
  set.setTransform(1, 0, 0, 1, 0, 0);
  dust(P, b, 110, 11, [-700, -700, 700, 700], 2.2, (x, y) => 0.45 * Math.exp(-(x * x + y * y) / 300000), COLD, cam);
  partTag(ov, smooth(ramp(b, 0.5, 1.5)));
  caption(ov, t, CX, CAP_Y + 40, { maxW: 860, size: 60 });
}

function shotRoom(b, t, S, set, ov, P) {
  S.freeze = smooth(ramp(b, TL.FREEZE, TL.FREEZE + 0.6));
  const cam = camera(0, 170, lerp(1.06, 1.18, sine(ramp(b, 14, 30))));
  const [lx, ly] = cam.s(0, DOOR.y1);
  const open = ease(ramp(b, TL.EVENTS.doorOpen, TL.EVENTS.doorOpen + 3));
  S.bg.glow = [lx, ly, 640 * cam.z, 0.2 + 0.4 * open];
  S.bg.glowCol = HALL;
  // the freeze, rippling out from the phone in your hand (below frame)
  if (b >= TL.FREEZE && b < TL.FREEZE + 4) {
    const u = (b - TL.FREEZE) / 4;
    S.ripple = [CX, H + 100, u * 2600, 0.9 * (1 - smooth(u))];
  }
  cam.apply(set);
  drawDoorInside(set, b);
  set.setTransform(1, 0, 0, 1, 0, 0);
  dust(P, b, 160, 31, [-900, -900, 900, 900], 2.2, (x, y) => 0.35 * Math.exp(-((x * x) / 200000 + ((y - DOOR.y1) ** 2) / 120000)), HALL, cam);
  // you leave the phone and drift to the door
  if (b >= TL.EVENTS.amberWake) {
    const pts = [[18, 300, 1100], [21, 120, 500], [24, 0, 150], [27, -40, -40], [30, 0, -260]];
    const ap = (bb) => cam.s(...path(pts, bb));
    const [x, y] = ap(b);
    pushAmber(P, x, y, b, 0.8, smooth(ramp(b, 18, 19)), (bb) => ap(Math.max(18, bb)));
  }
  clockTag(ov, b);
  caption(ov, t, CX, CAP_Y, { maxW: 860, size: 60 });
}

function shotHall(b, t, S, set, ov, P) {
  S.freeze = 1;
  set.setTransform(1, 0, 0, 1, 0, 0);
  drawHall(set, b, P);
  dust(P, b, 120, 41, [0, 0, W, 1400], 1.8, () => 0.22, HALL);
  // you walk slowly down the middle of them
  const u = ramp(b, 30, 58);
  const Z = lerp(1.6, 9.5, sine(u));
  const [ax, ay] = proj(0, 0.1, Z);
  pushAmber(P, ax, ay, b, lerp(0.8, 0.35, sine(u)), 1, (bb) => proj(0, 0.1, lerp(1.6, 9.5, sine(ramp(bb, 30, 58)))));
  clockTag(ov, b);
  caption(ov, t, CX, CAP_Y + 20, { maxW: 880, size: 60 });
}

function shotRecord(b, t, S, set, ov, P) {
  S.freeze = 1;
  const el = t - TL.timeOf(TL.EVENTS.record);
  const a = smooth(ramp(b, 58, 58.5));
  ov.save();
  ov.translate(CX, CY - 160); ov.scale(1.45, 1.45); ov.translate(-CX, -CY);
  const y0 = CY - 110;
  label(ov, 'NEW VOICEMAIL', CX, y0 - 110, 20, 'rgba(200,214,240,0.6)', a, 'center', 0.3);
  label(ov, 'To: You', CX, y0 - 50, 40, 'rgba(236,240,250,0.95)', a, 'center', 0, 500);
  label(ov, 'Deliver: Yesterday, 3:14 AM', CX, y0 - 6, 24, 'rgba(205,216,238,0.7)', a, 'center', 0, 400);
  label(ov, 'Recording', CX - 62, y0 + 101, 28, 'rgba(240,244,250,0.95)', a, 'left', 0, 500);
  label(ov, mmss(el), CX + 110, y0 + 101, 28, 'rgba(240,244,250,0.6)', a, 'left', 0, 300);
  ov.restore();
  const pulse = 0.75 + 0.25 * Math.sin(el * 4.2);
  const K = 1.45, kx = (x) => CX + (x - CX) * K, ky = (y) => CY - 160 + (y - CY) * K;
  P.push(kx(CX - 92), ky(CY - 110 + 92), 46 * K, 5, [RED[0] * 1.5, RED[1] * 1.5, RED[2] * 1.5], a, 0.24, 0.5 * pulse);
  S.bg.glow = [kx(CX - 92), ky(CY - 18), 500, 0.05 * a]; S.bg.glowCol = RED;
  // what the microphone hears: you
  waveStrip(ov, t, CX - 440, CY + 260, 880, 120, { bar: 5, gap: 4, span: 3.0, playhead: true, alpha: a });
  clockTag(ov, b);
  caption(ov, t, CX, CAP_Y, { maxW: 880, size: 60 });
}

function shotOutside(b, t, S, set, ov, P) {
  S.freeze = b < TL.RESUME ? 1 : 0;
  const cam = camera(0, 170, lerp(1.1, 1.24, sine(ramp(b, 78, 88))));
  S.bg.glow = [CX, 0, 1100, b >= TL.RESUME ? 0.16 : 0.1]; S.bg.glowCol = HALL;
  if (b >= TL.RESUME && b < TL.RESUME + 3) {
    const u = (b - TL.RESUME) / 3;
    S.ripple = [CX, CY + 300, u * 2400, 0.7 * (1 - smooth(u))];   // the world lets go
  }
  cam.apply(set);
  drawDoorOutside(set, b);
  set.setTransform(1, 0, 0, 1, 0, 0);
  S.shake = knockShake(b).map((v) => v * 0.5);
  dust(P, b, 140, 61, [-900, -900, 900, 900], 2.0, () => 0.3, HALL, cam);
  // you, at your own door. You lean in on each knock.
  let lean = 0;
  for (const k of TL.EVENTS.knocks) { const u = b - k; if (u > -0.25 && u < 0.4) lean += Math.exp(-((u - 0.0) ** 2) / 0.02); }
  const [ax, ay] = cam.s(0, -10 - lean * 26);
  pushAmber(P, ax, ay + 40 * cam.z, b, 0.9, 1);
  clockTag(ov, b);
  caption(ov, t, CX, CAP_Y, { maxW: 880, size: 62 });
}

function shotTitle(b, t, S, set, ov, P) {
  S.bg.glow = [CX, CY, 800, 0.05];
  S.bg.glowCol = [0.5, 0.6, 0.55];
  const a = smooth(ramp(b, 88, 88.6));
  label(ov, 'THE STILLNESS', CX, CY - 130, 24, 'rgba(200,214,232,0.7)', a, 'center', 0.4);
  ov.save();
  ov.textAlign = 'center'; ov.globalAlpha = a;
  ov.font = `118px ${SERIF}`; ov.letterSpacing = '6px';
  ov.fillStyle = 'rgba(232,237,240,0.97)';
  ov.fillText('THE SEVEN', CX + 3, CY);
  ov.fillText('MINUTES', CX + 3, CY + 120);
  ov.restore();
  label(ov, 'PART 3  ·  3:07 → 3:14 A.M.', CX, CY + 220, 24, 'rgba(200,214,226,0.65)', smooth(ramp(b, 89, 89.6)), 'center', 0.3, 500);
  dust(P, b, 80, 51, [0, 0, W, H], 1.6, () => 0.10);
  // you, still moving, below the title
  const x = CX + lerp(-120, 120, ramp(b, 88, 95.5)) + Math.sin(b * 1.9) * 6;
  pushAmber(P, x, CY + 360, b, 0.7, smooth(ramp(b, 88.5, 89.5)));
}

function shotBlack(b, t, S) { S.grain = 0.0; }

const SHOT_FN = { phone: shotPhone, room: shotRoom, hall: shotHall, record: shotRecord, outside: shotOutside, title: shotTitle, black: shotBlack };

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
