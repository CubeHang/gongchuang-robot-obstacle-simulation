# -*- coding: utf-8 -*-
"""直接读取截图像素：定位画布、验证格子颜色、定位绿色小车与黄色路径。"""
import sys
import numpy as np
from PIL import Image

src = sys.argv[1]
a = np.asarray(Image.open(src).convert("RGB")).astype(int)
H, W, _ = a.shape
print("截图尺寸 %dx%d" % (W, H))

R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
white = (R > 250) & (G > 250) & (B > 250)
ys, xs = np.where(white)
print("纯白像素 %d，范围 x %d..%d y %d..%d" % (white.sum(), xs.min(), xs.max(), ys.min(), ys.max()))

green = (G > 140) & (G > R + 60) & (G > B + 60)
print("绿色(小车/路径)像素 %d" % green.sum())
if green.sum():
    ys, xs = np.where(green)
    print("  绿色范围 x %d..%d y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))

yellow = (R > 200) & (G > 170) & (B < 120) & (abs(R - G) < 70)
print("黄色像素 %d" % yellow.sum())

blue = (B > 120) & (B > R + 60) & (B > G + 60)
print("蓝色像素 %d" % blue.sum())
if blue.sum():
    ys, xs = np.where(blue)
    print("  蓝色范围 x %d..%d y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))

# 横向扫描，找出画布左右边界（连续白色段）
for y in (30, 60, 120, H // 2):
    row = white[y]
    idx = np.where(row)[0]
    print("y=%d 白色像素 x %s" % (y, "%d..%d" % (idx.min(), idx.max()) if len(idx) else "无"))

print("\n前 40 行每行的白色像素数：")
for y in range(0, min(40, H)):
    print("  y=%3d white=%4d dark=%4d" % (y, white[y].sum(), (a[y].mean(axis=1) < 100).sum()))
