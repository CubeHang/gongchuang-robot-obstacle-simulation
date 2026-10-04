# -*- coding: utf-8 -*-
"""无人值守演示：自动选定出发点，依次跑几个目标，最后回到出发点。

用途：不需要人工点击也能看到完整效果（路径规划 + 小车动画 + 结束总结）。
注意：不需要移动鼠标，也不会占用输入焦点。
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M

START = (1, 5)
ROUTE = [(1, 3), (5, 3), (3, 1), (1, 3), (5, 3)]


class E:
    pass


win = tk.Tk()
sim = M.Simulator(win, START)
win.update()


def click(key):
    ev = E()
    ev.x, ev.y = sim.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    sim.on_motion(ev)
    sim.on_click(ev)


def run_until_still(limit=20.0):
    """推进 Tk 事件循环直到小车停下（窗口被手动关掉时直接结束）。"""
    t0 = time.time()
    while sim.move is not None and time.time() - t0 < limit:
        try:
            win.update()
        except tk.TclError:
            return False
        time.sleep(0.01)
    return True


print("出发点：%s" % M.GRID[START].name, flush=True)
for goal in ROUTE:
    path, err = M.shortest_path(sim.car_cell.key, goal)
    assert not err, err
    print("→ %s：%d 格  %s" % (M.GRID[goal].name, len(path),
                               " → ".join(c.name for c in path)), flush=True)
    click(goal)
    run_until_still()
    print("   已到达，累计行驶 %d 格" % sim.steps, flush=True)

print("回到出发点 %s" % M.GRID[START].name, flush=True)
path, _ = M.shortest_path(sim.car_cell.key, START)
print("→ %s：%d 格" % (M.GRID[START].name, len(path)), flush=True)
click(START)
try:
    win.update()
except tk.TclError:
    print("窗口已关闭", flush=True)
print("仿真结束，累计行驶 %d 格，到达过：%s"
      % (sim.steps, "、".join(sim.visited_goals)), flush=True)

# 停 3 秒展示结束总结，再关掉（期间窗口可能被手动关闭）
t0 = time.time()
while time.time() - t0 < 3:
    try:
        win.update()
    except tk.TclError:
        break
    time.sleep(0.02)
try:
    win.destroy()
except tk.TclError:
    pass
print("done", flush=True)
