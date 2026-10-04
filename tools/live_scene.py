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


# 先驶到红色区域
sim.on_click(event_for((1, 3)))
t0 = time.time()
while sim.move is not None and time.time() - t0 < 15:
    win.update()
    time.sleep(0.01)

# 悬停白色区域2，显示最短路径预览
sim.on_motion(event_for((5, 3)))
win.update()

with open(READY, "w", encoding="utf-8") as f:
    f.write("ready")
print("ready")

t0 = time.time()
while time.time() - t0 < 12:
    win.update()
    time.sleep(0.02)
win.destroy()
