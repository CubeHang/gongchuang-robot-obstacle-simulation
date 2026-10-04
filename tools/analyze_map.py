# -*- coding: utf-8 -*-
"""分析比赛地图：找出黑色网格线位置，并给出 5x5 每格的主色。"""
import numpy as np
from PIL import Image

img = Image.open("map.jpg").convert("RGB")
a = np.asarray(img).astype(int)
H, W, _ = a.shape
print("size:", W, "x", H)

# 灰度 + 暗度判定
gray = a.mean(axis=2)
dark = gray < 110  # 黑线

col_dark = dark.sum(axis=0) / H
row_dark = dark.sum(axis=1) / W


def runs(profile, thr):
    out = []
    start = None
    for i, v in enumerate(profile):
        if v >= thr and start is None:
            start = i
        elif v < thr and start is not None:
            out.append((start, i - 1, (start + i - 1) / 2))
            start = None
    if start is not None:
        out.append((start, len(profile) - 1, (start + len(profile) - 1) / 2))
    return out


print("\n-- 竖线 (列方向, 阈值 0.5) --")
for r in runs(col_dark, 0.5):
    print("  x %d..%d  center %.1f  ratio %.2f" % (r[0], r[1], r[2], col_dark[int(r[2])]))

print("\n-- 横线 (行方向, 阈值 0.5) --")
for r in runs(row_dark, 0.5):
    print("  y %d..%d  center %.1f  ratio %.2f" % (r[0], r[1], r[2], row_dark[int(r[2])]))

# 按 5x5 均分取每格中心区域主色
print("\n-- 5x5 均分，每格中心 30% 区域主色 --")
for gy in range(5):
    row_txt = []
    for gx in range(5):
        x0 = int(W * gx / 5); x1 = int(W * (gx + 1) / 5)
        y0 = int(H * gy / 5); y1 = int(H * (gy + 1) / 5)
        cx0 = x0 + int((x1 - x0) * 0.35); cx1 = x0 + int((x1 - x0) * 0.65)
        cy0 = y0 + int((y1 - y0) * 0.35); cy1 = y0 + int((y1 - y0) * 0.65)
        patch = a[cy0:cy1, cx0:cx1].reshape(-1, 3)
        med = np.median(patch, axis=0).astype(int)
        r, g, b = med
        if r > 200 and g > 200 and b > 200:
            t = "W"       # 白
        elif r > 180 and g > 150 and b < 120:
            t = "Y"       # 黄
        elif b > 120 and b > r + 40:
            t = "B"       # 蓝
        elif r > 120 and r > g + 50 and r > b + 50:
            t = "R"       # 红
        elif max(r, g, b) < 120:
            t = "K"       # 黑
        else:
            t = "?"       # 灰/其他
        row_txt.append("%s(%3d,%3d,%3d)" % (t, r, g, b))
    print(" row%d " % (gy + 1), " ".join(row_txt))
