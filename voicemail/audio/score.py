"""ONE NEW VOICEMAIL — score and sound design around the voice.

    python3 audio/score.py audio/cues.json out/voice.wav out/score.wav

The hallway hum follows the peephole light exactly (same FLICKER table as the picture).
The music ducks under the voice. Mastered to -14 LUFS integrated, <= -1 dBTP.
"""
import json
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d

SR = 48000
cues = json.load(open(sys.argv[1]))
voice, vsr = sf.read(sys.argv[2])
OUT = sys.argv[3]
assert vsr == SR
N = int(cues['duration'] * SR)
BEAT = cues['beat']
t = np.arange(N) / SR
rng = np.random.default_rng(96)
L = np.zeros(N)
R = np.zeros(N)
ev = cues['events']
SIL = ev['silence']


def b2s(b):
    return b * BEAT


def env_keys(keys):
    return np.interp(t, [b2s(k[0]) for k in keys], [k[1] for k in keys])


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def bp(x, a, b, o=2):
    return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)


def place(sig, at, gain=1.0, pan=0.0, dest=None):
    i = int(round(at * SR))
    if i >= N or i + len(sig) <= 0:
        return
    s = sig[max(0, -i): N - i] * gain
    i = max(0, i)
    a = (pan + 1) * np.pi / 4
    (L if dest is None else dest[0])[i:i + len(s)] += s * np.cos(a)
    (R if dest is None else dest[1])[i:i + len(s)] += s * np.sin(a)


def decay(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR))
    return e


def reverb(x, rt=1.6, wet=0.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR))
    ir = lp(ir, 4500)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


# music bus (ducked under the voice) and fx bus (not ducked)
mL, mR = np.zeros(N), np.zeros(N)

# ---------------------------------------------------------------- drone: C# and a semitone that shouldn't be there
f0 = 34.65
ph = 2 * np.pi * f0 * t
dr_env = env_keys([(0, 0), (4, 0.35), (16, 0.45), (32, 0.6), (52, 0.55), (61.4, 0.7), (61.5, 0.15), (66, 0.6), (76, 0.85),
                   (80.5, 0.35), (84.8, 0.35), (85.6, 1.0), (86, 0.9), (90, 0.4), (95, 0.3)])
sub = np.sin(ph) * 0.3
harm = np.tanh(2.0 * (np.sin(2 * ph) + 0.6 * np.sin(3 * ph * 1.0008) + 0.5 * np.sin(4 * ph * 0.9993)))
harm = lp(harm, 600)
rub = env_keys([(0, 0), (32, 0), (52, 0.4), (66, 0.6), (76, 1.0), (80.5, 0.3), (84.8, 0.3), (85.6, 0.9), (95, 0.5)])
cl = sum(np.sin(2 * np.pi * f * t * (1 + 0.002 * np.sin(2 * np.pi * 0.07 * t + f))) for f in (277.18, 293.66, 415.3))
cl = lp(cl, 1800) * 0.06
mL += (sub + 0.3 * harm) * dr_env + cl * rub * dr_env
mR += (sub + 0.3 * harm * 0.98) * dr_env + np.roll(cl, 700) * rub * dr_env

# ---------------------------------------------------------------- the phone line: hiss and crackle while the message plays
line_env = env_keys([(0, 0), (8.4, 0), (8.6, 1), (16, 0.8), (52, 0.65), (76, 0.7), (85.0, 0.6), (85.3, 0), (96, 0)])
hiss = bp(rng.standard_normal(N), 400, 3400, 4) * 0.012
crk = np.zeros(N)
for _ in range(240):
    at = rng.uniform(b2s(8.6), b2s(85))
    n = int(rng.uniform(0.002, 0.03) * SR)
    i = int(at * SR)
    crk[i:i + n] += rng.standard_normal(n) * rng.uniform(0.01, 0.06) * np.exp(-np.arange(n) / (0.004 * SR))
line = hp(hiss + bp(crk, 300, 4000), 250) * line_env
L += line
R += line

# ---------------------------------------------------------------- phone UI sounds
def tone(f, dur, g=1.0, dec=0.1):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return np.sin(2 * np.pi * f * tt) * decay(n, 0.003, dec) * g


place(tone(1318.5, 0.6, 1, 0.12) + tone(1760, 0.6, 0.6, 0.1), b2s(ev['notify']), 0.08)
place(bp(rng.standard_normal(int(0.02 * SR)), 1500, 6000) * decay(int(0.02 * SR), 0.0005, 0.004), b2s(ev['play']), 0.15)
nb = int(0.42 * SR)
beep = np.sin(2 * np.pi * 1000 * np.arange(nb) / SR) * np.minimum(1, np.minimum(np.arange(nb) / (0.01 * SR), (nb - np.arange(nb)) / (0.02 * SR)))
place(bp(beep, 300, 3400), b2s(ev['beep']), 0.16)
place(tone(2093, 0.08, 1, 0.02), b2s(ev['minute']), 0.05, 0.4)          # 3:13 -> 3:14
place(tone(880, 0.14, 1, 0.05), b2s(ev['record']), 0.07)
place(tone(1174.7, 0.14, 1, 0.05), b2s(ev['record']) + 0.16, 0.07)


# ---------------------------------------------------------------- footsteps behind the door, the knocks
def thud(f=70, dur=0.5, click=0.3, seed=0):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 18)
    body += 0.6 * np.sin(2 * np.pi * f * 2.6 * tt) * np.exp(-tt * 30)
    cl_ = bp(r.standard_normal(n), 800, 5000) * np.exp(-tt * 160) * click
    return np.tanh(2 * (body + cl_))


for k, at in enumerate([ev['feet'], ev['feet'] + 0.7 * BEAT]):
    place(lp(reverb(thud(60, 0.6, 0.15, k), 0.8, 0.3, k), 900), at, 0.22, -0.1 + 0.2 * k)
for k, at in enumerate(ev['knocks']):
    kn = thud(95, 0.9, 0.9, 10 + k)
    kn[: int(0.5 * SR)] += 0.5 * thud(190, 0.5, 0.5, 20 + k)
    rattle = bp(rng.standard_normal(int(0.25 * SR)), 2500, 7000) * np.exp(-np.arange(int(0.25 * SR)) / (0.05 * SR)) * 0.25
    kn[: len(rattle)] += rattle
    place(reverb(kn, 1.4, 0.3, 30 + k), at, 0.62, 0.05)
# the hallway light dies: a relay click
place(bp(rng.standard_normal(int(0.03 * SR)), 1000, 6000) * decay(int(0.03 * SR), 0.0005, 0.006), b2s(85.15), 0.25)

# ---------------------------------------------------------------- fluorescent hum: follows the peephole light exactly
light = np.ones(N)
for a, c in cues['flicker']:
    light[int(a * SR): int(c * SR)] = 0
zone = env_keys([(0, 0), (51.99, 0), (52, 1), (75.99, 1), (76, 0), (96, 0)])
light = light * zone
light = lp(light, 400, 1)                      # 1 ms edges: abrupt, but no click
hum = sum(np.sin(2 * np.pi * 120 * h * t + h) / h ** 0.8 for h in range(1, 14))
hum = np.tanh(1.5 * hum) * 0.05 + bp(rng.standard_normal(N), 2000, 8000) * 0.004
hum_env = env_keys([(52, 0.7), (66, 0.8), (75.9, 1.0)])
L += hum * light * hum_env
R += np.roll(hum, 31) * light * hum_env
for a, c in cues['flicker']:                  # a sputter each time it comes back on
    sp = bp(rng.standard_normal(int(0.06 * SR)), 1500, 7000) * decay(int(0.06 * SR), 0.001, 0.015)
    place(sp, c, 0.12, 0.2)
# the flash: everything stops, a low pressure where the light was
fl = ev['flash']
nfl = int(1.2 * SR)
press = np.sin(2 * np.pi * 27.5 * np.arange(nfl) / SR) * np.sin(np.linspace(0, np.pi, nfl)) * 0.6
place(press, fl, 0.5)
sw = hp(bp(rng.standard_normal(int(1.2 * SR)), 1500, 9000), 1500) * np.linspace(0, 1, int(1.2 * SR)) ** 3
place(sw, fl - 1.2, 0.05, -0.3)

# ---------------------------------------------------------------- title, breath, silence
nb2 = int(3.5 * SR)
tb = np.arange(nb2) / SR
boom = np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(32 + 45 * np.exp(-tb * 8)) / SR) * np.exp(-tb * 1.6))
place(boom, ev['title'], 0.75)
place(hp(bp(rng.standard_normal(int(1.5 * SR)), 1200, 9000), 1200) * np.linspace(0, 1, int(1.5 * SR)) ** 3, ev['title'] - 1.5, 0.06)
nbr = int(1.2 * SR)
breath = bp(rng.standard_normal(nbr), 500, 5000) * np.sin(np.linspace(0, np.pi, nbr)) ** 1.5
breath += 0.5 * bp(rng.standard_normal(nbr), 150, 900) * np.sin(np.linspace(0, np.pi, nbr)) ** 2
place(breath, ev['breath'], 0.12)

# ---------------------------------------------------------------- the voice, and the music ducking under it
v = voice[:N] if len(voice) >= N else np.pad(voice, (0, N - len(voice)))
venv = lp(np.abs(v), 8)
duck = 1 - 0.75 * np.clip(venv / (venv.max() * 0.15), 0, 1)
duck = minimum_filter1d(duck, int(0.25 * SR))          # hold the duck between words
L += mL * duck
R += mR * duck
vg = np.ones(N)
for ln in cues['voice']:                       # the whisper is close and dry, a little louder
    if ln['fx'] == 'whisper':
        vg[int((ln['t0'] - 0.3) * SR):] = 2.1
    if ln['fx'] == 'sys':
        vg[int((ln['t0'] - 0.2) * SR): int((ln['t0'] + 5) * SR)] = 1.5
vr = reverb(v, 0.9, 0.12, 77)                  # a small room around the phone speaker
L += vr * vg * 0.9
R += vr * vg * 0.9

# ---------------------------------------------------------------- check: is every line clearly above everything else?
if '--check' in sys.argv:
    import os  # noqa: E402
    m = pyln.Meter(SR, block_size=0.2)
    vb = np.stack([vr * vg * 0.9] * 2, axis=1)
    bed = np.stack([L, R], axis=1) - vb
    for ln in json.loads(open('src/voice_data.js').read().split('export const LINES = ')[1].split(';\n')[0]):
        a_, b_ = int(ln['v0'] * SR), int(ln['v1'] * SR)
        lv, lb = m.integrated_loudness(vb[a_:b_]), m.integrated_loudness(bed[a_:b_])
        print(f"  {ln['id']:4s} voice {lv:6.1f}  bed {lb:6.1f}  -> voice {lv - lb:+5.1f} dB")

# ---------------------------------------------------------------- master
gate = np.ones(N)
i0 = int(SIL * SR)
gate[i0:i0 + 200] = np.linspace(1, 0, 200)
gate[i0 + 200:] = 0
mix = np.stack([L * gate, R * gate], axis=1)
mix = hp(mix.T, 28).T
meter = pyln.Meter(SR)
mix *= 10 ** ((-14.0 - meter.integrated_loudness(mix)) / 20)


def true_peak(x):
    return 20 * np.log10(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0))) + 1e-12)


for _ in range(6):
    if true_peak(mix) <= -1.0:
        break
    thr = 10 ** (-1.6 / 20)
    g = np.minimum(1, thr / np.maximum(np.max(np.abs(mix), axis=1), 1e-9))
    win = int(0.003 * SR)
    g = minimum_filter1d(g, 2 * win + 1)
    g = np.convolve(g, np.ones(win) / win, mode='same')
    a_r = np.exp(-1 / (0.12 * SR))
    red = signal.lfilter([1 - a_r], [1, -a_r], 1 - g)
    mix *= (1 - np.maximum(1 - g, red))[:, None]
    mix *= 10 ** ((-14.0 - meter.integrated_loudness(mix)) / 20)
mix *= gate[:, None]
sf.write(OUT, mix.astype(np.float32), SR, subtype='PCM_24')
print(f'wrote {OUT}: integrated {meter.integrated_loudness(mix):.2f} LUFS, true peak {true_peak(mix):.2f} dBTP')
