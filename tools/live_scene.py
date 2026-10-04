# -*- coding: utf-8 -*-
"""把界面摆到“已放好障碍物、已勾选目标区域（显示计划预览）”的状态，供截图核验。"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M

HERE = os.path.dirname(os.path.abspath(__file__))
READY = os.path.join(HERE, "shots", "Ready.txt")
os.makedirs(os.path.dirname(READY), exist_ok=True)
if os.path.exists(READY):
    os.remove(READY)

# 行程示例：红色区域去两次，其余各一次
TRIP = [(1, 3), (3, 5), (5, 3), (1, 3)]


class E:
    pass


win = tk.Tk()
sim = M.Simulator(win, (1, 5))
win.geometry("+20+20")
win.attributes("-topmost", True)
win.update()


def event_for(key):
    ev = E()
    ev.x, ev.y = sim.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    return ev


# 阶段①：放一个障碍物（挡住出发点1 去红色区域的直路）
sim.on_motion(event_for((1, 4)))
sim.on_click(event_for((1, 4)))
win.update()
assert sim.obstacle_keys == [(1, 4)], "障碍物应为 r1c4"

# 阶段②：在地图上依次点击目标区域（红色区域点两次），停在“行程已排好”的状态
sim.enter_targets()
win.update()
assert sim.phase == "targets", "应停在目标区域选择阶段"
for key in TRIP:
    ev = event_for(key)
    sim.on_motion(ev)
    sim.on_click(ev)
    win.update()
assert sim.targets == TRIP, "行程应当与点选一致"
segs, info = M.build_plan(sim.start_key, sim.targets)
assert not info["error"], info["error"]
print("行程：%s，共 %d 步" % (M.target_selection_text(sim.targets), info["total_steps"]), flush=True)

with open(READY, "w", encoding="utf-8") as f:
    f.write("ready")
print("ready", flush=True)

t0 = time.time()
while time.time() - t0 < 12:
    win.update()
    time.sleep(0.02)
win.destroy()
