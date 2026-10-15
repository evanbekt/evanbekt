"""The voice: synthesized with Piper (Kathleen voice, CC0), then made wrong.

    python3 audio/voice.py audio/cues.json /path/to/en-us-kathleen-low.onnx

Writes audio/stems/<id>.wav (processed, 48 kHz), out/voice.wav (all lines on the timeline)
and src/voice_data.js (line timings, word timings, and a 3 kHz copy of the voice the
renderer draws as the waveform).
"""
import base64
import json
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
cues = json.load(open(sys.argv[1]))
MODEL = sys.argv[2]
N = int(cues['duration'] * SR)
rng = np.random.default_rng(314)


def synth(text, speed):
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run(['python3', '-m', 'piper', '-m', MODEL, '--length-scale', str(speed), '-f', f.name],
                       input=text.encode(), check=True, capture_output=True)
        x, sr = sf.read(f.name)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return signal.resample_poly(x, SR, sr)


def bp(x, lo, hi, order=4):
    return signal.sosfilt(signal.butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'high', fs=SR, output='sos'), x)


def repitch(x, ratio):
    """Pitch AND formants by `ratio` (< 1 = lower, slower). Slightly too low for a person."""
    up, down = 100, int(round(100 * ratio))
    return signal.resample_poly(x, up, down)


def whisperize(x):
    """Keep the spectral envelope, throw away the pitch: random phase STFT."""
    f, t, Z = signal.stft(x, SR, nperseg=1024)
    mag = np.abs(Z)
    ph = np.exp(1j * rng.uniform(0, 2 * np.pi, Z.shape))
    _, y = signal.istft(mag * ph, SR, nperseg=1024)
    y = hp(y[:len(x)], 900) * 1.4
    return np.pad(y, (0, max(0, len(x) - len(y))))


def reverse_swell(x, dur=0.9):
    """The reverb of the line, played backwards, arriving before the line does."""
    n = int(dur * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.25 * SR))
    ir = lp(ir, 5000)
    wet = signal.fftconvolve(x[::-1], ir)[: len(x) + n][::-1]
    wet /= np.max(np.abs(wet)) + 1e-9
    return wet[:n] * np.linspace(0, 1, n) ** 2


def phone(x, lo=300, hi=3400, drive=2.0):
    y = bp(x, lo, hi)
    y = np.tanh(drive * y) / np.tanh(drive)
    return y


def norm(x, peak=0.8):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def fx_sys(x):
    return norm(phone(x, 320, 3400, 1.5), 0.6), 0


def fx_you(x, swell=False):
    a = repitch(x, 0.88)                       # down ~2.2 semitones, formants too
    b = repitch(x, 0.865)                      # a second you, a hair lower: they beat against each other
    d = int(0.019 * SR)
    b = np.pad(b, (d, 0))[: len(a)]
    b = np.pad(b, (0, len(a) - len(b)))
    w = whisperize(a)
    y = a + 0.45 * b + 0.30 * w
    y = phone(y, 260, 3600, 2.4)
    pre = 0
    if swell:
        s = reverse_swell(y)
        y = np.concatenate([0.35 * phone(s, 260, 3600, 1.0), y])
        pre = len(s)
    return norm(y), pre


def fx_glitch(x):
    y, _ = fx_you(x)
    # stutter the first syllable, drop the line out once, crush a stretch
    g = int(0.075 * SR)
    st = np.concatenate([y[:g]] * 3 + [y])
    mid = int(len(st) * 0.55)
    st[mid: mid + int(0.11 * SR)] *= 0.02
    seg = slice(int(len(st) * 0.68), int(len(st) * 0.85))
    q = 2 ** 4
    st[seg] = np.round(st[seg] * q) / q
    hold = st[seg][:: 6].repeat(6)[: seg.stop - seg.start]
    st[seg] = 0.5 * st[seg] + 0.5 * hold
    return norm(st), 0


def fx_whisper(x):
    a = repitch(x, 0.93)
    w = whisperize(a)
    y = w + 0.12 * lp(a, 2500)               # almost no voice left: breath with words in it
    y = hp(y, 120)
    return norm(y, 0.7), 0


FX = {'sys': fx_sys, 'you': fx_you, 'glitch': fx_glitch, 'whisper': fx_whisper}
SWELL = {'l1', 'l4', 'l6'}

track = np.zeros(N)
lines = []
for v in cues['voice']:
    raw = synth(v['text'], v['speed'])
    if v['fx'] == 'you':
        y, pre = fx_you(raw, swell=v['id'] in SWELL)
    else:
        y, pre = FX[v['fx']](raw)
    sf.write(f"audio/stems/{v['id']}.wav", y.astype(np.float32), SR)
    i0 = int(v['t0'] * SR) - pre
    i1 = min(N, i0 + len(y))
    track[i0:i1] += y[: i1 - i0]
    speech0 = v['t0']
    speech1 = (i0 + len(y)) / SR
    # word timings: spread the words over the voiced part by character weight
    env = np.abs(signal.hilbert(y[pre:]))
    env = lp(env, 20)
    voiced = np.nonzero(env > 0.06 * env.max())[0]
    v0 = speech0 + (voiced[0] / SR if len(voiced) else 0)
    v1 = speech0 + (voiced[-1] / SR if len(voiced) else len(y) / SR)
    words = (v.get('caption') or v['text']).split(' ')
    wts = np.array([len(w) + 2 for w in words], float)
    cum = np.concatenate([[0], np.cumsum(wts)]) / wts.sum()
    lines.append({'id': v['id'], 'fx': v['fx'], 't0': round(speech0, 4), 't1': round(speech1, 4),
                  'v0': round(v0, 4), 'v1': round(v1, 4),
                  'words': [{'w': w, 't': round(v0 + c * (v1 - v0), 4)} for w, c in zip(words, cum[:-1])]})
    print(f"{v['id']:4s} {v['fx']:8s} {speech0:6.2f}-{speech1:6.2f}s  ({speech1 - speech0:4.2f}s)  {v['text']}")

# check no line runs into the next one
for a, b in zip(lines, lines[1:]):
    if a['t1'] > b['t0'] - 0.15:
        print(f"WARNING: {a['id']} ends at {a['t1']:.2f}s, {b['id']} starts at {b['t0']:.2f}s")

sf.write('out/voice.wav', track.astype(np.float32), SR)
wf = signal.resample_poly(track, 1, 16)                    # 3 kHz, plenty for a drawn waveform
wf = np.clip(np.round(wf / (np.max(np.abs(wf)) + 1e-9) * 127), -127, 127).astype(np.int8)
b64 = base64.b64encode(wf.tobytes()).decode()
with open('src/voice_data.js', 'w') as f:
    f.write('// Generated by audio/voice.py. Do not edit.\n')
    f.write(f'export const LINES = {json.dumps(lines)};\n')
    f.write(f'export const WAVE_RATE = {SR // 16};\n')
    f.write(f'export const WAVE_B64 = "{b64}";\n')
print('wrote out/voice.wav, src/voice_data.js', f'({len(b64) / 1e3:.0f} kB waveform)')
