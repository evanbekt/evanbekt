"""THE TALL ONE — trailer score and sound, on the timeline voice.py wrote.

    python3 audio/score.py
Braams on the black cards; a record scratch when the friend first cuts in; then a big, stupid,
confident groove (drums, staccato strings, bass) with a whoosh and boom on every cut; a riser
into the jar line; a montage of hits; one last braam on the title, and silence for the punchline.
Writes out/score.wav at -14 LUFS integrated, <= -1 dBTP.
"""
import json

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d

SR = 48000
TL = json.load(open('out/timeline.json'))
BEATS = TL['beats']
N = int(TL['total'] * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(190)
L, R = np.zeros(N), np.zeros(N)
mL, mR = np.zeros(N), np.zeros(N)
MUS = (mL, mR)


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def bp(x, a, b, o=2):
    return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)


def place(sig, at, gain=1.0, pan=0.0, bus=MUS):
    i = int(round(at * SR))
    if i >= N or i + len(sig) <= 0:
        return
    s = sig[max(0, -i): N - i] * gain
    i = max(0, i)
    a = (pan + 1) * np.pi / 4
    bus[0][i:i + len(s)] += s * np.cos(a)
    bus[1][i:i + len(s)] += s * np.sin(a)


def reverb(x, rt=1.8, wet=0.3, seed=1):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def braam(dur=3.0, root=26):
    """The trailer horn: detuned saws an octave apart, a filter that blooms, distortion, a long hall."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = np.zeros(n)
    for m, g in ((root, 1.0), (root + 12, 0.7), (root + 19, 0.35), (root + 24, 0.3)):
        for d in (0.997, 1.0, 1.004):
            s += g * signal.sawtooth(2 * np.pi * hz(m) * d * tt + rng.uniform(0, 6))
    env = np.minimum(1, tt / 0.04) * np.exp(-tt / (dur * 0.45))
    out = np.zeros(n)
    k = 10
    for i in range(k):
        a, b = i * n // k, (i + 1) * n // k
        out[a:b] = lp(s, 250 + 2200 * np.exp(-tt[a] / 0.5), 2)[a:b]
    out = np.tanh(1.8 * out * env / 3) * 0.9
    sub = np.sin(2 * np.pi * hz(root - 12) * tt) * np.exp(-tt / 1.5)
    return reverb(out + 0.7 * sub, 3.5, 0.35, 7)


def boom(dur=1.6, f=48):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-tt * 25))) / SR) * np.exp(-tt * 3.2)
    return reverb(np.tanh(2.2 * body) + lp(rng.standard_normal(n), 2000) * np.exp(-tt * 40) * 0.5, 2.0, 0.25, 3)


def whoosh(dur=0.5):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    k = 8
    for i in range(k):
        a, b = i * n // k, (i + 1) * n // k
        c = 400 + 5000 * (tt[a] / dur) ** 2
        out[a:b] = bp(x, c * 0.6, min(c * 1.6, 20000), 2)[a:b]
    return out * (tt / dur) ** 2 * 0.8


def kick():
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    return np.tanh(3 * np.sin(2 * np.pi * np.cumsum(50 * (1 + 2.5 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 9))


def snare():
    n = int(0.3 * SR)
    tt = np.arange(n) / SR
    return (bp(rng.standard_normal(n), 1500, 9000) * np.exp(-tt * 18) * 0.8
            + np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 30) * 0.6)


def stab(f, dur=0.16):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = sum(signal.sawtooth(2 * np.pi * f * d * tt) for d in (0.996, 1.0, 1.005)) / 3
    return lp(s, 2600) * np.minimum(1, tt / 0.004) * np.exp(-tt * 16)


# ---------------------------------------------------------------- the black cards
place(braam(3.4, 26), BEATS[0]['t0'], 0.8)
place(braam(4.0, 24), BEATS[1]['t0'], 0.85)
drone = (np.sin(2 * np.pi * hz(38) * t) + 0.4 * np.sin(2 * np.pi * hz(45) * t)) * np.exp(-((t - 4) / 4) ** 2)
place(drone * 0.1, 0)
# the first photo: epic for one line, then the friend, then the scratch
b2 = BEATS[2]
place(boom(), b2['t0'], 0.6)
k_in = b2['lines'][1]['t0']
n = int(0.42 * SR)
tt = np.arange(n) / SR
scratch = bp(rng.standard_normal(n), 300, 4000) * (np.sin(2 * np.pi * tt / tt[-1] * 1.5) > 0) * 0.6
scratch += np.sin(2 * np.pi * np.cumsum(600 - 500 * np.sin(np.pi * tt / tt[-1])) / SR) * 0.4
place(scratch * np.exp(-tt * 3), k_in - 0.4, 0.55)

# ---------------------------------------------------------------- the groove: 104 BPM, D minor, confident
BPM = 104
q = 60 / BPM
g0 = b2['t1']                      # starts on the cut to the height shot
g1 = BEATS[9]['t0']                # stops for the jar line
prog = [(50, [62, 65, 69]), (46, [58, 62, 65]), (48, [60, 64, 67]), (45, [57, 61, 64])]   # Dm Bb C A
i = 0
while g0 + i * q / 2 < g1:
    at = g0 + i * q / 2
    beat = i // 2
    bar = beat // 4
    root, ch = prog[bar % 4]
    if i % 2 == 0:
        if beat % 4 in (0, 2):
            place(kick(), at, 0.75)
        else:
            place(snare(), at, 0.45, 0.05)
    place(bp(rng.standard_normal(int(0.05 * SR)), 6000, 12000) * np.exp(-np.arange(int(0.05 * SR)) / (0.008 * SR)), at, 0.12, 0.3)
    place(stab(hz(ch[i % 3] + (12 if i % 4 == 3 else 0))), at, 0.13, -0.2 + 0.4 * (i % 2))
    if i % 4 == 0:
        n = int(q * 1.9 * SR)
        tt = np.arange(n) / SR
        bass = lp(signal.sawtooth(2 * np.pi * hz(root - 12) * tt), 400) * np.minimum(1, tt / 0.01) * np.exp(-tt * 1.5)
        place(bass, at, 0.32)
    i += 1
# a whoosh into, and a boom on, every cut while it plays
for b in BEATS[3:10]:
    place(whoosh(), b['t0'] - 0.5, 0.35)
    place(boom(1.2, 44), b['t0'], 0.45)

# ---------------------------------------------------------------- the jar: drums out, a riser, a hit
jb = BEATS[9]
n1 = jb['lines'][1]['t0'] - jb['t0']
n = int(n1 * SR)
tt = np.arange(n) / SR
riser = np.sin(2 * np.pi * np.cumsum(110 + 700 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1]) ** 2 * 0.3
riser += bp(rng.standard_normal(n), 500, 8000) * (tt / tt[-1]) ** 3 * 0.5
place(riser, jb['t0'], 0.6)
for m in (50, 57, 62, 65, 69):                          # a choir pad: formant-filtered saws
    n = int((jb['t1'] - jb['lines'][1]['t0'] + 0.5) * SR)
    tt = np.arange(n) / SR
    s = signal.sawtooth(2 * np.pi * hz(m) * tt * (1 + 0.003 * np.sin(2 * np.pi * 5 * tt)))
    s = bp(s, 500, 1200) + 0.5 * bp(s, 2200, 3000)
    place(s * np.minimum(1, tt / 0.3) * np.minimum(1, (tt[-1] - tt) / 0.4) * 0.05, jb['lines'][1]['t0'], 1.0)
place(braam(3.0, 26), jb['lines'][1]['t0'], 0.6)
place(boom(2.0, 40), jb['lines'][1]['t0'], 0.6)

# ---------------------------------------------------------------- title: montage hits, the braam, then nothing
tb = BEATS[10]
for k in range(int(1.4 * 30 / 5)):
    place(boom(0.5, 70), tb['t0'] + k * 5 / 30, 0.35)
    place(whoosh(0.15), tb['t0'] + k * 5 / 30 - 0.15, 0.2)
place(braam(2.4, 26), tb['t0'] + 1.4, 1.0)
place(boom(1.4, 36), tb['t0'] + 1.4, 0.7)
# rating: a soft low note, and one small pluck after "to your phone"
rb = BEATS[11]
place(boom(1.5, 60), rb['t0'], 0.3)
n = int(2.5 * SR)
tt = np.arange(n) / SR
pluck = (np.sin(2 * np.pi * hz(74) * tt) + 0.3 * np.sin(2 * np.pi * hz(86) * tt) * np.exp(-tt * 5)) * np.exp(-tt * 2.5)
place(reverb(pluck, 2, 0.3, 2), rb['lines'][-1]['t1'] + 0.25, 0.25)

# ---------------------------------------------------------------- voices on top, music ducked under them
v, _ = sf.read('out/voice.wav')
v = np.pad(v, (0, max(0, N - len(v))))[:N]
venv = lp(np.abs(v), 8)
duck = minimum_filter1d(1 - 0.6 * np.clip(venv / (venv.max() * 0.1), 0, 1), int(0.3 * SR))
VG = 1.25
L = mL * duck + VG * v
R = mR * duck + VG * v
fade = np.ones(N)
fade[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR)) ** 2
mix = hp(np.stack([L * fade, R * fade], axis=1).T, 28).T
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
if tp > -1.0:
    mix *= 10 ** ((-1.05 - tp) / 20)

bed = np.stack([mL * duck, mR * duck], axis=1)
vv = np.stack([VG * v, VG * v], axis=1)
worst = 99
for b in BEATS:
    for ln in b['lines']:
        a, b2_ = int(ln['t0'] * SR), int(ln['t1'] * SR)
        sp = lambda x: hp(x.T, 300, 4).T  # noqa: E731
        d = m.integrated_loudness(sp(vv[a:b2_])) - m.integrated_loudness(sp(bed[a:b2_]))
        worst = min(worst, d)
        if d < 8:
            print(f'  low: {ln["text"]} {d:+.1f} dB')
sf.write('out/score.wav', mix.astype(np.float32), SR, subtype='PCM_24')
print(f'{m.integrated_loudness(mix):.2f} LUFS, true peak {true_peak(mix):.2f} dBTP, weakest line {worst:+.1f} dB over the bed')
