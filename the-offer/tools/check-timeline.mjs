// Sanity checks on the edit: cuts on whole beats, every line readable for >= 1.5 s, beat grid = 60 s.
import * as TL from '../src/timeline.js';
let ok = true;
const fail = (m) => { ok = false; console.log('FAIL', m); };
if (Math.abs(TL.timeOf(TL.TOTAL_BEATS) - TL.DURATION) > 1e-9) fail('128 beats != 60 s');
for (const c of TL.CUTS) if (c !== Math.round(c)) fail(`cut at ${c} is off-beat`);
for (const s of TL.SCENES) if (s.b0 !== Math.round(s.b0)) fail(`scene ${s.id} off-beat`);
for (const l of TL.LINES) {
  const full = (Math.min(l.b1, 128) - (l.b1 >= 128 ? 0 : TL.FADE_OUT) - (l.b0 + TL.FADE_IN)) * TL.BEAT;
  const any = (Math.min(l.b1, 128) - l.b0) * TL.BEAT;
  console.log(`${l.id.padEnd(8)} ${TL.timeOf(l.b0).toFixed(2).padStart(6)}s  full ${full.toFixed(2)}s  visible ${any.toFixed(2)}s  "${l.text}"`);
  if (full < 1.5) fail(`${l.id} fully visible only ${full.toFixed(2)} s`);
}
const ticks = TL.tickEvents();
console.log('ticks', ticks.length, 'freezes', TL.freezeEvents().map((b) => b.toFixed(2)).join(' '));
console.log('scene5 ticks', ticks.filter((t) => t.b >= 96 && t.b < 120).map((t) => t.b.toFixed(2) + (t.dir < 0 ? '(back)' : '')).join(' '));
console.log('accepted at b92:', TL.acceptedCount(92), ' b82:', TL.acceptedCount(82), ' b119:', TL.acceptedCount(119.01));
console.log(ok ? 'ALL OK' : 'PROBLEMS');
