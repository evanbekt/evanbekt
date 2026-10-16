"""307: OCCUPIED — the entity's voice. Piper TTS with the Kathleen voice (CC0), processed.

    python3 audio/voice.py /path/to/en-us-kathleen-low.onnx
Writes out/voice.wav (48 kHz mono, 60 s) and out/lines.json.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from story import LINES  # noqa: E402

SR = 48000
N = 60 * SR
MODEL = sys.argv[1]


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def repitch(x, ratio):
    return signal.resample_poly(x, 100, int(round(100 * ratio)))


def fit(x, n):
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def room(x, rt, wet, seed):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


def whisperize(x, seed=3):
    r = np.random.default_rng(seed)
    _, _, Z = signal.stft(x, SR, nperseg=1024)
    _, y = signal.istft(np.abs(Z) * np.exp(1j * r.uniform(0, 2 * np.pi, Z.shape)), SR, nperseg=1024)
    return fit(hp(y, 700), len(x))


def norm(x, peak):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def entity(x):
    """A deep voice, a sub-octave under it and a whisper over it, swelling in backwards."""
    a = repitch(x, 0.74)
    n = len(a)
    y = a + 0.32 * fit(repitch(x, 0.37), n) + 0.45 * fit(whisperize(x), n)
    y *= 1 - 0.18 + 0.18 * np.sin(2 * np.pi * 31 * np.arange(n) / SR)
    pre = int(0.8 * SR)
    ir = lp(np.random.default_rng(9).standard_normal(pre) * np.exp(-np.arange(pre) / (0.25 * SR)), 4000)
    swell = signal.fftconvolve(y[::-1], ir)[: n + pre][::-1][:pre]
    swell = swell / (np.max(np.abs(swell)) + 1e-9) * np.linspace(0, 1, pre) ** 2
    return norm(room(hp(np.concatenate([0.35 * swell, y]), 40), 2.6, 0.3, 6), 0.85), pre


def whisper(x):
    a = repitch(x, 0.8)
    y = whisperize(a) * 1.3 + 0.25 * fit(repitch(x, 0.4), len(a))
    return norm(room(hp(y, 90), 0.5, 0.05, 7), 0.8), 0


def small(x):
    """The same thing, deflated: a little higher, a little smaller, behind the door."""
    a = repitch(x, 0.92)
    y = a + 0.25 * fit(whisperize(a, 5), len(a))
    return norm(room(lp(hp(y, 160), 2600), 0.7, 0.18, 4), 0.6), 0


FX = {'c': (entity, 1.35), 'cw': (whisper, 1.4), 'small': (small, 1.2)}

track, lines = np.zeros(N), []
for i, (kind, at, text) in enumerate(LINES):
    fx, speed = FX[kind]
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run(['python3', '-m', 'piper', '-m', MODEL, '--length-scale', str(speed), '-f', f.name],
                       input=text.encode(), check=True, capture_output=True)
        x, sr = sf.read(f.name)
    x = signal.resample_poly(x if x.ndim == 1 else x.mean(axis=1), SR, sr)
    y, pre = fx(x)
    sf.write(f'audio/stems/{i:02d}_{kind}.wav', y.astype(np.float32), SR)
    a = int((at - pre / SR) * SR)
    b = min(N, a + len(y))
    track[a:b] += y[: b - a]
    lines.append(dict(kind=kind, t0=at, t1=round(at + (len(y) - pre) / SR, 3), text=text))
    print(f'{kind:5s} {at:5.1f}-{lines[-1]["t1"]:5.1f}  {text}')
sf.write('out/voice.wav', track.astype(np.float32), SR)
json.dump(lines, open('out/lines.json', 'w'), indent=1)
