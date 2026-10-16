"""Voices and timeline for one reel.

    python3 voice.py wild|him30|transfer
Reads <reel>/story.py: BEATS (each with lines [(who, text) or (who, text, opts)]) and VOICES
({who: dict(model, speed, pitch, room=(rt, wet), whisper, level)}).
Models: ryan (Piper "ryan", CC BY-NC-SA 4.0: fine for a personal, non-commercial profile video)
and kathleen (Piper "kathleen", CC0).
Writes <reel>/out/voice.wav, <reel>/out/timeline.json and per-line stems.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
VOX = '/tmp/claude-0/voices'
MODEL = {'ryan': f'{VOX}/en-us-ryan-high/en-us-ryan-high.onnx', 'kathleen': f'{VOX}/kathleen/en-us-kathleen-low.onnx'}
REEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), sys.argv[1])
spec = importlib.util.spec_from_file_location('story', os.path.join(REEL, 'story.py'))
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)


def room(x, rt, wet, seed):
    if wet <= 0:
        return x
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = lp(r.standard_normal(n) * np.exp(-np.arange(n) / (rt / 6.9 * SR)), 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    y = signal.fftconvolve(x, ir)
    return np.pad(x, (0, len(y) - len(x))) * (1 - wet) + wet * y


def level(x, target):
    env = np.sqrt(np.clip(lp(x ** 2, 30), 1e-9, None))
    return x * lp(np.clip(target / env, 0.3, 3.0), 8)


def whisperize(x, seed=3):
    r = np.random.default_rng(seed)
    _, _, Z = signal.stft(x, SR, nperseg=1024)
    _, y = signal.istft(np.abs(Z) * np.exp(1j * r.uniform(0, 2 * np.pi, Z.shape)), SR, nperseg=1024)
    y = hp(y[: len(x)], 600)
    return np.pad(y, (0, max(0, len(x) - len(y))))


def trim(x):
    idx = np.where(np.abs(x) > 0.01 * np.max(np.abs(x)))[0]
    return x[max(0, idx[0] - int(0.02 * SR)): idx[-1] + int(0.05 * SR)]


def synth(who, text, opts):
    v = dict(story.VOICES[who], **opts)
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run(['python3', '-m', 'piper', '-m', MODEL[v['model']], '--length-scale', str(v['speed']), '-f', f.name],
                       input=text.encode(), check=True, capture_output=True)
        x, sr = sf.read(f.name)
    x = trim(signal.resample_poly(x if x.ndim == 1 else x.mean(axis=1), SR, sr))
    p = v.get('pitch', 1.0)
    if p != 1.0:
        x = signal.resample_poly(x, 100, int(round(100 / p)))
    x = hp(x, 60) + v.get('chest', 0.0) * lp(x, 180)
    if v.get('whisper'):
        x = 0.35 * x + whisperize(x)
    x = np.tanh(v.get('drive', 1.5) * level(x, 0.13)) / np.tanh(v.get('drive', 1.5))
    if v.get('phone'):
        x = lp(hp(x, 400), 3200)
    n0 = len(x)
    rt, wet = v.get('room', (0.4, 0.05))
    x = room(x, rt, wet, 3)
    return x / (np.max(np.abs(x)) + 1e-9) * 0.8 * v.get('gain', 1.0), n0 / SR


if __name__ == '__main__':
    os.makedirs(os.path.join(REEL, 'stems'), exist_ok=True)
    t, beats, clips = 0.3, [], []
    for bi, b in enumerate(story.BEATS):
        t0 = t
        t += b.get('lead', 0.35)
        bl = []
        for li, line in enumerate(b['lines']):
            who, text = line[:2]
            opts = line[2] if len(line) > 2 else {}
            y, speech = synth(who, text, opts)
            sf.write(os.path.join(REEL, 'stems', f'{bi:02d}_{li}_{who}.wav'), y.astype(np.float32), SR)
            clips.append((t, y))
            bl.append(dict(who=who, text=opts.get('sub', text), t0=round(t, 3), t1=round(t + speech, 3)))
            last = li == len(b['lines']) - 1
            nxt = {} if last else (b['lines'][li + 1][2] if len(b['lines'][li + 1]) > 2 else {})
            t += speech + (0 if last else nxt.get('gap', b.get('gap', 0.28)))   # gap = the pause before a line
        t += b.get('hold', 0.3)
        beats.append(dict(b, t0=round(t0, 3), t1=round(t, 3), lines=bl))
    total = round(t + 0.5, 3)
    track = np.zeros(int((total + 4) * SR))
    for at, y in clips:
        a = int(at * SR)
        track[a:a + len(y)] += y
    sf.write(os.path.join(REEL, 'out', 'voice.wav'), track[: int(total * SR)].astype(np.float32), SR)
    json.dump(dict(total=total, beats=beats), open(os.path.join(REEL, 'out', 'timeline.json'), 'w'), indent=1)
    for b in beats:
        print(f'{b["t0"]:6.2f}-{b["t1"]:6.2f} {b["kind"]:8s} ' + ' | '.join(f'{l["who"]}: {l["text"]}' for l in b['lines']))
    print(sys.argv[1], 'total', total)
