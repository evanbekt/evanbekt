// THE OFFER — master timeline. Shared by the renderer (browser) and the cue exporter (Node).
// Everything is expressed in beats on a 128 BPM grid: 128 beats = 60 s.

export const BPM = 128;
export const FPS = 60;
export const DURATION = 60;
export const BEAT = 60 / BPM;            // 0.46875 s
export const TOTAL_BEATS = 128;
export const beatOf = (t) => t / BEAT;
export const timeOf = (b) => b * BEAT;

export const SCENES = [
  { id: 1, name: 'the message',     b0: 0,   b1: 16 },
  { id: 2, name: 'the power',       b0: 16,  b1: 40 },
  { id: 3, name: 'the catch',       b0: 40,  b1: 64 },
  { id: 4, name: 'the math',        b0: 64,  b1: 96 },
  { id: 5, name: 'the realization', b0: 96,  b1: 120 },
  { id: 6, name: 'the question',    b0: 120, b1: 128 },
];

// Shots. Hard cuts happen only at shot boundaries, and every boundary is a whole beat.
export const SHOTS = [
  { name: 'phone',  b0: 0,   b1: 16 },
  { name: 'tos',    b0: 16,  b1: 24 },
  { name: 'room',   b0: 24,  b1: 64 },   // room, freeze, then continuous pull back to the grid
  { name: 'math',   b0: 64,  b1: 96 },   // continuous from the grid
  { name: 'clock',  b0: 96,  b1: 120 },
  { name: 'thumb',  b0: 120, b1: 123 },
  { name: 'title',  b0: 123, b1: 128 },
];
export const CUTS = [16, 24, 96, 120, 123];

export function shotAt(b) {
  for (const s of SHOTS) if (b >= s.b0 && b < s.b1) return s;
  return SHOTS[SHOTS.length - 1];
}

// ---------------------------------------------------------------------------
// World clock. "Frozen" = this clock stalls. The amber dot always runs on real time.
// Keyframes are [beat, speed]; speed is linear between keys.
export const SPEED_KEYS = [
  [0, 1], [28, 1], [28.2, 0],                       // THE freeze
  [64, 0], [64.6, 1],                               // the world resumes for the math
  [71, 1], [71.1, 0], [72.6, 0], [72.7, 1],         // someone else stops the world (you never know)
  [74.5, 1], [74.6, 0], [75.4, 0], [75.5, 1],
  [96, 1],                                          // the stutter
  [98.4, 1], [98.5, 0], [100.0, 0], [100.1, 1],
  [101.6, 1], [101.7, 0], [102.4, 0], [102.5, 1],
  [104.9, 1], [105.0, 0], [106.8, 0], [106.9, 1],
  [108.0, 1], [108.1, -0.8], [109.5, -0.8], [109.6, 0], [110.4, 0], [110.5, 1],   // the hand slips back
  [112.6, 1], [112.7, 0], [113.3, 0], [113.4, 1],
  [114.4, 1], [114.5, 0], [116.4, 0], [116.5, 1],
  [117.3, 1], [117.4, 0], [119.9, 0], [120.0, 1],
  [127, 1], [127.15, 0], [128, 0],                  // the whole frame freezes; only you keep moving
];

const _cum = (() => {
  const c = [0];
  for (let i = 1; i < SPEED_KEYS.length; i++) {
    const [b0, s0] = SPEED_KEYS[i - 1], [b1, s1] = SPEED_KEYS[i];
    c.push(c[i - 1] + (b1 - b0) * (s0 + s1) / 2);
  }
  return c;
})();

export function worldSpeed(b) {
  if (b <= SPEED_KEYS[0][0]) return SPEED_KEYS[0][1];
  for (let i = 1; i < SPEED_KEYS.length; i++) {
    const [b1, s1] = SPEED_KEYS[i];
    if (b <= b1) {
      const [b0, s0] = SPEED_KEYS[i - 1];
      return s0 + (s1 - s0) * (b - b0) / (b1 - b0);
    }
  }
  return SPEED_KEYS[SPEED_KEYS.length - 1][1];
}

// Integral of worldSpeed from 0 to b, in beats.
export function worldBeats(b) {
  if (b <= 0) return b;
  for (let i = 1; i < SPEED_KEYS.length; i++) {
    const [b1] = SPEED_KEYS[i];
    if (b <= b1) {
      const [b0, s0] = SPEED_KEYS[i - 1];
      const s = worldSpeed(b);
      return _cum[i - 1] + (b - b0) * (s0 + s) / 2;
    }
  }
  const n = SPEED_KEYS.length - 1;
  return _cum[n] + (b - SPEED_KEYS[n][0]) * SPEED_KEYS[n][1];
}

// Clock: one tick every TICK_BEATS of world time.
export const TICK_BEATS = 2;
export const tickCount = (b) => Math.floor(worldBeats(b) / TICK_BEATS + 1e-9);

// ---------------------------------------------------------------------------
// The others. 100 slots on a 10 x 10 grid; slot AMBER_SLOT is you.
export const AMBER_SLOT = 36;   // row 3, col 6
function lcg(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
export const ACCEPT_ORDER = (() => {
  const slots = [];
  for (let i = 0; i < 100; i++) if (i !== AMBER_SLOT) slots.push(i);
  const r = lcg(3071);
  for (let i = slots.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [slots[i], slots[j]] = [slots[j], slots[i]]; }
  return slots;
})();

// Beat at which the k-th other (1-based) accepts.
export const ACCEPT_BEATS = (() => {
  const a = [];
  for (let k = 1; k <= 14; k++) a.push(82);                 // the counter appears at 14
  for (let k = 15; k <= 23; k++) a.push(84 + (k - 15));     // one per beat -> 23 at beat 92
  for (let k = 24; k <= 99; k++) {                          // accelerating toward 99
    const u = (k - 23) / 76;
    a.push(100 + 19 * Math.pow(u, 0.5));
  }
  return a;
})();

export function acceptedCount(b) {
  let n = 0;
  for (const ab of ACCEPT_BEATS) if (b >= ab) n++;
  return n;
}

// Heartbeat: quickens through scene 4, fades early in scene 5.
export const HEARTBEATS = (() => {
  const out = [];
  let b = 64;
  while (b < 100) {
    const u = Math.min(1, (b - 64) / 32);
    out.push(b);
    b += 2 - 1.3 * u;   // 2 beats (64 bpm) -> 0.7 beats (~183 bpm)
  }
  return out;
})();

// Freeze events: where world speed drops from moving to stopped.
export function freezeEvents() {
  const ev = [];
  for (let i = 1; i < SPEED_KEYS.length; i++) {
    const [b0, s0] = SPEED_KEYS[i - 1], [, s1] = SPEED_KEYS[i];
    if (Math.abs(s0) > 0.5 && s1 === 0) ev.push(b0);
  }
  return ev;
}

// Tick events, found by watching the clock in real time.
export function tickEvents() {
  const ev = [];
  let last = tickCount(0);
  for (let b = 0; b <= TOTAL_BEATS; b += 1 / 512) {
    const c = tickCount(b);
    if (c !== last) { ev.push({ b, dir: Math.sign(c - last) }); last = c; }
  }
  return ev;
}

// ---------------------------------------------------------------------------
// Story text. Every line holds at least 1.5 s at full opacity (checked by tools/check-timeline.mjs).
export const LINES = [
  { id: 'except',  b0: 31,    b1: 38.5, text: '— except yourself.' },
  { id: 'ninety',  b0: 46.5,  b1: 51.5, text: 'Ninety-nine others have received this offer.' },
  { id: 'they',    b0: 52,    b1: 57, text: 'They will know exactly how to use it.' },
  { id: 'you',     b0: 58,    b1: 63.75, text: 'You will not.' },
  { id: 'dlabel',  b0: 64.5,  b1: 79.5, text: 'DECLINE' },
  { id: 'nothing', b0: 65.5,  b1: 70.25, text: 'Nothing happens.' },
  { id: 'anyone',  b0: 70.25, b1: 76,   text: 'But anyone can stop the world, and you would never know.' },
  { id: 'alabel',  b0: 76,    b1: 95.5, text: 'ACCEPT' },
  { id: 'oneof',   b0: 77,    b1: 82.5, text: 'You become one of a hundred.' },
  { id: 'safe',    b0: 98,    b1: 106,  text: 'Accepting doesn’t make you safe.' },
  { id: 'chance',  b0: 107,   b1: 118.5, text: 'It only gives you a chance to find out who else is awake in the silence.' },
  { id: 'title',   b0: 123,   b1: 128, text: 'THE OFFER' },        // lines that reach the end hold, no fade out
  { id: 'q',       b0: 124,   b1: 128, text: 'Do you take it?' },
];
export const FADE_IN = 0.6, FADE_OUT = 0.6;   // beats

// Sound-design cue points that are not derived from the clock or the grid.
export const EVENTS = {
  phoneWake: 4,          // screen lights up, haptic buzz
  notify: 4.5,           // notification lands
  tosCut: 16,
  roomCut: 24,
  freeze: 28,
  amberWake: 28.5,
  pullBack: 40,
  othersPulse: [53, 55],
  buzzes: [80, 80.75],   // phone buzz, counter arrives
  counterOn: 82,
  clockCut: 96,
  thumbCut: 120,
  titleCut: 123,
  finalFreeze: 127,
  silence: 127,          // total silence for the last beat
};

// Everything the score needs, in seconds.
export function cueList() {
  const s = (b) => +(timeOf(b)).toFixed(5);
  return {
    bpm: BPM, fps: FPS, duration: DURATION, beat: BEAT,
    scenes: SCENES.map((x) => ({ ...x, t0: s(x.b0), t1: s(x.b1) })),
    cuts: CUTS.map(s),
    ticks: tickEvents().map((e) => ({ t: s(e.b), dir: e.dir })),
    freezes: freezeEvents().map(s),
    heartbeats: HEARTBEATS.map(s),
    chimes: ACCEPT_BEATS.map((b, i) => ({ t: s(b), k: i + 1 })),
    events: Object.fromEntries(Object.entries(EVENTS).map(([k, v]) => [k, Array.isArray(v) ? v.map(s) : s(v)])),
    lines: LINES.map((l) => ({ id: l.id, t0: s(l.b0), t1: s(Math.min(l.b1, 128)), text: l.text })),
    worldSpeed: Array.from({ length: 128 * 16 + 1 }, (_, i) => +worldSpeed(i / 16).toFixed(3)),  // 1/16 beat resolution
  };
}
