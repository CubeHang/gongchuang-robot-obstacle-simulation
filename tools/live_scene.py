# -*- coding: utf-8 -*-
"""启动仿真界面并停在“已到达红色区域、鼠标悬停白色区域2”的状态，供截图。"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M

HERE = os.path.dirname(os.path.abspath(__file__))
READY = os.path.join(HERE, "shots", "Ready.txt")
os.makedirs(os.path.dirname(READY), exist_ok=True)


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


# 比赛准备：先摆好障碍物（挡住出发点1 去红色区域的直路），再开始仿真
sim.on_click(event_for((1, 4)))
win.update()
sim.begin_simulation()
win.update()
assert sim.phase == "select", "应当已进入仿真阶段"
assert sim.obstacle_keys == [(1, 4)], "障碍物应为 r1c4"

# 先驶到红色区域，并等动画彻底停下（否则截图可能拍到车在途中）
sim.on_click(event_for((1, 3)))
t0 = time.time()
while sim.move is not None and time.time() - t0 < 15:
    win.update()
    time.sleep(0.01)
settle = time.time()
while sim.move is not None and time.time() - settle < 3:
    win.update()
    time.sleep(0.02)
assert sim.car_cell.key == (1, 3), "小车应停在红色区域，实际 %s" % (sim.car_cell.key,)

# 悬停白色区域2 (3,1)，显示最短路径预览
sim.on_motion(event_for((3, 1)))
win.update()

with open(READY, "w", encoding="utf-8") as f:
    f.write("ready")
print("ready")

t0 = time.time()
while time.time() - t0 < 12:
    win.update()
    time.sleep(0.02)
win.destroy()
