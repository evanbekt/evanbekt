"""COUNTERSIGNED — voices. Piper TTS with the Kathleen voice (CC0), processed per character.

    python3 audio/voice.py /path/to/en-us-kathleen-low.onnx

Writes out/voice{1..6}.wav (48 kHz mono, lines on the timeline) and out/lines{1..6}.json
(start/end of each spoken line, for subtitles and the mix).
"""
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from story import PARTS  # noqa: E402

SR = 48000
N = 60 * SR
MODEL = sys.argv[1]


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def repitch(x, ratio):
    return signal.resample_poly(x, 100, int(round(100 * ratio)))


def room(x, rt, wet, seed):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - wet) + wet * signal.fftconvolve(x, ir)[: len(x)]


def whisperize(x, seed=3):
    r = np.random.default_rng(seed)
    f, t, Z = signal.stft(x, SR, nperseg=1024)
    _, y = signal.istft(np.abs(Z) * np.exp(1j * r.uniform(0, 2 * np.pi, Z.shape)), SR, nperseg=1024)
    y = hp(y[: len(x)], 700)
    return np.pad(y, (0, max(0, len(x) - len(y))))


def norm(x, peak):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


SIGNER = {'holder': (0.95, 1.15), 'marta': (1.0, 1.1), 'haas': (0.78, 1.15), 'lily': (1.24, 1.1), 'mara': (0.95, 1.18)}
SPEED_C, SPEED_CW = 1.35, 1.4


def counterparty(x):
    """Not one voice: a deep one, a sub-octave under it, a whisper above it. It arrives backwards."""
    a = repitch(x, 0.74)
    b = repitch(x, 0.37)
    w = whisperize(x)
    n = len(a)
    b = np.pad(b, (0, max(0, n - len(b))))[:n]
    w = np.pad(w, (0, max(0, n - len(w))))[:n]
    y = a + 0.32 * b + 0.45 * w
    tt = np.arange(n) / SR
    y = y * (1 - 0.18 + 0.18 * np.sin(2 * np.pi * 31 * tt))                 # a slow ring: not quite a throat
    pre = int(0.8 * SR)
    r = np.random.default_rng(9)
    ir = lp(r.standard_normal(pre) * np.exp(-np.arange(pre) / (0.25 * SR)), 4000)
    swell = signal.fftconvolve(y[::-1], ir)[: n + pre][::-1][:pre]
    swell = swell / (np.max(np.abs(swell)) + 1e-9) * np.linspace(0, 1, pre) ** 2
    y = np.concatenate([0.35 * swell, y])
    return norm(room(hp(y, 40), 2.6, 0.3, 6), 0.85), pre


def counterparty_whisper(x):
    a = repitch(x, 0.8)
    y = whisperize(a) * 1.3 + 0.25 * repitch(x, 0.4)[: len(a)] if len(repitch(x, 0.4)) >= len(a) else whisperize(a) * 1.3
    return norm(room(hp(y, 90), 0.5, 0.05, 7), 0.8), 0


def signer_fx(who, x):
    pitch, _ = SIGNER[who]
    y = repitch(x, pitch)
    return norm(room(hp(y, 90), 0.6, 0.1, 8), 0.75), 0


def synth(job):
    part, i, kind, at, text, who = job
    speed = SPEED_C if kind == 'c' else SPEED_CW if kind == 'cw' else SIGNER[who][1]
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run(['python3', '-m', 'piper', '-m', MODEL, '--length-scale', str(speed), '-f', f.name],
                       input=text.encode(), check=True, capture_output=True)
        x, sr = sf.read(f.name)
    x = signal.resample_poly(x if x.ndim == 1 else x.mean(axis=1), SR, sr)
    y, pre = counterparty(x) if kind == 'c' else counterparty_whisper(x) if kind == 'cw' else signer_fx(who, x)
    sf.write(f'audio/stems/{part}_{i:02d}_{kind}.wav', y.astype(np.float32), SR)
    return part, i, kind, at, text, len(y) / SR, pre / SR


if __name__ == '__main__':
    jobs = [(p, i, k, at, txt, P['signer']) for p, P in PARTS.items() for i, (k, at, txt) in enumerate(P['lines'])]
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(synth, jobs))
    for p in PARTS:
        track = np.zeros(N)
        lines = []
        for (pp, i, kind, at, text, dur, pre) in sorted(r for r in res if r[0] == p):
            y, _ = sf.read(f'audio/stems/{p}_{i:02d}_{kind}.wav')
            a = int((at - pre) * SR)
            b = min(N, a + len(y))
            track[a:b] += y[: b - a]
            lines.append(dict(kind=kind, t0=at, t1=round(at - pre + dur, 3), text=text))
        for a, b in zip(lines, lines[1:]):
            if a['t1'] > b['t0'] - 0.1:
                print(f'WARNING part {p}: "{a["text"]}" ends {a["t1"]:.2f}s, next starts {b["t0"]:.2f}s')
        sf.write(f'out/voice{p}.wav', track.astype(np.float32), SR)
        json.dump(lines, open(f'out/lines{p}.json', 'w'), indent=1)
        print(f'part {p}: {len(lines)} lines, last ends {lines[-1]["t1"]:.2f}s')
