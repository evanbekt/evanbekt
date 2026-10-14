"""Loudness per octave band and per scene, read back from an audio file (wav or the muxed mp4's audio).
   python3 tools/audio_report.py file.wav audio/cues.json"""
import json, subprocess, sys
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

path, cues = sys.argv[1], json.load(open(sys.argv[2]))
if not path.endswith('.wav'):
    tmp = '/tmp/_ar.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path, '-vn', '-ac', '2', '-ar', '48000', tmp], check=True)
    path = tmp
x, sr = sf.read(path)
m = pyln.Meter(sr)
up = signal.resample_poly(x, 4, 1, axis=0)
print(f'integrated {m.integrated_loudness(x):6.2f} LUFS   true peak {20*np.log10(np.abs(up).max()):6.2f} dBTP   '
      f'LRA-ish (short-term p10-p95) see below')
print('\nper octave band (integrated loudness of the band-limited mix, LUFS; "-inf" = silent)')
bands = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
for fc in bands:
    lo, hi = fc / np.sqrt(2), min(fc * np.sqrt(2), sr / 2 * 0.99)
    sos = signal.butter(4, [lo, hi], 'band', fs=sr, output='sos')
    y = signal.sosfilt(sos, x, axis=0)
    try:
        v = m.integrated_loudness(y)
    except Exception:
        v = -np.inf
    rms = 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-12)
    print(f'  {fc:7.1f} Hz  {v:7.1f} LUFS   rms {rms:6.1f} dBFS  ' + '#' * max(0, int((rms + 60) / 1.5)))
ph = signal.sosfilt(signal.butter(4, 300, 'high', fs=sr, output='sos'), x, axis=0)
print(f'\nphone-speaker check (4th-order HP at 300 Hz): {m.integrated_loudness(ph):6.2f} LUFS  '
      f'(full-range minus phone = {m.integrated_loudness(x) - m.integrated_loudness(ph):.1f} dB)')
print('\nper scene')
for s in cues['scenes']:
    a, b = int(s['t0'] * sr), int(s['t1'] * sr)
    seg = x[a:b]
    try:
        v = m.integrated_loudness(seg)
    except Exception:
        v = -np.inf
    print(f"  scene {s['id']} {s['name']:16s} {s['t0']:6.2f}-{s['t1']:6.2f}s  {v:7.1f} LUFS")
sil = cues['events']['silence']
tail = x[int((sil + 0.01) * sr):]
print(f'\nlast beat ({sil:.3f}s -> end): peak {20*np.log10(np.abs(tail).max()+1e-12):.1f} dBFS  (want silence)')
# short-term loudness curve, 3 s windows every 1 s
st = []
for i in range(0, len(x) - 3 * sr, sr):
    try:
        st.append(m.integrated_loudness(x[i:i + 3 * sr]))
    except Exception:
        st.append(-70)
st = np.array(st)
print('short-term (3 s) per second:', ' '.join(f'{v:.0f}' for v in np.clip(st, -70, 0)))
