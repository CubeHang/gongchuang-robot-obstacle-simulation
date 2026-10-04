# -*- coding: utf-8 -*-
"""在真实屏幕截图中校验界面：用色块几何反推屏幕缩放，再逐格比对颜色与小车位置。

思路：黄色禁行格在图上正好是 r2c2 / r2c4 / r4c2 / r4c4 四块，
用它们的像素边界可以精确解出“地图坐标 -> 截图坐标”的线性变换，
然后用同一变换去预测红/蓝格位置并比对，从而验证界面画的是不是这张地图。
"""
import sys
import os
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image
import map_sim as M

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "shots", "live.png")
a = np.asarray(Image.open(src).convert("RGB")).astype(int)
H, W, _ = a.shape
print("live 截图 %dx%d" % (W, H))
R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]


def blobs(mask, minpx=2000):
    seen = np.zeros(mask.shape, bool)
    out = []
    ys, xs = np.where(mask)
    for y, x in zip(ys, xs):
        if seen[y, x]:
            continue
        q = deque([(y, x)])
        seen[y, x] = True
        x0 = x1 = x
        y0 = y1 = y
        n = 0
        while q:
            cy, cx = q.popleft()
            n += 1
            x0, x1 = min(x0, cx), max(x1, cx)
            y0, y1 = min(y0, cy), max(y1, cy)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] \
                        and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        if n >= minpx:
            out.append((n, x0, y0, x1, y1))
    out.sort(key=lambda t: (t[2], t[1]))
    return out


yellow = blobs((R > 200) & (G > 170) & (B < 120), 2000)
print("\n黄色块 %d 个：" % len(yellow))
for n, x0, y0, x1, y1 in yellow:
    print("   px %6d  x %4d..%4d y %4d..%4d" % (n, x0, x1, y0, y1))

FAIL = 0
if len(yellow) < 4:
    print("✘ 黄色禁行格少于 4 块")
    sys.exit(1)

# 标定：黄色块的外边缘就是该格子与外框交界处的黑线位置。
# 截图可能只露出地图的一部分（窗口超出桌面时底部会被裁掉），
# 所以用左上角和右上角两个黄色块分别对 x 做两点标定。
top = sorted(yellow, key=lambda t: t[2])[:2]
top.sort(key=lambda t: t[1])
left_blob, right_blob = top[0], top[1]
x_left = left_blob[1]                 # r2c2 左边界
x_right = right_blob[3]               # r2c4 右边界
X_LEFT_MAP = M.X_BOUNDS[1]
X_RIGHT_MAP = M.X_BOUNDS[4]
k = (x_right - x_left) / (X_RIGHT_MAP - X_LEFT_MAP)
ox = x_left - X_LEFT_MAP * k
# 纵向：顶部黄色块的上边缘 = r2c2 上边界
ky = k
oy = left_blob[2] - M.Y_BOUNDS[1] * ky
print("\n标定：kx = %.4f  ky = %.4f  偏移 ox=%.1f oy=%.1f" % (k, ky, ox, oy))
print("  两个黄色块 x %d..%d / %d..%d  y %d..%d / %d..%d"
      % (left_blob[1], left_blob[3], right_blob[1], right_blob[3],
         left_blob[2], left_blob[4], right_blob[2], right_blob[4]))
pred_r2c4 = (ox + M.X_BOUNDS[3] * k, ox + M.X_BOUNDS[4] * k)
print("  用标定预测 r2c4 的 x 范围 %.0f..%.0f（实测 %d..%d）"
      % (pred_r2c4[0], pred_r2c4[1], right_blob[1], right_blob[3]))
# 只校验截图中可见的部分
VIS = (oy + M.MAP_PX_H * ky) > H
print("  截图%s显示完整地图（地图底边预测 y=%.0f，截图高 %d）"
      % ("未" if VIS else "完整", oy + M.MAP_PX_H * ky, H))


def xy(mx, my):
    return ox + mx * k, oy + my * ky

def sample_at(x, y):
    xi, yi = int(round(x)), int(round(y))
    if 0 <= yi < H and 0 <= xi < W:
        return a[yi, xi]
    return None


print("\n红/蓝格位置比对：")
for key, want_hex in (((1, 3), "#eb0301"), ((1, 5), "#0b02cb"), ((3, 1), "#ffffff"),
                      ((3, 3), "#c6c7c1"), ((1, 4), "#7b3f00"), ((3, 5), "#ff8c00")):
    cell = M.GRID[key]
    cxp, cyp = xy(cell.cx, cell.cy)
    half = (cell.x1 - cell.x0) * 0.22 * k
    halfy = (cell.y1 - cell.y0) * 0.22 * ky
    pts = [(cxp - half, cyp - halfy), (cxp + half, cyp - halfy),
           (cxp - half, cyp + halfy), (cxp + half, cyp + halfy)]
    want = np.array([int(want_hex[i:i + 2], 16) for i in (1, 3, 5)])
    got = [sample_at(x, y) for x, y in pts]
    vis = [g for g in got if g is not None]
    hit = sum(1 for g in vis if np.abs(g - want).max() < 30)
    ok = hit >= max(2, len(vis) - 1) and len(vis) > 0
    print("  %s %-10s 预测中心 (%4d,%4d)  可见取样 %d 个，命中 %d 个"
          % ("✔" if ok else "✘", cell.name, round(cxp), round(cyp), len(vis), hit))
    if not ok:
        FAIL += 1

print("\n全图逐格颜色抽查（每格取 4 角，只统计截图中可见的部分）：")
OBS = np.array([int(M.C_OBSTACLE[i:i + 2], 16) for i in (1, 3, 5)])
bad = 0
n_obs = 0
for r in range(1, 6):
    for c in range(1, 6):
        cell = M.GRID[(r, c)]
        want = np.array([int(cell.color[i:i + 2], 16) for i in (1, 3, 5)])
        got = []
        for fx, fy in ((0.2, 0.2), (0.8, 0.2), (0.2, 0.8), (0.8, 0.8)):
            g = sample_at(*xy(cell.x0 + (cell.x1 - cell.x0) * fx,
                              cell.y0 + (cell.y1 - cell.y0) * fy))
            if g is not None:
                got.append(g)
        if not got:
            print("  · r%dc%d 在截图外（窗口底部被裁切）" % (r, c))
            continue
        hit = sum(1 for g in got if np.abs(g - want).max() < 25)
        hit_obs = sum(1 for g in got if np.abs(g - OBS).max() < 25)
        if hit_obs > hit:            # 这一格被摆成了障碍物
            n_obs += 1
            print("  ✔ r%dc%d 是障碍物（棕色）" % (r, c))
            continue
        if hit < len(got):
            bad += 1
            print("  ✘ r%dc%d 期望 %s 命中 %d/%d" % (r, c, tuple(want), hit, len(got)))
print("  可见格子中不完全匹配的：%d（其中障碍物格 %d 个）" % (bad, n_obs))
FAIL += bad

# 绿色小车：此刻停在出发点（截图场景停在“目标区域选择”阶段）
# 注意：深绿色路径线也是偏绿的，这里用连通域取“最大的那块”才是小车
car_mask = (G > 170) & (G > R + 110) & (G > B + 110)
ys, xs = np.where(car_mask)
if len(xs):
    from collections import deque as _dq
    seen = np.zeros(car_mask.shape, bool)
    best = None
    for y0_, x0_ in zip(ys, xs):
        if seen[y0_, x0_]:
            continue
        q = _dq([(y0_, x0_)])
        seen[y0_, x0_] = True
        pts = []
        while q:
            cy_, cx_ = q.popleft()
            pts.append((cy_, cx_))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy_ + dy, cx_ + dx
                if 0 <= ny < car_mask.shape[0] and 0 <= nx < car_mask.shape[1] \
                        and car_mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        if best is None or len(pts) > len(best):
            best = pts
    if best:
        gx = sum(p[1] for p in best) / len(best)
        gy = sum(p[0] for p in best) / len(best)
        cell = M.GRID[(1, 5)]
        ex, ey = xy(cell.cx, cell.cy)
        d = ((gx - ex) ** 2 + (gy - ey) ** 2) ** 0.5
        print("\n绿色小车（最大绿色连通域 %d px）质心 (%.0f,%.0f) vs 出发点1 格心 (%.0f,%.0f)，偏差 %.1f px（格宽 %.0f px）"
              % (len(best), gx, gy, ex, ey, d, (cell.x1 - cell.x0) * k))
        ok = d < 0.15 * (cell.x1 - cell.x0) * k
        print("  " + ("✔ 小车停在出发点格心" if ok else "✘ 小车位置不对"))
        FAIL += 0 if ok else 1
    else:
        print("\n✘ 未找到绿色小车")
        FAIL += 1
else:
    print("\n✘ 未找到绿色小车")
    FAIL += 1

# 计划预览：黄色虚线应当出现，且覆盖到最后一个目标（白色区域2）附近
yellow_line = (R > 220) & (G > 150) & (G < 215) & (B < 120)
print("\n黄色计划预览像素 %d %s" % (yellow_line.sum(), "✔" if yellow_line.sum() > 300 else "✘"))
if yellow_line.sum() <= 300:
    FAIL += 1
else:
    segs, info = M.build_plan((1, 5), list(M.DEFAULT_TARGETS))
    hit_seg = 0
    for seg in segs:
        ok_seg = False
        for j in range(len(seg) - 1):
            p, q = seg[j], seg[j + 1]
            midx, midy = (p.cx + q.cx) / 2, (p.cy + q.cy) / 2
            px_, py_ = xy(midx, midy)
            x0_, y0_ = max(0, int(px_) - 10), max(0, int(py_) - 10)
            x1_, y1_ = min(W, int(px_) + 11), min(H, int(py_) + 11)
            if x1_ > x0_ and y1_ > y0_ and yellow_line[y0_:y1_, x0_:x1_].any():
                ok_seg = True
                break
        hit_seg += 1 if ok_seg else 0
    print("  计划 %d 段中有 %d 段落在截图可见范围内并有黄色虚线 %s"
          % (len(segs), hit_seg, "✔" if hit_seg >= 4 else "✘"))
    if hit_seg < 4:
        FAIL += 1

print("\n" + ("真实截图校验通过 ✔" if FAIL == 0 else "真实截图校验失败 %d 项" % FAIL))
sys.exit(1 if FAIL else 0)
