# -*- coding: utf-8 -*-
"""按像素分类输出 ASCII 图，便于看清真实布局。"""
import numpy as np
from PIL import Image

img = Image.open("map.jpg").convert("RGB")
a = np.asarray(img).astype(int)
H, W, _ = a.shape
print("size:", W, "x", H)

R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
mx = a.max(axis=2)

cls = np.full((H, W), ".", dtype="<U1")
cls[(R > 150) & (G > 130) & (B < 130)] = "Y"          # 黄
cls[(B > 120) & (B > R + 40)] = "B"                   # 蓝
cls[(R > 120) & (R > G + 50) & (R > B + 50)] = "R"    # 红
cls[mx < 130] = "K"                                   # 黑
cls[(R > 150) & (G > 150) & (B > 150)] = "w"          # 白/灰

# 以 12x12 像素为块做众数降采样
step = 12
out = []
for y in range(0, H - step + 1, step):
    line = []
    for x in range(0, W - step + 1, step):
        blk = cls[y:y + step, x:x + step].ravel()
        vals, cnt = np.unique(blk, return_counts=True)
        line.append(vals[cnt.argmax()])
    out.append("".join(line))

hdr = "    " + "".join(str((i // 10) % 10) for i in range(len(out[0])))
hdr2 = "    " + "".join(str(i % 10) for i in range(len(out[0])))
print(hdr)
print(hdr2)
for i, line in enumerate(out):
    print("%3d " % i, line)

# 每格的众数统计：以 5x5 均分为底
print("\n-- 5x5 均分：每格内各类像素占比 --")
for gy in range(5):
    row = []
    for gx in range(5):
        x0, x1 = int(W * gx / 5), int(W * (gx + 1) / 5)
        y0, y1 = int(H * gy / 5), int(H * (gy + 1) / 5)
        blk = cls[y0:y1, x0:x1].ravel()
        vals, cnt = np.unique(blk, return_counts=True)
        s = cnt.sum()
        top = sorted(zip(cnt, vals), reverse=True)[:3]
        row.append(" ".join("%s%.0f%%" % (v, 100 * c / s) for c, v in top))
    print(" r%d " % (gy + 1), " | ".join(row))
