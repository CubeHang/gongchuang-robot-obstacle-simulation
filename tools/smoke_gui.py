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

# ------------------------------------------------------- 阶段②：选择目标区域 --
print("\n=== 阶段②：勾选目标区域 ===")
check(sim.phase == "targets", "进入目标区域阶段（实际 %s）" % sim.phase)
check(sim.targets == list(M.DEFAULT_TARGETS), "默认四个目标区域都勾选：%s"
      % M.target_selection_text(sim.targets))
check(len(sim.canvas.find_withtag("preview")) > 0, "进入目标阶段即用虚线画出整条计划路径")
check(sim.lbl_target[(1, 3)].cget("text") == "第 1 个", "红色区域编号 1")
check(sim.lbl_target[(3, 5)].cget("text") == "第 2 个", "橙色区域编号 2")
check(sim.lbl_target[(5, 3)].cget("text") == "第 3 个", "白色区域1 编号 3")
check(sim.lbl_target[(3, 1)].cget("text") == "第 4 个", "白色区域2 编号 4")

# 取消橙色
sim.var_targets[(3, 5)].set(False)
sim.on_target_toggle()
check((3, 5) not in sim.targets, "取消勾选橙色区域后它不在计划里")
check(sim.lbl_target[(3, 5)].cget("text") == "不前往", "橙色区域显示“不前往”")
check(sim.targets == [(1, 3), (5, 3), (3, 1)], "顺序保持：%s" % M.target_selection_text(sim.targets))

# 重新勾选 -> 排到最后
sim.var_targets[(3, 5)].set(True)
sim.on_target_toggle()
check(sim.targets[-1] == (3, 5), "重新勾选的橙色区域排在最后（第 4 个）")

# 调整顺序
sim.targets = list(M.DEFAULT_TARGETS)
sim.var_targets[(1, 3)].set(True)
sim.on_target_toggle()
sim.var_targets[(3, 1)].set(False); sim.on_target_toggle()
check(sim.targets == [(1, 3), (3, 5), (5, 3)], "取消白色区域2：%s"
      % M.target_selection_text(sim.targets))
sim.var_targets[(3, 1)].set(True); sim.on_target_toggle()
order_before = list(sim.targets)
sim.move_target(1)
check(sim.targets == order_before[1:] + order_before[:1], "“延后”把第一个目标移到最后")

# 把顺序恢复成默认，便于后续比对
sim.targets = list(M.DEFAULT_TARGETS)
sim.on_target_toggle()

# 弹窗预览：一整条计划用虚线画出来
plan_segs, plan_info = M.build_plan(sim.start_key, sim.targets)
check("预计总里程" in sim.lbl_plan.cget("text"), "面板显示了预计总里程")
check("4 步" in sim.lbl_plan.cget("text") or str(plan_info["total_steps"]) in sim.lbl_plan.cget("text"),
      "面板总里程与计划一致（%d 步）" % plan_info["total_steps"])
check(len(sim.canvas.find_withtag("preview")) > 0, "地图上用虚线画出了计划路径")

# 恢复成四个目标，检查预计里程变成完整计划的步数
sim.targets = list(M.DEFAULT_TARGETS)
for var in sim.var_targets.values():
    var.set(True)
sim.on_target_toggle()
full_segs, full_info = M.build_plan(sim.start_key, sim.targets)
check(sim.plan_info.get("total_steps") == full_info["total_steps"],
      "四个目标时预计总里程 = %d 步" % full_info["total_steps"])

# 全部取消勾选 -> 不能开始
sim.targets = []
for var in sim.var_targets.values():
    var.set(False)
sim.on_target_toggle()
check(str(sim.btn_plan["state"]) == "disabled", "一个目标都没选时不能开始仿真")
sim.var_targets[(1, 3)].set(True)
sim.on_target_toggle()
check(sim.targets == [(1, 3)], "重新勾选红色区域")

# ------------------------------------------------------- 阶段③：自动连跑 --
print("\n=== 阶段③：自动跑完整场仿真 ===")
# 先只选一个目标试一次
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
check("计划访问：红色区域" in text, "总结里列出了计划访问的目标")
win.destroy()

# ---- 第二次：四个目标全选，完整跑一遍 ----
print("\n=== 完整仿真：四个目标全选 ===")
win2 = tk.Tk()
sim2 = M.Simulator(win2, (1, 5))
win2.update()


def click2(key):
    ev = E(); ev.x, ev.y = sim2.to_canvas(M.GRID[key].cx, M.GRID[key].cy)
    sim2.on_motion(ev)
    sim2.on_click(ev)


click2((4, 5))                 # 障碍物：r4c5，影响不到目标
sim2.enter_targets()
win2.update()
check(sim2.targets == list(M.DEFAULT_TARGETS), "四个目标都在计划里")

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
check(sim2.visited_goals == [GRID_NAME for GRID_NAME in
                             [M.GRID[k].goal_name for k in sim2.targets]],
      "四个目标都到达过：%s" % "、".join(sim2.visited_goals))
check(sim2.phase == "done", "阶段变为 done")
check("仿真结束" in sim2.lbl_mode.cget("text"), "模式显示仿真结束")
text2 = sim2.txt.get("1.0", "end")
check("未到达目标：无" in text2, "总结里未到达目标为“无”")
tops = [w for w in win2.winfo_children() if isinstance(w, tk.Toplevel)]
check(len(tops) == 1, "跑完后弹出结束对话框")

# 日志里应当能看到逐段记录
check(text2.count("第 ") >= info["segments"], "记录里逐段列出了行驶过程")
win2.destroy()

print("\n" + ("全部通过 ✔" if not FAIL else "失败 %d 项：%s" % (len(FAIL), FAIL)))
sys.exit(1 if FAIL else 0)
