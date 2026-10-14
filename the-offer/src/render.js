// THE OFFER — renderer. Every frame is a pure function of time.
// WebGL2: light, beam, particles, dot grid, freeze ripple, motion-blur accumulation.
// Canvas 2D: type, phone UI and the flat set pieces.

import * as TL from './timeline.js';
import { createGL } from './gl.js';

const Q = new URLSearchParams(location.search);
const W = +(Q.get('w') || 1920), H = +(Q.get('h') || 1080);
const SUB = +(Q.get('sub') || 8);
const SHUTTER = 0.5;                       // 180-degree shutter
const PORTRAIT = H > W;
const CX = W / 2, CY = H / 2;

// ---------------------------------------------------------------- palette
const AMBER = [1.0, 0.56, 0.17];           // you: a dying amber
const ICE = [0.60, 0.86, 1.0];             // the others
const COLD = [0.72, 0.82, 1.0];            // phone light
const WORLD = [0.56, 0.61, 0.70];          // the world, desaturated
const css = (c, a = 1) => `rgba(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)},${a})`;
const INK = '#dfe5ee';
const UI = '"Inter", sans-serif';
const SERIF = '"Instrument Serif", serif';

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
const logLerp = (a, b, t) => Math.exp(lerp(Math.log(a), Math.log(b), t));

function lineAlpha(id, b) {
  const l = TL.LINES.find((x) => x.id === id);
  if (!l) return 0;
  const fin = smooth(ramp(b, l.b0, l.b0 + TL.FADE_IN));
  return l.b1 >= TL.TOTAL_BEATS ? fin : fin * (1 - smooth(ramp(b, l.b1 - TL.FADE_OUT, l.b1)));
}
const lineText = (id) => TL.LINES.find((x) => x.id === id).text;

// Hermite path through timed waypoints [[beat, x, y], ...]
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

// ---------------------------------------------------------------- particles
const MAXP = 6000;
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

// ---------------------------------------------------------------- camera
function camera(x, y, z) {
  return {
    x, y, z,
    s: (wx, wy) => [CX + (wx - x) * z, CY + (wy - y) * z],
    apply: (ctx) => ctx.setTransform(z, 0, 0, z, CX - x * z, CY - y * z),
  };
}

// ---------------------------------------------------------------- layout
const L = PORTRAIT ? {
  phoneZ: [1.42, 1.62], phoneY: [-30, -90],
  room: {
    win: [-470, -840, -40, -330], clock: [290, -640, 118], tableY: 430, tableX: [-560, 560],
    phone: [-250, 418], cup: [190, 430], beamA: [-250, -560], beamB: [170, 1000], beamW: [130, 470],
    z: [0.98, 1.04],
  },
  amber: [[28.5, -250, 412], [30.5, -150, 180], [32.5, 230, 120], [34, 300, 300], [36.5, -60, -120], [38.2, -330, -520], [41, -120, -330]],
  grid: { cx: 0, cy: -400, sp: 82, r: 8 },
  gridMath: { cx: 0, cy: -470, sp: 70, r: 7 },
  decline: [0, 330],
  textX: 90, textW: 900,
  clock: [0, -430, 330],
} : {
  phoneZ: [0.92, 1.18], phoneY: [-30, -90],
  room: {
    win: [-860, -440, -300, 40], clock: [700, -330, 118], tableY: 200, tableX: [-640, 780],
    phone: [-250, 188], cup: [250, 200], beamA: [-560, -220], beamB: [130, 640], beamW: [150, 520],
    z: [1.0, 1.06],
  },
  amber: [[28.5, -250, 182], [30.5, -170, 10], [32.5, 190, -50], [34, 310, 60], [36.5, -110, -210], [38.2, -470, -230], [41, -260, -90]],
  grid: { cx: 470, cy: 0, sp: 68, r: 7.5 },
  gridMath: { cx: 480, cy: 20, sp: 60, r: 6.5 },
  decline: [-470, 30],
  textX: 150, textW: 880,
  clock: [-420, 0, 330],
};

const slotPos = (g, i) => {
  const r = Math.floor(i / 10), c = i % 10;
  return [CX + g.cx + (c - 4.5) * g.sp, CY + g.cy + (r - 4.5) * g.sp];
};

// ---------------------------------------------------------------- 2D helpers
function wrap(ctx, text, maxW) {
  const words = text.split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    const tryL = cur ? cur + ' ' + w : w;
    if (ctx.measureText(tryL).width > maxW && cur) { lines.push(cur); cur = w; } else cur = tryL;
  }
  if (cur) lines.push(cur);
  return lines;
}

// Same line count as a greedy wrap, but with the narrowest width that keeps it: no orphans.
function wrapBalanced(ctx, text, maxW) {
  const n = wrap(ctx, text, maxW).length;
  if (n < 2) return wrap(ctx, text, maxW);
  let lo = maxW * 0.4, hi = maxW;
  for (let i = 0; i < 14; i++) { const mid = (lo + hi) / 2; if (wrap(ctx, text, mid).length > n) lo = mid; else hi = mid; }
  return wrap(ctx, text, hi);
}

// Story line in the serif. Fades in with a small rise; returns block height.
function storyLine(ctx, id, b, x, y, o = {}) {
  const a = lineAlpha(id, b);
  if (a <= 0.002) return 0;
  const l = TL.LINES.find((q) => q.id === id);
  const size = o.size || (PORTRAIT ? 74 : 68);
  ctx.save();
  ctx.font = `${o.italic ? 'italic ' : ''}${size}px ${SERIF}`;
  ctx.textAlign = o.align || 'left';
  ctx.textBaseline = 'alphabetic';
  const rise = (1 - smooth(ramp(b, l.b0, l.b0 + 1.2))) * 14;
  const lines = wrapBalanced(ctx, l.text, o.maxW || L.textW);
  const lh = size * 1.12;
  ctx.fillStyle = o.color || INK;
  ctx.globalAlpha = a;
  lines.forEach((s, i) => ctx.fillText(s, x, y + rise + i * lh));
  ctx.restore();
  return lines.length * lh;
}

function label(ctx, text, x, y, size, color, a, align = 'left', spacing = 0.22, weight = 600) {
  if (a <= 0.002) return;
  ctx.save();
  ctx.font = `${weight} ${size}px ${UI}`;
  ctx.letterSpacing = `${size * spacing}px`;
  ctx.textAlign = align;
  ctx.fillStyle = color;
  ctx.globalAlpha = a;
  ctx.fillText(text, x, y);
  ctx.restore();
}

function rrect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

// ---------------------------------------------------------------- phone
const PW = 470, PH = 960;
function drawPhone(ctx, b, mode, on, extra = {}) {
  // body
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.8)'; ctx.shadowBlur = 60; ctx.shadowOffsetY = 20;
  rrect(ctx, -PW / 2, -PH / 2, PW, PH, 72);
  ctx.fillStyle = '#0a0b0e'; ctx.fill();
  ctx.restore();
  rrect(ctx, -PW / 2, -PH / 2, PW, PH, 72);
  ctx.lineWidth = 3; ctx.strokeStyle = `rgba(150,170,205,${0.10 + 0.28 * on})`; ctx.stroke();
  // screen
  const sx = -PW / 2 + 16, sy = -PH / 2 + 16, sw = PW - 32, sh = PH - 32;
  ctx.save();
  rrect(ctx, sx, sy, sw, sh, 58);
  ctx.clip();
  const g = ctx.createLinearGradient(0, sy, 0, sy + sh);
  g.addColorStop(0, `rgba(${18 + 22 * on},${24 + 34 * on},${34 + 58 * on},1)`);
  g.addColorStop(0.55, `rgba(${8 + 12 * on},${10 + 18 * on},${16 + 30 * on},1)`);
  g.addColorStop(1, `rgba(${5 + 6 * on},${6 + 8 * on},${9 + 14 * on},1)`);
  ctx.fillStyle = g;
  ctx.fillRect(sx, sy, sw, sh);
  // dynamic island
  rrect(ctx, -60, sy + 22, 120, 34, 17); ctx.fillStyle = '#020203'; ctx.fill();
  if (on > 0.01) {
    ctx.globalAlpha = on;
    if (mode === 'lock') drawLock(ctx, b, extra);
    else drawOfferUI(ctx, b, extra);
    ctx.globalAlpha = 1;
  }
  // glass sheen
  const sg = ctx.createLinearGradient(sx, sy, sx + sw, sy + sh);
  sg.addColorStop(0, 'rgba(255,255,255,0.035)'); sg.addColorStop(0.4, 'rgba(255,255,255,0)');
  ctx.fillStyle = sg; ctx.fillRect(sx, sy, sw, sh);
  ctx.restore();
}

function drawLock(ctx, b, x) {
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(214,226,250,0.72)';
  ctx.font = `500 24px ${UI}`;
  ctx.letterSpacing = '1px';
  ctx.fillText('Thursday, 14 November', 0, -330);
  ctx.letterSpacing = '0px';
  ctx.font = `200 156px ${UI}`;
  ctx.fillStyle = 'rgba(232,240,255,0.94)';
  ctx.fillText('3:07', 0, -175);
  // notification
  const n = x.notify;
  if (n > 0.001) {
    ctx.save();
    ctx.globalAlpha *= n;
    ctx.translate(0, (1 - n) * -26);
    const cw = 412, cx = -cw / 2, cy = -90;
    ctx.font = `500 25px ${UI}`;
    const body = wrap(ctx, 'You have been offered the Stillness. Accept or decline by sunrise.', cw - 48);
    const ch = 92 + body.length * 33;
    rrect(ctx, cx, cy, cw, ch, 30);
    ctx.fillStyle = 'rgba(36,44,60,0.88)'; ctx.fill();
    ctx.lineWidth = 1.5; ctx.strokeStyle = 'rgba(190,210,245,0.14)'; ctx.stroke();
    // empty sender avatar
    ctx.beginPath(); ctx.arc(cx + 42, cy + 40, 15, 0, Math.PI * 2);
    ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(200,215,240,0.55)'; ctx.stroke();
    ctx.textAlign = 'left';
    ctx.font = `600 17px ${UI}`; ctx.letterSpacing = '3px';
    ctx.fillStyle = 'rgba(200,215,240,0.62)';
    ctx.fillText('NO SENDER', cx + 70, cy + 46);
    ctx.letterSpacing = '0px';
    ctx.textAlign = 'right'; ctx.font = `400 18px ${UI}`;
    ctx.fillText('now', cx + cw - 24, cy + 46);
    ctx.textAlign = 'left'; ctx.font = `500 25px ${UI}`;
    ctx.fillStyle = 'rgba(238,243,255,0.97)';
    body.forEach((s, i) => ctx.fillText(s, cx + 24, cy + 96 + i * 33));
    ctx.restore();
  }
  // bottom affordances
  ctx.fillStyle = 'rgba(30,36,48,0.8)';
  for (const sxx of [-150, 150]) { ctx.beginPath(); ctx.arc(sxx, 350, 34, 0, Math.PI * 2); ctx.fill(); }
  rrect(ctx, -70, 430, 140, 7, 4); ctx.fillStyle = 'rgba(220,230,250,0.6)'; ctx.fill();
}

function drawOfferUI(ctx, b, x) {
  ctx.textAlign = 'center';
  ctx.font = `600 17px ${UI}`; ctx.letterSpacing = '5px';
  ctx.fillStyle = 'rgba(200,215,240,0.6)';
  ctx.fillText('THE STILLNESS', 0, -300);
  ctx.letterSpacing = '0px';
  ctx.font = `46px ${SERIF}`;
  ctx.fillStyle = 'rgba(236,241,252,0.95)';
  ctx.fillText('99 others', 0, -200);
  ctx.fillText('have accepted.', 0, -150);
  ctx.font = `400 21px ${UI}`;
  ctx.fillStyle = 'rgba(190,205,232,0.6)';
  ctx.fillText('Sunrise in 00:41:12', 0, -90);
  // buttons
  rrect(ctx, -170, 150, 340, 84, 42); ctx.fillStyle = 'rgba(226,236,255,0.94)'; ctx.fill();
  ctx.font = `600 27px ${UI}`; ctx.fillStyle = '#0b0f17'; ctx.fillText('Accept', 0, 202);
  rrect(ctx, -170, 260, 340, 84, 42); ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(210,222,245,0.5)'; ctx.stroke();
  ctx.fillStyle = 'rgba(210,222,245,0.8)'; ctx.fillText('Decline', 0, 312);
  rrect(ctx, -70, 430, 140, 7, 4); ctx.fillStyle = 'rgba(220,230,250,0.5)'; ctx.fill();
}

function drawThumb(ctx, tip, ang, light) {
  ctx.save();
  ctx.translate(tip[0], tip[1]);
  ctx.rotate(ang);
  // thumb as a long rounded capsule pointing up; drawn in local space, tip at (0,0)
  const w = 168, len = 760;
  ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 70; ctx.shadowOffsetY = 26;
  rrect(ctx, -w / 2, -10, w, len, w / 2);
  const fg = ctx.createLinearGradient(0, -10, 0, 420);
  fg.addColorStop(0, `rgba(${30 + 20 * light},${34 + 26 * light},${44 + 40 * light},1)`);
  fg.addColorStop(1, '#0b0c0f');
  ctx.fillStyle = fg; ctx.fill();
  ctx.shadowColor = 'transparent';
  // rim light from the screen
  const g = ctx.createLinearGradient(0, -10, 0, 260);
  g.addColorStop(0, `rgba(170,195,240,${0.55 * light})`); g.addColorStop(1, 'rgba(170,195,240,0)');
  rrect(ctx, -w / 2, -10, w, len, w / 2);
  ctx.lineWidth = 4; ctx.strokeStyle = g; ctx.stroke();
  // nail
  rrect(ctx, -46, 18, 92, 120, 40);
  ctx.fillStyle = `rgba(120,140,175,${0.10 * light})`; ctx.fill();
  ctx.lineWidth = 1.5; ctx.strokeStyle = `rgba(170,195,240,${0.22 * light})`; ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------- clock
function secondAngle(b) {
  const wb = TL.worldBeats(b);
  const ticks = Math.floor(wb / TL.TICK_BEATS + 1e-9);
  const since = (wb - ticks * TL.TICK_BEATS) / TL.TICK_BEATS;   // 0..1 in world time
  const spring = Math.exp(-since * 26) * Math.cos(since * 70) * 0.35;
  return (ticks + 7 - spring * Math.sign(TL.worldSpeed(b) || 1)) * Math.PI / 30;
}

function drawClock(ctx, x, y, r, b, light = 1) {
  ctx.save();
  ctx.translate(x, y);
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2);
  ctx.fillStyle = '#0d1016'; ctx.fill();
  ctx.lineWidth = r * 0.05; ctx.strokeStyle = `rgba(70,82,102,${0.8 * light})`; ctx.stroke();
  for (let i = 0; i < 60; i++) {
    const a = i / 60 * Math.PI * 2, major = i % 5 === 0;
    const r0 = r * (major ? 0.80 : 0.86), r1 = r * 0.91;
    ctx.beginPath();
    ctx.moveTo(Math.sin(a) * r0, -Math.cos(a) * r0); ctx.lineTo(Math.sin(a) * r1, -Math.cos(a) * r1);
    ctx.lineWidth = r * (major ? 0.022 : 0.008);
    ctx.strokeStyle = `rgba(150,165,190,${(major ? 0.7 : 0.35) * light})`;
    ctx.stroke();
  }
  const hand = (a, len, wdt, col, back = 0.12) => {
    ctx.save(); ctx.rotate(a);
    ctx.beginPath(); ctx.moveTo(0, r * back); ctx.lineTo(0, -len);
    ctx.lineCap = 'round'; ctx.lineWidth = wdt; ctx.strokeStyle = col; ctx.stroke();
    ctx.restore();
  };
  hand((3 + 7 / 60) / 12 * Math.PI * 2, r * 0.5, r * 0.045, `rgba(170,182,204,${0.9 * light})`);
  hand(7 / 60 * Math.PI * 2, r * 0.74, r * 0.03, `rgba(170,182,204,${0.9 * light})`);
  hand(secondAngle(b), r * 0.82, r * 0.012, `rgba(225,235,255,${light})`, 0.22);
  ctx.beginPath(); ctx.arc(0, 0, r * 0.03, 0, Math.PI * 2); ctx.fillStyle = `rgba(225,235,255,${light})`; ctx.fill();
  ctx.restore();
}

// ---------------------------------------------------------------- the room (flat set)
function drawRoom(ctx, b) {
  const R = L.room;
  const [wx0, wy0, wx1, wy1] = R.win;
  // window: night sky
  const g = ctx.createLinearGradient(0, wy0, 0, wy1);
  g.addColorStop(0, '#1a2537'); g.addColorStop(1, '#0d131e');
  ctx.fillStyle = g; ctx.fillRect(wx0, wy0, wx1 - wx0, wy1 - wy0);
  // moon
  ctx.beginPath(); ctx.arc(wx1 - (wx1 - wx0) * 0.24, wy0 + (wy1 - wy0) * 0.22, 26, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(190,205,230,0.55)'; ctx.fill();
  // rooftops
  ctx.fillStyle = '#080b11';
  ctx.beginPath(); ctx.moveTo(wx0, wy1);
  const steps = [[0, .78], [.14, .78], [.14, .66], [.3, .66], [.3, .74], [.46, .74], [.46, .6], [.58, .6], [.58, .7], [.8, .7], [.8, .64], [1, .64], [1, 1]];
  for (const [u, v] of steps) ctx.lineTo(wx0 + u * (wx1 - wx0), wy0 + v * (wy1 - wy0));
  ctx.closePath(); ctx.fill();
  // frame + mullions
  ctx.strokeStyle = '#1b212c'; ctx.lineWidth = 16;
  ctx.strokeRect(wx0, wy0, wx1 - wx0, wy1 - wy0);
  ctx.lineWidth = 9;
  ctx.beginPath(); ctx.moveTo((wx0 + wx1) / 2, wy0); ctx.lineTo((wx0 + wx1) / 2, wy1);
  ctx.moveTo(wx0, (wy0 + wy1) / 2); ctx.lineTo(wx1, (wy0 + wy1) / 2); ctx.stroke();
  ctx.fillStyle = '#151a23'; ctx.fillRect(wx0 - 30, wy1 + 4, wx1 - wx0 + 60, 16);   // sill
  // clock
  drawClock(ctx, R.clock[0], R.clock[1], R.clock[2], b, 0.8);
  // table
  const ty = R.tableY, [tx0, tx1] = R.tableX;
  ctx.fillStyle = '#0e1118'; ctx.fillRect(tx0, ty, tx1 - tx0, 30);
  ctx.fillStyle = 'rgba(120,140,175,0.22)'; ctx.fillRect(tx0, ty, tx1 - tx0, 2);
  ctx.fillStyle = '#0a0c11';
  ctx.fillRect(tx0 + 50, ty + 30, 26, 900); ctx.fillRect(tx1 - 76, ty + 30, 26, 900);
  // phone lying on the table
  const [px, py] = R.phone;
  rrect(ctx, px - 80, py - 6, 160, 12, 5); ctx.fillStyle = '#07080a'; ctx.fill();
  ctx.fillStyle = 'rgba(200,220,255,0.85)'; ctx.fillRect(px - 72, py - 7, 144, 2);
  // cup
  const [cx, cy] = R.cup;
  ctx.fillStyle = '#161a22';
  ctx.beginPath(); ctx.moveTo(cx - 50, cy - 104); ctx.lineTo(cx + 50, cy - 104); ctx.lineTo(cx + 40, cy); ctx.lineTo(cx - 40, cy); ctx.closePath(); ctx.fill();
  ctx.lineWidth = 9; ctx.strokeStyle = '#161a22';
  ctx.beginPath(); ctx.arc(cx + 52, cy - 58, 22, -Math.PI / 2, Math.PI / 2); ctx.stroke();
  ctx.fillStyle = 'rgba(150,170,205,0.28)'; ctx.fillRect(cx - 50, cy - 106, 100, 3);
  // kettle, tilted, pouring
  ctx.save();
  ctx.translate(cx + 150, cy - 360);
  ctx.rotate(-0.62);
  ctx.fillStyle = '#141820';
  rrect(ctx, -70, -60, 150, 130, 34); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-70, 10); ctx.lineTo(-150, -22); ctx.lineTo(-150, -8); ctx.lineTo(-70, 40); ctx.fill();
  ctx.lineWidth = 12; ctx.strokeStyle = '#141820';
  ctx.beginPath(); ctx.arc(95, 5, 42, -Math.PI / 2, Math.PI / 2); ctx.stroke();
  ctx.fillStyle = 'rgba(150,170,205,0.22)'; ctx.fillRect(-70, -60, 150, 3);
  ctx.restore();
}

function kettleSpout() {
  const [cx, cy] = L.room.cup;
  const a = -0.62, lx = -150, ly = -15;
  return [cx + 150 + lx * Math.cos(a) - ly * Math.sin(a), cy - 360 + lx * Math.sin(a) + ly * Math.cos(a)];
}

function beamMask(x, y) {
  const R = L.room;
  const [ax, ay] = R.beamA, [bx, by] = R.beamB;
  const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy);
  const ux = dx / len, uy = dy / len;
  const along = ((x - ax) * ux + (y - ay) * uy) / len, across = (x - ax) * -uy + (y - ay) * ux;
  const w = lerp(R.beamW[0], R.beamW[1], clamp(along));
  return smooth(ramp(1 - Math.abs(across) / w, 0, 0.65)) * smooth(ramp(along, 0, 0.12)) * (1 - smooth(ramp(along, 0.7, 1.15)));
}

// ---------------------------------------------------------------- amber dot
function amberPos(b) {
  return path(L.amber, b);
}
function pushAmber(P, x, y, b, scale = 1, alpha = 1, trailFn = null) {
  const breath = 0.85 + 0.15 * Math.sin(b * Math.PI * 0.5);
  const c = [AMBER[0] * 1.7, AMBER[1] * 1.7, AMBER[2] * 1.7];
  if (trailFn) {
    for (let k = 10; k >= 1; k--) {
      const [tx, ty] = trailFn(b - k * 0.07);
      P.push(tx, ty, 26 * scale, 0, AMBER, alpha * 0.22 * (1 - k / 11), 0.18, 0.4);
    }
  }
  P.push(x, y, 70 * scale, 5, c, alpha, 0.11, 0.5 * breath);
}

// ---------------------------------------------------------------- dust
function dustField(P, b, n, seed, region, sizeR, alphaFn, cam = null, drift = 1) {
  const wb = TL.worldBeats(b);
  const [x0, y0, x1, y1] = region;
  for (let i = 0; i < n; i++) {
    const h1 = hash2(i, seed), h2 = hash2(i, seed + 1), h3 = hash2(i, seed + 2), h4 = hash2(i, seed + 3);
    let x = x0 + fract(h1 + wb * 0.004 * (h3 - 0.3) * drift) * (x1 - x0) + Math.sin(wb * 0.35 * drift + h4 * 6.28) * 14;
    let y = y0 + fract(h2 - wb * 0.006 * (0.4 + h4) * drift) * (y1 - y0) + Math.cos(wb * 0.27 * drift + h3 * 6.28) * 10;
    const a = alphaFn(x, y, i);
    if (a <= 0.003) continue;
    let sx = x, sy = y, z = 1;
    if (cam) { [sx, sy] = cam.s(x, y); z = cam.z; }
    const r = (1.2 + h3 * h3 * sizeR) * Math.max(z, 0.35);
    P.push(sx, sy, r * 4, 0, COLD, a, 0.25, 0.35);
  }
}

// ---------------------------------------------------------------- shots
function freezeAmt(b) {
  const s = Math.abs(TL.worldSpeed(b));
  const gate = b < 28 ? 0 : b < 64 ? 1 : b < 96 ? 0.55 : b < 124 ? 0.65 : 1;
  if (b >= 28 && b < 64.6) return smooth(ramp(b, 28, 28.6)) * (1 - ramp(b, 64, 64.6));
  return (1 - clamp(s)) * gate;
}

function baseState() {
  return {
    bg: {
      base: [0.012, 0.014, 0.02], base2: [0.006, 0.007, 0.011],
      glow: [CX, CY, 400, 0], glowCol: COLD, glow2: [CX, CY, 400, 0], glow2Col: COLD,
      beam: [0, 0, 1, 1], beamP: [1, 1, 0, 0], beamCol: COLD, vig: 0.9, lift: 0,
    },
    freeze: 0, setAlpha: 1, ripple: [CX, CY, 0, 0], shake: [0, 0], clip: [0, 0, W, H],
    grain: 0.032,
  };
}

function shotPhone(b, S, set, ov, P) {
  const u = ramp(b, 0, 16);
  const z = lerp(L.phoneZ[0], L.phoneZ[1], sine(u));
  const cam = camera(0, lerp(L.phoneY[0], L.phoneY[1], sine(u)), z);
  const on = smooth(ramp(b, TL.EVENTS.phoneWake, TL.EVENTS.phoneWake + 0.3));
  const notify = ease(ramp(b, TL.EVENTS.notify, TL.EVENTS.notify + 0.9));
  const flick = on * (0.97 + 0.03 * Math.sin(TL.worldBeats(b) * 9.1));
  const [gx, gy] = cam.s(0, 0);
  S.bg.base = [0.010, 0.011, 0.016]; S.bg.base2 = [0.004, 0.005, 0.008];
  S.bg.glow = [gx, gy, 760 * z, 0.30 * flick + 0.012];
  S.bg.glowCol = [0.55, 0.68, 0.95];
  cam.apply(set);
  // nightstand: a glass of water and the charging cable, barely there
  set.save();
  set.strokeStyle = 'rgba(8,9,12,1)'; set.lineWidth = 12; set.lineCap = 'round';
  set.beginPath(); set.moveTo(0, PH / 2); set.bezierCurveTo(0, PH / 2 + 160, 380, PH / 2 + 60, 520, PH / 2 + 300); set.stroke();
  set.restore();
  set.save();
  set.rotate(-0.035);
  drawPhone(set, b, 'lock', on, { notify });
  set.restore();
  // motes in the phone light
  dustField(P, b, 140, 11, [-700, -700, 700, 700], 2.4, (x, y) => {
    const d = Math.hypot(x, y) / 700;
    return (0.03 + 0.55 * on) * Math.exp(-d * d * 2.5);
  }, cam);
  S.grain = 0.036;
}

function shotTos(b, S, set, ov, P) {
  S.bg.glow = [CX, CY + (PORTRAIT ? 0 : 60), PORTRAIT ? 1100 : 1000, 0.12];
  S.bg.glowCol = [0.5, 0.62, 0.9];
  const u = ramp(b, 16, 24);
  const scroll = -sine(u) * 40;
  const colW = PORTRAIT ? 900 : 1120;
  const x0 = CX - colW / 2;
  let y = CY + (PORTRAIT ? -470 : -330) + scroll;
  const a = smooth(ramp(b, 16, 16.4)) * (1 - smooth(ramp(b, 23.7, 24)));
  set.save();
  set.globalAlpha = a;
  set.textAlign = 'left';
  set.font = `600 18px ${UI}`; set.letterSpacing = '6px'; set.fillStyle = 'rgba(190,205,232,0.5)';
  set.fillText('THE STILLNESS', x0, y);
  set.letterSpacing = '0px';
  y += 70;
  set.font = `56px ${SERIF}`; set.fillStyle = 'rgba(214,224,240,0.72)';
  set.fillText('Terms of the Offer', x0, y);
  y += 28;
  set.fillStyle = 'rgba(160,178,210,0.18)'; set.fillRect(x0, y, colW, 1.5);
  y += 64;
  const dim = (txt, alpha = 0.30, size = 25, indent = 0, wt = 400) => {
    set.font = `${wt} ${size}px ${UI}`; set.fillStyle = `rgba(190,205,232,${alpha})`;
    for (const s of wrap(set, txt, colW - indent)) { set.fillText(s, x0 + indent, y); y += size * 1.5; }
  };
  const bar = (w) => { set.fillStyle = 'rgba(150,165,195,0.13)'; set.fillRect(x0 + 52, y - 19, w, 22); y += 37; };
  dim('1.   Grant', 0.42, 22, 0, 600);
  y += 40;
  // the key clause
  const k = smooth(ramp(b, 16.6, 17.6));
  set.font = `500 ${PORTRAIT ? 44 : 48}px ${UI}`;
  const key = ['Freeze time, and everything in it,', 'except '];
  set.fillStyle = `rgba(160,178,210,${0.10 * k})`;
  set.fillRect(x0 - 24, y - 52, 4, PORTRAIT ? 124 : 130);
  set.fillStyle = `rgba(236,242,252,${0.35 + 0.6 * k})`;
  set.fillText('1.1', x0, y);
  set.fillText(key[0], x0 + 80, y);
  y += PORTRAIT ? 58 : 64;
  set.fillText(key[1], x0 + 80, y);
  const ew = set.measureText(key[1]).width;
  set.fillStyle = css(AMBER, 0.35 + 0.65 * k);
  set.fillText('yourself.', x0 + 80 + ew, y);
  y += 84;
  dim('1.2   The Stillness lasts for as long as you hold it. Time spent inside it is not refunded.', 0.30, 23, 52);
  y += 18;
  dim('2.   Holders', 0.38, 22, 0, 600);
  y += 4;
  dim('2.1   This offer is not exclusive.', 0.46, 23, 52);
  dim('2.2   Holders are not notified of one another.', 0.30, 23, 52);
  bar(colW * 0.52);
  y += 10;
  dim('3.   Acceptance', 0.30, 22, 0, 600);
  y += 4;
  dim('3.1   This offer expires at sunrise. Silence is taken as refusal.', 0.24, 23, 52);
  bar(colW * 0.7);
  set.restore();
  dustField(P, b, 70, 21, [0, 0, W, H], 1.6, () => 0.10 * a);
  S.grain = 0.03;
}

function roomCam(b) {
  const R = L.room;
  const z = lerp(R.z[0], R.z[1], sine(ramp(b, 24, 40)));
  return camera(0, 0, z);
}

const GRID_Z = PORTRAIT ? 0.042 : 0.036;
function pullCam(b) {
  // continuous camera from the room into the grid: the room shrinks into your cell
  const c0 = roomCam(40);
  const end = L.amber[L.amber.length - 1];
  const A = [end[1], end[2]];
  const e = sine(ramp(b, 40, 47.5));
  const z = logLerp(c0.z, GRID_Z, e);
  const s0 = c0.s(A[0], A[1]);
  const s1 = slotPos(L.grid, TL.AMBER_SLOT);
  const e2 = sine(ramp(b, 40.5, 47.5));
  const sp = [lerp(s0[0], s1[0], e2), lerp(s0[1], s1[1], e2)];
  return { cam: camera(A[0] - (sp[0] - CX) / z, A[1] - (sp[1] - CY) / z, z), A, e };
}

function shotRoom(b, S, set, ov, P) {
  const pulling = b >= 40;
  let cam, A, e = 0;
  if (!pulling) cam = roomCam(b);
  else ({ cam, A, e } = pullCam(b));
  const z = cam.z;
  const R = L.room;
  const fade = 1 - smooth(ramp(b, 43, 46.5));          // the room leaves as the grid arrives
  S.freeze = freezeAmt(b);
  S.setAlpha = fade;
  // light
  const [phx, phy] = cam.s(R.phone[0], R.phone[1]);
  S.bg.base = [0.016, 0.019, 0.027]; S.bg.base2 = [0.008, 0.009, 0.013];
  S.bg.glow = [phx, phy - 40 * z, 520 * z, 0.26 * fade];
  S.bg.glowCol = [0.5, 0.63, 0.92];
  const [wx, wy] = cam.s((R.win[0] + R.win[2]) / 2, (R.win[1] + R.win[3]) / 2);
  S.bg.glow2 = [wx, wy, 520 * z, 0.06 * fade]; S.bg.glow2Col = [0.45, 0.55, 0.8];
  const [ax, ay] = cam.s(...R.beamA), [bx, by] = cam.s(...R.beamB);
  S.bg.beam = [ax, ay, bx, by];
  S.bg.beamP = [R.beamW[0] * z, R.beamW[1] * z, 0.085 * fade, TL.worldBeats(b)];
  S.bg.beamCol = [0.55, 0.66, 0.9];
  const [w0x, w0y] = cam.s(R.win[0], R.win[1]), [w1x, w1y] = cam.s(R.win[2], R.win[3]);
  S.clip = [w0x, w0y, w1x, w1y];
  // set
  if (fade > 0.002) { cam.apply(set); drawRoom(set, b); }
  const wb = TL.worldBeats(b);
  // freeze ripple from the phone
  if (b >= TL.EVENTS.freeze && b < 32) {
    const u = (b - TL.EVENTS.freeze) / 3;
    S.ripple = [phx, phy, u * (PORTRAIT ? 2300 : 2400), 0.9 * (1 - smooth(u))];
    P.push(phx, phy, u * 2400 + 40, 4, COLD, 0.10 * (1 - u), 1 - 30 / (u * 2400 + 40), 0.015);
  }
  if (fade > 0.002) {
    // birds outside the window
    const [wx0, wy0, wx1, wy1] = R.win;
    for (let i = 0; i < 7; i++) {
      const h1 = hash2(i, 5), h2 = hash2(i, 6), h3 = hash2(i, 7);
      const span = wx1 - wx0 + 240;
      const x = wx0 - 120 + fract(h1 + wb * (0.010 + 0.006 * h2)) * span;
      const y = wy0 + (0.18 + 0.4 * h2) * (wy1 - wy0) + Math.sin(wb * 0.9 + h3 * 6) * 10;
      const flap = Math.sin(wb * Math.PI * (2.6 + h3) + h1 * 6.28);
      const [sx, sy] = cam.s(x, y);
      P.push(sx, sy, (24 + 14 * h3) * z, 2, [0.02, 0.025, 0.035], fade, -0.08 + 0.16 * h2, flap);
    }
    // the coffee pour
    const S0 = kettleSpout();
    const M = [R.cup[0] + 4, R.cup[1] - 100];
    for (let i = 0; i < 90; i++) {
      const u = fract(wb * 0.7 + i / 90);
      const jit = (hash2(i, 9) - 0.5) * 7 * u;
      const x = lerp(S0[0], M[0], u) + jit - Math.sin(u * Math.PI) * 10;
      const y = S0[1] + (M[1] - S0[1]) * u * u;
      const [sx, sy] = cam.s(x, y);
      const size = (15 - 6 * u) * z;
      const ang = Math.atan2(2 * (M[1] - S0[1]) * u, M[0] - S0[0]);
      // dark coffee, each drop catching a cold glint from the phone
      P.push(sx, sy, size, 1, [0.07, 0.05, 0.04], fade, -ang + Math.PI / 2, 0.7);
      P.push(sx - 2.5 * z, sy - 2 * z, size * 0.75, 0, [0.62, 0.70, 0.86], 0.55 * fade, 0.16, 0.25);
    }
    // splash
    for (let i = 0; i < 12; i++) {
      const u = fract(wb * 1.3 + hash2(i, 12));
      const vx = (hash2(i, 13) - 0.5) * 70, vy = -50 - 50 * hash2(i, 14);
      const x = M[0] + vx * u, y = M[1] + vy * u + 140 * u * u;
      const [sx, sy] = cam.s(x, y);
      P.push(sx, sy, 5 * z, 0, [0.62, 0.70, 0.84], 0.4 * fade * (1 - u), 0.3, 0);
    }
    // dust: brightest inside the beam
    dustField(P, b, 320, 31, PORTRAIT ? [-560, -980, 560, 980] : [-980, -560, 980, 560], 2.6, (x, y) => {
      const m = beamMask(x, y);
      const dp = Math.hypot(x - R.phone[0], y - R.phone[1]) / 500;
      return fade * (0.04 + 0.8 * m + 0.25 * Math.exp(-dp * dp * 3));
    }, cam);
  }
  // the others: arrive as the camera pulls back
  if (pulling) {
    const gA = smooth(ramp(b, 42, 46));
    gridDots(P, b, S, L.grid, (i) => {
      const r = Math.floor(i / 10) - Math.floor(TL.AMBER_SLOT / 10), c = (i % 10) - (TL.AMBER_SLOT % 10);
      return cam.s(A[0] + c * L.grid.sp / GRID_Z, A[1] + r * L.grid.sp / GRID_Z);
    }, gA, 1, 'catch');
  }
  // you
  if (b >= TL.EVENTS.amberWake) {
    const intro = smooth(ramp(b, 28.5, 29.6));
    let ap;
    let wander = amberWander(b);
    if (!pulling) ap = cam.s(...amberPos(b));
    else ap = cam.s(...amberPos(b));
    const blend = smooth(ramp(b, 40, 42));
    ap = [ap[0] + wander[0] * blend, ap[1] + wander[1] * blend];
    const tr = b < 41.5 ? (bb) => cam.s(...amberPos(Math.max(28.5, bb))) : null;
    pushAmber(P, ap[0], ap[1], b, lerp(1, 0.75, e) * intro, intro, tr);
  }
  // story
  if (!PORTRAIT) storyLine(ov, 'except', b, CX, 110, { align: 'center', italic: true, color: css(AMBER, 0.95), size: 60 });
  else storyLine(ov, 'except', b, CX, 1730, { align: 'center', italic: true, color: css(AMBER, 0.95), size: 72 });
  storyCatch(b, ov);
  S.grain = 0.032;
}

function amberWander(b) {
  // you never quite stop. Nervous on "You will not."
  const nerv = smooth(ramp(b, 58, 59)) * (1 - smooth(ramp(b, 63, 64)));
  const amp = 3 + 5 * nerv, f = 0.9 + 2.2 * nerv;
  return [Math.sin(b * f * 1.7) * amp + Math.sin(b * f * 3.1 + 1) * amp * 0.5 * nerv,
    Math.cos(b * f * 1.3) * amp + Math.cos(b * f * 2.7 + 2) * amp * 0.5 * nerv];
}

// Grid of the others. mode 'catch': all lit ice-blue; 'math': lit by acceptance.
function gridDots(P, b, S, g, posFn, alpha, scale, mode) {
  for (let i = 0; i < 100; i++) {
    if (i === TL.AMBER_SLOT) continue;
    const [x, y] = posFn(i);
    if (x < -100 || y < -100 || x > W + 100 || y > H + 100) continue;
    let fill = 1, glow = 0.35, a = alpha, col = ICE;
    if (mode === 'catch') {
      // "They will know exactly how to use it": a calm, synchronized pulse
      for (const pb of TL.EVENTS.othersPulse) {
        const u = (b - pb) / 1.6;
        if (u > 0 && u < 1) {
          const rr = g.r * (1.5 + 3.5 * u);
          P.push(x, y, rr + 6, 4, ICE, 0.45 * (1 - u) * alpha, 1 - 3 / (rr + 6), 0.1);
          glow += 0.6 * (1 - u);
        }
      }
    } else {
      const k = TL.ACCEPT_ORDER.indexOf(i);
      const ab = TL.ACCEPT_BEATS[k];
      const acc = b >= ab;
      fill = acc ? smooth(ramp(b, ab, ab + 0.35)) : 0;
      glow = acc ? 0.25 + 1.2 * Math.exp(-(b - ab) * 2.2) : 0.0;
      a = alpha * (acc ? 1 : 0.55);
    }
    const sz = g.r * 4.5 * scale;
    P.push(x, y, sz, 3, [col[0] * 0.82, col[1] * 0.9, col[2] * 0.98], a, fill, glow, 1 / 4.5, 0.05);
  }
}

function storyCatch(b, ov) {
  if (b < 41 || b > 64) return;
  if (!PORTRAIT) {
    const x = L.textX, y = CY - 20;
    storyLine(ov, 'ninety', b, x, y - 30);
    storyLine(ov, 'they', b, x, y - 30);
    storyLine(ov, 'you', b, x, y + 30, { color: css(AMBER, 0.95), italic: true, size: 84 });
  } else {
    const y = CY + 360;
    storyLine(ov, 'ninety', b, CX, y, { align: 'center', maxW: 860 });
    storyLine(ov, 'they', b, CX, y, { align: 'center', maxW: 860 });
    storyLine(ov, 'you', b, CX, y + 40, { align: 'center', color: css(AMBER, 0.95), italic: true, size: 96 });
  }
}

function shotMath(b, S, set, ov, P) {
  S.freeze = freezeAmt(b);
  // the grid slides to its "accept" place and the dots go dim, undecided
  const mv = sine(ramp(b, 64, 67));
  const g = {
    cx: lerp(L.grid.cx, L.gridMath.cx, mv), cy: lerp(L.grid.cy, L.gridMath.cy, mv),
    sp: lerp(L.grid.sp, L.gridMath.sp, mv), r: lerp(L.grid.r, L.gridMath.r, mv),
  };
  const dimToMath = smooth(ramp(b, 64, 65.5));
  S.bg.glow = [CX + g.cx, CY + g.cy, 620, 0.05];
  S.bg.glowCol = [0.4, 0.55, 0.85];
  // the grid: "catch" look fading into "math" look
  if (dimToMath < 1) gridDots(P, b, S, g, (i) => slotPos(g, i), 1 - dimToMath, 1, 'catch');
  gridDots(P, b, S, g, (i) => slotPos(g, i), dimToMath, 1, 'math');
  // you: out to "decline" and back into the grid for "accept"
  const slot = slotPos(g, TL.AMBER_SLOT);
  const D = [CX + L.decline[0], CY + L.decline[1]];
  const out = sine(ramp(b, 64.5, 69)), back = sine(ramp(b, 76, 80));
  let ap = [lerp(slot[0], D[0], out), lerp(slot[1], D[1], out)];
  ap = [lerp(ap[0], slot[0], back), lerp(ap[1], slot[1], back)];
  const wan = amberWander(b);
  const trail = (bb) => {
    const o = sine(ramp(bb, 64.5, 69)), k = sine(ramp(bb, 76, 80));
    const p = [lerp(slot[0], D[0], o), lerp(slot[1], D[1], o)];
    return [lerp(p[0], slot[0], k) + wan[0], lerp(p[1], slot[1], k) + wan[1]];
  };
  pushAmber(P, ap[0] + wan[0], ap[1] + wan[1], b, 0.75, 1, trail);
  // "anyone can stop the world": while it is stopped, others move around you
  const wb = TL.worldBeats(b);
  if (b > 70 && b < 77) {
    for (let i = 0; i < 9; i++) {
      const stopped = 1 - clamp(Math.abs(TL.worldSpeed(b)));
      const seg = b < 73.5 ? 0 : 1;
      const r = 110 + 120 * hash2(i, 40 + seg);
      const ang = hash2(i, 50 + seg) * 6.283 + (b - 70) * 0.25 * (hash2(i, 60) - 0.5);
      const x = D[0] + Math.cos(ang) * r * (PORTRAIT ? 1.6 : 1.2), y = D[1] + Math.sin(ang) * r * 0.9;
      P.push(x, y, 30, 3, [ICE[0] * 0.82, ICE[1] * 0.9, ICE[2] * 0.98], 0.75 * stopped, 1, 0.4, 1 / 4.5, 0.05);
    }
  }
  // background motes run on world time: you can see them stop
  dustField(P, b, 160, 71, [0, 0, W, H], 1.8, () => 0.16, null, 3);
  // counter
  if (b >= 80) {
    const sh = buzzShake(b);
    S.shake = sh;
  }
  // type
  const lx = PORTRAIT ? CX : D[0];
  const ly = PORTRAIT ? D[1] + 170 : D[1] - 190;
  const al = lineAlpha('dlabel', b);
  label(ov, 'DECLINE', lx, ly + (PORTRAIT ? 0 : 0), 22, 'rgba(200,214,240,0.8)', al, 'center', 0.32);
  const tw = PORTRAIT ? 860 : 680;
  storyLine(ov, 'nothing', b, lx, ly + (PORTRAIT ? 110 : 330), { align: 'center', maxW: tw, size: PORTRAIT ? 70 : 60 });
  storyLine(ov, 'anyone', b, lx, ly + (PORTRAIT ? 110 : 330), { align: 'center', maxW: tw, size: PORTRAIT ? 64 : 56 });
  const gx = CX + L.gridMath.cx, gy = CY + L.gridMath.cy - 5 * L.gridMath.sp - 50;
  label(ov, 'ACCEPT', gx, gy, 22, 'rgba(200,214,240,0.8)', lineAlpha('alabel', b), 'center', 0.32);
  const oy = PORTRAIT ? CY + L.gridMath.cy + 5 * L.gridMath.sp + 100 : CY + L.gridMath.cy + 5 * L.gridMath.sp + 90;
  storyLine(ov, 'oneof', b, gx, oy, { align: 'center', maxW: 860, size: PORTRAIT ? 64 : 54 });
  // the phone buzzes: a notification banner, then the counter
  const ban = smooth(ramp(b, 80, 80.6)) * (1 - smooth(ramp(b, 83.4, 84)));
  if (ban > 0.002) banner(ov, b, ban, 'Others are accepting.');
  if (b >= TL.EVENTS.counterOn) {
    const ca = smooth(ramp(b, 82, 82.6));
    const n = TL.acceptedCount(b);
    if (!PORTRAIT) counterBig(ov, D[0], CY - 30, n, ca, b, 1);
    else counterBig(ov, CX, CY + 430, n, ca, b, 1);
  }
  S.grain = 0.03;
}

function buzzShake(b) {
  let x = 0, y = 0;
  for (const bz of TL.EVENTS.buzzes) {
    const u = b - bz;
    if (u > 0 && u < 0.6) {
      const env = Math.sin(Math.PI * u / 0.6);
      x += Math.sin(u * 160) * 2.5 * env; y += Math.cos(u * 137) * 1.5 * env;
    }
  }
  return [x, y];
}

function banner(ctx, b, a, text) {
  ctx.save();
  ctx.globalAlpha = a;
  const w = PORTRAIT ? 760 : 640, h = 92;
  const x = CX - w / 2, y = (PORTRAIT ? 120 : 64) + (1 - a) * -20;
  rrect(ctx, x, y, w, h, 28);
  ctx.fillStyle = 'rgba(30,37,50,0.92)'; ctx.fill();
  ctx.lineWidth = 1.5; ctx.strokeStyle = 'rgba(190,210,245,0.16)'; ctx.stroke();
  ctx.beginPath(); ctx.arc(x + 46, y + h / 2, 14, 0, Math.PI * 2);
  ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(200,215,240,0.55)'; ctx.stroke();
  ctx.textAlign = 'left';
  ctx.font = `600 15px ${UI}`; ctx.letterSpacing = '3px'; ctx.fillStyle = 'rgba(200,215,240,0.6)';
  ctx.fillText('THE STILLNESS', x + 78, y + 37);
  ctx.letterSpacing = '0px';
  ctx.font = `500 24px ${UI}`; ctx.fillStyle = 'rgba(238,243,255,0.96)';
  ctx.fillText(text, x + 78, y + 68);
  ctx.textAlign = 'right'; ctx.font = `400 16px ${UI}`; ctx.fillStyle = 'rgba(200,215,240,0.6)';
  ctx.fillText('now', x + w - 26, y + 37);
  ctx.restore();
}

function counterBig(ctx, x, y, n, a, b, scale) {
  if (a <= 0.002) return;
  ctx.save();
  ctx.globalAlpha = a;
  ctx.textAlign = 'center';
  // last change pulses
  const last = TL.ACCEPT_BEATS.filter((q) => q <= b).pop() || 0;
  const pop = Math.exp(-(b - last) * 3);
  ctx.font = `200 ${Math.round(220 * scale)}px ${UI}`;
  ctx.fontVariantNumeric = 'tabular-nums';
  ctx.fillStyle = `rgba(${Math.round(lerp(220, 175, pop))},${Math.round(lerp(232, 228, pop))},255,0.97)`;
  ctx.fillText(String(n), x, y + 60 * scale);
  ctx.font = `600 ${Math.round(22 * scale)}px ${UI}`; ctx.letterSpacing = `${7 * scale}px`;
  ctx.fillStyle = 'rgba(200,214,240,0.75)';
  ctx.fillText('ACCEPTED', x + 3 * scale, y + 120 * scale);
  ctx.letterSpacing = '0px';
  ctx.font = `400 ${Math.round(20 * scale)}px ${UI}`; ctx.fillStyle = 'rgba(200,214,240,0.45)';
  ctx.fillText('of 99 others', x, y + 156 * scale);
  ctx.restore();
}

function shotClock(b, S, set, ov, P) {
  S.freeze = freezeAmt(b);
  const u = ramp(b, 96, 120);
  const [cx, cy, r] = L.clock;
  const z = lerp(1.0, 1.07, sine(u));
  const cam = camera(0, 0, z);
  const [sx, sy] = cam.s(cx, cy);
  S.bg.base = [0.012, 0.014, 0.02];
  S.bg.glow = [sx - r * 0.3, sy - r * 0.4, r * 2.6 * z, 0.16 * (1 - 0.5 * u)];
  S.bg.glowCol = [0.5, 0.62, 0.9];
  S.bg.vig = 0.9 + 0.5 * u;          // the room closes in, gets quieter
  cam.apply(set);
  drawClock(set, cx, cy, r, b, 1);
  // motes, running on the stuttering world clock
  dustField(P, b, Math.round(170 - 110 * u), 81, [0, 0, W, H], 2.0, (x, y) => 0.2 * (1 - 0.6 * u), null, 3);
  // counter + mini grid
  const n = TL.acceptedCount(b);
  const k = smooth(ramp(b, 96, 96.6));
  const mg = PORTRAIT ? { cx: 150, cy: 760, sp: 17, r: 3.4 } : { cx: 690, cy: -330, sp: 17, r: 3.4 };
  const lx = CX + (PORTRAIT ? -110 : 470), ly = CY + (PORTRAIT ? 700 : -360);
  ov.save();
  ov.globalAlpha = k;
  ov.textAlign = 'left';
  ov.font = `200 ${PORTRAIT ? 120 : 108}px ${UI}`; ov.fontVariantNumeric = 'tabular-nums';
  const last = TL.ACCEPT_BEATS.filter((q) => q <= b).pop() || 0;
  const pop = Math.exp(-(b - last) * 3);
  ov.fillStyle = `rgba(${Math.round(lerp(220, 175, pop))},${Math.round(lerp(232, 228, pop))},255,0.95)`;
  ov.fillText(String(n), lx - (PORTRAIT ? 120 : 110), ly + 40);
  ov.font = `600 17px ${UI}`; ov.letterSpacing = '5px'; ov.fillStyle = 'rgba(200,214,240,0.7)';
  ov.fillText('ACCEPTED', lx - (PORTRAIT ? 116 : 106), ly + 78);
  ov.restore();
  for (let i = 0; i < 100; i++) {
    const [x, y] = slotPos(mg, i);
    if (i === TL.AMBER_SLOT) { pushAmber(P, x, y, b, 0.22, k); continue; }
    const kk = TL.ACCEPT_ORDER.indexOf(i);
    const ab = TL.ACCEPT_BEATS[kk];
    const acc = b >= ab;
    P.push(x, y, mg.r * 4.5, 3, [ICE[0] * 0.82, ICE[1] * 0.9, ICE[2] * 0.98], k * (acc ? 1 : 0.5),
      acc ? smooth(ramp(b, ab, ab + 0.25)) : 0, acc ? 0.2 + 1.4 * Math.exp(-(b - ab) * 3) : 0, 1 / 4.5, 0.08);
  }
  // story
  if (!PORTRAIT) {
    storyLine(ov, 'safe', b, CX + 40, CY + 10, { maxW: 800, size: 66 });
    storyLine(ov, 'chance', b, CX + 40, CY - 40, { maxW: 780, size: 62 });
  } else {
    storyLine(ov, 'safe', b, CX, CY + 220, { align: 'center', maxW: 900, size: 74 });
    storyLine(ov, 'chance', b, CX, CY + 160, { align: 'center', maxW: 900, size: 66 });
  }
  S.grain = 0.03;
}

function shotThumb(b, S, set, ov, P) {
  S.freeze = freezeAmt(b);
  const u = ramp(b, 120, 123);
  const z = PORTRAIT ? lerp(1.6, 1.7, sine(u)) : lerp(1.0, 1.08, sine(u));
  const cam = camera(PORTRAIT ? 30 : 60, PORTRAIT ? 80 : 60, z);
  const [gx, gy] = cam.s(0, 0);
  S.bg.base = [0.010, 0.011, 0.016];
  S.bg.glow = [gx, gy, 760 * z, 0.30];
  S.bg.glowCol = [0.55, 0.68, 0.95];
  cam.apply(set);
  set.save(); set.rotate(-0.035);
  drawPhone(set, b, 'offer', 1, {});
  // the thumb hovers. It trembles.
  const wb = TL.worldBeats(b);
  const ap = ease(ramp(b, 120, 122.4));
  const tip = [lerp(230, 30, ap) + Math.sin(wb * 5.3) * 2.5, lerp(560, 215, ap) + Math.cos(wb * 4.1) * 2.5];
  // shadow on the glass
  const sg = set.createRadialGradient(tip[0] + 40, tip[1] + 60, 10, tip[0] + 40, tip[1] + 60, 160);
  sg.addColorStop(0, `rgba(0,0,0,${0.55 * ap})`); sg.addColorStop(1, 'rgba(0,0,0,0)');
  set.fillStyle = sg; set.fillRect(tip[0] - 200, tip[1] - 150, 450, 450);
  drawThumb(set, tip, -0.62, 1);
  set.restore();
  dustField(P, b, 90, 91, [-700, -700, 700, 700], 2.0, (x, y) => 0.4 * Math.exp(-(x * x + y * y) / 300000), cam);
  S.grain = 0.034;
}

function shotTitle(b, S, set, ov, P) {
  S.freeze = freezeAmt(b);
  const wb = TL.worldBeats(b);
  S.bg.glow = [CX, CY - 30, PORTRAIT ? 800 : 900, 0.075];
  S.bg.glowCol = [0.45, 0.58, 0.9];
  // the title breathes on world time, so it stops when the world stops
  const breathe = 1 + 0.025 * smooth((wb - 123) / 5);
  const a = lineAlpha('title', b);
  ov.save();
  ov.translate(CX, CY - (PORTRAIT ? 60 : 40));
  ov.scale(breathe, breathe);
  ov.textAlign = 'center';
  ov.font = `${PORTRAIT ? 170 : 210}px ${SERIF}`;
  ov.letterSpacing = `${PORTRAIT ? 18 : 30}px`;
  ov.fillStyle = `rgba(232,237,246,${0.97 * a})`;
  ov.fillText('THE OFFER', PORTRAIT ? 9 : 15, 0);
  ov.letterSpacing = '0px';
  ov.restore();
  storyLine(ov, 'q', b, CX, CY + (PORTRAIT ? 90 : 105), { align: 'center', italic: true, size: PORTRAIT ? 70 : 64, color: 'rgba(196,208,228,0.92)' });
  // motes, then the whole frame stops
  dustField(P, b, 110, 101, [0, 0, W, H], 1.8, () => 0.14, null, 3);
  // you keep moving a beat longer than everything else
  const ax = CX + lerp(-200, 170, (b - 123) / 5.2) + Math.sin(b * 1.9) * 6;
  const ay = CY + (PORTRAIT ? 300 : 245) + Math.sin(b * 1.3) * 10;
  const ain = smooth(ramp(b, 123.6, 124.8));
  pushAmber(P, ax, ay, b, 0.8, ain, (bb) => [CX + lerp(-200, 170, (bb - 123) / 5.2) + Math.sin(bb * 1.9) * 6, CY + (PORTRAIT ? 300 : 245) + Math.sin(bb * 1.3) * 10]);
  if (b >= TL.EVENTS.finalFreeze) {
    const u = (b - TL.EVENTS.finalFreeze) / 1.6;
    S.ripple = [CX, CY, u * 1600, 0.35 * (1 - smooth(u))];
  }
  S.grain = 0.03;
}

const SHOT_FN = { phone: shotPhone, tos: shotTos, room: shotRoom, math: shotMath, clock: shotClock, thumb: shotThumb, title: shotTitle };

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
  SHOT_FN[shot.name](b, S, setCtx, ovCtx, parts);
  setCtx.setTransform(1, 0, 0, 1, 0, 0);
  return S;
}

// Sub-frame times: jittered within a 180-degree shutter, never straddling a cut.
function subTimes(f) {
  const tc = f / TL.FPS;
  const out = [];
  for (let s = 0; s < SUB; s++) {
    const j = hash2(f, s + 0.5);
    let t = tc + ((s + j) / SUB - 0.5) * SHUTTER / TL.FPS;
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
  // grain is seeded by the world clock: when the world freezes, so does the film
  const seed = Math.floor(TL.worldBeats(TL.beatOf(seedT)) * TL.BEAT * TL.FPS + 0.5) % 9973;
  G.endFrame(seed, grain, pixels);
  for (let i = 0, j = 0; i < pixels.length; i += 4, j += 3) { rgb[j] = pixels[i]; rgb[j + 1] = pixels[i + 1]; rgb[j + 2] = pixels[i + 2]; }
}

window.renderFrame = (f) => { renderAt(subTimes(f), f / TL.FPS); return true; };
window.renderStill = (t, sub = SUB) => {
  const f = t * TL.FPS;
  const times = [];
  for (let s = 0; s < sub; s++) times.push(Math.min(TL.DURATION - 1e-4, t + ((s + 0.5) / sub - 0.5) * SHUTTER / TL.FPS));
  renderAt(times, t);
  return true;
};
// Readback in slices of <= ~1 MB of base64 so no single DevTools message is large.
const ROWS = Math.max(1, Math.floor(720000 / (W * 3)));
window.sliceCount = Math.ceil(H / ROWS);
window.getSlice = (k) => {
  const a = k * ROWS * W * 3, e = Math.min(H, (k + 1) * ROWS) * W * 3;
  let s = '';
  for (let i = a; i < e; i += 0x8000) s += String.fromCharCode.apply(null, rgb.subarray(i, Math.min(e, i + 0x8000)));
  return btoa(s);
};
window.__G = G; window.READY = true;
