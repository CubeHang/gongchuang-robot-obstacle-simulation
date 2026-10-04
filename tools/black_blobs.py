# -*- coding: utf-8 -*-
"""严格黑色像素的连通域分析。"""
import numpy as np
from PIL import Image
from collections import deque

a = np.asarray(Image.open("map.jpg").convert("RGB")).astype(int)
H, W, _ = a.shape
mx = a.max(axis=2)
mn = a.min(axis=2)
black = (mx < 130) & ((mx - mn) < 60)   # 真黑/深灰，排除黄色
print("真黑像素:", black.sum())

lab = np.zeros((H, W), dtype=bool)
boxes = []
for yy in range(H):
    if not black[yy].any():
        continue
    for xx in np.where(black[yy])[0]:
        if lab[yy, xx]:
            continue
        q = deque([(yy, xx)])
        lab[yy, xx] = True
        miny = maxy = yy; minx = maxx = xx; n = 0
        while q:
            cy, cx = q.popleft(); n += 1
            if cy < miny: miny = cy
            if cy > maxy: maxy = cy
            if cx < minx: minx = cx
            if cx > maxx: maxx = cx
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < H and 0 <= nx < W and black[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = True
                    q.append((ny, nx))
        if n >= 60:
            boxes.append((n, minx, miny, maxx, maxy))

boxes.sort(reverse=True)
print("连通域(>=60px):", len(boxes))
for n, minx, miny, maxx, maxy in boxes[:30]:
    print("  px %6d  x %4d..%4d (w%4d)  y %4d..%4d (h%4d)" %
          (n, minx, maxx, maxx - minx + 1, miny, maxy, maxy - miny + 1))
