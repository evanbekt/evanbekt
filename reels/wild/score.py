"""WILD SINGLES — forest, river and wind under soft strings and a harp; camera clicks on the long-lens
shots; a choir when he smiles; a hush for the punchline."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from sound import SR, Mix, bp, hz, lp, pad, pluck, reverb  # noqa: E402

M = Mix(os.path.dirname(os.path.abspath(__file__)), 11)
B = M.tl['beats']
t, N, rng = M.t, M.N, M.rng

# forest air everywhere, the river under the river shot, birds now and then
air = lp(M.noise(N), 900) * 0.05
M.place(air, 0, bus='fx')
r0, r1 = B[1]['t0'], B[1]['t1']
river = bp(M.noise(N), 300, 5000) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t)) * np.clip((t - r0 + 0.5) / 1.0, 0, 1) * np.clip((r1 + 0.6 - t) / 0.8, 0, 1)
M.place(river * 0.08, 0, bus='fx')
at = 1.0
while at < N / SR - 3:
    n = int(0.12 * SR)
    x = np.arange(n) / SR
    f0 = rng.uniform(2500, 4200)
    chirp = np.sin(2 * np.pi * np.cumsum(f0 + 1500 * np.sin(2 * np.pi * x / 0.12)) / SR) * np.sin(np.pi * x / x[-1])
    for k in range(rng.integers(2, 4)):
        M.place(chirp * 0.05, at + k * 0.16, pan=rng.uniform(-0.8, 0.8), bus='fx')
    at += rng.uniform(1.8, 3.5)

# strings: A minor to F to C to G, slow; a harp arpeggio over them
prog = [[57, 64, 69, 72], [53, 60, 65, 69], [48, 55, 64, 67], [55, 62, 67, 71]]
bar = 3.2
k = 0
while k * bar < N / SR:
    M.place(reverb(pad(prog[k % 4], bar + 1.0, 1200, 1.0, 1.0, k), 2.5, 0.3, 2) * 0.16, k * bar)
    for j, m in enumerate(prog[k % 4] + [prog[k % 4][1] + 12]):
        M.place(pluck(hz(m + 12), 2.0, 0.6) * 0.06, k * bar + 0.8 + j * 0.22, pan=-0.3 + 0.15 * j)
    k += 1

# long-lens shots: a shutter burst as they open
for b in B:
    if b.get('viewfinder'):
        for j in range(3):
            n = int(0.06 * SR)
            M.place(bp(M.noise(n), 2000, 9000) * np.exp(-np.arange(n) / (0.008 * SR)), b['t0'] + 0.25 + j * 0.13, 0.25, 0.2, bus='fx')
# he smiles: a choir swell
rare = next(b for b in B if b.get('rare'))
sm = rare['lines'][1]['t0']
for m in (60, 64, 67, 72, 76):
    n = int(4.0 * SR)
    x = np.arange(n) / SR
    from scipy import signal as _s
    s = _s.sawtooth(2 * np.pi * hz(m) * x * (1 + 0.003 * np.sin(2 * np.pi * 5 * x)))
    s = bp(s, 500, 1100) + 0.5 * bp(s, 2300, 3100)
    M.place(reverb(s * np.minimum(1, x / 0.8) * np.minimum(1, (4 - x) / 1.2), 3, 0.4, 5) * 0.05, sm - 0.4)
# the end: a hush before "Is he single?", then a harp gliss on "Yes."
end = B[-1]
yes = end['lines'][2]['t0']
for j, m in enumerate([60, 64, 67, 72, 76, 79, 84, 88]):
    M.place(pluck(hz(m), 2.5, 0.5) * 0.09, yes + 0.15 + j * 0.06, pan=-0.4 + 0.1 * j)
M.mus[:, int((end['lines'][1]['t0'] - 0.4) * SR): int((yes + 0.1) * SR)] *= 0.25
M.master(duck_depth=0.5, voice_gain=1.3)
