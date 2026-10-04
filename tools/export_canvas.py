# -*- coding: utf-8 -*-
"""把 Tk 画布内容直接导出为 PNG（通过 postscript + Pillow），用于核验绘制结果。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from PIL import Image
import map_sim as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shots")
os.makedirs(OUT, exist_ok=True)


class E:
    pass


def export(canvas, name, scale=1.0):
    ps = canvas.postscript(colormode="color", x=0, y=0,
                           width=canvas.winfo_width(), height=canvas.winfo_height(),
                           pagewidth=canvas.winfo_width(), pageheight=canvas.winfo_height())
    img = Image.open(__import__("io").BytesIO(ps.encode("latin-1")))
    if scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    path = os.path.join(OUT, name)
    img.convert("RGB").save(path)
    print("写出 %s  %dx%d" % (path, img.width, img.height))
    return path


# ---- 出发点选择弹窗 ----
root = tk.Tk()
root.withdraw()
dlg = M.StartDialog(root)
dlg.top.update()
export(dlg.canvas, "dialog_start.png", 1.0)
dlg.top.destroy()
root.destroy()

# ---- 主界面三种状态 ----
win = tk.Tk()
sim = M.Simulator(win, (1, 5))
win.geometry("+20+20")
win.update()

# 状态1：悬停白色区域1，显示黄色预览最短路径
cell = M.GRID[(5, 1)]
ev = E(); ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
sim.on_motion(ev)
win.update()
export(sim.canvas, "canvas_state1.png")

# 状态2：行驶到红色区域之后，悬停白色区域2
ev2 = E(); ev2.x, ev2.y = sim.to_canvas(M.GRID[(1, 3)].cx, M.GRID[(1, 3)].cy)
sim.on_click(ev2)
import time
t0 = time.time()
while sim.move is not None and time.time() - t0 < 10:
    win.update()
    time.sleep(0.01)
ev2.x, ev2.y = sim.to_canvas(M.GRID[(5, 3)].cx, M.GRID[(5, 3)].cy)
sim.on_motion(ev2)
win.update()
export(sim.canvas, "canvas_state2.png")
win.destroy()
print("done")
