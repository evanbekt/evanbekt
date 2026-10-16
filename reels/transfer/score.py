"""TRANSFER NEWS — a stadium: crowd bed with swells, a news sting, a referee's whistle, a driving
drum loop, a tick-tick counter on the stats, and the crowd going up for HERE WE GO."""
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from sound import SR, Mix, boom, bp, hat, hz, kick, lp, reverb, snare, whoosh  # noqa: E402

M = Mix(os.path.dirname(os.path.abspath(__file__)), 94)
B = M.tl['beats']
t, N, rng = M.t, M.N, M.rng

# the crowd: a pink-ish roar, breathing, with swells on the big moments
crowd = bp(M.noise(N), 250, 3500) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.17 * t) * np.sin(2 * np.pi * 0.05 * t + 1))
swell = np.zeros(N)
here = B[7]['lines'][0]['t0']
for c, amp, w in [(B[1]['t0'] + 1.0, 0.8, 1.5), (B[3]['lines'][0]['t0'] + 0.8, 0.6, 1.2), (here + 0.4, 1.8, 2.5), (B[-1]['t0'] + 0.5, 1.0, 2.0)]:
    swell += amp * np.exp(-((t - c) / w) ** 2)
M.place(reverb(crowd * (0.35 + swell), 1.5, 0.3, 4) * 0.12, 0, bus='fx')


def whistle(dur=0.5):
    x = np.arange(int(dur * SR)) / SR
    trill = 1 + 0.5 * (np.sin(2 * np.pi * 28 * x) > 0)
    s = np.sin(2 * np.pi * np.cumsum(3100 + 120 * trill) / SR) * np.minimum(1, x / 0.02) * np.minimum(1, (dur - x) / 0.05)
    return s + 0.2 * bp(rng.standard_normal(len(x)), 2500, 4000)


M.place(whistle(0.35), 0.15, 0.25, bus='fx')
M.place(whistle(0.9), B[-1]['t1'] - 1.3, 0.25, bus='fx')
# the sting: brass stab and timpani on BREAKING
x = np.arange(int(1.2 * SR)) / SR
stab = sum(signal.sawtooth(2 * np.pi * hz(m) * d * x) for m in (50, 57, 62, 66) for d in (0.997, 1.003))
M.place(reverb(lp(stab / 8, 2500) * np.exp(-x * 3), 2, 0.3) * 0.5, B[0]['t0'] + 0.1)
M.place(boom(rng, 1.6, 52), B[0]['t0'] + 0.1, 0.7)
# the drum loop, 128 BPM, from the first player shot to the card
BPM = 128
q = 60 / BPM
start, stop = B[1]['t0'], B[7]['t0']
i = 0
while start + i * q / 2 < stop:
    at = start + i * q / 2
    beat = i // 2
    if i % 2 == 0:
        M.place(kick(0.75), at)
        if beat % 2 == 1:
            M.place(snare(rng), at, 0.4)
    M.place(hat(rng, 0.04), at + q / 4, 0.08, 0.3)
    if i % 8 == 0:
        n = int(q * 3.8 * SR)
        xx = np.arange(n) / SR
        root = [38, 38, 36, 41][(i // 8) % 4]
        M.place(lp(signal.sawtooth(2 * np.pi * hz(root) * xx), 300) * np.exp(-xx * 0.8) * np.minimum(1, xx / 0.01), at, 0.28)
    i += 1
# a whoosh on every cut, a counter ticking up on every stat
for b in B[1:9]:
    M.place(whoosh(rng, 0.4), b['t0'] - 0.3, 0.3, bus='fx')
    if b.get('stat'):
        for j in range(12):
            nn = int(0.015 * SR)
            M.place(bp(rng.standard_normal(nn), 3000, 8000) * np.exp(-np.arange(nn) / (0.003 * SR)), b['t0'] + 0.6 + j * 0.07, 0.15, 0.4, bus='fx')
# HERE WE GO: boom, and a gold-card shimmer
M.place(boom(rng, 2.0, 40), here, 0.8)
xx = np.arange(int(1.5 * SR)) / SR
shimmer = sum(np.sin(2 * np.pi * f * xx) for f in (2093, 2637, 3136, 4186)) * np.exp(-xx * 2.5)
M.place(reverb(shimmer, 2, 0.4) * 0.05, B[7]['t0'] + 0.8, bus='fx')
M.master(duck_depth=0.55, voice_gain=1.25)
