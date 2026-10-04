# -*- coding: utf-8 -*-
"""检查 Tk 画布上实际绘制出的图形元素（颜色/位置），核验渲染正确。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
import map_sim as M
import time

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
    (5, 3): "#ffffff",   # 白色区域1（白色目标区）
    (3, 1): "#ffffff",   # 白色区域2（白色目标区）
    (3, 3): "#c6c7c1",   # 普通可通行（灰色）
    (3, 5): "#ff8c00",   # 橙色格子
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

# ---- 阶段一：在准备阶段放一个障碍物，检查障碍物绘制 ----
print("\n准备阶段：")
check(sim.phase == "setup", "初始为障碍物准备阶段")
click_cell = M.GRID[(3, 2)]
ev = E(); ev.x, ev.y = sim.to_canvas(click_cell.cx, click_cell.cy)
sim.on_motion(ev)
win.update()
check("放障碍物" in sim.lbl_status.cget("text"), "准备阶段悬停提示可放障碍物")
sim.on_click(ev)
win.update()
check(sim.obstacle_keys == [(3, 2)], "点击后放置了障碍物 r3c2")
obs_rects = [i for i in sim.canvas.find_withtag("obs")
             if sim.canvas.type(i) == "rectangle"]
check(len(obs_rects) == 1, "画布上画出 1 个障碍物方块（实际 %d）" % len(obs_rects))
if obs_rects:
    check(sim.canvas.itemcget(obs_rects[0], "fill") == M.C_OBSTACLE,
          "障碍物填充色 = %s" % M.C_OBSTACLE)
check(sim.canvas.type([i for i in sim.canvas.find_withtag("obs")
                       if sim.canvas.type(i) == "text"][0]) == "text",
      "障碍物上有文字标注")

# ---- 阶段②：目标区域阶段，点击目标区域加入行程 ----
sim.enter_targets()
win.update()
check(sim.phase == "targets", "进入目标区域阶段")
check(sim.targets == [], "刚进入时行程为空")


def click_goal(key):
    ev = E(); ev.x, ev.y = sim.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    sim.on_motion(ev)
    sim.on_click(ev)
    win.update()


TRIP = [(1, 3), (3, 5), (5, 3), (1, 3)]      # 红色区域去两次
for key in TRIP:
    click_goal(key)
check(sim.targets == TRIP, "点选后的行程：%s" % M.target_selection_text(sim.targets))
preview_items = list(sim.canvas.find_withtag("preview"))
check(len(preview_items) > 0, "地图上画出计划预览（%d 个图元）" % len(preview_items))
preview_lines = [i for i in preview_items if sim.canvas.type(i) == "line"]
check(len(preview_lines) == sim.plan_info["segments"],
      "预览折线数量 = 计划段数（%d）" % sim.plan_info["segments"])

# 每一段折线的顶点应当与该段最短路径的格心一致
ok = True
for i, seg in enumerate(sim.plan):
    line = preview_lines[i]
    coords = sim.canvas.coords(line)
    for j, cell in enumerate(seg):
        cx, cy = sim.to_canvas(cell.cx, cell.cy)
        if abs(coords[2 * j] - cx) > 1 or abs(coords[2 * j + 1] - cy) > 1:
            ok = False
check(ok, "每段预览折线的顶点都与 BFS 最短路径格心一致")

# 访问顺序标记：红色区域访问 2 次，应出现“第1,4次”角标
marks = sim.canvas.find_withtag("mark")
mark_texts = [sim.canvas.itemcget(i, "text") for i in marks
              if sim.canvas.type(i) == "text"]
check(any("第1,4次" in t for t in mark_texts),
      "重复访问的目标标出“第1,4次”：%s" % mark_texts)

# 悬停在目标区域上给出提示
ev = E(); ev.x, ev.y = sim.to_canvas(M.GRID[(3, 5)].cx, M.GRID[(3, 5)].cy)
sim.on_motion(ev)
win.update()
check("橙色区域" in sim.lbl_status.cget("text"), "悬停橙色区域给出说明：%r"
      % sim.lbl_status.cget("text").replace("\n", " | "))

# ---- 阶段③：开始仿真，检查深绿色路径线与小车跟随 ----
sim.begin_simulation()
win.update()
check(sim.phase == "run", "开始后进入自动仿真阶段")
t0 = time.time()
while sim.move is None and not sim.finished and time.time() - t0 < 3:
    win.update(); time.sleep(0.01)
green_lines = [i for i in sim.canvas.find_withtag("path")
               if sim.canvas.type(i) == "line"
               and sim.canvas.itemcget(i, "fill") == M.C_PATH]
check(len(green_lines) == 1, "行驶中显示深绿色已规划路径")

t0 = time.time()
while (sim.move is not None or (not sim.finished and sim.phase == "run")) \
        and time.time() - t0 < 60:
    win.update(); time.sleep(0.005)
check(sim.finished, "自动仿真跑完并结束")
check(sim.car_cell.key == (1, 5), "小车回到出发点格心")

# ---- 绘制后小车跟随 ----
car = [i for i in sim.canvas.find_all()
       if sim.canvas.type(i) == "oval" and sim.canvas.itemcget(i, "fill") == M.C_CAR]
x0, y0, x1, y1 = sim.canvas.coords(car[0])
cx, cy = sim.to_canvas(M.GRID[(1, 5)].cx, M.GRID[(1, 5)].cy)
check(abs((x0 + x1) / 2 - cx) < 1 and abs((y0 + y1) / 2 - cy) < 1,
      "小车最后停在出发点 (1,5) 格心")
check(sim.steps == sim.plan_info["total_steps"],
      "总步数 %d = 计划步数 %d" % (sim.steps, sim.plan_info["total_steps"]))

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
