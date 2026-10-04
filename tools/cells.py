# -*- coding: utf-8 -*-
"""确认 5x5 每个格子中心的真实内容与颜色。"""
import numpy as np
from PIL import Image

a = np.asarray(Image.open("map.jpg").convert("RGB")).astype(int)
H, W, _ = a.shape

# 从黑线检测得到的实际分界（像素）
xs = [0, 239.5, 445.5, 625.5, 829.5, 1080]
ys = [0, 242.5, 446.5, 635.5, 831.0, 1070]


def describe(x0, x1, y0, y1):
    x0, x1, y0, y1 = int(x0), int(x1), int(y0), int(y1)
    p = a[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(p, axis=0).astype(int)
    # 最亮的 20% 像素（相当于“底色”）
    lum = p.mean(axis=1)
    thr = np.percentile(lum, 80)
    base = np.median(p[lum >= thr], axis=0).astype(int)
    # 最暗的 5%
    thr2 = np.percentile(lum, 5)
    dark = np.median(p[lum <= thr2], axis=0).astype(int)
    return med, base, dark


print("每格：中位色 | 基底(亮)色 | 暗色 | size(px)")
for gy in range(5):
    for gx in range(5):
        x0, x1 = xs[gx], xs[gx + 1]
        y0, y1 = ys[gy], ys[gy + 1]
        # 内缩 12px 避开黑线
        med, base, dark = describe(x0 + 14, x1 - 14, y0 + 14, y1 - 14)
        print("r%dc%d  med(%3d,%3d,%3d)  base(%3d,%3d,%3d)  dark(%3d,%3d,%3d)  %dx%d"
              % (gy + 1, gx + 1, med[0], med[1], med[2], base[0], base[1], base[2],
                 dark[0], dark[1], dark[2], int(x1 - x0), int(y1 - y0)))
