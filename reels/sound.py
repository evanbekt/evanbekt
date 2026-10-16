"""Shared sound kit for the reels: filters, placement, instruments, and a master that rides the
music under the voices and lands at -14 LUFS, <= -1 dBTP."""
import json
import os

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d

SR = 48000


class Mix:
    def __init__(self, reel_dir, seed):
        self.dir = reel_dir
        self.tl = json.load(open(os.path.join(reel_dir, 'out', 'timeline.json')))
        self.N = int(self.tl['total'] * SR)
        self.t = np.arange(self.N) / SR
        self.rng = np.random.default_rng(seed)
        self.mus = np.zeros((2, self.N))
        self.fx = np.zeros((2, self.N))

    def place(self, sig, at, gain=1.0, pan=0.0, bus='mus'):
        i = int(round(at * SR))
        if i >= self.N or i + len(sig) <= 0:
            return
        s = sig[max(0, -i): self.N - i] * gain
        i = max(0, i)
        a = (pan + 1) * np.pi / 4
        b = self.mus if bus == 'mus' else self.fx
        b[0, i:i + len(s)] += s * np.cos(a)
        b[1, i:i + len(s)] += s * np.sin(a)

    def noise(self, n):
        return self.rng.standard_normal(n)

    def master(self, duck_depth=0.6, voice_gain=1.25):
        v, _ = sf.read(os.path.join(self.dir, 'out', 'voice.wav'))
        v = np.pad(v, (0, max(0, self.N - len(v))))[: self.N]
        venv = lp(np.abs(v), 8)
        duck = minimum_filter1d(1 - duck_depth * np.clip(venv / (venv.max() * 0.1), 0, 1), int(0.3 * SR))
        Lm = self.mus * duck + self.fx * (0.6 + 0.4 * duck)
        mix = (Lm + voice_gain * v).T
        fade = np.ones(self.N)
        fade[-int(0.5 * SR):] = np.linspace(1, 0, int(0.5 * SR)) ** 2
        mix = hp((mix * fade[:, None]).T, 28).T
        m = pyln.Meter(SR)
        mix *= 10 ** ((-14.0 - m.integrated_loudness(mix)) / 20)
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
        worst = 99
        for b in self.tl['beats']:
            for ln in b['lines']:
                a, e = int(ln['t0'] * SR), int(ln['t1'] * SR)
                vv = np.stack([voice_gain * v[a:e]] * 2, axis=1)
                d = m.integrated_loudness(hp(vv.T, 300, 4).T) - m.integrated_loudness(hp(Lm[:, a:e], 300, 4).T)
                worst = min(worst, d)
        sf.write(os.path.join(self.dir, 'out', 'score.wav'), mix.astype(np.float32), SR, subtype='PCM_24')
        print(f'{os.path.basename(self.dir)}: {m.integrated_loudness(mix):.2f} LUFS, true peak {true_peak(mix):.2f} dBTP, '
              f'weakest line {worst:+.1f} dB over the bed')


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def bp(x, a, b, o=2):
    return signal.sosfilt(signal.butter(o, [a, min(b, SR / 2 - 100)], 'band', fs=SR, output='sos'), x)


def true_peak(x):
    return 20 * np.log10(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0))) + 1e-12)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def reverb(x, rt=1.8, wet=0.3, seed=1):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def pad(notes, dur, bright=1500, att=0.8, rel=1.0, seed=0):
    """Soft string pad: detuned saws, low-passed, slow in and out."""
    r = np.random.default_rng(seed)
    x = tt(dur)
    s = sum(signal.sawtooth(2 * np.pi * hz(m) * d * x + r.uniform(0, 6)) for m in notes for d in (0.997, 1.0, 1.003))
    s = lp(s / (3 * len(notes)), bright)
    return s * np.minimum(1, x / att) * np.minimum(1, (dur - x) / rel)


def pluck(f, dur=1.5, bright=1.0):
    x = tt(dur)
    s = np.sin(2 * np.pi * f * x) + 0.4 * bright * np.sin(2 * np.pi * 2 * f * x) * np.exp(-x * 8) + 0.2 * bright * np.sin(2 * np.pi * 3 * f * x) * np.exp(-x * 14)
    return s * np.minimum(1, x / 0.003) * np.exp(-x * 3)


def kick(level=1.0):
    x = tt(0.35)
    return np.tanh(3 * np.sin(2 * np.pi * np.cumsum(50 * (1 + 2.5 * np.exp(-x * 40))) / SR) * np.exp(-x * 9)) * level


def snare(rng, level=1.0):
    x = tt(0.3)
    return (bp(rng.standard_normal(len(x)), 1500, 9000) * np.exp(-x * 18) * 0.8 + np.sin(2 * np.pi * 190 * x) * np.exp(-x * 30) * 0.6) * level


def clap(rng):
    x = tt(0.25)
    env = sum(np.exp(-np.maximum(x - d, 0) * 60) * (x >= d) for d in (0, 0.012, 0.024))
    return bp(rng.standard_normal(len(x)), 900, 6000) * env * 0.6


def hat(rng, dur=0.05):
    x = tt(dur)
    return hp(rng.standard_normal(len(x)), 7000) * np.exp(-x / (dur / 5))


def whoosh(rng, dur=0.5):
    x = tt(dur)
    n = rng.standard_normal(len(x))
    out = np.zeros(len(x))
    k = 8
    for i in range(k):
        a, b = i * len(x) // k, (i + 1) * len(x) // k
        c = 400 + 5000 * (x[a] / dur) ** 2
        out[a:b] = bp(n, c * 0.6, c * 1.6)[a:b]
    return out * (x / dur) ** 2 * 0.8


def boom(rng, dur=1.4, f=46):
    x = tt(dur)
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-x * 25))) / SR) * np.exp(-x * 3.2)
    return reverb(np.tanh(2.2 * body) + lp(rng.standard_normal(len(x)), 2000) * np.exp(-x * 40) * 0.5, 2.0, 0.25, 3)


def ding(f=1760, dur=0.6):
    x = tt(dur)
    return (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2.76 * x) * np.exp(-x * 12)) * np.exp(-x * 7)
