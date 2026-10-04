# -*- coding: utf-8 -*-
"""对渲染出的效果图做像素校验：每个格子中心颜色是否符合地图定义。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image
import map_sim as M

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "shots", "route_preview.png")
im = Image.open(src).convert("RGB")
a0 = np.asarray(Image.open(src).convert("RGB")).astype(int)
# 只保留“地图底色/黄/蓝/红”这类地图专用色，排除标题文字与白边
base = (np.abs(a0 - np.array([198, 199, 193])).max(axis=2) < 12)
yellow = (a0[:, :, 0] > 200) & (a0[:, :, 1] > 170) & (a0[:, :, 2] < 120)
blue = (a0[:, :, 2] > 120) & (a0[:, :, 2] > a0[:, :, 0] + 60)
red = (a0[:, :, 0] > 150) & (a0[:, :, 0] > a0[:, :, 1] + 60)
mask = base | yellow | blue | red
rows = np.where(mask.sum(axis=1) > 50)[0]
cols = np.where(mask.sum(axis=0) > 50)[0]
y0, y1 = int(rows.min()), int(rows.max())
x0, x1 = int(cols.min()), int(cols.max())
a = np.asarray(im).astype(int)
print("效果图 %dx%d" % (im.width, im.height))

# 图中地图内容的范围：只统计纵向较大块的深色像素，避开标题文字
print("地图内容范围 x %d..%d y %d..%d" % (x0, x1, y0, y1))
kx = (x1 - x0) / M.MAP_PX_W
ky = (y1 - y0) / M.MAP_PX_H
print("比例 kx=%.4f ky=%.4f（应基本相等）" % (kx, ky))


def px(mx, my):
    return a[int(round(y0 + my * ky)), int(round(x0 + mx * kx))]


FAIL = 0
for r in range(1, 6):
    for c in range(1, 6):
        cell = M.GRID[(r, c)]
        # 取格子内四个偏置点（避开中心的车/文字）
        pts = [(0.22, 0.22), (0.78, 0.22), (0.22, 0.78), (0.78, 0.78)]
        want = np.array([int(cell.color[i:i + 2], 16) for i in (1, 3, 5)])
        ok = True
        for fx, fy in pts:
            mx = cell.x0 + (cell.x1 - cell.x0) * fx
            my = cell.y0 + (cell.y1 - cell.y0) * fy
            got = px(mx, my)
            if np.abs(got - want).max() > 26:
                ok = False
        tag = {M.FLOOR: ".", M.WALL: "Y", M.START: "B", M.GOAL: "G"}[cell.kind]
        if not ok:
            FAIL += 1
        print("  %s r%dc%d 期望色 %s  像素采样 %s" %
              ("✔" if ok else "✘", r, c, tuple(want),
               [tuple(px(cell.x0 + (cell.x1 - cell.x0) * fx,
                         cell.y0 + (cell.y1 - cell.y0) * fy)) for fx, fy in pts]))

# 绿色路径像素应存在，且大致覆盖全部 5 列 5 行
green = (a[:, :, 1] > 90) & (a[:, :, 1] > a[:, :, 0] + 40) & (a[:, :, 1] > a[:, :, 2] + 30)
gys, gxs = np.where(green)
print("\n绿色路径像素 %d，覆盖 x %d..%d y %d..%d" % (green.sum(), gxs.min(), gxs.max(), gys.min(), gys.max()))
if green.sum() < 500:
    FAIL += 1
    print("  ✘ 绿色路径像素过少")
else:
    print("  ✔ 绿色路径已绘制")

print("\n" + ("渲染校验通过 ✔" if FAIL == 0 else "渲染校验失败 %d 项" % FAIL))
sys.exit(1 if FAIL else 0)
