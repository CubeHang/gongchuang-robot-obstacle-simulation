# -*- coding: utf-8 -*-
"""把界面摆到指定状态，写 Ready.txt 通知截图脚本，用于人工/自动视觉检查。"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M

HERE = os.path.dirname(os.path.abspath(__file__))
READY = os.path.join(HERE, "Ready.txt")
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
if os.path.exists(READY):
    os.remove(READY)


class E:
    pass


def signal(tag):
    with open(READY, "w", encoding="utf-8") as f:
        f.write(tag)


def wait_shot(win, seconds=2.0):
    t0 = time.time()
    while time.time() - t0 < seconds:
        win.update()
        time.sleep(0.02)


win = tk.Tk()
sim = M.Simulator(win, (1, 5))
win.geometry("+30+20")
win.update()

# 状态 1：初始，鼠标悬停在“白色区域1”，显示黄色预览路径
cell = M.GRID[(5, 1)]
ev = E()
ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
sim.on_motion(ev)
sim.status("已到达 出发点1。\n请选择下一个目标地点（或点击出发点结束仿真）")
win.update()
signal("state1")
print("state1 ready -> 悬停白色区域1，预览最短路径")
wait_shot(win, 2.5)

# 状态 2：小车行驶到红色区域，路径用深绿实线显示
if os.path.exists(READY):
    os.remove(READY)
cell = M.GRID[(1, 3)]
ev = E()
ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
sim.on_click(ev)
t0 = time.time()
while sim.move is not None and time.time() - t0 < 10:
    win.update()
    time.sleep(0.01)
ev.x, ev.y = sim.to_canvas(M.GRID[(5, 3)].cx, M.GRID[(5, 3)].cy)
sim.on_motion(ev)
win.update()
signal("state2")
print("state2 ready -> 已到达红色区域，悬停白色区域2")
wait_shot(win, 2.0)

# 状态 3：结束对话框
if os.path.exists(READY):
    os.remove(READY)
sim.finish()
win.update()
signal("state3")
print("state3 ready -> 结束对话框")
wait_shot(win, 2.0)

if os.path.exists(READY):
    os.remove(READY)
win.destroy()
print("done")
