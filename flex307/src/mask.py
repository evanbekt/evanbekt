"""The tenant's matte: the two nets combined, minus the two coworkers, feathered."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

a = np.asarray(Image.open('assets/m_isnet.png'), np.float32) / 255
b = np.asarray(Image.open('assets/m_human.png'), np.float32) / 255
H, W = a.shape
m = np.where(np.arange(H)[:, None] < 0.62 * H, np.maximum(a, b), np.minimum(a, b))
S = W / 2000                                         # polygons drawn on a 2000-wide view of the photo
cut = Image.new('L', (W, H), 0)
d = ImageDraw.Draw(cut)
for poly in [
    [(660, 340), (744, 340), (746, 470), (736, 512), (660, 520)],                   # the colleague behind his left shoulder
    [(990, 438), (1150, 430), (1252, 592), (1100, 590), (1040, 584), (980, 562)],   # the colleague seen through his arm
    [(1088, 748), (1380, 722), (1380, 840), (1060, 850)],                           # their arm, under his bicep
    [(1040, 780), (1380, 780), (1380, 985), (1040, 1005)],                          # their lap, by the desk
]:
    d.polygon([(x * S, y * S) for x, y in poly], fill=255)
cut = np.asarray(cut.filter(ImageFilter.GaussianBlur(6 * S)), np.float32) / 255
m = np.clip((m - 0.15) / 0.7, 0, 1) * (1 - cut)
Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)).save('assets/matte.png')
src = np.asarray(Image.open('assets/source.jpg').convert('RGB'), np.float32)
dbg = src * (0.15 + 0.85 * m[..., None]) + np.array([255, 0, 0]) * (cut[..., None] * 0.35)
Image.fromarray(np.clip(dbg, 0, 255).astype(np.uint8)).resize((1000, 667)).save('/tmp/claude-0/-home-user-evanbekt/2277fd8d-d77e-561f-8e0e-9ccc458b91c8/scratchpad/matte_dbg.png')
