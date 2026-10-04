# -*- coding: utf-8 -*-
"""列出所有内部黑色线段（横/竖），确定网格。"""
import numpy as np
from PIL import Image

a = np.asarray(Image.open("map.jpg").convert("RGB")).astype(int)
H, W, _ = a.shape
mx = a.max(axis=2); mn = a.min(axis=2)
black = (mx < 130) & ((mx - mn) < 60)

colr = black.sum(axis=0) / H
rowr = black.sum(axis=1) / W


def report(profile, label, limit):
    print("\n=== %s：占比 > 0.25 的连续段 ===" % label)
    segs = []
    s = None
    for i, v in enumerate(profile):
        if v > 0.25 and s is None:
            s = i
        elif v <= 0.25 and s is not None:
            segs.append((s, i - 1))
            s = None
    if s is not None:
        segs.append((s, len(profile) - 1))
    for s, e in segs:
        mid = (s + e) // 2
        print("   %s %4d..%4d  (w=%d)  峰值占比 %.2f" % (label, s, e, e - s + 1, profile[mid]))


report(colr, "竖线 x", W)
report(rowr, "横线 y", H)

# 也看看弱一些的线（0.1~0.25）
print("\n=== 竖线 占比 0.08~0.25（可能是短线段） ===")
for i, v in enumerate(colr):
    if 0.08 < v <= 0.25:
        print("   x=%d %.2f" % (i, v))
print("\n=== 横线 占比 0.08~0.25 ===")
for i, v in enumerate(rowr):
    if 0.08 < v <= 0.25:
        print("   y=%d %.2f" % (i, v))
