// ONE NEW VOICEMAIL — master timeline, shared by the renderer (browser) and the audio tools (Node).
// 96 BPM: 96 beats = 60 s, one beat = 0.625 s.

export const BPM = 96;
export const FPS = 60;
export const DURATION = 60;
export const BEAT = 60 / BPM;
export const TOTAL_BEATS = 96;
export const beatOf = (t) => t / BEAT;
export const timeOf = (b) => b * BEAT;

export const SCENES = [
  { id: 1, name: 'the notification', b0: 0,  b1: 16 },
  { id: 2, name: 'the message',      b0: 16, b1: 32 },
  { id: 3, name: 'the door',         b0: 32, b1: 52 },
  { id: 4, name: 'the peephole',     b0: 52, b1: 76 },
  { id: 5, name: 'the knock',        b0: 76, b1: 86 },
  { id: 6, name: 'the recording',    b0: 86, b1: 96 },
];
export const SHOTS = [
  { name: 'phone',    b0: 0,  b1: 16 },
  { name: 'wave',     b0: 16, b1: 32 },
  { name: 'door',     b0: 32, b1: 52 },
  { name: 'peephole', b0: 52, b1: 76 },
  { name: 'door2',    b0: 76, b1: 86 },
  { name: 'title',    b0: 86, b1: 91 },
  { name: 'record',   b0: 91, b1: 95 },
  { name: 'black',    b0: 95, b1: 96 },
];
export const CUTS = SHOTS.slice(1).map((s) => s.b0);
export function shotAt(b) {
  for (const s of SHOTS) if (b >= s.b0 && b < s.b1) return s;
  return SHOTS[SHOTS.length - 1];
}

// The voice. `fx`: sys = the voicemail system, you = your own voice from tomorrow,
// glitch = the line breaks up, whisper = no longer on the phone. Durations come from the synth.
export const VOICE = [
  { id: 'sys', b0: 9.5,  fx: 'sys',     speed: 1.0,  text: 'First new message. Received tomorrow, at three fourteen A.M.',
    caption: 'First new message. Received tomorrow, at 3:14 a.m.' },
  { id: 'l1',  b0: 18,   fx: 'you',     speed: 1.2,  text: 'Hi. It\'s me.' },
  { id: 'l2',  b0: 21,   fx: 'you',     speed: 1.2,  text: 'I\'m calling you from tomorrow night.' },
  { id: 'l3',  b0: 26,   fx: 'you',     speed: 1.2,  text: 'Don\'t be scared. It\'s very quiet here.' },
  { id: 'l4',  b0: 33.5, fx: 'you',     speed: 1.2,  text: 'At three fourteen, you\'ll hear someone in the hallway.',
    caption: 'At 3:14, you’ll hear someone in the hallway.' },
  { id: 'l5',  b0: 45,   fx: 'you',     speed: 1.25, text: 'Don\'t open the door.' },
  { id: 'l6',  b0: 53.5, fx: 'you',     speed: 1.25, text: 'I opened the door.' },
  { id: 'l7',  b0: 60,   fx: 'glitch',  speed: 1.3,  text: 'I\'m still standing here.' },
  { id: 'l8',  b0: 66,   fx: 'you',     speed: 1.25, text: 'I\'ve been standing here for a very long time.' },
  { id: 'l9',  b0: 81,   fx: 'whisper', speed: 1.4,  text: 'Please. Let me in.' },
];

// A caption holds until the next line starts, or CAPTION_HOLD beats after the voice ends.
export const CAPTION_HOLD = 2.5;

// Story text that is not spoken.
export const TITLES = [
  { id: 'title',    b0: 86,   b1: 91, text: 'ONE NEW VOICEMAIL' },
  { id: 'received', b0: 87,   b1: 91, text: 'Received tomorrow, 3:14 a.m.' },
];

export const EVENTS = {
  screenOn: 3,
  notify: 3.5,
  play: 8.5,          // the message is opened
  beep: 16.25,        // the voicemail beep, as the cut lands on the waveform
  minute: 40,         // 3:13 -> 3:14
  feet: 42,           // two shadows in the light under the door
  flash: 61.5,        // the light dies; someone is right there
  knocks: [77, 78, 79],
  title: 86,
  record: 91,
  breath: 93.5,
  black: 95,
  silence: 95,        // nothing after this
};

// Hallway lights in the peephole: deterministic flicker, on (1) / off (0).
// Shared with the score so the hum and crackle drop out exactly with the light.
export const FLICKER = [
  // [b0, b1] spans where the light is OFF
  [56.0, 56.12], [56.3, 56.38], [58.9, 59.05],
  [61.5, 62.35],                                   // the flash: off long enough to see the shape
  [64.2, 64.3], [64.45, 64.6], [67.8, 68.0], [69.9, 70.3], [71.7, 71.8], [72.9, 73.4], [74.6, 75.2],
];
export function lightOn(b) {
  if (b < 52 || b >= 76) return 1;
  for (const [a, c] of FLICKER) if (b >= a && b < c) return 0;
  return 1;
}

// Where the figure stands in the corridor (depth 0 = at the door, 1 = far end), after each blackout.
// null = not there.
export function figureDepth(b) {
  if (b < 61.5 || b >= 76) return null;
  if (b < 62.35) return 0.02;                      // right at the peephole, in the dark
  if (b < 66) return null;                         // gone again
  const stages = [[66, 0.95], [68.0, 0.75], [70.3, 0.5], [71.8, 0.36], [73.4, 0.2], [75.2, 0.05]];
  let d = null;
  for (const [sb, sd] of stages) if (b >= sb) d = sd;
  return d;
}

export function cueList(voiceDurations = {}) {
  const s = (b) => +timeOf(b).toFixed(5);
  return {
    bpm: BPM, fps: FPS, duration: DURATION, beat: BEAT,
    scenes: SCENES.map((x) => ({ ...x, t0: s(x.b0), t1: s(x.b1) })),
    cuts: CUTS.map(s),
    voice: VOICE.map((v) => ({ ...v, t0: s(v.b0) })),
    events: Object.fromEntries(Object.entries(EVENTS).map(([k, v]) => [k, Array.isArray(v) ? v.map(s) : s(v)])),
    flicker: FLICKER.map(([a, c]) => [s(a), s(c)]),
  };
}
