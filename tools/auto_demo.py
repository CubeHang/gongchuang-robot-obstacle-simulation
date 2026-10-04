# -*- coding: utf-8 -*-
"""无人值守演示：自动随机放置障碍物 -> 开始仿真 -> 依次跑目标 -> 回到出发点。

完整走一遍新流程（含避障），不需要人工点击，也不会占用鼠标。
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


def event_for(key):
    ev = E()
    ev.x, ev.y = sim.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    return ev


def click(key):
    sim.on_motion(event_for(key))
    sim.on_click(event_for(key))


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

# ---- 阶段一：随机放置障碍物（模拟比赛） ----
sim.randomize_obstacles()
win.update()
print("障碍物：%s" % "、".join(M.GRID[k].name for k in sim.obstacle_keys), flush=True)
assert sim.obstacle_keys, "随机放置应当成功"
ok, bad = M.reachable_goals(START)
assert not bad, "随机放置后目标应全部可达，实际不可达：%s" % bad

# ---- 阶段二：开始仿真 ----
sim.begin_simulation()
win.update()
assert sim.phase == "select", "开始仿真后应处于选择目标阶段"
print("已开始仿真（障碍物 %d 个）" % len(sim.obstacle_keys), flush=True)

# ---- 阶段三：逐个目标行驶 ----
for goal in ROUTE:
    path, err = M.shortest_path(sim.car_cell.key, goal)
    assert not err, err
    print("→ %s：%d 格  %s" % (M.GRID[goal].name, len(path),
                               " → ".join(c.name for c in path)), flush=True)
    assert all(c.passable for c in path), "路径不能穿过障碍物"
    click(goal)
    if not run_until_still():
        print("窗口被关闭，演示结束", flush=True)
        sys.exit(0)
    print("   已到达，累计行驶 %d 格" % sim.steps, flush=True)

print("回到出发点 %s（小车先开回去，到站后才结束）" % M.GRID[START].name, flush=True)
path, _ = M.shortest_path(sim.car_cell.key, START)
print("→ %s：%d 格" % (M.GRID[START].name, len(path)), flush=True)
click(START)
try:
    win.update()
except tk.TclError:
    print("窗口已关闭", flush=True)
assert not sim.finished, "还没到出发点，不应提前结束"
assert sim.move is not None and sim.move.get("returning"), "这一段应是返回出发点"
run_until_still()
assert sim.car_cell.key == START, "小车应停在出发点，实际 %s" % (sim.car_cell.key,)
assert sim.finished, "到达出发点后才结束仿真"
print("小车已回到出发点，仿真结束，累计行驶 %d 格，到达过：%s"
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
