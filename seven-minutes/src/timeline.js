// THE STILLNESS, PART 3: THE SEVEN MINUTES — master timeline (renderer + audio tools).
// Joins Part 1 (The Offer: the Stillness, 3:07, the 99 others) and Part 2 (One New Voicemail:
// 3:14, the door, the knocks). 96 BPM: 96 beats = 60 s, one beat = 0.625 s. 1080 x 1920 only.

export const BPM = 96;
export const FPS = 60;
export const DURATION = 60;
export const BEAT = 60 / BPM;
export const TOTAL_BEATS = 96;
export const beatOf = (t) => t / BEAT;
export const timeOf = (b) => b * BEAT;

export const SCENES = [
  { id: 1, name: 'accepted',       b0: 0,  b1: 14 },
  { id: 2, name: 'the stillness',  b0: 14, b1: 30 },
  { id: 3, name: 'the hallway',    b0: 30, b1: 58 },
  { id: 4, name: 'the recording',  b0: 58, b1: 78 },
  { id: 5, name: 'the other side', b0: 78, b1: 88 },
  { id: 6, name: 'part 3',         b0: 88, b1: 96 },
];
export const SHOTS = [
  { name: 'phone',   b0: 0,    b1: 14 },
  { name: 'room',    b0: 14,   b1: 30 },
  { name: 'hall',    b0: 30,   b1: 58 },
  { name: 'record',  b0: 58,   b1: 78 },
  { name: 'outside', b0: 78,   b1: 88 },
  { name: 'title',   b0: 88,   b1: 95.5 },
  { name: 'black',   b0: 95.5, b1: 96 },
];
export const CUTS = SHOTS.slice(1).map((s) => s.b0);
export function shotAt(b) {
  for (const s of SHOTS) if (b >= s.b0 && b < s.b1) return s;
  return SHOTS[SHOTS.length - 1];
}

// The world clock (Part 1's rule): frozen = this clock stalls. You run on real time.
export const SPEED_KEYS = [[0, 1], [16.5, 1], [16.7, 0], [80, 0], [80.12, 1], [96, 1]];
const _cum = (() => {
  const c = [0];
  for (let i = 1; i < SPEED_KEYS.length; i++) {
    const [b0, s0] = SPEED_KEYS[i - 1], [b1, s1] = SPEED_KEYS[i];
    c.push(c[i - 1] + (b1 - b0) * (s0 + s1) / 2);
  }
  return c;
})();
export function worldSpeed(b) {
  for (let i = 1; i < SPEED_KEYS.length; i++) {
    const [b1, s1] = SPEED_KEYS[i];
    if (b <= b1) { const [b0, s0] = SPEED_KEYS[i - 1]; return s0 + (s1 - s0) * (b - b0) / (b1 - b0); }
  }
  return 1;
}
export function worldBeats(b) {
  if (b <= 0) return b;
  for (let i = 1; i < SPEED_KEYS.length; i++) {
    const [b1] = SPEED_KEYS[i];
    if (b <= b1) { const [b0, s0] = SPEED_KEYS[i - 1]; return _cum[i - 1] + (b - b0) * (s0 + worldSpeed(b)) / 2; }
  }
  return _cum[_cum.length - 1] + (b - SPEED_KEYS[SPEED_KEYS.length - 1][0]);
}
export const FREEZE = 16.5, RESUME = 80;
export const frozen = (b) => b >= FREEZE + 0.2 && b < RESUME;
// The wall clock reads 3:07 until the world moves again; then it has always been 3:14.
export const clockText = (b) => (b >= RESUME ? '3:14' : '3:07');

// The voice. near = you, now, in the room (dry, doubled, too low). p2 = Part 2's exact audio.
export const VOICE = [
  { id: 'n1',  b0: 3,    fx: 'near', speed: 1.2,  text: 'I accepted at three oh seven.', caption: 'I accepted at 3:07.' },
  { id: 'n2',  b0: 8,    fx: 'near', speed: 1.2,  text: 'I only wanted to see who else was awake.' },
  { id: 'n3',  b0: 15,   fx: 'near', speed: 1.25, text: 'So I stopped the world.' },
  { id: 'n4',  b0: 23,   fx: 'near', speed: 1.25, text: 'And I opened the door.' },
  { id: 'n5',  b0: 32,   fx: 'near', speed: 1.2,  text: 'Everyone was out here.' },
  { id: 'n6',  b0: 37,   fx: 'near', speed: 1.2,  text: 'Standing at their own doors.' },
  { id: 'n7',  b0: 43,   fx: 'near', speed: 1.2,  text: 'Knocking. Asking to be let back in.' },
  { id: 'n8',  b0: 51,   fx: 'near', speed: 1.25, text: 'Nobody gets back in while it\'s still.', caption: 'Nobody gets back in while it’s still.' },
  { id: 'n9',  b0: 59.5, fx: 'near', speed: 1.2,  text: 'The phone still works.' },
  { id: 'n10', b0: 64,   fx: 'near', speed: 1.2,  text: 'It just doesn\'t know what day it is.', caption: 'It just doesn’t know what day it is.' },
  { id: 'hi',  b0: 71,   fx: 'p2',   stem: 'p2_hi', pre: 0.9, text: 'Hi. It\'s me.', caption: 'Hi. It’s me.' },
  { id: 'let', b0: 84,   fx: 'p2w',  stem: 'p2_whisper', pre: 0, text: 'Please. Let me in.' },
];
export const CAPTION_HOLD = 2.5;

export const EVENTS = {
  accepted: 1.5,      // the app says so
  freeze: FREEZE,     // on "stopped"
  amberWake: 18,      // you leave the phone
  doorOpen: 25.5,
  turn: 49.5,         // every one of them turns to look at you
  record: 58,
  knocks: [80, 81, 82],
  resume: RESUME,     // the first knock starts the world again: 3:14
  title: 88,
  silence: 95.5,
};

// Who is standing in the hallway: [side, depth] per door. Their dots are Part 1's ice-blue.
export const OTHERS = (() => {
  const out = [];
  for (let k = 0; k < 22; k++) out.push([k % 2 ? 1 : -1, 1.25 + k * 0.85]);
  return out;
})();

export function cueList() {
  const s = (b) => +timeOf(b).toFixed(5);
  return {
    bpm: BPM, fps: FPS, duration: DURATION, beat: BEAT,
    scenes: SCENES.map((x) => ({ ...x, t0: s(x.b0), t1: s(x.b1) })),
    cuts: CUTS.map(s),
    voice: VOICE.map((v) => ({ ...v, t0: s(v.b0) })),
    events: Object.fromEntries(Object.entries(EVENTS).map(([k, v]) => [k, Array.isArray(v) ? v.map(s) : s(v)])),
    worldSpeed: Array.from({ length: 96 * 16 + 1 }, (_, i) => +worldSpeed(i / 16).toFixed(3)),
  };
}
