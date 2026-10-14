# THE OFFER

A 60-second psychological-thriller teaser, rendered entirely from code. No video models, stock footage, stock audio or After Effects. The only external files are two open-source fonts.

*You have been offered the Stillness: freeze time, and everything in it, except yourself. Ninety-nine others have received this offer. Do you take it?*

## How it's built

| Piece | File | What it does |
|---|---|---|
| Timeline | `src/timeline.js` | The single source of truth: a 128 BPM grid (128 beats = 60 s), shots and cuts, story lines, the **world clock** (speed keyframes that stall at every freeze), the acceptance schedule, the heartbeat, and the cue-list export. |
| Renderer | `src/render.js`, `src/gl.js` | Every frame is a pure function of time. WebGL2 draws the light, beam, particles (dust, coffee, birds), dot grid, amber dot and freeze ripple. Canvas 2D draws the type, the phone UI and the flat set pieces. "Frozen" means the world clock stalls while the amber dot's clock keeps running. Grain is seeded by the world clock, so the film grain freezes too. |
| Capture | `tools/render.mjs` | Headless Chrome (SwiftShader). Each frame averages 8 jittered sub-frames under a 180° shutter, and no sub-frame crosses a cut. Pixels come back in slices under 1 MB each and pipe straight into ffmpeg. The frame range is split across 4 workers. |
| Score | `audio/score.py` | Synthesized from `audio/cues.json`: sub drone, bowed-string tension, room tone, a pulse and a clock that both run on the world clock (so they cut out at each freeze), a heartbeat that quickens through scene 4, a chime per accepted dot, phone haptics, and total silence for the last beat. Mastered to -14 LUFS integrated, ≤ -1 dBTP. |
| Checks | `tools/check-timeline.mjs`, `tools/audio_report.py`, `tools/review.sh`, `tools/contact.py` | Checks that cuts land on beats and every line holds ≥ 1.5 s. Measures loudness per octave band, per scene and through a phone-speaker filter. Builds contact sheets pulled from the actual encodes. |

## The edit

| Beats | Time | Scene |
|---|---|---|
| 0–16 | 0–7.5 s | **The message.** 3:07 a.m., no sender. |
| 16–40 | 7.5–18.75 s | **The power.** Terms of service, then the freeze at beat 28. |
| 40–64 | 18.75–30 s | **The catch.** Pull back into a grid of 100. |
| 64–96 | 30–45 s | **The math.** Decline or accept; the counter goes 14, then 23. |
| 96–120 | 45–56.25 s | **The realization.** The clock stutters and the count runs to 99. |
| 120–128 | 56.25–60 s | **The question.** A thumb hovers, then THE OFFER. Everything freezes at beat 127; the amber dot moves one beat longer, in silence. |

## Build

```bash
pip install numpy scipy pyloudnorm soundfile pillow
tools/deliver.sh                 # about 2 h on 4 cores: both renders, score, mux, phone copy, poster, styleframes
SKIP_RENDER=1 tools/deliver.sh   # reuse the rendered video, rebuild everything else
```

Preview one moment in a browser: serve the folder (`npx http-server .`), open `src/index.html?w=1920&h=1080`, then run `renderStill(13.5)` in the console. Add `&w=1080&h=1920` for the vertical layout.

Fonts: [Inter](https://github.com/rsms/inter) and [Instrument Serif](https://github.com/Instrument/instrument-serif), both SIL Open Font License, from the Google Fonts repository.
