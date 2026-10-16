"""HIM 30 — keynote music: soft kick and claps, a plucky arpeggio, an airy pad; a whoosh for every
card, a ding for every spec row, and the music held low under the fine print."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from sound import SR, Mix, clap, ding, hat, hz, kick, pad, pluck, reverb, whoosh  # noqa: E402

M = Mix(os.path.dirname(os.path.abspath(__file__)), 30)
B = M.tl['beats']
N, rng = M.N, M.rng
BPM = 112
q = 60 / BPM
start = B[1]['t0']               # the beat starts with the first product card
stop = B[-1]['t0']
prog = [[62, 66, 69, 73], [59, 62, 66, 69], [55, 59, 62, 66], [57, 61, 64, 69]]   # D Bm G A
i = 0
while start + i * q / 2 < stop:
    at = start + i * q / 2
    beat, bar = i // 2, i // 16
    ch = prog[bar % 4]
    if i % 2 == 0 and beat % 2 == 0:
        M.place(kick(0.6), at)
    if i % 2 == 0 and beat % 4 == 1 or i % 2 == 0 and beat % 4 == 3:
        M.place(clap(rng), at, 0.35)
    M.place(hat(rng), at, 0.06 + 0.04 * (i % 2), 0.3)
    M.place(pluck(hz(ch[i % 4] + 12), 0.6, 0.8), at, 0.07, -0.25 + 0.5 * (i % 2))
    if i % 16 == 0:
        M.place(reverb(pad(ch, q * 8 + 0.6, 2400, 0.4, 0.6, bar), 2, 0.3, 3) * 0.12, at)
    i += 1
# intro: just a pad and a bell on the name
M.place(reverb(pad([62, 69, 74], B[0]['t1'] + 0.5, 1800, 1.0, 0.8), 2.5, 0.3) * 0.13, 0.2)
M.place(ding(1175, 2.0) * 0.18, B[0]['lines'][1]['t0'], bus='fx')
M.place(ding(1760, 2.0) * 0.1, B[0]['lines'][1]['t0'] + 0.02, bus='fx')
for b in B[1:7]:
    M.place(whoosh(rng, 0.45), b['t0'] - 0.25, 0.25, bus='fx')
specs = B[7]
for j in range(8):
    M.place(ding(2093 if j % 2 else 1760, 0.4) * 0.08, specs['t0'] + 0.3 + j * 0.28, pan=-0.2 + 0.05 * j, bus='fx')
# end: one chord, then quiet for the fine print, then a final bell
end = B[-1]
M.place(reverb(pad([62, 66, 69, 74], end['t1'] - end['t0'], 2000, 0.3, 1.5), 2.5, 0.3) * 0.12, end['t0'])
M.mus[:, int((end['lines'][1]['t0'] - 0.2) * SR): int(end['lines'][1]['t1'] * SR)] *= 0.35
M.place(ding(1175, 2.5) * 0.15, end['lines'][2]['t1'] + 0.1, bus='fx')
M.master(duck_depth=0.55, voice_gain=1.25)
