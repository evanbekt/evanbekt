"""DEVELOPING — voices. Piper TTS with the Kathleen voice (CC0), processed per character.

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


SPEED = {'m': 1.18, 'mw': 1.3, 'e': 1.05, 'ed': 1.1, 'n': 0.98}


def fx(kind, x):
    if kind == 'm':        # Mara: a little lower and slower than the voice was made, close and dry
        y = repitch(x, 0.95)
        return norm(room(hp(y, 80), 0.5, 0.08, 1), 0.8)
    if kind == 'mw':       # Mara whispering to herself
        y = repitch(x, 0.95)
        y = 0.35 * y + whisperize(y) * 1.2
        return norm(room(hp(y, 120), 0.4, 0.06, 2), 0.7)
    if kind == 'e':        # Elise, sixteen: higher, brighter, in the room
        y = repitch(x, 1.12)
        return norm(room(hp(y, 120), 0.6, 0.12, 3), 0.75)
    if kind == 'ed':       # Elise on the other side of the door
        y = repitch(x, 1.12)
        y = lp(y, 1400, 4) * 1.5
        return norm(room(hp(y, 150), 1.1, 0.35, 4), 0.55)
    if kind == 'n':        # the nurse: lower, brisk, the corridor behind her
        y = repitch(x, 0.86)
        return norm(room(hp(y, 100), 1.3, 0.22, 5), 0.7)
    raise ValueError(kind)


def synth(job):
    part, i, kind, at, text = job
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run(['python3', '-m', 'piper', '-m', MODEL, '--length-scale', str(SPEED[kind]), '-f', f.name],
                       input=text.encode(), check=True, capture_output=True)
        x, sr = sf.read(f.name)
    x = signal.resample_poly(x if x.ndim == 1 else x.mean(axis=1), SR, sr)
    y = fx(kind, x)
    sf.write(f'audio/stems/{part}_{i:02d}_{kind}.wav', y.astype(np.float32), SR)
    return part, i, kind, at, text, len(y) / SR


if __name__ == '__main__':
    jobs = [(p, i, k, at, txt) for p, P in PARTS.items() for i, (k, at, txt) in enumerate(P['lines'])]
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(synth, jobs))
    for p in PARTS:
        track = np.zeros(N)
        lines = []
        for (pp, i, kind, at, text, dur) in sorted(r for r in res if r[0] == p):
            y, _ = sf.read(f'audio/stems/{p}_{i:02d}_{kind}.wav')
            a = int(at * SR)
            b = min(N, a + len(y))
            track[a:b] += y[: b - a]
            lines.append(dict(kind=kind, t0=at, t1=round(at + dur, 3), text=text))
        for a, b in zip(lines, lines[1:]):
            if a['t1'] > b['t0'] - 0.1:
                print(f'WARNING part {p}: "{a["text"]}" ends {a["t1"]:.2f}s, next starts {b["t0"]:.2f}s')
        sf.write(f'out/voice{p}.wav', track.astype(np.float32), SR)
        json.dump(lines, open(f'out/lines{p}.json', 'w'), indent=1)
        print(f'part {p}: {len(lines)} lines, last ends {lines[-1]["t1"]:.2f}s')
