"""DEVELOPING — score and sound for one part, built from the story's own cue points.

    python3 audio/score.py PART

Soft piano in D minor with tape hiss; every part after the first opens with a rewind.
Polaroid flash, shutter and motor, pen on paper, knocks, paper. Voices on top, music ducked.
Writes out/score{PART}.wav at -14 LUFS integrated, <= -1 dBTP.
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
rng = np.random.default_rng(1000 + PART)
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


def piano(f, dur=3.0, vel=1.0):
    """A soft felt-piano note: a few slightly inharmonic partials, fast attack, long decay."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = np.zeros(n)
    for k, a in [(1, 1.0), (2, 0.45), (3, 0.18), (4, 0.1), (5, 0.05)]:
        fk = f * k * (1 + 0.0004 * k * k)
        s += a * np.sin(2 * np.pi * fk * tt) * np.exp(-tt * (1.2 + 0.9 * k))
    s *= np.minimum(1, tt / 0.006)
    s += 0.02 * bp(rng.standard_normal(n), 200, 2000) * np.exp(-tt * 40)        # the felt hammer
    return lp(s, 2600 + 1600 * vel) * vel


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------- music: D minor, 72 BPM, slow arpeggios
BEAT = 60 / 72
CHORDS = [[50, 57, 62, 65, 69], [46, 53, 58, 62, 65], [41, 48, 53, 57, 60], [45, 52, 57, 61, 64]]   # Dm Bb F A
music = np.zeros(N)
start = 2.0 if PART > 1 else 4.0
end = P['shots'][-1]['t0'] + 3.0
b = 0
while start + b * BEAT < end:
    ch = CHORDS[(b // 8) % 4]
    at = start + b * BEAT
    step = b % 8
    idx = [0, 2, 3, 4, 3, 2, 1, 2][step]
    vel = 0.55 if step == 0 else 0.32
    note = piano(hz(ch[idx] + 12), 3.0, vel)
    i = int(at * SR)
    j = min(N, i + len(note))
    music[i:j] += note[: j - i]
    if step == 0:                                    # the bass, once a bar
        bn = piano(hz(ch[0] - 12), 5.0, 0.5)
        j = min(N, i + len(bn))
        music[i:j] += bn[: j - i]
    b += 1
# one last low note on the title, then the piano stops
tn = P['shots'][-1]['t0']
place(piano(hz(38), 6.0, 0.8), tn, 0.5, bus=MUS)
music = reverb(music, 2.4, 0.35, 3)
flutter = 1 + 0.03 * np.sin(2 * np.pi * 0.7 * t) + 0.015 * np.sin(2 * np.pi * 5.3 * t)   # old tape
mL += music * flutter * 0.42
mR += np.roll(music, 600) * flutter * 0.42
hiss = hp(bp(rng.standard_normal(N), 1500, 9000), 1500) * 0.006
L += hiss
R += np.roll(hiss, 999)
room = lp(rng.standard_normal(N), 500) * 0.03
L += room
R += np.roll(room, 7000)

# ---------------------------------------------------------------- the rewind, at the top of every part but the first
if PART > 1:
    seg = music[int(30 * SR): int(32.2 * SR)][::-1] * np.linspace(0.2, 1.0, int(2.2 * SR))
    place(seg, 0.0, 0.9, bus=MUS)
    n = int(1.9 * SR)
    tt = np.arange(n) / SR
    whine = np.sin(2 * np.pi * np.cumsum(900 + 2600 * (tt / tt[-1]) ** 2) / SR) * 0.15
    whine += bp(rng.standard_normal(n), 2000, 7000) * 0.3 * np.sin(np.pi * tt / tt[-1])
    place(whine * np.sin(np.pi * tt / tt[-1]), 0.05, 0.25)
    place(bp(rng.standard_normal(int(0.05 * SR)), 800, 4000) * np.exp(-np.arange(int(0.05 * SR)) / (0.01 * SR)), 1.95, 0.4)  # clunk


# ---------------------------------------------------------------- the camera
def flash_charge(dur=0.7):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(2200 + 4500 * tt / dur) / SR) * (tt / dur) ** 1.5 * 0.2


def shutter():
    n = int(0.12 * SR)
    tt = np.arange(n) / SR
    c = bp(rng.standard_normal(n), 1500, 8000) * np.exp(-tt * 90)
    c[int(0.05 * SR):] += bp(rng.standard_normal(n - int(0.05 * SR)), 1000, 6000) * np.exp(-tt[: n - int(0.05 * SR)] * 120) * 0.7
    return c


def motor(dur=0.9):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    m = np.sign(np.sin(2 * np.pi * 140 * tt)) * 0.3 + np.sin(2 * np.pi * 280 * tt) * 0.2
    m = bp(m, 150, 3000) * np.minimum(1, np.minimum(tt / 0.02, (dur - tt) / 0.05))
    return m + bp(rng.standard_normal(n), 2000, 6000) * 0.05


def pen(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    strokes = (np.sin(2 * np.pi * 7 * tt + 3 * np.sin(2 * np.pi * 1.3 * tt)) > -0.2).astype(float)
    strokes = lp(strokes, 30, 1)
    return bp(rng.standard_normal(n), 2500, 8000) * strokes * 0.35


def thud(f, dur, seed):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 18)
    body += 0.6 * np.sin(2 * np.pi * f * 2.6 * tt) * np.exp(-tt * 30)
    return np.tanh(2 * (body + bp(r.standard_normal(n), 800, 5000) * np.exp(-tt * 160) * 0.6))


def paper(dur=0.5):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return bp(rng.standard_normal(n), 1500, 7000) * np.sin(np.pi * tt / tt[-1]) * 0.25


for tf in P.get('flashes', []):
    place(flash_charge(), tf - 0.75, 1.0, 0.1)
    place(shutter(), tf, 0.8)
for s in P['shots']:
    if s.get('eject') is not None:
        place(motor(), s['eject'] + 0.1, 0.35, 0.05)
    if s['kind'] == 'polaroid' and s.get('write') is not None:
        place(pen(max(1.2, 0.075 * len(s['note']))), s['write'], 0.5, -0.1)
    if s.get('scrawl'):
        place(pen(1.6), s['scrawl_t'], 0.6, 0.1)
    for k in s.get('knocks', []):
        place(reverb(thud(92, 0.8, int(k * 10)), 1.0, 0.25, 9), k, 0.55, 0.05)
    if s['kind'] in ('desk', 'title'):
        place(paper(), s['t0'] + 0.1, 0.6)
    if s.get('pull'):
        place(paper(1.2), s['pull'][0], 0.6)
    if s.get('slip'):
        place(paper(1.8), s['slip'][0], 0.5)
        place(paper(0.3), s['slip'][1], 0.4)
    if s.get('feet') is not None:
        for k in range(2):
            place(lp(thud(55, 0.6, 77 + k), 600), s['feet'] + 0.6 * k, 0.25)

# ---------------------------------------------------------------- voices, and the music ducking under them
v, _ = sf.read(f'out/voice{PART}.wav')
venv = lp(np.abs(v), 8)
duck = minimum_filter1d(1 - 0.82 * np.clip(venv / (venv.max() * 0.12), 0, 1), int(0.35 * SR))
L += mL * duck
R += mR * duck
L += v * 1.35
R += v * 1.35

# ---------------------------------------------------------------- master
fade = np.ones(N)
fade[-int(0.5 * SR):] = np.linspace(1, 0, int(0.5 * SR)) ** 2
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

# intelligibility: every line, voice vs everything else in the speech band
lines = json.load(open(f'out/lines{PART}.json'))
bed = np.stack([L - 1.35 * v, R - 1.35 * v], axis=1)
vv = np.stack([1.35 * v, 1.35 * v], axis=1)
worst = 99
for ln in lines:
    a, b2 = int(ln['t0'] * SR), int(ln['t1'] * SR)
    sp = lambda x: hp(x.T, 300, 4).T  # noqa: E731
    d = m.integrated_loudness(sp(vv[a:b2])) - m.integrated_loudness(sp(bed[a:b2]))
    worst = min(worst, d)
sf.write(f'out/score{PART}.wav', mix.astype(np.float32), SR, subtype='PCM_24')
print(f'part {PART}: {m.integrated_loudness(mix):.2f} LUFS, true peak {true_peak(mix):.2f} dBTP, '
      f'weakest line {worst:+.1f} dB over the bed (speech band)')
