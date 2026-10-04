# -*- coding: utf-8 -*-
"""检查 Tk 画布上实际绘制出的图形元素（颜色/位置），核验渲染正确。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M

FAIL = []


def check(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAIL.append(msg)


class E:
    pass


win = tk.Tk()
sim = M.Simulator(win, (1, 5))
win.update()
print("窗口请求尺寸 主窗口 %dx%d，画布 %dx%d，屏幕 %dx%d" %
      (win.winfo_reqwidth(), win.winfo_reqheight(),
       sim.canvas.winfo_width(), sim.canvas.winfo_height(),
       win.winfo_screenwidth(), win.winfo_screenheight()))

# ---- 背景格子 ----
rects = [i for i in sim.canvas.find_all() if sim.canvas.type(i) == "rectangle"]
print("画布矩形数量：%d" % len(rects))


def color_at_cell(key):
    """找出覆盖该格子中心的填充矩形颜色。"""
    cell = M.GRID[key]
    cx, cy = sim.to_canvas(cell.cx, cell.cy)
    for i in rects:
        x0, y0, x1, y1 = sim.canvas.coords(i)
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            fill = sim.canvas.itemcget(i, "fill")
            if fill:
                return fill
    return None


EXPECT = {
    (1, 5): "#0b02cb",   # 蓝 出发点1
    (5, 5): "#0b02cb",   # 蓝 出发点2
    (2, 2): "#f0d000", (2, 4): "#f0d000", (4, 2): "#f0d000", (4, 4): "#f0d000",
    (1, 3): "#eb0301",   # 红
    (5, 1): "#c6c7c1",   # 白色区域1（底灰白）
    (5, 3): "#c6c7c1",   # 白色区域2
    (3, 3): "#c6c7c1",   # 普通可通行
}
for key, want in EXPECT.items():
    got = color_at_cell(key)
    check(got == want, "r%dc%d 填充色 %s（期望 %s）" % (key[0], key[1], got, want))

# ---- 绿色小车 ----
ovals = [i for i in sim.canvas.find_all() if sim.canvas.type(i) == "oval"]
car = [i for i in ovals if sim.canvas.itemcget(i, "fill") == M.C_CAR]
check(len(car) == 1, "存在 1 个绿色圆形小车（实际 %d 个）" % len(car))
if car:
    x0, y0, x1, y1 = sim.canvas.coords(car[0])
    cell = M.GRID[(1, 5)]
    cx, cy = sim.to_canvas(cell.cx, cell.cy)
    check(abs((x0 + x1) / 2 - cx) < 1 and abs((y0 + y1) / 2 - cy) < 1,
          "小车中心与出发点1 格心重合 (%.1f,%.1f)" % ((x0 + x1) / 2, (y0 + y1) / 2))
    check(abs((x1 - x0) / 2 - M.CAR_R) < 1, "小车半径 = %d px" % M.CAR_R)

# ---- 悬停 (5,1) 应出现黄色预览路径，且经过 9 个格心 ----
# 先把鼠标移到一个普通格子再移到目标格（模拟真实鼠标轨迹）
for k in [(3, 3), (5, 1)]:
    ev = E()
    ev.x, ev.y = sim.to_canvas(M.GRID[k].cx, M.GRID[k].cy)
    sim.on_motion(ev)
    win.update()
cell = M.GRID[(5, 1)]
ev = E(); ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
path_items = list(sim.canvas.find_withtag("path"))
yellow_lines = [i for i in path_items if sim.canvas.type(i) == "line"
                and sim.canvas.itemcget(i, "fill") == "#facc15"]
yellow_dots = [i for i in path_items
               if sim.canvas.type(i) == "oval" and sim.canvas.itemcget(i, "fill") == "#facc15"]
check(len(yellow_lines) == 1, "预览路径画出了折线")
check(len(yellow_dots) == 9, "预览路径标出 9 个格心（实际 %d）" % len(yellow_dots))

want_keys = [c.key for c in M.shortest_path((1, 5), (5, 1))[0]]
coords = sim.canvas.coords(yellow_lines[0])
ok = True
for i, key in enumerate(want_keys):
    cx, cy = sim.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    if abs(coords[2 * i] - cx) > 1 or abs(coords[2 * i + 1] - cy) > 1:
        ok = False
check(ok, "折线顶点与最短路径格心逐一对应（%s）" % "→".join("r%dc%d" % k for k in want_keys))

# 状态栏文本包含路径与格数
st = sim.lbl_status.cget("text")
check("9 个格子" in st, "状态栏显示经过格数：%r" % st.replace("\n", " | "))

# ---- 行驶中深绿色路径线 ----
ev = E(); ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
sim.on_click(ev)
win.update()
green_lines = [i for i in sim.canvas.find_withtag("path")
               if sim.canvas.type(i) == "line"
               and sim.canvas.itemcget(i, "fill") == M.C_PATH]
check(len(green_lines) == 1, "行驶中显示深绿色已规划路径")
import time
t0 = time.time()
while sim.move is not None and time.time() - t0 < 15:
    win.update(); time.sleep(0.01)
check(sim.car_cell.key == (5, 1), "小车抵达白色区域1")

# ---- 绘制后小车跟随 ----
car = [i for i in sim.canvas.find_all()
       if sim.canvas.type(i) == "oval" and sim.canvas.itemcget(i, "fill") == M.C_CAR]
x0, y0, x1, y1 = sim.canvas.coords(car[0])
cx, cy = sim.to_canvas(M.GRID[(5, 1)].cx, M.GRID[(5, 1)].cy)
check(abs((x0 + x1) / 2 - cx) < 1 and abs((y0 + y1) / 2 - cy) < 1, "小车停在白色区域1 格心")

# ---- 面板尺寸是否放得下 ----
win.update()
pw = win.winfo_reqwidth()
check(pw <= win.winfo_screenwidth(), "窗口宽度 %d 未超过屏幕宽 %d" % (pw, win.winfo_screenwidth()))
check(win.winfo_reqheight() <= win.winfo_screenheight(),
      "窗口高度 %d 未超过屏幕高 %d" % (win.winfo_reqheight(), win.winfo_screenheight()))
print("提示：窗口建议尺寸 %dx%d" % (win.winfo_reqwidth(), win.winfo_reqheight()))
win.destroy()

# ---- 起点弹窗尺寸 ----
root = tk.Tk(); root.withdraw()
dlg = M.StartDialog(root)
root.update()
dw, dh = dlg.top.winfo_reqwidth(), dlg.top.winfo_reqheight()
print("起点弹窗建议尺寸 %dx%d" % (dw, dh))
check(dw <= root.winfo_screenwidth() and dh <= root.winfo_screenheight(), "起点弹窗未超出屏幕")
check(dlg.canvas.winfo_reqwidth() >= 400, "起点弹窗地图宽度足够（%d px）" % dlg.canvas.winfo_reqwidth())
dlg.top.destroy(); root.destroy()

print("\n" + ("全部通过 ✔" if not FAIL else "失败 %d 项" % len(FAIL)))
sys.exit(1 if FAIL else 0)
