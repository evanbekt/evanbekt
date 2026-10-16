"""THE TALL ONE — voices, and the timeline they set.

    python3 audio/voice.py
N: the narrator, Piper "ryan" (CC BY-NC-SA 4.0, RyanSpeech; fine for a personal, non-commercial
profile video), pitched down a touch, compressed, with a little hall.
K: the friend, Piper "kathleen" (CC0), dry and close.
Writes out/voice.wav (48 kHz mono) and out/timeline.json (beats and lines, in seconds).
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
from story import BEATS  # noqa: E402

SR = 48000
V = '/tmp/claude-0/voices'
MODELS = {'N': (f'{V}/en-us-ryan-high/en-us-ryan-high.onnx', 1.12), 'K': (f'{V}/kathleen/en-us-kathleen-low.onnx', 1.0)}


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def room(x, rt, wet, seed):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    y = signal.fftconvolve(x, ir)
    return np.pad(x, (0, len(y) - len(x))) * (1 - wet) + wet * y


def level(x, target=0.12, speed=0.03):
    """Gentle RMS leveller: a broadcast voice sits at one loudness."""
    env = np.sqrt(lp(x ** 2, 1 / speed) .clip(1e-9))
    g = np.clip(target / env, 0.3, 3.0)
    return x * lp(g, 8)


def trim(x, thr=0.01):
    idx = np.where(np.abs(x) > thr * np.max(np.abs(x)))[0]
    return x[max(0, idx[0] - int(0.02 * SR)): idx[-1] + int(0.05 * SR)]


def synth(who, text, big=False):
    model, speed = MODELS[who]
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run(['python3', '-m', 'piper', '-m', model, '--length-scale', str(speed), '-f', f.name],
                       input=text.encode(), check=True, capture_output=True)
        x, sr = sf.read(f.name)
    x = trim(signal.resample_poly(x if x.ndim == 1 else x.mean(axis=1), SR, sr))
    if who == 'N':
        x = signal.resample_poly(x, 100, 91)                      # about 1.6 semitones down
        x = hp(x, 55) + 0.35 * lp(x, 180)                         # weight in the chest
        x = np.tanh(2.2 * level(x, 0.14)) / np.tanh(2.2)
        n0 = len(x)
        x = room(x, 2.8 if big else 1.4, 0.22 if big else 0.1, 3)
    else:
        x = hp(level(x, 0.11), 120)
        n0 = len(x)
        x = room(x, 0.35, 0.06, 5)
    return x / (np.max(np.abs(x)) + 1e-9) * 0.8, n0 / SR


if __name__ == '__main__':
    t, lines, beats = 0.3, [], []
    clips = []
    for bi, b in enumerate(BEATS):
        t0 = t
        t += b.get('lead', 0.35)
        bl = []
        for li, (who, text) in enumerate(b['lines']):
            y, speech = synth(who, text, big=(bi == 0))
            sf.write(f'audio/stems/{bi:02d}_{li}_{who}.wav', y.astype(np.float32), SR)
            clips.append((t, y))
            bl.append(dict(who=who, text=text, t0=round(t, 3), t1=round(t + speech, 3)))
            last = li == len(b['lines']) - 1
            t += speech + (0 if last else 0.28) + (0.35 if b.get('scratch') and li == 0 else 0)
        t += b.get('hold', 0.3)
        beats.append(dict(b, t0=round(t0, 3), t1=round(t, 3), lines=bl))
        lines += bl
    total = round(t + 0.6, 3)
    track = np.zeros(int((total + 4) * SR))
    for at, y in clips:
        a = int(at * SR)
        track[a:a + len(y)] += y
    track = track[: int(total * SR)]
    sf.write('out/voice.wav', track.astype(np.float32), SR)
    json.dump(dict(total=total, beats=beats), open('out/timeline.json', 'w'), indent=1)
    for b in beats:
        print(f'{b["t0"]:6.2f}-{b["t1"]:6.2f} {b["kind"]:7s} ' + ' | '.join(f'{l["who"]}: {l["text"]}' for l in b['lines']))
    print('total', total)
