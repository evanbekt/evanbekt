"""Cut the tenant out of the source photo: two segmentation nets, averaged, then cleaned up."""
import sys
import numpy as np
import onnxruntime as ort
from PIL import Image

M = '/tmp/claude-0/models'
im = Image.open(sys.argv[1]).convert('RGB')
W, H = im.size


def run(model, size, mean, std):
    s = ort.InferenceSession(f'{M}/{model}', providers=['CPUExecutionProvider'])
    x = np.asarray(im.resize((size, size), Image.LANCZOS), np.float32) / 255
    x = ((x - mean) / std).transpose(2, 0, 1)[None].astype(np.float32)
    y = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    y = (y - y.min()) / (y.max() - y.min() + 1e-9)
    return np.asarray(Image.fromarray((y * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS), np.float32) / 255


a = run('isnet.onnx', 1024, np.array([.5, .5, .5]), np.array([1., 1., 1.]))
b = run('u2net_human_seg.onnx', 320, np.array([.485, .456, .406]), np.array([.229, .224, .225]))
Image.fromarray((a * 255).astype(np.uint8)).save(sys.argv[2] + '_isnet.png')
Image.fromarray((b * 255).astype(np.uint8)).save(sys.argv[2] + '_human.png')
