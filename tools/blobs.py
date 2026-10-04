# -*- coding: utf-8 -*-
"""在非网格线区域寻找深色文字块。"""
import numpy as np
from PIL import Image
from scipy import ndimage  # 可能不存在

a = np.asarray(Image.open("map.jpg").convert("RGB")).astype(int)
H, W, _ = a.shape
lum = a.mean(axis=2)

dark = lum < 165
# 屏蔽已知网格线
for x0, x1 in ((233, 247), (439, 453), (619, 633), (823, 837), (1072, 1080)):
    dark[:, x0:x1] = False
for y0, y1 in ((236, 250), (440, 454), (629, 643), (824, 839)):
    dark[y0:y1, :] = False

print("屏蔽网格线后深色像素:", dark.sum())

# 简单的连通域（4 邻域 BFS）
lab = np.zeros((H, W), dtype=int)
cur = 0
from collections import deque
boxes = []
for yy in range(H):
    for xx in range(W):
        if dark[yy, xx] and lab[yy, xx] == 0:
            cur += 1
            q = deque([(yy, xx)])
            lab[yy, xx] = cur
            miny = maxy = yy
            minx = maxx = xx
            n = 0
            while q:
                cy, cx = q.popleft()
                n += 1
                if cy < miny: miny = cy
                if cy > maxy: maxy = cy
                if cx < minx: minx = cx
                if cx > maxx: maxx = cx
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and dark[ny, nx] and lab[ny, nx] == 0:
                        lab[ny, nx] = cur
                        q.append((ny, nx))
            if n >= 40:
                boxes.append((n, minx, miny, maxx, maxy))

boxes.sort(reverse=True)
print("连通域数量(>=40px):", len(boxes))
for n, minx, miny, maxx, maxy in boxes[:40]:
    print("  px %5d  x %4d..%4d (w%3d)  y %4d..%4d (h%3d)" % (n, minx, maxx, maxx - minx + 1, miny, maxy, maxy - miny + 1))
