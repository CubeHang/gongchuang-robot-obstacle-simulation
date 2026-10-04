# -*- coding: utf-8 -*-
"""对路径效果图做逐格像素校验。

标定方式与 verify_live.py 一致：用 4 个黄色禁行块的边界反推
“地图像素坐标 -> 图片像素坐标”的线性变换，再逐格比对颜色与路径。
"""
import sys
import os
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image
import map_sim as M

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SHOTS, "route_preview.png")

a = np.asarray(Image.open(src).convert("RGB")).astype(int)
H, W, _ = a.shape
R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
print("效果图 %s %dx%d" % (os.path.basename(src), W, H))


def blobs(mask, minpx=1500):
    seen = np.zeros(mask.shape, bool)
    out = []
    for y, x in zip(*np.where(mask)):
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


yellow = blobs((R > 200) & (G > 170) & (B < 120))
print("黄色禁行块 %d 个" % len(yellow))
FAIL = 0
if len(yellow) < 4:
    print("✘ 黄色禁行块不足 4 个，无法标定")
    sys.exit(1)

top = sorted(yellow, key=lambda t: t[2])[:2]
top.sort(key=lambda t: t[1])
k = (top[1][3] - top[0][1]) / (M.X_BOUNDS[4] - M.X_BOUNDS[1])
ox = top[0][1] - M.X_BOUNDS[1] * k
oy = top[0][2] - M.Y_BOUNDS[1] * k
print("标定：k=%.4f  ox=%.1f  oy=%.1f" % (k, ox, oy))
print("  预测地图范围 x %.1f..%.1f  y %.1f..%.1f"
      % (ox, ox + M.MAP_PX_W * k, oy, oy + M.MAP_PX_H * k))

# 用红色块复核标定
red = blobs((R > 150) & (R > G + 60) & (R > B + 60), 1500)
if red:
    pr = (ox + M.X_BOUNDS[2] * k, ox + M.X_BOUNDS[3] * k)
    print("  红色块预测 x %.1f..%.1f，实测 %d..%d（差 %.1f px）"
          % (pr[0], pr[1], red[0][1], red[0][3],
             abs(pr[0] - red[0][1]) + abs(pr[1] - red[0][3])))


def sample(mx, my):
    xi = int(round(ox + mx * k))
    yi = int(round(oy + my * k))
    if 0 <= yi < H and 0 <= xi < W:
        return a[yi, xi]
    return None


OBS = np.array([int(M.C_OBSTACLE[i:i + 2], 16) for i in (1, 3, 5)])

print("\n逐格取 4 角颜色（灰/白/黄/蓝/红/棕六种之一）：")
bad = 0
n_obs = 0
for r in range(1, 6):
    line = []
    for c in range(1, 6):
        cell = M.GRID[(r, c)]
        base = np.array([int(cell.color[i:i + 2], 16) for i in (1, 3, 5)])
        got = [sample(cell.x0 + (cell.x1 - cell.x0) * fx,
                      cell.y0 + (cell.y1 - cell.y0) * fy)
               for fx, fy in ((0.2, 0.2), (0.8, 0.2), (0.2, 0.8), (0.8, 0.8))]
        vis = [g for g in got if g is not None]
        hit_base = sum(1 for g in vis if np.abs(g - base).max() < 30)
        hit_obs = sum(1 for g in vis if np.abs(g - OBS).max() < 30)
        is_obs = hit_obs > hit_base
        if is_obs:
            n_obs += 1
        # 障碍物格子里有“障碍”文字，允许 1 个角被文字盖住
        need = 3 if is_obs else 4
        ok = len(vis) == 4 and max(hit_base, hit_obs) >= need
        if not ok:
            bad += 1
            print("  ✘ r%dc%d 期望 %s（或障碍物色）命中 底色 %d / 障碍色 %d  取样 %s"
                  % (r, c, tuple(int(v) for v in base), hit_base, hit_obs,
                     [tuple(int(v) for v in g) for g in vis]))
        line.append(("障" if is_obs else "✔") if ok else "✘")
    print("  r%d " % r + " ".join(line))
print("格子颜色不匹配数：%d / 25（其中障碍物格 %d 个）" % (bad, n_obs))
FAIL += bad

# 路径：按图上识别出的障碍物重算整条计划，逐段中点附近应出现绿色像素
green = (G > 90) & (G > R + 40) & (G > B + 30)
route = [M.START_CELLS[0]] + list(M.DEFAULT_TARGETS) + [M.START_CELLS[0]]
# 用像素识别障碍物：每个格子中心附近取一圈点，多数命中障碍物色才算
obs_keys = []
for r in range(1, 6):
    for c in range(1, 6):
        cell = M.GRID[(r, c)]
        pts = [sample(cell.cx + ddx, cell.cy + ddy)
               for ddx in (-25, 0, 25) for ddy in (-25, 0, 25)]
        pts = [p for p in pts if p is not None]
        hit = sum(1 for p in pts if np.abs(p - OBS).max() < 20)
        if pts and hit >= max(3, len(pts) - 3):
            obs_keys.append((r, c))
print("\n图中识别到的障碍物：%s" % (obs_keys or "无"))

# 按识别结果重建地图状态，再算 BFS
M.clear_obstacles()
for key in obs_keys:
    M.GRID[key].obstacle = True
M.set_active_start(route[0])
ok, bad = M.reachable_goals(route[0])
print("按图片识别结果重算：障碍物 %s，不可达目标 %s" % (obs_keys or "无", bad or "无"))
if bad:
    FAIL += 1

print("路径校验：")
missing = []
for i in range(len(route) - 1):
    path, err = M.shortest_path(route[i], route[i + 1])
    if err:
        print("  ✘ %s -> %s : %s" % (route[i], route[i + 1], err))
        FAIL += 1
        continue
    crossed = [c.key for c in path if c.key in obs_keys]
    seg_missing = 0
    for j in range(len(path) - 1):
        p, q = path[j], path[j + 1]
        midx, midy = (p.cx + q.cx) / 2, (p.cy + q.cy) / 2
        if not any(green[int(round(oy + (midy + ddy) * k)), int(round(ox + (midx + ddx) * k))]
                   for ddx in range(-10, 11, 2) for ddy in range(-10, 11, 2)):
            seg_missing += 1
            missing.append((p.key, q.key))
    if crossed:
        FAIL += 1
    print("  %s %s → %s：%d 格%s%s"
          % ("✔" if seg_missing == 0 and not crossed else "✘", M.GRID[route[i]].name,
             M.GRID[route[i + 1]].name, len(path),
             "" if seg_missing == 0 else "（%d 段缺绿色像素）" % seg_missing,
             "" if not crossed else "（穿过了障碍物 %s）" % crossed))
if missing:
    FAIL += 1

print("\n" + ("渲染校验通过 ✔" if FAIL == 0 else "渲染校验失败 %d 项" % FAIL))
sys.exit(1 if FAIL else 0)
