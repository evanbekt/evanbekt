"""THE OFFER — score and sound design, synthesized from the timeline's cue list.

    python3 audio/score.py audio/cues.json out/score.wav

Sounds that belong to the world (room tone, the pulse, the clock) run on the world clock,
so they stop when the world stops. Mastered to -14 LUFS integrated, -1 dBTP.
"""
import json
import sys

import numpy as np
import pyloudnorm as pyln
from scipy import signal

SR = 48000
cues = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
DUR = cues['duration']
BEAT = cues['beat']
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(128)
L = np.zeros(N)
R = np.zeros(N)


def b2s(b):
    return b * BEAT


def env_keys(keys):
    """Piecewise-linear envelope from [(beat, value), ...] sampled at audio rate."""
    xs = np.array([b2s(k[0]) for k in keys])
    ys = np.array([k[1] for k in keys])
    return np.interp(t, xs, ys)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, f0, f1, order=2):
    return signal.sosfilt(signal.butter(order, [f0, f1], 'band', fs=SR, output='sos'), x)


def place(sig, at, gain=1.0, pan=0.0):
    """Add a mono one-shot at time `at` (s), equal-power pan -1..1."""
    i = int(round(at * SR))
    if i >= N or i + len(sig) <= 0:
        return
    s = sig[max(0, -i): N - i] * gain
    i = max(0, i)
    a = (pan + 1) * np.pi / 4
    L[i:i + len(s)] += s * np.cos(a)
    R[i:i + len(s)] += s * np.sin(a)


def adsr(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR))
    return e


# World speed at audio rate (cue list holds it at 1/16-beat resolution).
ws_b = np.arange(len(cues['worldSpeed'])) / 16
world = np.abs(np.interp(t, ws_b * BEAT, cues['worldSpeed']))
world = lp(world, 60, 1)                      # 2-3 ms smoothing, keeps the cut abrupt
SILENCE_AT = cues['events']['silence']

# ---------------------------------------------------------------- sub drone (D)
f0 = 36.71
drone_env = env_keys([(0, 0), (3, 0.35), (16, 0.55), (24, 0.7), (28, 0.95), (40, 0.85), (47, 0.7), (64, 0.75),
                      (96, 0.8), (104, 0.6), (118, 0.38), (120, 0.6), (123, 1.0), (127, 1.0)])
# a very slow pitch sag after the freeze: the world settles
sag = 1 - 0.012 * env_keys([(0, 0), (28, 0), (30, 1), (64, 1), (66, 0), (128, 0)])
ph = 2 * np.pi * np.cumsum(f0 * sag) / SR
sub = np.sin(ph) + 0.35 * np.sin(2 * ph + 0.3)
# harmonics through saturation so the drone survives phone speakers
harm = np.tanh(2.2 * (np.sin(2 * ph * 1.0007) + 0.6 * np.sin(3 * ph * 0.9994) + 0.4 * np.sin(4 * ph * 1.0011)))
harm_dark = lp(harm, 380, 2)
harm_bright = lp(harm, 1400, 2)
bright = env_keys([(0, 0.1), (24, 0.3), (28, 0.6), (40, 0.3), (64, 0.45), (96, 0.6), (118, 0.1), (120, 0.4), (123, 1), (127, 1)])
dr = 0.24 * sub + 0.34 * (harm_dark * (1 - bright) + harm_bright * bright)
beat_mod = 1 + 0.06 * np.sin(2 * np.pi * 0.11 * t)
L += dr * drone_env * beat_mod * 0.9
R += dr * drone_env * (2 - beat_mod) * 0.9

# ---------------------------------------------------------------- strings: a bowed tension layer in the mids
def saw(freq, n_h=24):
    out = np.zeros(N)
    vib = 1 + 0.0025 * np.sin(2 * np.pi * (4.6 + freq % 1) * t + freq)
    ph = 2 * np.pi * np.cumsum(freq * vib) / SR
    for h in range(1, n_h + 1):
        if freq * h > 6000:
            break
        out += np.sin(h * ph) / h
    return out


def voice(freq, keys, gain):
    v = (saw(freq * 0.9985) + saw(freq * 1.0015)) * 0.5
    return v * env_keys(keys) * gain


strings_l = np.zeros(N)
strings_r = np.zeros(N)
# D minor, then a semitone rubs in as the count runs away
for f, keys, g, pan in [
    (146.83, [(0, 0), (8, 0), (16, 0.5), (27.5, 0.8), (28, 0.35), (40, 0.4), (47, 0.6), (64, 0.5), (96, 0.6), (118, 0.3), (120, 0.6), (127, 1)], 0.11, -0.3),
    (220.00, [(0, 0), (16, 0), (24, 0.4), (28, 0.6), (47, 0.5), (64, 0.45), (96, 0.55), (118, 0.25), (120, 0.6), (127, 1)], 0.09, 0.3),
    (174.61, [(0, 0), (40, 0), (47, 0.5), (64, 0.5), (80, 0.6), (96, 0.5), (118, 0.2), (120, 0.5), (127, 0.9)], 0.08, 0.1),
    (311.13, [(0, 0), (96, 0), (104, 0.25), (116, 0.5), (118, 0.2), (120, 0.6), (127, 1)], 0.05, -0.1),
    (293.66, [(0, 0), (60, 0), (64, 0.3), (96, 0.4), (120, 0.5), (127, 0.8)], 0.05, 0.2),
]:
    v = lp(voice(f, keys, g), 2200)
    a = (pan + 1) * np.pi / 4
    strings_l += v * np.cos(a)
    strings_r += v * np.sin(a)
L += strings_l * 1.45
R += strings_r * 1.45

# ---------------------------------------------------------------- room tone: stops with the world
pink = np.cumsum(rng.standard_normal(N)) * 0.02
pink = hp(pink, 40)
pink = pink / np.max(np.abs(pink))
air = lp(bp(rng.standard_normal(N), 300, 4000), 3000) * 0.5 + 0.5 * lp(pink, 900)
room_env = env_keys([(0, 0.8), (16, 1), (24, 1), (64, 1), (96, 1), (110, 0.6), (120, 0.7), (127, 1)])
air2 = lp(bp(rng.standard_normal(N), 300, 4000), 3000) * 0.5 + 0.5 * lp(np.roll(pink, 12345), 900)
L += air * world * room_env * 0.07
R += air2 * world * room_env * 0.07

# ---------------------------------------------------------------- the pulse: runs on world beats
def pulse_hit():
    n = int(0.28 * SR)
    tt = np.arange(n) / SR
    f = 52 + 40 * np.exp(-tt * 40)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14)
    click = bp(rng.standard_normal(n), 1500, 4500) * np.exp(-tt * 260) * 0.5
    return np.tanh(1.6 * body) * 0.75 + click + 0.5 * bp(np.tanh(3 * body), 180, 700)


wb = np.cumsum(np.interp(t, ws_b * BEAT, cues['worldSpeed'])) / SR / BEAT      # world beats
pulse_zone = env_keys([(0, 0), (15.9, 0), (16, 0.55), (27, 0.75), (28.3, 0.75), (28.31, 0), (95.9, 0), (96, 0.6), (119.9, 0.55),
                       (120, 0.7), (127, 0.9)])
crossing = np.nonzero(np.diff(np.floor(wb + 1e-6)) > 0)[0]
ph_ = pulse_hit()
for i in crossing:
    g = pulse_zone[i]
    if g > 0.01 and i / SR < SILENCE_AT:
        place(ph_, i / SR, 0.5 * g)

# ---------------------------------------------------------------- clock ticks
def tick(back=False):
    n = int(0.06 * SR)
    tt = np.arange(n) / SR
    s = bp(rng.standard_normal(n), 2200, 6500) * np.exp(-tt * 180) + 0.35 * np.sin(2 * np.pi * 3150 * tt) * np.exp(-tt * 90)
    s += 0.25 * np.sin(2 * np.pi * 820 * tt) * np.exp(-tt * 120)
    return s[::-1] * np.linspace(0.2, 1, n) if back else s


tick_gain = env_keys([(0, 0.35), (16, 0.35), (24, 0.6), (64, 0.5), (96, 1.0), (118, 0.8), (120, 0.6), (127, 0.6)])
for k in cues['ticks']:
    if k['t'] < SILENCE_AT:
        place(tick(k['dir'] < 0), k['t'], 0.32 * tick_gain[int(k['t'] * SR)], 0.35)

# ---------------------------------------------------------------- freezes
def glass(freq, dur, decay):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = np.zeros(n)
    for m, a in [(1, 1), (2.76, 0.5), (5.40, 0.25), (8.93, 0.12)]:
        s += a * np.sin(2 * np.pi * freq * m * tt + m)
    return s * adsr(n, 0.004, decay)


def swell(dur):
    n = int(dur * SR)
    s = hp(bp(rng.standard_normal(n), 1500, 9000), 1500)
    return s * np.linspace(0, 1, n) ** 3


main = cues['events']['freeze']
place(swell(BEAT * 1.0), main - BEAT * 1.0, 0.22, -0.2)
nb = int(2.5 * SR)
tb = np.arange(nb) / SR
boom = np.sin(2 * np.pi * np.cumsum(34 + 50 * np.exp(-tb * 9)) / SR) * np.exp(-tb * 2.2)
place(np.tanh(1.5 * boom), main, 0.85)
place(glass(1174.7, 4.0, 1.6), main + 0.02, 0.10, -0.4)
place(glass(1567.98, 4.0, 1.9), main + 0.05, 0.07, 0.4)
for fz in cues['freezes']:
    if abs(fz - main) < 0.01 or fz >= SILENCE_AT - 0.01:
        continue
    place(swell(0.18), fz - 0.18, 0.07, 0.3)   # the faintest inhale, then nothing

# ---------------------------------------------------------------- the amber dot wakes: one warm, low tone
nw = int(3.0 * SR)
tw = np.arange(nw) / SR
warm = (np.sin(2 * np.pi * 293.66 * tw) + 0.3 * np.sin(2 * np.pi * 587.3 * tw)) * adsr(nw, 0.25, 1.1)
place(lp(warm, 1500), cues['events']['amberWake'], 0.10, -0.1)

# ---------------------------------------------------------------- the others: an ice pad under scene 3
ice_env = env_keys([(0, 0), (42, 0), (47, 1), (62, 1), (64.5, 0.25), (95, 0.25), (96, 0)])
pad = np.zeros(N)
for f, d in [(587.33, 0.13), (880.0, -0.09), (1318.5, 0.07), (1760.0, 0.05)]:
    pad += np.sin(2 * np.pi * (f + d) * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t + f))
pad = lp(pad, 3500)
L += pad * ice_env * 0.022
R += np.roll(pad, 480) * ice_env * 0.022
for p in cues['events']['othersPulse']:
    for j, f in enumerate([1174.7, 1760.0]):
        place(glass(f, 2.5, 0.7), p + j * 0.012, 0.05, -0.3 + 0.6 * j)
# swell into the pull-back
pb = cues['events']['pullBack']
nsw = int(3.3 * SR)
sw = lp(rng.standard_normal(nsw), 1800) * np.sin(np.linspace(0, np.pi, nsw)) ** 2
place(sw, pb, 0.12)

# ---------------------------------------------------------------- heartbeat: quickens through scene 4
def heart():
    n = int(0.42 * SR)
    tt = np.arange(n) / SR
    def thump(at, f, g):
        x = np.zeros(n)
        k = tt - at
        m = k >= 0
        x[m] = np.sin(2 * np.pi * f * k[m] * (1 + 0.6 * np.exp(-k[m] * 30))) * np.exp(-k[m] * 22) * g
        return x
    s = thump(0, 58, 1.0) + thump(0.17, 50, 0.7)
    s = np.tanh(1.8 * s)
    knock = bp(np.tanh(4 * s), 160, 600) * 0.9            # the part a phone speaker can play
    return 0.8 * s + knock


hb_env = env_keys([(0, 0), (63.9, 0), (64, 0.55), (80, 0.8), (96, 1.0), (98, 0.6), (100, 0)])
for h in cues['heartbeats']:
    g = hb_env[min(N - 1, int(h * SR))]
    if g > 0.01:
        place(heart(), h, 0.75 * g)

# ---------------------------------------------------------------- phone
def haptic(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 172 * tt)) * 0.5 + np.sin(2 * np.pi * 344 * tt) * 0.3
    s = lp(s, 2500) * np.minimum(1, np.minimum(tt / 0.01, (dur - tt) / 0.02))
    return s


wake = cues['events']['phoneWake']
place(haptic(0.16), wake, 0.20)
place(haptic(0.16), wake + 0.24, 0.20)
place(glass(880.0, 2.5, 0.8), cues['events']['notify'], 0.07, 0.1)
place(glass(1174.7, 2.5, 0.9), cues['events']['notify'] + 0.16, 0.06, 0.1)
for bz in cues['events']['buzzes']:
    place(haptic(0.22), bz, 0.24)

# ---------------------------------------------------------------- a soft chime for every accepted dot
scale = [587.33, 698.46, 783.99, 880.0, 1046.5, 1174.7, 1396.9]
for c in cues['chimes']:
    k, at = c['k'], c['t']
    if at >= SILENCE_AT:
        continue
    f = scale[(k * 5 + k // 7) % len(scale)]
    if k <= 14:                                   # the first fourteen arrive together; spread a hair
        at += (k - 1) * 0.028
        g = 0.05
    elif k <= 23:
        g = 0.075
    else:                                         # the room gets quieter as the count runs away
        g = 0.06 * (1 - 0.65 * (k - 23) / 76)
    place(glass(f, 1.6, 0.45), at, g, -0.6 + 1.2 * ((k * 37) % 100) / 100)

# ---------------------------------------------------------------- cuts and the end
def thump(g=1.0, f=48, dur=1.2):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return np.tanh(1.4 * np.sin(2 * np.pi * np.cumsum(f + 30 * np.exp(-tt * 20)) / SR) * np.exp(-tt * 4.5)) * g


for c in cues['cuts']:
    place(thump(0.32), c)
# thumb: a thin, dissonant high tone under the hover
thumb = cues['events']['thumbCut']
nt = int((cues['events']['titleCut'] - thumb + 0.3) * SR)
tt = np.arange(nt) / SR
diss = (np.sin(2 * np.pi * 1174.7 * tt) + np.sin(2 * np.pi * 1244.5 * tt)) * np.linspace(0, 1, nt) ** 2
place(lp(diss, 4000), thumb, 0.025)
# title
title = cues['events']['titleCut']
place(thump(0.9, 40, 3.0), title)
place(glass(587.33, 4.0, 1.8), title + 0.01, 0.05)
place(glass(293.66, 4.0, 2.2), title + 0.01, 0.06)

# ---------------------------------------------------------------- total silence for the last beat
gate = np.ones(N)
i0 = int(SILENCE_AT * SR)
fade = int(0.004 * SR)
gate[i0:i0 + fade] = np.linspace(1, 0, fade)
gate[i0 + fade:] = 0
L *= gate
R *= gate

# ---------------------------------------------------------------- master
mix = np.stack([L, R], axis=1)
mix = hp(mix.T, 28, 2).T                             # nothing below the audible floor
meter = pyln.Meter(SR)
loud = meter.integrated_loudness(mix)
mix *= 10 ** ((-14.0 - loud) / 20)


def true_peak(x):
    up = signal.resample_poly(x, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


# gentle look-ahead limiter if needed, then re-normalize
from scipy.ndimage import minimum_filter1d  # noqa: E402
for _ in range(6):
    if true_peak(mix) <= -1.0:
        break
    thr = 10 ** (-1.6 / 20)
    pk = np.max(np.abs(mix), axis=1)
    g = np.minimum(1, thr / np.maximum(pk, 1e-9))
    win = int(0.003 * SR)
    g = minimum_filter1d(g, 2 * win + 1)                          # look ahead and behind
    g = np.convolve(g, np.ones(win) / win, mode='same')           # smooth attack, stays below
    a_r = np.exp(-1 / (0.12 * SR))
    red = signal.lfilter([1 - a_r], [1, -a_r], 1 - g)             # slow release
    mix *= (1 - np.maximum(1 - g, red))[:, None]
    mix *= 10 ** ((-14.0 - meter.integrated_loudness(mix)) / 20)

mix *= gate[:, None]                                  # again, after every filter: the last beat is silent
loud = meter.integrated_loudness(mix)
tp = true_peak(mix)
import soundfile as sf  # noqa: E402
sf.write(OUT, mix.astype(np.float32), SR, subtype='PCM_24')
print(f'wrote {OUT}: integrated {loud:.2f} LUFS, true peak {tp:.2f} dBTP')
