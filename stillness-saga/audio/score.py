"""THE STILLNESS, PARTS 4-6 — score and sound design around the voices.

    python3 audio/score.py PART audio/cuesN.json out/voiceN.wav out/scoreN.wav [--check]

Same palette as Part 2 (drone, line hiss, hum, knocks), plus each part's own devices.
Mastered to -14 LUFS integrated, <= -1 dBTP; the last half-beat is silent.
"""
import json
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d

SR = 48000
PART = int(sys.argv[1])
cues = json.load(open(sys.argv[2]))
voice, _ = sf.read(sys.argv[3])
OUT = sys.argv[4]
N = int(cues['duration'] * SR)
BEAT = cues['beat']
t = np.arange(N) / SR
rng = np.random.default_rng(400 + PART)
L, R = np.zeros(N), np.zeros(N)
mL, mR = np.zeros(N), np.zeros(N)
ev = cues['events']
SIL = ev['silence']
MUS = (mL, mR)


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


def tone(f, dur, dec, g=1.0):
    n = int(dur * SR)
    return np.sin(2 * np.pi * f * np.arange(n) / SR) * decay(n, 0.003, dec) * g


def glass(freq, dur, dec):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * freq * m * tt + m) for m, a in [(1, 1), (2.76, 0.5), (5.40, 0.25), (8.93, 0.12)]) * decay(n, 0.004, dec)


def thud(f, dur, click, seed):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 18)
    body += 0.6 * np.sin(2 * np.pi * f * 2.6 * tt) * np.exp(-tt * 30)
    return np.tanh(2 * (body + bp(r.standard_normal(n), 800, 5000) * np.exp(-tt * 160) * click))


def knock(seed, f=95, gain=0.6, pan=0.05, at=0.0, rt=1.4, bright=0.9):
    kn = thud(f, 0.9, bright, seed)
    kn[: int(0.5 * SR)] += 0.5 * thud(2 * f, 0.5, 0.5 * bright, seed + 100)
    place(reverb(kn, rt, 0.3, seed + 200), at, gain, pan)


def haptic(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 172 * tt)) * 0.5 + np.sin(2 * np.pi * 344 * tt) * 0.3
    return lp(s, 2500) * np.minimum(1, np.minimum(tt / 0.01, (dur - tt) / 0.02))


def boom(at, g=0.75):
    nb = int(3.5 * SR)
    tb = np.arange(nb) / SR
    place(np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(32 + 45 * np.exp(-tb * 8)) / SR) * np.exp(-tb * 1.6)), at, g)
    n1 = int(1.5 * SR)
    place(hp(bp(rng.standard_normal(n1), 1200, 9000), 1200) * np.linspace(0, 1, n1) ** 3, at - 1.5, 0.06)


def pings(times, g=0.05):
    for at in times:
        place(tone(1567.98, 0.25, 0.06) + tone(2093, 0.25, 0.05, 0.5), at, g, 0.15)


# ---------------------------------------------------------------- drone (Part 2's C#), per-part envelope
f0 = 34.65
ph = 2 * np.pi * f0 * t
dr = 0.3 * np.sin(ph) + 0.3 * lp(np.tanh(2.0 * (np.sin(2 * ph) + 0.6 * np.sin(3 * ph * 1.0008) + 0.5 * np.sin(4 * ph * 0.9993))), 600)
rub = lp(sum(np.sin(2 * np.pi * f * t * (1 + 0.002 * np.sin(2 * np.pi * 0.07 * t + f))) for f in (277.18, 293.66, 415.3)), 1800) * 0.06
DR = {4: [(0, 0.3), (24, 0.45), (46, 0.6), (58.5, 0.2), (62, 0.5), (84, 1.0), (89.5, 1.0), (93, 0.4)],
      5: [(0, 0.25), (24, 0.35), (46, 0.55), (64, 0.7), (76, 0.85), (80.5, 0.2), (88, 1.0), (93, 0.4)],
      6: [(0, 0.15), (26, 0.25), (48, 0.4), (70.5, 0.9), (71, 0.3), (82, 0.6), (90, 0.2), (95, 0.2)]}[PART]
RUB = {4: [(0, 0), (46, 0.5), (58.5, 0.3), (84, 1.0)], 5: [(0, 0.2), (46, 0.6), (76, 1.0), (80.5, 0.3)],
       6: [(0, 0), (36, 0.5), (48, 0.3), (70.5, 1.0), (82, 0.6)]}[PART]
de, re_ = env_keys(DR), env_keys(RUB)
mL += dr * de + rub * re_ * de
mR += dr * de * 0.98 + np.roll(rub, 700) * re_ * de

# ---------------------------------------------------------------- the line: hiss and crackle while a voicemail or call is on
line_on = np.zeros(N)
for v in cues['voice']:
    if v['fx'] in ('you', 'glitch', 'sys', 'op'):
        a, b = int((v['t0'] - 0.6) * SR), int((v['t0'] + 4.5) * SR)
        line_on[max(0, a):min(N, b)] = 1
line_on = lp(line_on, 8, 1)
hiss = bp(rng.standard_normal(N), 400, 3400, 4) * 0.012
crk = np.zeros(N)
for _ in range(200):
    i = int(rng.uniform(0, 59) * SR)
    n = int(rng.uniform(0.002, 0.03) * SR)
    crk[i:i + n] += rng.standard_normal(n) * rng.uniform(0.01, 0.06) * np.exp(-np.arange(n) / (0.004 * SR))
line = hp(hiss + bp(crk, 300, 4000), 250) * line_on
L += line
R += line
room = lp(bp(rng.standard_normal(N), 200, 3000), 2000) * 0.02
L += room
R += np.roll(room, 9000)

# ---------------------------------------------------------------- PART 4: 99 NEW VOICEMAILS
if PART == 4:
    for at in ev['notify']:
        place(tone(1318.5, 0.6, 0.12) + tone(1760, 0.6, 0.1, 0.6), at, 0.07)
    pings(cues['chat'])
    for at in cues['chat']:                             # someone is typing
        for k in range(3):
            place(bp(rng.standard_normal(int(0.01 * SR)), 2000, 6000) * decay(int(0.01 * SR), 0.0005, 0.003), at - 0.4 + k * 0.1, 0.05)
    nb = int(0.42 * SR)
    place(bp(np.sin(2 * np.pi * 1000 * np.arange(nb) / SR), 300, 3400), ev['tapPlay'] + 0.35, 0.12)
    place(bp(np.sin(2 * np.pi * 1000 * np.arange(nb) / SR), 300, 3400), ev['playAll'] + 0.2, 0.12)
    # hallway hum, exactly as long as the light is on in the peephole
    light = np.ones(N)
    for a, c in cues['flicker']:
        light[int(a * SR): int(c * SR)] = 0
    zone = env_keys([(0, 0), (58.49, 0), (58.5, 1), (84.99, 1), (85, 0), (96, 0)])
    light = lp(light * zone, 400, 1)
    hum = np.tanh(1.5 * sum(np.sin(2 * np.pi * 120 * h * t + h) / h ** 0.8 for h in range(1, 14))) * 0.05
    L += hum * light
    R += np.roll(hum, 31) * light
    for a, c in cues['flicker']:                        # light comes back: more of them. A low hit each time.
        place(bp(rng.standard_normal(int(0.06 * SR)), 1500, 7000) * decay(int(0.06 * SR), 0.001, 0.015), c, 0.12, 0.2)
        place(lp(thud(48, 1.2, 0.0, int(c * 10)), 140), c, 0.35)
    # the whole hallway knocks at once
    for k in range(30):
        knock(500 + k, f=80 + 40 * rng.random(), gain=0.22 + 0.2 * rng.random(), pan=rng.uniform(-0.7, 0.7),
              at=ev['knocks'] + 0.1 + k * 0.11 * BEAT / 0.625 + rng.uniform(0, 0.05))
    boom(ev['title'])

# ---------------------------------------------------------------- PART 5: DON'T ANSWER
if PART == 5:
    def ring_cycle():
        # a plain phone ring: two short bursts of a warbling tone, then quiet
        n = int(2.0 * SR)
        tt = np.arange(n) / SR
        car = np.sin(2 * np.pi * 1300 * tt + 2.0 * np.sin(2 * np.pi * 20 * tt)) + 0.5 * np.sin(2 * np.pi * 1950 * tt)
        gate = ((tt < 0.4) | ((tt > 0.6) & (tt < 1.0))).astype(float)
        return bp(car * lp(gate, 60, 1), 600, 4000) * 0.5
    for a, c in ev['rings']:
        x = a
        while x < c - 0.4:
            place(ring_cycle(), x, 0.14, 0.1)
            place(haptic(0.4), x, 0.12)
            place(haptic(0.4), x + 0.6, 0.12)
            x += 2.2
    for at in ev['missed']:
        place(np.concatenate([tone(659.25, 0.18, 0.06), tone(523.25, 0.4, 0.1)]), at, 0.06)   # missed: two falling notes
    # 911: the keypad, then the ringback, then her
    for k, f in enumerate([(852, 1477), (697, 1209), (697, 1209)]):
        n = int(0.12 * SR)
        place((tone(f[0], 0.12, 1, 0.5) + tone(f[1], 0.12, 1, 0.5)) * np.ones(n), ev['dial'] - 0.6 + k * 0.2, 0.06)
    n = int(1.4 * SR)
    rb = (np.sin(2 * np.pi * 440 * np.arange(n) / SR) + np.sin(2 * np.pi * 480 * np.arange(n) / SR)) * (np.arange(n) < SR * 1.0)
    place(bp(rb, 300, 3400), ev['dial'] + 0.1, 0.04)
    pings([c for c in cues['chat'] if c > 0])
    # the phone on the floor buzzes against the boards while the voices plead
    for k in range(40):
        at = b2s(46) + k * b2s(1.5)
        if at < b2s(64):
            place(lp(haptic(0.35), 600), at, 0.16, 0.4)
    # soft knocks from more and more of them
    for k in range(22):
        at = b2s(48 + k * 0.75 + rng.uniform(0, 0.3))
        if at < b2s(64):
            knock(700 + k, f=70 + 50 * rng.random(), gain=0.12 + 0.1 * (k / 22), pan=rng.uniform(-0.6, 0.6), at=at, bright=0.4)
    # the clock montage: a tick per jump
    for b in (64, 67, 70, 73):
        place(tone(2093, 0.08, 0.02), b2s(b), 0.06, 0.4)
    # it answers itself: the click, then a breath on the line
    place(bp(rng.standard_normal(int(0.02 * SR)), 1500, 6000) * decay(int(0.02 * SR), 0.0005, 0.004), ev['answered'], 0.2)
    nbr = int(1.6 * SR)
    br = bp(rng.standard_normal(nbr), 400, 3400) * np.sin(np.linspace(0, np.pi, nbr)) ** 1.5
    place(br, ev['answered'] + 0.4, 0.07)
    boom(ev['title'])

# ---------------------------------------------------------------- PART 6: SUNRISE
if PART == 6:
    # morning: birds, far away, through a window you can't see
    for k in range(26):
        at = rng.uniform(0.5, b2s(68))
        n = int(rng.uniform(0.08, 0.2) * SR)
        tt = np.arange(n) / SR
        f = rng.uniform(2800, 4200)
        ch = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.25 * np.sin(2 * np.pi * rng.uniform(15, 30) * tt))) / SR) * np.sin(np.pi * tt / tt[-1])
        place(ch, at, rng.uniform(0.01, 0.03), rng.uniform(-0.8, 0.8))
    # the door
    od = b2s(ev['doorOpen'])
    no = int(b2s(3.5) * SR)
    to = np.arange(no) / SR
    groan = np.sin(2 * np.pi * np.cumsum(70 + 25 * np.sin(np.pi * to / to[-1])) / SR) * np.sin(np.pi * to / to[-1]) ** 2
    place(lp(np.tanh(2 * groan) + 0.3 * bp(rng.standard_normal(no), 300, 1200), 1500), od, 0.16)
    place(tone(1318.5, 0.6, 0.12) + tone(1760, 0.6, 0.1, 0.6), ev['notify'], 0.07)
    nb = int(0.42 * SR)
    place(bp(np.sin(2 * np.pi * 1000 * np.arange(nb) / SR), 300, 3400), ev['tapPlay'] + 0.35, 0.12)
    # you become the holder: Part 1's freeze
    fz = ev['freeze']
    nbm = int(2.5 * SR)
    tb = np.arange(nbm) / SR
    place(lp(np.tanh(1.5 * np.sin(2 * np.pi * np.cumsum(34 + 50 * np.exp(-tb * 9)) / SR) * np.exp(-tb * 2.2)), 110, 4), fz, 0.9)
    place(glass(1174.7, 4.0, 1.6), fz + 0.02, 0.08, -0.4)
    place(glass(1567.98, 4.0, 1.9), fz + 0.05, 0.05, 0.4)
    quiet = np.where(t < fz, 1.0, np.clip(1 - (t - fz) * 5, 0.25, 1))   # the world goes quiet around you
    L *= quiet
    R *= quiet
    # the card, and the three knocks from Part 2. Nobody answers them.
    place(lp(thud(40, 2.5, 0.0, 9), 120), ev['final'], 0.5)
    for k, at in enumerate(ev['knocks']):
        knock(900 + k, f=95, gain=0.6, pan=0.05, at=at)

# ---------------------------------------------------------------- voices on top; the music ducks under them
v = voice[:N] if len(voice) >= N else np.pad(voice, (0, N - len(voice)))
venv = lp(np.abs(v), 8)
duck = minimum_filter1d(1 - 0.75 * np.clip(venv / (venv.max() * 0.15), 0, 1), int(0.25 * SR))
L += mL * duck
R += mR * duck
vg = np.ones(N)
for ln in cues['voice']:
    a_ = int((ln['t0'] - 0.3) * SR)
    e_ = int((ln['t0'] + 5) * SR)
    vg[a_:e_] = {'whisper': 2.1, 'child': 1.7, 'op': 1.2, 'sys': 1.3}.get(ln['fx'], 1.0)
vr = reverb(v, 0.9, 0.12, 77)
L += vr * vg * 0.9
R += vr * vg * 0.9

if '--check' in sys.argv:
    m = pyln.Meter(SR, block_size=0.2)
    vb = np.stack([vr * vg * 0.9] * 2, axis=1)
    bed = np.stack([L, R], axis=1) - vb
    for ln in json.loads(open(f'src/voice_data{PART}.js').read().split('export const LINES = ')[1].split(';\n')[0]):
        a_, b_ = int(ln['v0'] * SR), int(ln['v1'] * SR)
        sp = lambda x: hp(x.T, 300, 4).T
        lvs, lbs = m.integrated_loudness(sp(vb[a_:b_])), m.integrated_loudness(sp(bed[a_:b_]))
        print(f"  {ln['id']:4s} speech band: voice {lvs - lbs:+5.1f} dB over everything else")

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
