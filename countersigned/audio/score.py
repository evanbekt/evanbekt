"""COUNTERSIGNED — score and sound for one part, from the shared skeleton of cue points.

    python3 audio/score.py PART

A low drone and a breathing, choir-like pad (formant-filtered noise) under the ink. Wet blooms,
typewriter keys, a pen on the signature, the fold, the eyes, the stamp. Voices on top, music ducked.
"""
import json
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from story import PARTS  # noqa: E402

SR = 48000
PART = int(sys.argv[1])
P = PARTS[PART]
N = 60 * SR
t = np.arange(N) / SR
rng = np.random.default_rng(2000 + PART)
L, R = np.zeros(N), np.zeros(N)
mL, mR = np.zeros(N), np.zeros(N)
MUS = (mL, mR)


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def bp(x, a, b, o=2):
    return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)


def env(keys):
    return np.interp(t, [k[0] for k in keys], [k[1] for k in keys])


def place(sig, at, gain=1.0, pan=0.0, bus=None):
    i = int(round(at * SR))
    if i >= N or i + len(sig) <= 0:
        return
    s = sig[max(0, -i): N - i] * gain
    i = max(0, i)
    a = (pan + 1) * np.pi / 4
    l_, r_ = (L, R) if bus is None else bus
    l_[i:i + len(s)] += s * np.cos(a)
    r_[i:i + len(s)] += s * np.sin(a)


def reverb(x, rt=2.5, wet=0.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 4500)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


# ---------------------------------------------------------------- the drone: low, a tritone above, breathing
root = [36.71, 34.65, 38.89, 32.70, 36.71, 30.87][PART - 1]
ph = 2 * np.pi * root * t
drone = 0.35 * np.sin(ph) + 0.25 * lp(np.tanh(2.2 * (np.sin(2 * ph) + 0.5 * np.sin(2 * ph * 1.414))), 500)
breath = 0.75 + 0.25 * np.sin(2 * np.pi * 0.13 * t)
d_env = env([(0, 0.2), (4, 0.4), (20, 0.6), (38, 0.7), (42, 1.0), (44, 0.5), (46, 0.9), (56, 0.8), (58.5, 0.2), (60, 0)])
mL += drone * breath * d_env
mR += drone * breath[::-1] * d_env


# ---------------------------------------------------------------- the choir: noise through vowel formants, like many mouths
def choir(f1, f2, f3, dur, seed):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    src = r.standard_normal(n)
    v = bp(src, f1 * 0.9, f1 * 1.1, 2) + 0.7 * bp(src, f2 * 0.93, f2 * 1.07, 2) + 0.3 * bp(src, f3 * 0.95, f3 * 1.05, 2)
    return v


pad = choir(500, 900, 2400, 60, 3) * env([(0, 0), (4, 0.3), (20, 0.5), (44, 0.2), (46, 1.0), (56, 0.8), (58.5, 0), (60, 0)])
pad2 = choir(300, 870, 2240, 60, 4) * env([(0, 0), (20, 0.3), (38, 0.6), (44, 0.2), (46, 0.9), (56, 0.7), (58.5, 0), (60, 0)])
mL += reverb(pad, 3.0, 0.5, 5) * 0.5
mR += reverb(pad2, 3.0, 0.5, 6) * 0.5


# ---------------------------------------------------------------- ink, paper, pen, keys
def bloom(dur, seed):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    src = r.standard_normal(n)
    u = tt / dur                                     # the filter opens as the ink spreads
    x = (lp(src, 400) * (1 - u) + lp(src, 1600) * u) * np.sin(np.pi * u) ** 2
    return x + 0.4 * np.sin(2 * np.pi * np.cumsum(60 + 40 * tt / dur) / SR) * np.sin(np.pi * tt / dur) ** 2


def key():
    n = int(0.05 * SR)
    tt = np.arange(n) / SR
    return bp(rng.standard_normal(n), 1500, 6000) * np.exp(-tt * 140) + 0.4 * np.sin(2 * np.pi * 180 * tt) * np.exp(-tt * 90)


def pen(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    strokes = lp((np.sin(2 * np.pi * 6 * tt + 2 * np.sin(2 * np.pi * 1.1 * tt)) > -0.3).astype(float), 30, 1)
    return bp(rng.standard_normal(n), 2500, 8000) * strokes * 0.4


def crinkle(dur):
    n = int(dur * SR)
    x = np.zeros(n)
    for _ in range(int(dur * 60)):
        i = rng.integers(0, n - 400)
        x[i:i + 400] += bp(rng.standard_normal(400), 2000, 9000) * np.exp(-np.arange(400) / 60) * rng.uniform(0.2, 1)
    return x * np.sin(np.pi * np.arange(n) / n)


def thud(f, dur, seed):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 14)
    return np.tanh(2 * (body + bp(r.standard_normal(n), 600, 4000) * np.exp(-tt * 120) * 0.5))


def glass(freq, dur, dec):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * freq * m * tt + m) for m, a in [(1, 1), (2.76, 0.5), (5.4, 0.25)]) * np.exp(-tt / dec) * np.minimum(1, tt / 0.004)


place(bloom(2.4, 1), 1.6, 0.35)                      # the drop on the card
place(reverb(bloom(10.0, 2), 2.0, 0.4, 7), 4.5, 0.4)  # the want blooms
place(reverb(bloom(4.0, 3), 2.0, 0.4, 8), 44.0, 0.55)  # the price spreads from the crease
lines = P['clause']
per = (36.5 - 21.0) / len(lines)
for i, ln in enumerate(lines):                       # the clause types itself
    st = 21.0 + i * per
    for k in range(len(ln)):
        if ln[k] != ' ':
            place(key(), st + per * 0.8 * k / max(1, len(ln)) + rng.uniform(0, 0.015), 0.12, rng.uniform(-0.2, 0.2))
    place(np.sin(2 * np.pi * 2093 * np.arange(int(0.25 * SR)) / SR) * np.exp(-np.arange(int(0.25 * SR)) / (0.06 * SR)), st + per * 0.8, 0.03)
if P['sig']:
    place(pen(2.5), 38.5, 0.55, -0.1)
place(reverb(bloom(2.5, 4), 1.5, 0.3, 9), 41.4, 0.3)  # the red bleeds
place(crinkle(1.8), 42.1, 0.7)                        # the fold
place(lp(thud(45, 1.6, 5), 200), 44.0, 0.6)
for k, f in enumerate([1244.5, 1661.2]):              # eyes open
    place(glass(f, 3.0, 0.9), 47.2 + k * 0.03, 0.05, -0.3 + 0.6 * k)
place(bp(rng.standard_normal(int(0.03 * SR)), 300, 2500) * np.exp(-np.arange(int(0.03 * SR)) / (0.005 * SR)), 47.0, 0.25)
place(reverb(thud(70, 1.4, 6), 1.2, 0.25, 10), 56.1, 0.7)   # COUNTERSIGNED
room = lp(rng.standard_normal(N), 400) * 0.02
L += room
R += np.roll(room, 9000)

# ---------------------------------------------------------------- voices on top
v, _ = sf.read(f'out/voice{PART}.wav')
venv = lp(np.abs(v), 8)
duck = minimum_filter1d(1 - 0.8 * np.clip(venv / (venv.max() * 0.12), 0, 1), int(0.35 * SR))
L += mL * duck
R += mR * duck
L += v * 1.3
R += v * 1.3

fade = np.ones(N)
fade[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR)) ** 2
mix = hp(np.stack([L * fade, R * fade], axis=1).T, 30).T
m = pyln.Meter(SR)
mix *= 10 ** ((-14.0 - m.integrated_loudness(mix)) / 20)


def true_peak(x):
    return 20 * np.log10(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0))) + 1e-12)


for _ in range(6):
    if true_peak(mix) <= -1.0:
        break
    g = np.minimum(1, 10 ** (-1.6 / 20) / np.maximum(np.max(np.abs(mix), axis=1), 1e-9))
    win = int(0.003 * SR)
    g = np.convolve(minimum_filter1d(g, 2 * win + 1), np.ones(win) / win, mode='same')
    a_r = np.exp(-1 / (0.12 * SR))
    mix *= (1 - np.maximum(1 - g, signal.lfilter([1 - a_r], [1, -a_r], 1 - g)))[:, None]
    mix *= 10 ** ((-14.0 - m.integrated_loudness(mix)) / 20)

lines_ = json.load(open(f'out/lines{PART}.json'))
bed = np.stack([L - 1.3 * v, R - 1.3 * v], axis=1)
vv = np.stack([1.3 * v, 1.3 * v], axis=1)
worst = 99
for ln in lines_:
    a, b = int(ln['t0'] * SR), int(ln['t1'] * SR)
    sp = lambda x: hp(x.T, 300, 4).T  # noqa: E731
    worst = min(worst, m.integrated_loudness(sp(vv[a:b])) - m.integrated_loudness(sp(bed[a:b])))
sf.write(f'out/score{PART}.wav', mix.astype(np.float32), SR, subtype='PCM_24')
print(f'part {PART}: {m.integrated_loudness(mix):.2f} LUFS, true peak {true_peak(mix):.2f} dBTP, weakest line {worst:+.1f} dB over the bed')
