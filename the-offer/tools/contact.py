"""Contact sheet: label each image with its time and beat, tile into a grid.
   python3 tools/contact.py out.jpg cols thumbW img1.png img2.png ...  (times parsed from names *_SS.SS.png)"""
import sys, re
from PIL import Image, ImageDraw, ImageFont
out, cols, tw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
files = sys.argv[4:]
ims = [Image.open(f).convert('RGB') for f in files]
th = round(tw * ims[0].height / ims[0].width)
font = ImageFont.truetype('fonts/Inter.ttf', max(14, tw // 22))
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (tw + 8) + 8, rows * (th + 8) + 8), (40, 40, 44))
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 8)
    sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
    m = re.search(r'(\d+\.\d+)\.(png|jpg)$', f)
    if m:
        t = float(m.group(1))
        d = ImageDraw.Draw(sheet)
        d.text((x + 6, y + 4), f'{t:5.2f}s  b{t * 128 / 60:5.1f}', fill=(255, 220, 0), font=font)
sheet.save(out, quality=90)
