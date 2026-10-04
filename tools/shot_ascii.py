# -*- coding: utf-8 -*-
"""把截图粗略渲染成 ASCII，直观确认窗口布局。"""
import sys
import numpy as np
from PIL import Image

src = sys.argv[1] if len(sys.argv) > 1 else "tools/shots/state1.png"
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(int)
H, W, _ = a.shape
print("size %dx%d" % (W, H))
lum = a.mean(axis=2)
print("亮度直方图：")
for lo in range(0, 256, 32):
    n = ((lum >= lo) & (lum < lo + 32)).sum()
    print("  %3d-%3d : %8d  (%.1f%%)" % (lo, lo + 31, n, 100.0 * n / lum.size))

R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
step = 14
print("\nASCII（W=白/亮 Y=黄 B=蓝 G=绿 R=红 K=黑 .=中灰）")
hdr = "     " + "".join(str((i * step // 100) % 10) for i in range(W // step))
print(hdr)
for y in range(0, H - step + 1, step):
    line = []
    for x in range(0, W - step + 1, step):
        r = R[y:y + step, x:x + step].mean()
        g = G[y:y + step, x:x + step].mean()
        b = B[y:y + step, x:x + step].mean()
        l = (r + g + b) / 3
        if b > 120 and b > r + 50 and b > g + 50:
            ch = "B"
        elif g > 120 and g > r + 40 and g > b + 40:
            ch = "G"
        elif r > 170 and g > 140 and b < 130:
            ch = "Y"
        elif r > 150 and r > g + 50 and r > b + 50:
            ch = "R"
        elif l < 60:
            ch = "K"
        elif l > 235:
            ch = "W"
        elif l > 180:
            ch = "."
        else:
            ch = ","
        line.append(ch)
    print("%4d " % y, "".join(line))
