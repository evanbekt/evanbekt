"""THE STILLNESS, PART 3: THE SEVEN MINUTES — score and sound design around the voice.

    python3 audio/score.py audio/cues.json out/voice.wav out/score.wav [--check]

Built from both earlier parts: Part 1's clock and freeze, Part 2's line, knocks and hum.
Everything that belongs to the world (room tone, clock, hum) runs on the world clock, so it
stops at 3:07 and floods back at the knock. Mastered to -14 LUFS integrated, <= -1 dBTP.
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
voice, _ = sf.read(sys.argv[2])
OUT = sys.argv[3]
N = int(cues['duration'] * SR)
BEAT = cues['beat']
t = np.arange(N) / SR
rng = np.random.default_rng(307)
L = np.zeros(N)
R = np.zeros(N)
mL, mR = np.zeros(N), np.zeros(N)
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


def decay(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR))
    return e


def reverb(x, rt=1.6, wet=0.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 4500)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


def glass(freq, dur, dec):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * freq * m * tt + m) for m, a in [(1, 1), (2.76, 0.5), (5.40, 0.25), (8.93, 0.12)])
    return s * decay(n, 0.004, dec)


ws_b = np.arange(len(cues['worldSpeed'])) / 16
world = np.abs(np.interp(t, ws_b * BEAT, cues['worldSpeed']))
world = lp(world, 60, 1)
wb = np.cumsum(np.interp(t, ws_b * BEAT, cues['worldSpeed'])) / SR / BEAT

# ---------------------------------------------------------------- drone: Part 2's C#, held breath
f0 = 34.65
ph = 2 * np.pi * f0 * t
dr = 0.3 * np.sin(ph) + 0.3 * lp(np.tanh(2.0 * (np.sin(2 * ph) + 0.6 * np.sin(3 * ph * 1.0008) + 0.5 * np.sin(4 * ph * 0.9993))), 600)
dr_env = env_keys([(0, 0.3), (14, 0.5), (16.5, 0.8), (17, 0.35), (30, 0.45), (49.5, 0.6), (58, 0.4), (78, 0.55), (80, 0.9), (86, 0.7), (88, 1.0), (95, 0.5)])
mL += dr * dr_env
mR += dr * dr_env * 0.97

# ---------------------------------------------------------------- the others: Part 1's ice pad, only while it's still
ice_env = env_keys([(0, 0), (17, 0), (22, 0.5), (30, 1), (58, 1), (60, 0.5), (79.9, 0.5), (80, 0), (96, 0)])
pad = sum(np.sin(2 * np.pi * (f + d) * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t + f)) for f, d in [(587.33, 0.13), (880.0, -0.09), (1318.5, 0.07), (1760.0, 0.05)])
pad = lp(pad, 3500) * 0.03
mL += pad * ice_env
mR += np.roll(pad, 480) * ice_env

# ---------------------------------------------------------------- room tone and fluorescent hum: the world's sounds
room = lp(bp(rng.standard_normal(N), 200, 4000), 2500) * 0.035
room_zone = env_keys([(0, 1), (30, 1), (78, 1), (96, 1)])
L += room * world * room_zone
R += np.roll(room, 9000) * world * room_zone
hum = np.tanh(1.5 * sum(np.sin(2 * np.pi * 120 * h * t + h) / h ** 0.8 for h in range(1, 14))) * 0.05
hum_zone = env_keys([(0, 0), (77.9, 0), (78, 1), (88, 1), (88.1, 0), (96, 0)])
L += hum * world * hum_zone
R += np.roll(hum, 31) * world * hum_zone


# ---------------------------------------------------------------- Part 1's clock: ticks every 2 world beats, until 3:07 holds
def tick():
    n = int(0.06 * SR)
    tt = np.arange(n) / SR
    return bp(rng.standard_normal(n), 2200, 6500) * np.exp(-tt * 180) + 0.35 * np.sin(2 * np.pi * 3150 * tt) * np.exp(-tt * 90)


tick_zone = env_keys([(0, 1), (14, 1), (14.01, 0.7), (30, 0.7), (30.01, 0), (78, 0), (78.01, 0.6), (88, 0.6), (88.01, 0), (96, 0)])
for i in np.nonzero(np.diff(np.floor(wb / 2 + 1e-6)) > 0)[0]:
    if tick_zone[i] > 0 and i / SR < SIL:
        place(tick(), i / SR, 0.3 * tick_zone[i], 0.35)

# ---------------------------------------------------------------- the freeze (Part 1's sound)
fz = ev['freeze']
n1 = int(b2s(1.0) * SR)
place(hp(bp(rng.standard_normal(n1), 1500, 9000), 1500) * np.linspace(0, 1, n1) ** 3, fz - b2s(1.0), 0.1, -0.2)
nb = int(2.5 * SR)
tb = np.arange(nb) / SR
# pure sub: it lands on "stopped" without covering the rest of the line
place(lp(np.tanh(1.5 * np.sin(2 * np.pi * np.cumsum(34 + 50 * np.exp(-tb * 9)) / SR) * np.exp(-tb * 2.2)), 110, 4), fz, 0.9)
n3_end = next(v['t0'] for v in cues['voice'] if v['id'] == 'n3') + 2.35   # the glass waits for the line to finish
place(glass(1174.7, 4.0, 1.6), n3_end, 0.09, -0.4)
place(glass(1567.98, 4.0, 1.9), n3_end + 0.03, 0.06, 0.4)
# you leave the phone: Part 1's warm tone
nw = int(3.0 * SR)
tw = np.arange(nw) / SR
place(lp((np.sin(2 * np.pi * 293.66 * tw) + 0.3 * np.sin(2 * np.pi * 587.3 * tw)) * decay(nw, 0.25, 1.1), 1500), b2s(18), 0.09, -0.1)

# ---------------------------------------------------------------- the door opens: a long, low pull, and the light's own hiss
od = ev['doorOpen']
no = int(b2s(3) * SR)
to = np.arange(no) / SR
groan = np.sin(2 * np.pi * np.cumsum(70 + 25 * np.sin(np.pi * to / to[-1])) / SR) * np.sin(np.pi * to / to[-1]) ** 2
place(lp(np.tanh(2 * groan) + 0.3 * bp(rng.standard_normal(no), 300, 1200), 1500), od, 0.18)
place(bp(rng.standard_normal(no), 3000, 9000) * np.linspace(0, 1, no) ** 2, od, 0.03)

# ---------------------------------------------------------------- they turn: every one of them at once
for j, f in enumerate([1174.7, 1760.0, 2349.3]):
    place(glass(f, 3.0, 0.9), ev['turn'] + j * 0.01, 0.06, -0.4 + 0.4 * j)
place(np.sin(2 * np.pi * 27.5 * np.arange(int(1.5 * SR)) / SR) * np.sin(np.linspace(0, np.pi, int(1.5 * SR))), ev['turn'], 0.35)

# ---------------------------------------------------------------- the recording (Part 2's beeps)
def tone(f, dur, dec):
    n = int(dur * SR)
    return np.sin(2 * np.pi * f * np.arange(n) / SR) * decay(n, 0.003, dec)


place(tone(880, 0.14, 0.05), ev['record'], 0.07)
place(tone(1174.7, 0.14, 0.05), ev['record'] + 0.16, 0.07)


# ---------------------------------------------------------------- the knocks (Part 2's), from this side of the door
def thud(f, dur, click, seed):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 18)
    body += 0.6 * np.sin(2 * np.pi * f * 2.6 * tt) * np.exp(-tt * 30)
    return np.tanh(2 * (body + bp(r.standard_normal(n), 800, 5000) * np.exp(-tt * 160) * click))


for k, at in enumerate(ev['knocks']):
    kn = thud(95, 0.9, 1.1, 10 + k)                     # closer and brighter than in Part 2: your knuckles
    kn[: int(0.5 * SR)] += 0.5 * thud(190, 0.5, 0.6, 20 + k)
    place(reverb(kn, 1.0, 0.22, 30 + k), at, 0.62, 0.05)

# ---------------------------------------------------------------- title, then nothing
nt = int(3.5 * SR)
tt = np.arange(nt) / SR
place(np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(32 + 45 * np.exp(-tt * 8)) / SR) * np.exp(-tt * 1.6)), ev['title'], 0.75)

# ---------------------------------------------------------------- voice on top; the music ducks under it
v = voice[:N] if len(voice) >= N else np.pad(voice, (0, N - len(voice)))
venv = lp(np.abs(v), 8)
duck = minimum_filter1d(1 - 0.75 * np.clip(venv / (venv.max() * 0.15), 0, 1), int(0.25 * SR))
L += mL * duck
R += mR * duck
vg = np.ones(N)
for ln in cues['voice']:
    a_ = int((ln['t0'] - (ln.get('pre') or 0) - 0.3) * SR)
    if ln['fx'] == 'near':
        vg[a_: int((ln['t0'] + 4) * SR)] = 1.6                # you, now: up front
    if ln['fx'] == 'p2w':
        vg[a_:] = 2.1
vr = reverb(v, 0.9, 0.12, 77)
L += vr * vg * 0.9
R += vr * vg * 0.9

if '--check' in sys.argv:
    m = pyln.Meter(SR, block_size=0.2)
    vb = np.stack([vr * vg * 0.9] * 2, axis=1)
    bed = np.stack([L, R], axis=1) - vb
    for ln in json.loads(open('src/voice_data.js').read().split('export const LINES = ')[1].split(';\n')[0]):
        a_, b_ = int(ln['v0'] * SR), int(ln['v1'] * SR)
        lv, lb = m.integrated_loudness(vb[a_:b_]), m.integrated_loudness(bed[a_:b_])
        sp = lambda x: hp(x.T, 300, 4).T                      # the speech band, where masking matters
        lvs, lbs = m.integrated_loudness(sp(vb[a_:b_])), m.integrated_loudness(sp(bed[a_:b_]))
        print(f"  {ln['id']:4s} voice {lv:6.1f}  bed {lb:6.1f}  -> {lv - lb:+5.1f} dB   speech band {lvs - lbs:+5.1f} dB")

# ---------------------------------------------------------------- master
gate = np.ones(N)
i0 = int(SIL * SR)
gate[i0:i0 + 200] = np.linspace(1, 0, 200)
gate[i0 + 200:] = 0
mix = hp(np.stack([L * gate, R * gate], axis=1).T, 28).T
meter = pyln.Meter(SR)
mix *= 10 ** ((-14.0 - meter.integrated_loudness(mix)) / 20)


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
    mix *= 10 ** ((-14.0 - meter.integrated_loudness(mix)) / 20)
mix *= gate[:, None]
sf.write(OUT, mix.astype(np.float32), SR, subtype='PCM_24')
print(f'wrote {OUT}: integrated {meter.integrated_loudness(mix):.2f} LUFS, true peak {true_peak(mix):.2f} dBTP')
