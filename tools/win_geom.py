# -*- coding: utf-8 -*-
"""报告真实窗口尺寸，用于判断界面是否被屏幕裁切。"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M

win = tk.Tk()
sim = M.Simulator(win, (1, 5))
win.geometry("+20+10")
win.update()
time.sleep(0.3)
win.update()
print("屏幕: %dx%d" % (win.winfo_screenwidth(), win.winfo_screenheight()))
print("窗口几何: %s" % win.winfo_geometry())
print("窗口外框: x=%d y=%d w=%d h=%d" % (win.winfo_x(), win.winfo_y(),
                                         win.winfo_width(), win.winfo_height()))
print("窗口内容需求: %dx%d" % (win.winfo_reqwidth(), win.winfo_reqheight()))
print("画布: x=%d y=%d %dx%d  需求 %dx%d" % (
    sim.canvas.winfo_x(), sim.canvas.winfo_y(),
    sim.canvas.winfo_width(), sim.canvas.winfo_height(),
    sim.canvas.winfo_reqwidth(), sim.canvas.winfo_reqheight()))
print("画布窗口左下角（屏幕坐标）: y=%d" % (win.winfo_y() + sim.canvas.winfo_y() + sim.canvas.winfo_height()))
print("tk scaling = %.3f" % win.tk.call("tk", "scaling"))
print("是否超出屏幕: 宽 %s 高 %s" % (
    win.winfo_x() + win.winfo_width() > win.winfo_screenwidth(),
    win.winfo_y() + win.winfo_height() > win.winfo_screenheight()))
win.destroy()
