"""Styleframes sheet: key frames rendered lossless from the timeline, plus palette and type.
   python3 tools/styleframes.py out/THE_OFFER_styleframes.png"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEAT = 60 / 128
FRAMES = [  # (beat, scene, caption)
    (8, '01  The message', '3:07 a.m. No sender. The phone is the only light.'),
    (19, '02  The power', 'Plain terms. One word in amber.'),
    (34, '02  The power', 'The world stops. You keep moving.'),
    (49.5, '03  The catch', 'Ninety-nine others.'),
    (72, '04  The math', 'Decline: someone stops the world. You never know.'),
    (88, '04  The math', 'Accept: they light up, one per beat.'),
    (112, '05  The realization', 'The second hand stutters. The count runs away.'),
    (122.5, '06  The question', 'A thumb over Accept.'),
    (126, '06  The question', 'Everything freezes but you.'),
]

tmp = tempfile.mkdtemp()
times = ','.join(f'{b * BEAT:.3f}' for b, _, _ in FRAMES)
subprocess.run(['node', os.path.join(ROOT, 'tools/render.mjs'), '--stills', times, '--ssub', '16', '--outdir', tmp], check=True)
shots = sorted(f for f in os.listdir(tmp) if f.endswith('.png'))

fw, fh, gap, mx = 800, 450, 36, 96
cols = 3
rows = (len(FRAMES) + cols - 1) // cols
W = mx * 2 + cols * fw + (cols - 1) * gap
head, cap, foot = 300, 96, 420
H = head + rows * (fh + cap) + foot
bg = (6, 7, 10)
sheet = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(sheet)
serif = lambda s: ImageFont.truetype(os.path.join(ROOT, 'fonts/InstrumentSerif-Regular.ttf'), s)
serif_i = lambda s: ImageFont.truetype(os.path.join(ROOT, 'fonts/InstrumentSerif-Italic.ttf'), s)


def inter(s, w=400):
    f = ImageFont.truetype(os.path.join(ROOT, 'fonts/Inter.ttf'), s)
    try:
        f.set_variation_by_axes([min(32, max(14, s)), w])
    except Exception:
        pass
    return f


INK, DIM = (226, 232, 242), (128, 140, 162)
d.text((mx, 110), 'THE OFFER', font=serif(120), fill=INK)
d.text((mx + 640, 158), 'Styleframes  ·  60 s  ·  128 BPM  ·  1920×1080 / 1080×1920', font=inter(30), fill=DIM)
for i, ((b, scene, caption), f) in enumerate(zip(FRAMES, shots)):
    x = mx + (i % cols) * (fw + gap)
    y = head + (i // cols) * (fh + cap)
    im = Image.open(os.path.join(tmp, f)).convert('RGB').resize((fw, fh), Image.LANCZOS)
    sheet.paste(im, (x, y))
    d.rectangle([x, y, x + fw - 1, y + fh - 1], outline=(30, 34, 44))
    d.text((x, y + fh + 18), scene.upper(), font=inter(18, 600), fill=DIM)
    d.text((x + 300, y + fh + 18), f'beat {b:g}  ·  {b * BEAT:.2f} s', font=inter(18), fill=(92, 102, 122))
    d.text((x, y + fh + 46), caption, font=serif_i(30), fill=INK)

# palette
y0 = head + rows * (fh + cap) + 60
d.text((mx, y0), 'PALETTE', font=inter(18, 600), fill=DIM)
pal = [((4, 5, 8), 'Room', '#040508', 'near-black'), ((22, 30, 48), 'Night', '#161E30', 'window, wall light'),
       ((184, 209, 255), 'Phone light', '#B8D1FF', 'the only light'), ((153, 219, 255), 'The others', '#99DBFF', 'ice-blue, 99 of them'),
       ((255, 143, 43), 'You', '#FF8F2B', 'a dying amber, used once')]
for i, (c, name, hx, note) in enumerate(pal):
    x = mx + i * 300
    d.rectangle([x, y0 + 40, x + 260, y0 + 150], fill=c, outline=(40, 44, 56))
    d.text((x, y0 + 166), name, font=inter(24, 600), fill=INK)
    d.text((x, y0 + 198), f'{hx}  ·  {note}', font=inter(18), fill=DIM)
# type
tx = mx + 1560
d.text((tx, y0), 'TYPE', font=inter(18, 600), fill=DIM)
d.text((tx, y0 + 34), 'Instrument Serif', font=serif(64), fill=INK)
d.text((tx, y0 + 108), 'story lines, condensed and unsettling', font=serif_i(28), fill=DIM)
d.text((tx, y0 + 164), 'Inter', font=inter(52, 300), fill=INK)
d.text((tx, y0 + 230), 'phone UI, labels, the counter', font=inter(22), fill=DIM)
sheet.save(OUT, optimize=True)
print('wrote', OUT)
