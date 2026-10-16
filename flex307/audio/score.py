"""307: OCCUPIED — score and sound, on the story's own cue points.

    python3 audio/score.py
Horror until the lamp clicks on at 34 s: drone, hum, heartbeat, knocks, ink. Then a brass hit,
the stamp, a stupid little fanfare, a slide whistle for the retreat, and a music box for the end.
Writes out/score.wav at -14 LUFS integrated, <= -1 dBTP.
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
from story import CHAT, FLEX_AT, KNOCKS, STAMP_AT  # noqa: E402

SR = 48000
N = 60 * SR
t = np.arange(N) / SR
rng = np.random.default_rng(307)
L, R = np.zeros(N), np.zeros(N)
mL, mR = np.zeros(N), np.zeros(N)
MUS = (mL, mR)


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def bp(x, a, b, o=2):
    return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)


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


def reverb(x, rt=1.8, wet=0.3, seed=1):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


def env(n, a, d):
    tt = np.arange(n) / SR
    return np.minimum(1, tt / max(a, 1e-4)) * np.exp(-tt / d)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def ss(a, b, x):
    k = np.clip((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


def thud(f, dur, seed, bright=0.6):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 18)
    body += 0.6 * np.sin(2 * np.pi * f * 2.6 * tt) * np.exp(-tt * 30)
    return np.tanh(2 * (body + bp(r.standard_normal(n), 800, 5000) * np.exp(-tt * 160) * bright))


# ---------------------------------------------------------------- horror, 0-34 s
horror = 1 - ss(33.6, 33.65, t)
drone = (np.sin(2 * np.pi * 36.7 * t) + 0.5 * np.sin(2 * np.pi * 55.0 * t + 0.4 * np.sin(2 * np.pi * 0.11 * t))
         + 0.25 * np.sin(2 * np.pi * 73.4 * 1.004 * t))
drone *= (0.5 + 0.5 * ss(0, 6, t)) * (0.7 + 0.3 * ss(17, 30, t)) * horror
place(drone * 0.16, 0, bus=MUS)
air = lp(rng.standard_normal(N), 700) * 0.035 * horror
L += air
R += np.roll(air, 4000)
# the hallway's fluorescent hum, whenever we can see the gap; it stutters with the strobe
gapvis = ((t >= 4) & (t < 11)) | ((t >= 17) & (t < 19.6)) | ((t >= 25) & (t < 33.6))
strobe = np.where((t >= 25) & (t < 33.6), 0.5 + 0.5 * np.sign(np.sin(t * 37.0) * np.sin(t * 11.3 + 1) - 0.55), 0)
hum = sum(np.sin(2 * np.pi * 120 * k * t) / k for k in (1, 2, 3, 5)) * lp(gapvis.astype(float), 20)
hum *= 1 - 0.85 * strobe
place(bp(hum, 100, 2000) * 0.03, 0, 0.2)
# heartbeat from the face shot on, getting faster
hb_t, bpm = 11.2, 62
while hb_t < 33.4:
    for k, g in ((0, 1.0), (0.16, 0.6)):
        n = int(0.25 * SR)
        tt = np.arange(n) / SR
        beat = lp(np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 22), 200)
        place(beat, hb_t + k, 0.5 * g * (0.6 + 0.4 * ss(11, 30, hb_t)), bus=MUS)
    bpm = 62 + 58 * ss(11, 33, hb_t)
    hb_t += 60 / bpm
# knocks on the door: hard ones at night, two soft ones at the end
for k in KNOCKS:
    soft = k > 50
    place(reverb(thud(95 if not soft else 150, 0.7, int(k * 10), 0.3 if soft else 0.6), 1.0, 0.25, 9), k,
          0.25 if soft else 0.75, 0.05)
# paper under the door, then the ink: wet, slow, everywhere
n = int(1.6 * SR)
place(bp(rng.standard_normal(n), 1500, 7000) * np.sin(np.pi * np.arange(n) / n) * 0.25, 17.2, 0.7)
ink = bp(rng.standard_normal(N), 120, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.7 * t + 3 * np.sin(2 * np.pi * 0.4 * t))) ** 3
ink *= ss(17.5, 19, t) * (1 - ss(33.4, 33.6, t)) + ss(45.3, 45.6, t) * (1 - ss(48.4, 48.9, t)) * 0.8
place(ink * 0.35, 0, -0.1)
# it stands up: a groan that climbs
n = int(3.4 * SR)
tt = np.arange(n) / SR
groan = np.sin(2 * np.pi * np.cumsum(38 + 30 * (tt / tt[-1]) ** 2) / SR)
groan = bp(np.tanh(3 * groan) + 0.3 * rng.standard_normal(n), 40, 600) * np.sin(np.pi * tt / tt[-1]) ** 0.5
place(groan * 0.4, 25.4, bus=MUS)
# its eyes open: a thin glassy shimmer
n = int(2.5 * SR)
tt = np.arange(n) / SR
shim = sum(np.sin(2 * np.pi * f * tt) for f in (2637, 2794, 3951)) * env(n, 0.02, 0.8)
place(reverb(shim, 2.5, 0.5, 4) * 0.05, 27.6, 0.3, bus=MUS)
# a riser into the dark, then nothing; then the lamp
n = int(2.0 * SR)
tt = np.arange(n) / SR
riser = bp(rng.standard_normal(n), 300, 6000) * (tt / tt[-1]) ** 3 + 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 900 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1]) ** 2
place(riser * 0.35, 31.6, bus=MUS)
n = int(0.05 * SR)
place(bp(rng.standard_normal(n), 1500, 8000) * np.exp(-np.arange(n) / (0.004 * SR)), FLEX_AT - 0.05, 0.6, -0.3)  # click

# ---------------------------------------------------------------- the reveal, 34-42 s
def brass(f, dur, vel=1.0, att=0.03):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = sum(signal.sawtooth(2 * np.pi * f * d * tt + p) for d, p in ((1, 0), (1.004, 1.3), (0.996, 2.1))) / 3
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * tt) * ss(0.2, 0.5, tt)
    s = sum(signal.sawtooth(2 * np.pi * np.cumsum(f * d * vib) / SR + p) for d, p in ((1, 0), (1.004, 1.3), (0.996, 2.1))) / 3
    cutoff_env = np.minimum(1, tt / att) * np.exp(-tt / 0.6) * 0.7 + 0.3
    out = np.zeros(n)
    blocks = 8
    for k in range(blocks):                                  # a filter that opens and settles
        a, b = k * n // blocks, (k + 1) * n // blocks
        out[a:b] = lp(s, 500 + 4500 * cutoff_env[a], 2)[a:b]
    rel = np.minimum(1, (dur - tt) / 0.12)
    return out * np.minimum(1, tt / att) * rel * vel


def chord(notes, dur, at, gain, vel=1.0):
    for m in notes:
        place(brass(hz(m), dur, vel), at, gain / len(notes) ** 0.5, bus=MUS)


def timp(f, at, gain):
    place(reverb(thud(f, 1.6, int(at * 7), 0.2), 1.6, 0.3, 2), at, gain, bus=MUS)


# the hit: Bb major, everything at once
chord([46, 58, 62, 65, 70], 1.6, FLEX_AT, 0.9)
timp(58, FLEX_AT, 0.9)
n = int(0.6 * SR)
place(hp(rng.standard_normal(n), 3000) * np.exp(-np.arange(n) / (0.05 * SR)) * 0.5, FLEX_AT, 0.6)   # flash pop
n = int(1.2 * SR)
place(lp(rng.standard_normal(n), 300) * env(n, 0.002, 0.35) * 1.2 + thud(48, 1.2, 77, 0.9) * 0.8, STAMP_AT, 0.9)  # the stamp
# the fanfare: dumb and proud
melody = [(36.7, 58, 0.25), (37.0, 62, 0.25), (37.3, 65, 0.25), (37.6, 70, 0.9), (38.6, 69, 0.25), (38.9, 70, 0.25),
          (39.2, 72, 0.6), (39.9, 74, 1.6)]
for at, m, d in melody:
    place(brass(hz(m), d, 1.0, 0.02), at, 0.32, bus=MUS)
chord([46, 53, 58, 62], 2.6, 37.6, 0.5, 0.8)
chord([51, 58, 63, 67], 1.3, 39.2, 0.5, 0.8)
chord([46, 53, 58, 62, 65], 2.4, 39.9, 0.6, 0.9)
for k in range(16):                                           # a timpani roll into the last chord
    timp(46 + 12, 38.8 + k * 0.07, 0.12 + 0.02 * k)
timp(46, 39.9, 0.9)

# ---------------------------------------------------------------- the retreat, 42-50 s
for at, _, _ in CHAT:                                         # notification: two soft marimba notes
    for k, m in ((0, 88), (0.11, 93)):
        n = int(0.5 * SR)
        tt = np.arange(n) / SR
        place((np.sin(2 * np.pi * hz(m) * tt) + 0.3 * np.sin(2 * np.pi * hz(m) * 4 * tt) * np.exp(-tt * 30)) * np.exp(-tt * 9), at + k, 0.12, 0.1)
n = int(3.0 * SR)                                             # the slide whistle as it shrinks
tt = np.arange(n) / SR
f = 1500 * 2 ** (-2.2 * (tt / tt[-1]) ** 1.3)
whistle = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.01 * np.sin(2 * np.pi * 6 * tt))) / SR) + 0.1 * bp(rng.standard_normal(n), 1000, 3000)
place(whistle * np.minimum(1, tt / 0.05) * np.minimum(1, (tt[-1] - tt) / 0.2) * 0.12, 45.6, 0.1, bus=MUS)
n = int(0.3 * SR)                                             # and the last of it goes under the door
place(lp(rng.standard_normal(n), 900) * np.exp(-np.arange(n) / (0.06 * SR)), 48.7, 0.35)
# warm room tone now the lamp is on
roomtone = lp(rng.standard_normal(N), 400) * 0.02 * ss(34, 35, t)
L += roomtone
R += np.roll(roomtone, 3000)

# ---------------------------------------------------------------- a music box for the end, 50-60 s
def pluck(f, dur=2.5):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 3.01 * tt) * np.exp(-tt * 6)
            + 0.15 * np.sin(2 * np.pi * f * 5.2 * tt) * np.exp(-tt * 12)) * np.exp(-tt * 2.2)


box = np.zeros(N)
for i, (at, m) in enumerate([(50.6, 82), (50.9, 86), (51.2, 89), (51.5, 94), (52.4, 93), (52.7, 94), (53.0, 96),
                             (53.6, 98), (55.8, 82), (56.1, 86), (56.4, 89), (56.7, 94), (57.4, 89), (58.1, 94)]):
    p = pluck(hz(m - 12))
    a = int(at * SR)
    b = min(N, a + len(p))
    box[a:b] += p[: b - a] * 0.6
place(reverb(box, 2.2, 0.35, 5) * 0.12, 0, bus=MUS)

# ---------------------------------------------------------------- voices, and the music ducking under them
v, _ = sf.read('out/voice.wav')
venv = lp(np.abs(v), 8)
duck = minimum_filter1d(1 - 0.75 * np.clip(venv / (venv.max() * 0.12), 0, 1), int(0.35 * SR))
L += mL * duck
R += mR * duck
VG = 1.3
L += v * VG
R += v * VG

# ---------------------------------------------------------------- master
fade = np.ones(N)
fade[-int(0.8 * SR):] = np.linspace(1, 0, int(0.8 * SR)) ** 2
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

tp = true_peak(mix)
if tp > -1.0:                                                 # the last fraction of a dB: a plain trim
    mix *= 10 ** ((-1.05 - tp) / 20)
lines = json.load(open('out/lines.json'))
bed = np.stack([L - VG * v, R - VG * v], axis=1)
vv = np.stack([VG * v, VG * v], axis=1)
worst = 99
for ln in lines:
    a, b2 = int(ln['t0'] * SR), int(ln['t1'] * SR)
    sp = lambda x: hp(x.T, 300, 4).T  # noqa: E731
    d = m.integrated_loudness(sp(vv[a:b2])) - m.integrated_loudness(sp(bed[a:b2]))
    print(f'  {ln["text"]:34s} {d:+.1f} dB over the bed')
    worst = min(worst, d)
sf.write('out/score.wav', mix.astype(np.float32), SR, subtype='PCM_24')
print(f'{m.integrated_loudness(mix):.2f} LUFS, true peak {true_peak(mix):.2f} dBTP, weakest line {worst:+.1f} dB')
