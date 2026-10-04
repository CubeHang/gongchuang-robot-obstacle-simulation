# -*- coding: utf-8 -*-
"""把指定像素区域的深色像素渲染成 ASCII，用于识别数字/文字。"""
import sys
import numpy as np
from PIL import Image

a = np.asarray(Image.open("map.jpg").convert("RGB")).astype(int)
lum = a.mean(axis=2)

x0, y0, x1, y1 = (int(v) for v in sys.argv[1:5])
step = int(sys.argv[5]) if len(sys.argv) > 5 else 3
thr = float(sys.argv[6]) if len(sys.argv) > 6 else 170.0

sub = lum[y0:y1, x0:x1]
print("region x %d..%d y %d..%d  min %.0f max %.0f" % (x0, x1, y0, y1, sub.min(), sub.max()))
rows = []
for y in range(0, sub.shape[0] - step + 1, step):
    line = []
    for x in range(0, sub.shape[1] - step + 1, step):
        blk = sub[y:y + step, x:x + step]
        line.append("#" if blk.min() < thr else ".")
    rows.append("".join(line))
print("     " + "".join(str((x0 + i * step) // 100 % 10) for i in range(len(rows[0]))))
for i, r in enumerate(rows):
    print("%4d " % (y0 + i * step), r)
