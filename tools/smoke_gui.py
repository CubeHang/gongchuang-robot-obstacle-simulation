# -*- coding: utf-8 -*-
"""用真实的 Tk 界面做自动化冒烟测试：模拟点击 + 驱动动画，验证整条流程。"""
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


# ---------------------------------------------------------------- 出发点弹窗 --
print("=== 出发点选择弹窗 ===")


class E:
    pass


# 与真实启动方式一致：master 必须是“已映射”的窗口，否则 transient 弹窗会被隐藏
root = tk.Tk()
root.overrideredirect(True)
try:
    root.attributes("-alpha", 0.0)
except tk.TclError:
    pass
root.geometry("1x1+-100+-100")
root.update()

dlg = M.StartDialog(root)
root.update()
# 回归检查：弹窗必须真的显示出来（曾因 root withdrawn + transient 被永久隐藏）
check(dlg.top.state() == "normal", "出发点弹窗状态为 normal（实际 %s）" % dlg.top.state())
check(dlg.top.winfo_viewable() == 1, "出发点弹窗在屏幕上可见")
check(dlg.top.winfo_width() > 400 and dlg.top.winfo_height() > 400,
      "出发点弹窗尺寸 %dx%d" % (dlg.top.winfo_width(), dlg.top.winfo_height()))
check(dlg.canvas.winfo_width() > 400, "弹窗内地图画布已渲染（宽 %d）" % dlg.canvas.winfo_width())

rc = dlg._cell_at(*dlg._tc(M.GRID[(1, 5)].cx, M.GRID[(1, 5)].cy))
check(rc is not None and rc.key == (1, 5), "弹窗中点击 (1,5) 中心可识别为蓝色出发点")
rc = dlg._cell_at(*dlg._tc(M.GRID[(3, 3)].cx, M.GRID[(3, 3)].cy))
check(rc is not None and rc.key == (3, 3), "弹窗中点击 (3,3) 中心识别正确")
# 非蓝色格子不应被接受
ev = E(); ev.x, ev.y = dlg._tc(M.GRID[(3, 3)].cx, M.GRID[(3, 3)].cy)
dlg._click(ev)
check(dlg.choice is None, "点击非蓝色格子不会选定出发点")
ev = E(); ev.x, ev.y = dlg._tc(M.GRID[(5, 5)].cx, M.GRID[(5, 5)].cy)
dlg._click(ev)
check(dlg.choice == (5, 5), "点击蓝色格子 (5,5) 成功选定出发点")
dlg.top.destroy()
root.destroy()

# ---------------------------------------------------------------- 主仿真界面 --
print("\n=== 主界面：点击坐标换算 ===")
win = tk.Tk()
sim = M.Simulator(win, (1, 5))
win.update()
check(win.state() == "normal" and win.winfo_viewable() == 1, "主窗口正常显示")
for key in [(1, 1), (1, 3), (2, 2), (3, 3), (5, 3), (5, 5)]:
    cell = M.GRID[key]
    got = sim.cell_at_canvas(*sim.to_canvas(cell.cx, cell.cy))
    check(got is not None and got.key == key,
          "画布坐标反查 r%dc%d 正确" % key)

check(sim.cell_at_canvas(2, 2) is None, "画布留白处返回 None（不误判格子）")


def drive(timeout=25.0):
    """推进 Tk 事件循环直到小车停止移动。"""
    import time
    t0 = time.time()
    while sim.move is not None:
        win.update()
        time.sleep(0.005)
        if time.time() - t0 > timeout:
            raise TimeoutError("动画超时")


def click(key):
    cell = M.GRID[key]
    ev = E(); ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
    sim.on_motion(ev)
    sim.on_click(ev)


# ------------------------------------------------------------ 阶段：放障碍物 --
print("\n=== 阶段①：放置障碍物 ===")
check(sim.phase == "setup", "初始进入障碍物准备阶段（实际 %s）" % sim.phase)
check(str(sim.btn_start["state"]) == "disabled", "没放障碍物时“开始仿真”按钮不可用")
sim.begin_simulation()
check(sim.phase == "setup", "没有障碍物时不能开始仿真")

# 被选中的出发点不能放障碍物
click((1, 5))
check(len(sim.obstacle_keys) == 0, "被选作出发点的蓝格不能放障碍物")
# 黄色禁行区与目标地点不能放
click((2, 2)); check(len(sim.obstacle_keys) == 0, "黄色禁行区不能放障碍物")
click((1, 3)); check(len(sim.obstacle_keys) == 0, "红色目标区域不能放障碍物")
click((5, 3)); check(len(sim.obstacle_keys) == 0, "白色区域1 不能放障碍物")
click((3, 1)); check(len(sim.obstacle_keys) == 0, "白色区域2 不能放障碍物")
# 另一个出发点可以放
click((5, 5))
check(sim.obstacle_keys == [(5, 5)], "另一个蓝色出发点可以放障碍物（视为普通路径）")
click((5, 5))
check(sim.obstacle_keys == [], "再点一下取消该障碍物")

# 手动放 1 个：r1c4 会挡住去红色区域的直路
click((1, 4))
check(sim.obstacle_keys == [(1, 4)], "手动放置障碍物成功")
check(M.GRID[(1, 4)].obstacle and not M.GRID[(1, 4)].passable, "障碍物格子不可通行")
check(str(sim.btn_start["state"]) == "normal", "有 1 个障碍物后可以开始仿真")
n_obs = len(sim.canvas.find_withtag("obs")) if hasattr(sim, "canvas") else 0
check(any(sim.canvas.itemcget(i, "fill") == M.C_OBSTACLE
          for i in sim.canvas.find_withtag("obs")
          if sim.canvas.type(i) == "rectangle"),
      "画布上画出了棕色障碍物")

# 第 3 个障碍物应被拒绝
click((3, 3)); click((3, 4))
check(len(sim.obstacle_keys) <= 2, "障碍物最多 2 个（实际 %d）" % len(sim.obstacle_keys))

# 随机放置
sim.randomize_obstacles()
check(1 <= len(sim.obstacle_keys) <= 2, "随机放置得到 1~2 个障碍物")
ok, bad = M.reachable_goals(sim.start_key)
check(not bad, "随机放置后三个目标仍全部可达")

# 手动摆一个会堵死出发点的组合，应被拦住不能开始
sim.clear_obstacle_ui()
click((1, 4)); click((2, 5))
check(str(sim.btn_start["state"]) == "disabled", "目标不可达时“开始仿真”被禁用")
sim.begin_simulation()
check(sim.phase == "setup", "目标不可达时不允许开始仿真")
check(sim.bad_goals, "状态栏/画布给出了不可达告警")

# 换成一组不影响通行的障碍物
sim.clear_obstacle_ui()
click((3, 3))
check(sim.obstacle_keys == [(3, 3)], "重新放置一个障碍物")
sim.begin_simulation()
check(sim.phase == "select", "点击“开始仿真”后进入选择目标阶段")
check(str(sim.btn_random["state"]) == "disabled", "开始仿真后随机按钮被禁用")
check(sim.obstacle_keys == [(3, 3)], "开始仿真后障碍物保持不变")

print("\n=== 行驶流程：出发 -> 三个目标来回 -> 回到出发点 ===")
seq = [(1, 3), (5, 3), (3, 1), (1, 3), (5, 3), (1, 3), (3, 1)]
expected_steps = 0
for goal in seq:
    p, e = M.shortest_path(sim.car_cell.key, goal)
    check(not e, "从 %s 到 %s 可规划出路径" % (sim.car_cell.name, M.GRID[goal].name))
    check(all(c.passable for c in p), "路径上没有不可通行格子（自动绕障）")
    before = sim.steps
    click(goal)
    drive()
    expected_steps += len(p) - 1
    check(sim.car_cell.key == goal, "小车已停在 %s" % M.GRID[goal].name)
    check(sim.steps == expected_steps,
          "累计行驶格数 = %d（期望 %d）" % (sim.steps, expected_steps))
    check(sim.move is None and sim.phase == "select", "到达后回到可选择的等待状态")

check(sim.visited_goals == ["红色区域", "白色区域1", "白色区域2"],
      "到达目标记录：%s" % "、".join(sim.visited_goals))

# 黄色禁行格点击无效
cell_before = sim.car_cell.key
click((2, 2))
check(sim.car_cell.key == cell_before and sim.move is None,
      "点击黄色禁行格 (2,2) 不产生移动")
check("禁止通行" in sim.lbl_status.cget("text"), "状态栏提示禁止通行")

# 行驶中不接受新的选择
click((1, 3))
check(sim.move is not None, "点击后进入行驶状态")
click((5, 3))
win.update()
check(sim.move is not None and sim.move["path"][-1].key == (1, 3),
      "行驶中再次点击不会插队改变当前目标")
drive()
check(sim.car_cell.key == (1, 3), "小车正常抵达 (1,3)")

# 点击出发点 -> 结束
print("\n=== 点击出发点结束仿真 ===")
click((1, 5))
win.update()
check(sim.finished, "点击出发点所在格子后进入结束状态")
check(sim.lbl_mode.cget("text") == "仿真结束", "模式显示“仿真结束”")
text = sim.txt.get("1.0", "end")
check("本次仿真结束" in text and "行驶格数" in text, "行驶记录中输出了总结")
check(len(sim.root.winfo_children()) >= 1, "弹出了结束对话框")

# 结束对话框按钮
tops = [w for w in win.winfo_children() if isinstance(w, tk.Toplevel)]
check(len(tops) == 1, "结束对话框存在")
win.destroy()

print("\n" + ("全部通过 ✔" if not FAIL else "失败 %d 项：%s" % (len(FAIL), FAIL)))
sys.exit(1 if FAIL else 0)
