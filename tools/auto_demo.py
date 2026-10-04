# -*- coding: utf-8 -*-
"""无人值守演示：随机障碍物 → 勾选目标区域 → 自动跑完整场仿真并回到出发点。

走的是界面上真实的三个阶段（对应面板上的 ① ② ③），不需要人工点击，也不会占用鼠标。
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M

START = (1, 5)
# 行程示例：红色区域去两次（同一个目标区域可以重复到达）
TARGETS = [(1, 3), (3, 5), (5, 3), (3, 1), (1, 3)]


class E:
    pass


win = tk.Tk()
sim = M.Simulator(win, START)
win.update()


def click_cell(key):
    """在准备阶段点击某格（放/取消障碍物）。"""
    ev = E()
    ev.x, ev.y = sim.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    sim.on_motion(ev)
    sim.on_click(ev)


print("出发点：%s" % M.GRID[START].name, flush=True)

# ---- 阶段①：随机放置障碍物（模拟比赛） ----
sim.randomize_obstacles()
win.update()
print("障碍物：%s" % ("、".join(M.GRID[k].name for k in sim.obstacle_keys) or "无"), flush=True)
assert sim.obstacle_keys, "随机放置应当成功"

# ---- 阶段②：在地图上依次点击目标区域（红/橙/白1/白2/红） ----
sim.enter_targets()
win.update()
for key in TARGETS:
    click_cell(key)
win.update()
print("行程（%d 个目标）：%s" % (len(sim.targets), M.target_selection_text(sim.targets)), flush=True)
assert sim.targets == TARGETS, "行程应当与点选一致"

segs, info = M.build_plan(sim.start_key, sim.targets)
assert not info["error"], info["error"]
for i, seg in enumerate(segs):
    print("  第%d段 %s → %s : %d 步" % (i + 1, seg[0].name, seg[-1].name, len(seg) - 1), flush=True)
print("预计共 %d 步（%d 段）" % (info["total_steps"], info["segments"]), flush=True)

# ---- 阶段③：开始仿真，一次跑完 ----
sim.begin_simulation()
win.update()
assert sim.phase == "run", "开始后应处于自动仿真阶段"

t0 = time.time()
while (sim.move is not None or (not sim.finished and sim.phase == "run")):
    try:
        win.update()
    except tk.TclError:
        print("窗口被关闭，演示结束", flush=True)
        sys.exit(0)
    time.sleep(0.004)
    if time.time() - t0 > 120:
        raise TimeoutError("仿真超时")

assert sim.car_cell.key == START, "小车应回到出发点，实际 %s" % (sim.car_cell.key,)
assert sim.finished, "跑完计划后应结束"
assert sim.steps == info["total_steps"], "步数 %d ≠ 计划 %d" % (sim.steps, info["total_steps"])
assert sim.visited_count.get("红色区域") == 2, "红色区域应当到达 2 次"
print("✔ 自动仿真结束：小车已回到 %s，共行驶 %d 步，到达次数：%s"
      % (M.GRID[START].name, sim.steps,
         "、".join("%s×%d" % (k, v) for k, v in sim.visited_count.items())), flush=True)

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
