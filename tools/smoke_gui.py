# -*- coding: utf-8 -*-
"""用真实的 Tk 界面做自动化冒烟测试：走完“选起点 → 摆障碍 → 选目标 → 自动连跑 → 回起点”。

新流程（v1.2）：
    ① 放置障碍物   →   ② 勾选目标区域（顺序 = 访问顺序）   →   ③ 点开始仿真自动跑完
"""
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


# ---------------------------------------------------------------- 出发点弹窗 --
print("=== 出发点选择弹窗 ===")

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
check(dlg.top.state() == "normal", "出发点弹窗状态为 normal（实际 %s）" % dlg.top.state())
check(dlg.top.winfo_viewable() == 1, "出发点弹窗在屏幕上可见")
check(dlg.top.winfo_width() > 400 and dlg.top.winfo_height() > 400,
      "出发点弹窗尺寸 %dx%d" % (dlg.top.winfo_width(), dlg.top.winfo_height()))
check(dlg.canvas.winfo_width() > 400, "弹窗内地图画布已渲染（宽 %d）" % dlg.canvas.winfo_width())

rc = dlg._cell_at(*dlg._tc(M.GRID[(1, 5)].cx, M.GRID[(1, 5)].cy))
check(rc is not None and rc.key == (1, 5), "弹窗中点击 (1,5) 中心可识别为蓝色出发点")
ev = E(); ev.x, ev.y = dlg._tc(M.GRID[(3, 3)].cx, M.GRID[(3, 3)].cy)
dlg._click(ev)
check(dlg.choice is None, "点击非蓝色格子不会选定出发点")
ev = E(); ev.x, ev.y = dlg._tc(M.GRID[(5, 5)].cx, M.GRID[(5, 5)].cy)
dlg._click(ev)
check(dlg.choice == (5, 5), "点击蓝色格子 (5,5) 成功选定出发点")
dlg.top.destroy()
root.destroy()

# ---------------------------------------------------------------- 主界面 --
print("\n=== 主界面：坐标换算 ===")
win = tk.Tk()
sim = M.Simulator(win, (1, 5))
win.update()
check(win.state() == "normal" and win.winfo_viewable() == 1, "主窗口正常显示")
for key in [(1, 1), (1, 3), (2, 2), (3, 3), (3, 5), (5, 3), (5, 5)]:
    got = sim.cell_at_canvas(*sim.to_canvas(M.GRID[key].cx, M.GRID[key].cy))
    check(got is not None and got.key == key, "画布坐标反查 r%dc%d 正确" % key)
check(sim.cell_at_canvas(2, 2) is None, "画布留白处返回 None（不误判格子）")


def drive(timeout=60.0):
    """推进 Tk 事件循环直到小车和整个计划都跑完。"""
    import time
    t0 = time.time()
    while (sim.move is not None or (not sim.finished and sim.phase == "run")):
        win.update()
        time.sleep(0.004)
        if time.time() - t0 > timeout:
            raise TimeoutError("仿真超时")


def click_cell(key):
    cell = M.GRID[key]
    ev = E(); ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
    sim.on_motion(ev)
    sim.on_click(ev)


# ------------------------------------------------------------ 阶段①：障碍物 --
print("\n=== 阶段①：放置障碍物 ===")
check(sim.phase == "setup", "初始进入障碍物准备阶段（实际 %s）" % sim.phase)
check(str(sim.btn_to_targets["state"]) == "disabled", "没放障碍物时“下一步”不可用")
sim.enter_targets()
check(sim.phase == "setup", "没有障碍物时不能进入目标区域阶段")

click_cell((1, 5))
check(len(sim.obstacle_keys) == 0, "被选作出发点的蓝格不能放障碍物")
for key in list(M.GOAL_INFO):
    click_cell(key)
check(len(sim.obstacle_keys) == 0, "四个目标区域都不能放障碍物")
click_cell((2, 2))
check(len(sim.obstacle_keys) == 0, "黄色禁行区不能放障碍物")
click_cell((5, 5))
check(sim.obstacle_keys == [(5, 5)], "另一个蓝色出发点可以放障碍物（视为普通路径）")
click_cell((5, 5))
check(sim.obstacle_keys == [], "再点一下取消该障碍物")

click_cell((1, 4))                      # 挡住去红色区域的直路
check(sim.obstacle_keys == [(1, 4)], "手动放置障碍物成功")
check(str(sim.btn_to_targets["state"]) == "normal", "有 1 个障碍物后可以进入下一步")
check(any(sim.canvas.itemcget(i, "fill") == M.C_OBSTACLE
          for i in sim.canvas.find_withtag("obs")
          if sim.canvas.type(i) == "rectangle"), "画布上画出了棕色障碍物")

sim.randomize_obstacles()
check(1 <= len(sim.obstacle_keys) <= 2, "随机放置得到 1~2 个障碍物")
check(not M.reachable_goals(sim.start_key)[1], "随机放置后目标仍全部可达")

# 堵死目标的组合要被拦住
sim.clear_obstacle_ui()
click_cell((1, 4)); click_cell((2, 5))
check(str(sim.btn_to_targets["state"]) == "disabled", "目标不可达时“下一步”被禁用")
sim.enter_targets()
check(sim.phase == "setup", "目标不可达时不允许进入目标阶段")

# 换一个不影响通行的障碍物
sim.clear_obstacle_ui()
click_cell((3, 3))
sim.enter_targets()

# ------------------------------------------------------- 阶段②：点击选目标 --
print("\n=== 阶段②：在地图上点击目标区域（可重复）===")
check(sim.phase == "targets", "进入目标区域阶段（实际 %s）" % sim.phase)
check(sim.targets == [], "进入时行程是空的")
check(str(sim.btn_plan["state"]) == "disabled", "行程为空时不能开始仿真")
check(len(sim.canvas.find_withtag("preview")) == 0, "行程为空时没有计划预览")
sim.begin_simulation()
check(sim.phase == "targets", "行程为空时不允许开始")


def click_goal(key):
    cell = M.GRID[key]
    ev = E(); ev.x, ev.y = sim.to_canvas(cell.cx, cell.cy)
    sim.on_motion(ev)
    sim.on_click(ev)
    win.update()


click_goal((1, 3))
check(sim.targets == [(1, 3)], "点击红色区域 → 加入行程")
check(len(sim.canvas.find_withtag("preview")) > 0, "加入后立即画出计划预览虚线")
check(len(sim.canvas.find_withtag("mark")) >= 2, "地图上标出了访问顺序")
click_goal((3, 5))
click_goal((1, 3))
check(sim.targets == [(1, 3), (3, 5), (1, 3)], "同一个目标区域可以点多次：%s"
      % M.target_selection_text(sim.targets))
plan_segs, plan_info = M.build_plan(sim.start_key, sim.targets)
check(sim.plan_info.get("total_steps") == plan_info["total_steps"],
      "面板预计里程与计划一致（%d 步 / %d 段）"
      % (plan_info["total_steps"], plan_info["segments"]))
check(str(plan_info["total_steps"]) in sim.lbl_plan.cget("text"), "面板显示了预计总里程")

# 非目标区域点不进去
n_before = len(sim.targets)
for key in [(3, 3), (2, 2), (1, 5), (3, 2)]:
    click_goal(key)
check(len(sim.targets) == n_before, "点非目标区域（灰格/禁行区/出发点）不会加入行程")
check("请点击目标区域" in sim.lbl_status.cget("text"), "状态栏提示要点目标区域")

# 撤销与清空
order_before = list(sim.targets)
sim.undo_last_target()
check(sim.targets == order_before[:-1], "“撤销上一个”去掉了最后一个目标")
sim.undo_last_target()
sim.undo_last_target()
check(sim.targets == [], "连续撤销后行程为空")
check(str(sim.btn_plan["state"]) == "disabled", "行程为空时开始按钮又被禁用")
sim.undo_last_target()
check(sim.targets == [], "空行程再撤销不会出错")

# 重新点一串（含重复）并测试清空
for key in [(1, 3), (3, 5), (5, 3), (3, 1), (1, 3), (3, 1), (1, 3)]:
    click_goal(key)
check(sim.targets == [(1, 3), (3, 5), (5, 3), (3, 1), (1, 3), (3, 1), (1, 3)],
      "7 个目标的行程：%s" % M.target_selection_text(sim.targets))
check(sim.targets.count((1, 3)) == 3, "红色区域在行程里出现 3 次")
marks = sim.canvas.find_withtag("mark")
mark_texts = [sim.canvas.itemcget(i, "text") for i in marks
              if sim.canvas.type(i) == "text"]
check(any("第" in t and "次" in t for t in mark_texts),
      "重复的目标区域标出了第几次去：%s" % mark_texts)
sim.clear_targets()
check(sim.targets == [], "“清空行程”清空所有目标")
check(len(sim.canvas.find_withtag("mark")) == 0, "清空后地图上的顺序标记也清掉了")
check(len(sim.canvas.find_withtag("preview")) == 0, "清空后计划预览也清掉了")

# ------------------------------------------------------- 阶段③：自动连跑 --
print("\n=== 阶段③：自动跑完整场仿真 ===")
# 先只选一个目标试一次
click_goal((1, 3))
segments, info = M.build_plan(sim.start_key, sim.targets)
check(info["segments"] == 2, "只有一个目标时计划是 2 段（去 + 回）")
sim.begin_simulation()
check(sim.phase == "run", "开始后进入自动仿真阶段")
check(str(sim.btn_random["state"]) == "disabled", "仿真中障碍物按钮被禁用")
check(str(sim.btn_plan["state"]) == "disabled", "仿真中开始按钮被禁用")
check("自动仿真中" in sim.lbl_mode.cget("text"), "模式显示自动仿真中")
drive()
check(sim.car_cell.key == (1, 5), "小车最后停在出发点")
check(sim.finished, "跑完计划后仿真结束")
check(sim.visited_goals == ["红色区域"], "到达记录正确：%s" % "、".join(sim.visited_goals))
text = sim.txt.get("1.0", "end")
check("小车已回到出发点" in text, "记录写明小车已回到出发点")
check("行程（1 个目标）" in text, "总结里列出了行程")
check("目标完成情况：红色区域 1/1" in text, "总结里写了目标完成情况")
win.destroy()

# ---- 第二次：包含重复目标的行程，完整跑一遍 ----
print("\n=== 完整仿真：含重复目标的行程 ===")
win2 = tk.Tk()
sim2 = M.Simulator(win2, (1, 5))
win2.update()


def click2(key):
    ev = E(); ev.x, ev.y = sim2.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    sim2.on_motion(ev)
    sim2.on_click(ev)
    win2.update()


click2((4, 5))                 # 障碍物：r4c5，影响不到目标
sim2.enter_targets()
win2.update()
TRIP = [(1, 3), (3, 5), (5, 3), (3, 1), (1, 3)]      # 红色区域去两次
for key in TRIP:
    click2(key)
check(sim2.targets == TRIP, "行程：%s" % M.target_selection_text(sim2.targets))
check(sim2.targets.count((1, 3)) == 2, "红色区域安排了 2 次")

segments, info = M.build_plan(sim2.start_key, sim2.targets)
total_steps = info["total_steps"]
print("  计划：%d 段，共 %d 步" % (info["segments"], total_steps))
for i, seg in enumerate(segments):
    print("    第%d段 %s → %s : %d 步" % (i + 1, seg[0].name, seg[-1].name, len(seg) - 1))

sim2.begin_simulation()
import time
t0 = time.time()
while (sim2.move is not None or (not sim2.finished and sim2.phase == "run")):
    win2.update()
    time.sleep(0.004)
    if time.time() - t0 > 60:
        raise TimeoutError("完整仿真超时")

check(sim2.finished, "完整仿真跑完并结束")
check(sim2.car_cell.key == (1, 5), "小车回到出发点 %s" % M.GRID[sim2.car_cell.key].name)
check(sim2.steps == total_steps, "总行驶格数 = %d（期望 %d）" % (sim2.steps, total_steps))
check(sim2.visited_count.get("红色区域") == 2, "红色区域到达 2 次（实际 %s）"
      % sim2.visited_count.get("红色区域"))
check(sim2.visited_count.get("橙色区域") == 1, "橙色区域到达 1 次")
check(sim2.phase == "done", "阶段变为 done")
check("仿真结束" in sim2.lbl_mode.cget("text"), "模式显示仿真结束")
text2 = sim2.txt.get("1.0", "end")
check("未完成：无" in text2, "总结里没有未完成的目标")
check("红色区域 2/2" in text2, "总结里写了红色区域 2/2")
tops = [w for w in win2.winfo_children() if isinstance(w, tk.Toplevel)]
check(len(tops) == 1, "跑完后弹出结束对话框")

# 日志里应当能看到逐段记录
check(text2.count("第 ") >= info["segments"], "记录里逐段列出了行驶过程")
win2.destroy()

print("\n" + ("全部通过 ✔" if not FAIL else "失败 %d 项：%s" % (len(FAIL), FAIL)))
sys.exit(1 if FAIL else 0)
