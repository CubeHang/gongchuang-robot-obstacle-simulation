# -*- coding: utf-8 -*-
"""精确定位黑线、彩色方块的范围。"""
import numpy as np
from PIL import Image

a = np.asarray(Image.open("map.jpg").convert("RGB")).astype(int)
H, W, _ = a.shape
R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
mx = a.max(axis=2)
mn = a.min(axis=2)

black = mx < 110
yellow = (R > 150) & (G > 130) & (B < 130)
blue = (B > 120) & (B > R + 40) & (B > G + 40)
red = (R > 120) & (R > G + 50) & (R > B + 50)

print("全图黑像素: %.2f%%  黄: %.2f%%  蓝: %.2f%%  红: %.2f%%" %
      (100 * black.mean(), 100 * yellow.mean(), 100 * blue.mean(), 100 * red.mean()))

colr = black.sum(axis=0)
rowr = black.sum(axis=1)
print("\n黑色像素数 > 30%% 的列（x: 占比）:")
print([(x, round(colr[x] / H, 2)) for x in range(W) if colr[x] / H > 0.30][:80])
print("\n黑色像素数 > 30%% 的行（y: 占比）:")
print([(y, round(rowr[y] / W, 2)) for y in range(H) if rowr[y] / W > 0.30][:80])


def bbox(mask, name):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        print(name, "none")
        return
    print("%s: x %d..%d  y %d..%d  (面积 %d)" % (name, xs.min(), xs.max(), ys.min(), ys.max(), len(xs)))


print()
bbox(yellow, "黄色整体")
bbox(blue, "蓝色整体")
bbox(red, "红色整体")

# 黄色连通块（按行列投影分块）
ys, xs = np.where(yellow)
print("\n黄色区 x 直方图分布段:")
xu = np.unique(xs)
segs = []
s = xu[0]
p = xu[0]
for v in xu[1:]:
    if v - p > 5:
        segs.append((s, p))
        s = v
    p = v
segs.append((s, p))
print(segs)
yu = np.unique(ys)
segs = []
s = yu[0]
p = yu[0]
for v in yu[1:]:
    if v - p > 5:
        segs.append((s, p))
        s = v
    p = v
segs.append((s, p))
print("黄色区 y 分布段:", segs)

for name, mask in (("蓝", blue), ("红", red)):
    ys, xs = np.where(mask)
    xu = np.unique(xs); segs = []; s = xu[0]; p = xu[0]
    for v in xu[1:]:
        if v - p > 5:
            segs.append((s, p)); s = v
        p = v
    segs.append((s, p))
    yu = np.unique(ys); segs2 = []; s = yu[0]; p = yu[0]
    for v in yu[1:]:
        if v - p > 5:
            segs2.append((s, p)); s = v
        p = v
    segs2.append((s, p))
    print("%s x 段: %s  y 段: %s" % (name, segs, segs2))
