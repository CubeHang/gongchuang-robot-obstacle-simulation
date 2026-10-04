# -*- coding: utf-8 -*-
"""生成“地图 + 最短路径”效果图（与 GUI 使用同一套地图数据与 BFS）。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
import map_sim as M

for fam in ("Microsoft YaHei", "SimHei", "DengXian"):
    try:
        matplotlib.rcParams["font.sans-serif"] = [fam]
        break
    except Exception:
        pass
matplotlib.rcParams["axes.unicode_minus"] = False

ROUTE = [(1, 5), (1, 3), (5, 1), (5, 3), (1, 3), (5, 1)]
route_name = " → ".join(M.GRID[k].name for k in ROUTE)

fig, ax = plt.subplots(figsize=(7.4, 7.4), dpi=130)

# 格子
for r in range(1, 6):
    for c in range(1, 6):
        cell = M.GRID[(r, c)]
        ax.add_patch(plt.Rectangle((cell.x0, cell.y0), cell.x1 - cell.x0,
                                   cell.y1 - cell.y0, facecolor=cell.color,
                                   edgecolor="none", zorder=1))

# 路径（逐段，带箭头）
total = 0
for i in range(len(ROUTE) - 1):
    a, b = M.GRID[ROUTE[i]], M.GRID[ROUTE[i + 1]]
    path, err = M.shortest_path(a.key, b.key)
    assert not err, err
    total += len(path) - 1
    ax.plot([p.cx for p in path], [p.cy for p in path], "-",
            color="#0b7a1e", lw=3.2, solid_capstyle="round",
            alpha=0.55 if i else 1.0, zorder=3)
    for j in range(len(path) - 1):
        p, q = path[j], path[j + 1]
        ax.add_patch(FancyArrowPatch((p.cx, p.cy), (q.cx, q.cy),
                                     arrowstyle="-|>", mutation_scale=16,
                                     color="#0b7a1e", lw=0, zorder=4))
    ax.text(a.cx, a.cy, str(i + 1), color="#ffffff", fontsize=11,
            weight="bold", ha="center", va="center", zorder=6,
            bbox=dict(boxstyle="circle,pad=0.22", fc="#0b7a1e", ec="none"))

for p in [c for k in ROUTE for c in M.shortest_path(ROUTE[0], k)[0]]:
    pass
for p in M.shortest_path((1, 5), (5, 1))[0]:
    ax.add_patch(Circle((p.cx, p.cy), 26, facecolor="none", edgecolor="#0b7a1e",
                        lw=1.4, zorder=5))

# 网格线（与原图像素一致）
for x in M.X_BOUNDS:
    ax.plot([x, x], [0, M.MAP_PX_H], color="#111111", lw=3.2, zorder=7)
for y in M.Y_BOUNDS:
    ax.plot([0, M.MAP_PX_W], [y, y], color="#111111", lw=3.2, zorder=7)

# 起点 / 目标 / 禁行 标注
for key in M.START_CELLS:
    cell = M.GRID[key]
    ax.text(cell.cx, cell.cy, "起点" + cell.mark, color="#ffffff", fontsize=11,
            weight="bold", ha="center", va="center", zorder=8)
    ax.add_patch(plt.Rectangle((cell.x0 + 6, cell.y0 + 6), cell.x1 - cell.x0 - 12,
                               cell.y1 - cell.y0 - 12, fill=False,
                               edgecolor="#ffffff", lw=2, zorder=8))
for key, (name, color, mark) in M.GOAL_INFO.items():
    cell = M.GRID[key]
    ax.text(cell.cx, cell.cy, mark, color="#ffffff" if mark == "红" else "#20242b",
            fontsize=15, weight="bold", ha="center", va="center", zorder=8)
    ax.add_patch(plt.Rectangle((cell.x0 + 6, cell.y0 + 6), cell.x1 - cell.x0 - 12,
                               cell.y1 - cell.y0 - 12, fill=False,
                               edgecolor="#ff9f1c", lw=2, ls="--", zorder=8))
for key in M.WALL_CELLS:
    cell = M.GRID[key]
    ax.text(cell.cx, cell.cy, "禁行", color="#5c4a00", fontsize=11, weight="bold",
            ha="center", va="center", zorder=8)

# 小车（绿圆）
car = M.GRID[ROUTE[0]]
ax.add_patch(Circle((car.cx, car.cy), 30, facecolor="none", edgecolor="#18c832",
                    lw=4, zorder=9))

ax.set_xlim(-8, M.MAP_PX_W + 8)
ax.set_ylim(M.MAP_PX_H + 8, -8)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("最短路效果：%s\n累计 %d 步（绿色箭头为 BFS 最短路径，序号为访问顺序）"
             % (route_name, total), fontsize=11)
plt.tight_layout()

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots", "route_preview.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out, facecolor="white")
print("写出", out, "  累计步数 =", total)
