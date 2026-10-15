// THE STILLNESS, PARTS 4-6 — timelines. One renderer, one file, `?part=4|5|6`.
// Told the way Part 2 is told: through the phone, the door and the peephole. 96 BPM, 96 beats = 60 s.
// The 99 others are the neighbours in Building 3; each of them hears from themselves too.

export const BPM = 96, FPS = 60, DURATION = 60, BEAT = 60 / BPM, TOTAL_BEATS = 96;
export const CAPTION_HOLD = 2.5;

// The building group chat. [beat, apartment, name, text]
const CHAT4 = [
  [9.5, '309', 'Marta', 'is anyone else’s phone going off'],
  [11.5, '312', 'Dev', 'voicemail from my own number??'],
  [13.5, '304', 'Mr. Haas', 'Nobody open your doors.'],
  [15.5, '311', 'Lily', 'mom is knocking'],
  [17.5, '311', 'Lily', 'but mom is asleep in her bed'],
  [19.5, '309', 'Marta', 'it knocks in my voice'],
  [21.5, '304', 'Mr. Haas', 'Whatever happens, don’t answer.'],
];
const CHAT5 = [
  ...CHAT4.map(([, apt, name, text], i) => [-20 + i * 0.01, apt, name, text]),   // last night's messages are still there
  [37, '309', 'Marta', 'I answered.'],
  [39, '309', 'Marta', 'it’s so quiet out here'],
  [41.5, null, null, 'Marta left the group'],
  [43.5, '312', 'Dev', 'she’s standing outside my door'],
];

const PARTS = {
  // ------------------------------------------------------------ PART 4: 99 NEW VOICEMAILS
  4: {
    title: '99 NEW VOICEMAILS',
    shots: [['lock', 0], ['chat', 8], ['wave', 24], ['chorus', 46], ['peep', 58.5], ['knock', 85], ['title', 89.5], ['black', 95.5]],
    chat: CHAT4,
    voice: [
      { id: 'sys', b0: 4,    fx: 'sys',     speed: 1.0,  text: 'You have ninety-nine new messages.', caption: 'You have 99 new messages.' },
      { id: 'v1',  b0: 25,   fx: 'you',     speed: 1.2,  text: 'Hi. It\'s me. Again.', caption: 'Hi. It’s me. Again.' },
      { id: 'v2',  b0: 29,   fx: 'you',     speed: 1.2,  text: 'I\'ve called you ninety-nine times.', caption: 'I’ve called you 99 times.' },
      { id: 'v3',  b0: 34,   fx: 'you',     speed: 1.2,  text: 'Every night I tell you not to open the door.' },
      { id: 'v4',  b0: 41,   fx: 'glitch',  speed: 1.3,  text: 'Every night, you open it.' },
      { id: 'c1',  b0: 66,   fx: 'child',   speed: 1.3,  text: 'Mommy? Can I come in?' },
      { id: 'v6',  b0: 76,   fx: 'whisper', speed: 1.4,  text: 'There\'s room for one more out here.', caption: 'There’s room for one more out here.' },
    ],
    events: { notify: [1.5, 3], tapPlay: 23.5, playAll: 45.5, chorus: [46, 58.5], knocks: 85, title: 89.5, silence: 95.5 },
  },
  // ------------------------------------------------------------ PART 5: DON'T ANSWER
  5: {
    title: 'DON’T ANSWER',
    shots: [['call', 0], ['dial', 24], ['chat', 36], ['door', 46], ['clock', 64], ['call2', 76], ['title', 88], ['black', 95.5]],
    chat: CHAT5,
    voice: [
      { id: 'v1', b0: 10.5, fx: 'you',     speed: 1.25, text: 'Pick up.' },
      { id: 'v2', b0: 21,   fx: 'you',     speed: 1.25, text: 'I can hear you breathing.' },
      { id: 'o1', b0: 26,   fx: 'op',      speed: 1.05, text: 'Nine one one. What is your emergency?', caption: '911. What is your emergency?' },
      { id: 'o2', b0: 30.5, fx: 'op',      speed: 1.05, text: 'We\'re getting the same call from every phone in your building.', caption: 'We’re getting the same call from every phone in your building.' },
      { id: 'v3', b0: 47,   fx: 'you',     speed: 1.2,  text: 'You don\'t have to open the door.', caption: 'You don’t have to open the door.' },
      { id: 'v4', b0: 53,   fx: 'you',     speed: 1.3,  text: 'Just answer.' },
      { id: 'v5', b0: 57,   fx: 'you',     speed: 1.2,  text: 'If you answer, one of us gets to come home.' },
      { id: 'v6', b0: 63,   fx: 'whisper', speed: 1.4,  text: 'Please.' },
      { id: 'v7', b0: 70,   fx: 'glitch',  speed: 1.2,  text: 'Answer. Answer. Answer.' },
      { id: 'v8', b0: 84,   fx: 'whisper', speed: 1.4,  text: 'Thank you.' },
    ],
    events: { rings: [[1, 9.5], [12.5, 20], [76.5, 80.5]], missed: [9.5, 20], dial: 24.5, answered: 80.5, title: 88, silence: 95.5 },
  },
  // ------------------------------------------------------------ PART 6: SUNRISE
  6: {
    title: 'SUNRISE',
    shots: [['dawn', 0], ['open', 14], ['hall', 26], ['floorphone', 48], ['holder', 68], ['final', 82], ['black', 95.5]],
    voice: [
      { id: 'c1', b0: 38,   fx: 'child',   speed: 1.3,  text: 'Are you the new one?' },
      { id: 'v1', b0: 52,   fx: 'you',     speed: 1.2,  text: 'Hi. It\'s me. From the first night.', caption: 'Hi. It’s me. From the first night.' },
      { id: 'v2', b0: 57.5, fx: 'you',     speed: 1.25, text: 'Somebody has to hold it.' },
      { id: 'v3', b0: 62.5, fx: 'you',     speed: 1.25, text: 'Last night, you answered.' },
      { id: 'v4', b0: 73,   fx: 'whisper', speed: 1.4,  text: 'It\'s yours now.', caption: 'It’s yours now.' },
    ],
    events: { doorOpen: 15.5, notify: 49.5, tapPlay: 51, hold: 69.5, freeze: 70.5, final: 82, knocks: [90, 91, 92], silence: 95.5 },
  },
};

export function make(part) {
  const P = PARTS[part];
  const shots = P.shots.map(([name, b0], i) => ({ name, b0, b1: i + 1 < P.shots.length ? P.shots[i + 1][1] : TOTAL_BEATS }));
  const TL = {
    PART: part, TITLE: P.title, BPM, FPS, DURATION, BEAT, TOTAL_BEATS, CAPTION_HOLD,
    beatOf: (t) => t / BEAT, timeOf: (b) => b * BEAT,
    SHOTS: shots, CUTS: shots.slice(1).map((s) => s.b0),
    VOICE: P.voice, EVENTS: P.events, CHAT: P.chat || [],
    shotAt(b) { for (const s of shots) if (b >= s.b0 && b < s.b1) return s; return shots[shots.length - 1]; },
  };
  // world clock: only Part 6 freezes, when you become the holder
  const fz = P.events.freeze;
  TL.worldSpeed = (b) => (part === 6 && b >= fz ? Math.max(0, 1 - (b - fz) / 0.2) : 1);
  TL.worldBeats = (b) => (part === 6 && b > fz ? fz + Math.min(b - fz, 0.2) / 2 : b);
  // Part 4 peephole: the lights die, and every time they come back there are more of them
  TL.FLICKER = part === 4 ? [[61.5, 61.9], [64.6, 65.2], [68.4, 69.2], [71.5, 72.4], [74.6, 75.4], [79.2, 80.4], [82.6, 85]] : [];
  TL.lightOn = (b) => { for (const [a, c] of TL.FLICKER) if (b >= a && b < c) return 0; return 1; };
  TL.crowd = (b) => {
    if (part !== 4) return 0;
    const steps = [[58.5, 0], [61.9, 1], [65.2, 3], [69.2, 6], [72.4, 11], [75.4, 18], [80.4, 30]];
    let n = 0; for (const [sb, c] of steps) if (b >= sb) n = c; return n;
  };
  TL.feetPairs = (b) => (part === 5 ? (b < 48 ? 1 : Math.min(8, 1 + Math.floor((b - 48) / 2))) : 0);
  TL.missedCalls = (b) => {
    if (part !== 5) return 0;
    if (b < 9.5) return 0; if (b < 20) return 1; if (b < 64) return 2 + Math.floor(Math.max(0, b - 46) / 4);
    const keys = [[64, 23], [67, 61], [70, 87], [73, 98]];
    let n = 12; for (const [kb, c] of keys) if (b >= kb) n = c; return n;
  };
  TL.clockText = (b) => {
    if (part === 4) return b < 58.5 ? '3:13' : '3:14';
    if (part === 5) { const keys = [[0, '3:07'], [24, '3:09'], [46, '3:16'], [64, '4:12'], [67, '5:03'], [70, '5:58'], [73, '6:31'], [76, '6:40']]; let s = '3:07'; for (const [kb, c] of keys) if (b >= kb) s = c; return s; }
    const keys = [[0, '6:41'], [26, '6:44'], [48, '6:47']]; let s = '6:41'; for (const [kb, c] of keys) if (b >= kb) s = c; return s;
  };
  TL.cueList = () => {
    const s = (b) => +(b * BEAT).toFixed(5);
    const conv = (v) => (Array.isArray(v) ? v.map(conv) : s(v));
    return {
      part, bpm: BPM, fps: FPS, duration: DURATION, beat: BEAT,
      scenes: shots.map((x, i) => ({ id: i + 1, name: x.name, b0: x.b0, b1: x.b1, t0: s(x.b0), t1: s(x.b1) })),
      cuts: TL.CUTS.map(s), voice: P.voice.map((v) => ({ ...v, t0: s(v.b0) })),
      events: Object.fromEntries(Object.entries(P.events).map(([k, v]) => [k, conv(v)])),
      chat: (P.chat || []).map(([b]) => s(b)),
      flicker: TL.FLICKER.map(([a, c]) => [s(a), s(c)]),
    };
  };
  return TL;
}
