# -*- coding: utf-8 -*-
"""
避障比赛地图仿真环境
=====================================================================
地图：5 行 x 5 列（由原图 4 条横向黑线 + 4 条纵向黑线划分而成，格子大小不均匀，
      本程序直接沿用原图像素比例还原）。

格子含义：
    蓝色格子 (r1c5) (r5c5) ......... 小车出发点（比赛随机二选一）
    黄色格子 (r2c2) (r2c4)
             (r4c2) (r4c4) ......... 禁止通行区域
    红色格子 (r1c3) ................ 目标地点：红色区域
    白格子   (r5c3) ................ 目标地点：白色区域 1（第 5 行第 3 列）
    白格子   (r3c1) ................ 目标地点：白色区域 2（第 3 行第 1 列）
    其余格子 ....................... 可通行（白色区域）

任务流程：
    选择出发点 -> 选择目标地点 -> 小车用最短路径行驶过去 -> 再选下一个目标
    -> …… -> 用户点回出发点，本次仿真结束。

路径规划：BFS（广度优先搜索）在 5x5 格子图上求最短路径，以“走过的格子数”
          作为距离度量，黄色禁止通行格子不可进入。

运行：  python map_sim.py
"""

import random
import tkinter as tk
from tkinter import font as tkfont
from collections import deque

# ----------------------------------------------------------------------------
# 1. 地图数据
# ----------------------------------------------------------------------------

ROWS, COLS = 5, 5

# 原地图上检测到的黑线像素位置（用于还原原图格子比例）
X_BOUNDS = [0, 239.5, 445.5, 625.5, 829.5, 1080.0]
Y_BOUNDS = [0, 242.5, 446.5, 635.5, 831.0, 1070.0]
MAP_PX_W = X_BOUNDS[-1]
MAP_PX_H = Y_BOUNDS[-1]

# 格子种类
FLOOR, WALL, START, GOAL = "floor", "wall", "start", "goal"

# 颜色
C_FLOOR = "#c6c7c1"       # 可通行区域（灰色背景）
C_GOAL_WHITE = "#ffffff"  # 白色目标区域
C_GOAL_ORANGE = "#ff8c00"  # 橙色目标区域
C_WALL = "#f0d000"        # 禁止通行（黄）
C_START = "#0b02cb"       # 出发点（蓝）
C_GOAL_RED = "#eb0301"    # 红色目标
C_OBSTACLE = "#7b3f00"    # 障碍物（棕色）
C_BAD = "#ff2d2d"         # 目标不可达的告警色
C_GRID = "#111111"        # 网格黑线
C_CAR = "#18c832"         # 小车（绿）
C_PATH = "#0e7a1e"        # 规划路径

# 特殊格子标注
START_CELLS = [(1, 5), (5, 5)]                       # (行, 列)，从 1 开始
WALL_CELLS = [(2, 2), (2, 4), (4, 2), (4, 4)]
# 目标区域：红色区域、橙色区域、白色区域1、白色区域2（顺序即默认访问顺序）
GOAL_INFO = {
    (1, 3): ("红色区域", C_GOAL_RED, "红"),
    (3, 5): ("橙色区域", C_GOAL_ORANGE, "橙"),   # 第 3 行第 5 列
    (5, 3): ("白色区域1", C_GOAL_WHITE, "1"),    # 第 5 行第 3 列
    (3, 1): ("白色区域2", C_GOAL_WHITE, "2"),    # 第 3 行第 1 列
}
DEFAULT_TARGETS = list(GOAL_INFO)

# 单独指定底色的普通格子（保持普通可通行格的身份，不改变通行规则）
CELL_COLORS = {}

# 当前被选作出发点的格子。比赛规则：两个蓝色格子随机二选一作为出发点，
# 没被选中的那个视为普通路径，可以放障碍物。
ACTIVE_START = [None]


def set_active_start(start_key):
    ACTIVE_START[0] = start_key
    return start_key


class Cell:
    """一个格子。"""

    def __init__(self, r, c):
        self.r = r                      # 行号 1..5
        self.c = c                      # 列号 1..5
        self.kind = FLOOR
        self.color = C_FLOOR
        self.goal_name = None           # 目标地点名称
        self.mark = ""                  # 格子内显示的字符
        self.obstacle = False           # 比赛开始前随机放置的障碍物
        # 原图像素范围（左上、右下），初始化后填入
        self.x0 = self.y0 = self.x1 = self.y1 = 0.0

    @property
    def key(self):
        return (self.r, self.c)

    @property
    def name(self):
        if self.kind == START:
            return "出发点" + self.mark
        if self.goal_name:
            return self.goal_name
        return "r%dc%d" % (self.r, self.c)

    @property
    def passable(self):
        """黄色禁行区与障碍物都不能进入。"""
        return self.kind != WALL and not self.obstacle

    @property
    def can_hold_obstacle(self):
        """能否放障碍物。

        规则：终点/禁行区不行；两个蓝色出发点里，被选作出发点的那个不行
        （小车就停在那儿），另一个出发点视为普通路径、可以放障碍物。
        """
        if self.obstacle:
            return False
        if self.kind == FLOOR:
            return True
        return self.kind == START and self.key != ACTIVE_START[0]

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2.0


def build_grid():
    """创建 5x5 格子并标注特殊区域。"""
    grid = {}
    for r in range(1, ROWS + 1):
        for c in range(1, COLS + 1):
            cell = Cell(r, c)
            cell.x0, cell.x1 = X_BOUNDS[c - 1], X_BOUNDS[c]
            cell.y0, cell.y1 = Y_BOUNDS[r - 1], Y_BOUNDS[r]
            grid[(r, c)] = cell

    for i, key in enumerate(START_CELLS, start=1):
        g = grid[key]
        g.kind, g.color, g.mark = START, C_START, str(i)

    for key in WALL_CELLS:
        g = grid[key]
        g.kind, g.color, g.mark = WALL, C_WALL, ""

    for key, (name, color, mark) in GOAL_INFO.items():
        g = grid[key]
        g.kind, g.color, g.goal_name, g.mark = GOAL, color, name, mark

    # 单独改底色的格子（仍然是普通可通行格子，只是颜色不同）
    for key, color in CELL_COLORS.items():
        grid[key].color = color

    return grid


GRID = build_grid()

# ----------------------------------------------------------------------------
# 2. 路径规划：BFS 最短路（4 邻域，黄色禁行区与障碍物都不可通行）
# ----------------------------------------------------------------------------

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]   # 上 下 左 右


def neighbors(cell):
    for dr, dc in DIRS:
        nxt = GRID.get((cell.r + dr, cell.c + dc))
        if nxt is not None and nxt.passable:
            yield nxt


def shortest_path(start_key, goal_key):
    """BFS 求最短路径（自动绕开黄色禁行区与障碍物）。

    返回 (路径格子列表, 说明信息)。列表含起点与终点；
    若不可达则返回 ([], 原因)。
    """
    s, t = GRID.get(start_key), GRID.get(goal_key)
    if s is None or t is None:
        return [], "格子不存在"
    if not s.passable:
        return [], "起点不可通行（禁行区或障碍物）"
    if not t.passable:
        return [], "目标不可通行（禁行区或障碍物）"
    if s.key == t.key:
        return [s], "已经在目标格子上"

    prev = {s.key: None}
    queue = deque([s])
    while queue:
        cur = queue.popleft()
        if cur.key == t.key:
            break
        for nxt in neighbors(cur):
            if nxt.key not in prev:
                prev[nxt.key] = cur
                queue.append(nxt)

    if t.key not in prev:
        return [], "绕开障碍物后无法到达"

    path = []
    node = t
    while node is not None:
        path.append(node)
        node = prev[node.key]
    path.reverse()
    return path, ""


def path_text(path):
    """路径的文字描述。"""
    if not path:
        return "(无路径)"
    return " → ".join(c.name for c in path)


# ----------------------------------------------------------------------------
# 3. 障碍物：可以放哪些格子、随机生成、可达性检查
# ----------------------------------------------------------------------------

OTHER_START = {START_CELLS[0]: START_CELLS[1], START_CELLS[1]: START_CELLS[0]}


def goal_cells():
    return [GRID[key] for key in GOAL_INFO]


def obstacle_candidates(start_key):
    """可放置障碍物的格子：除“被选作出发点的那个蓝格”以外的可通行格子。

    另一个蓝色出发点按比赛规则视为普通路径，因此可以放障碍物。
    """
    return [GRID[k] for k in sorted(GRID)
            if k != start_key and GRID[k].can_hold_obstacle]


def reachable_goals(start_key):
    """返回 (可达目标名列表, 不可达目标名列表)。"""
    ok, bad = [], []
    for cell in goal_cells():
        path, err = shortest_path(start_key, cell.key)
        (ok if path else bad).append(cell.goal_name)
    return ok, bad


def clear_obstacles():
    for cell in GRID.values():
        cell.obstacle = False


def place_obstacles(keys):
    """按给定格子摆放障碍物（会先清空原有障碍物）。"""
    clear_obstacles()
    for key in keys:
        cell = GRID.get(key)
        if cell is not None and cell.can_hold_obstacle:
            cell.obstacle = True
    return [GRID[k].key for k in keys if GRID.get(k) is not None and GRID[k].obstacle]


def random_obstacles(start_key, count=None, rng=None, max_tries=300):
    """模拟比赛随机放置 1~2 个障碍物。

    约束：不能放在出发点/另一个出发点/禁行区/目标地点上，
          并且放完之后三个目标地点必须仍然可达（否则重新随机）。
    返回 (障碍物格子列表, 说明文字)。
    """
    rng = rng or random
    cand = obstacle_candidates(start_key)
    if not cand:
        return [], "没有可放置障碍物的位置"

    want = count if count is not None else rng.choice((1, 2))
    want = max(1, min(int(want), 2, len(cand)))
    clear_obstacles()
    for _ in range(max_tries):
        picked = rng.sample(cand, want)
        for cell in picked:
            cell.obstacle = True
        _, bad = reachable_goals(start_key)
        if not bad:
            names = "、".join(c.name for c in picked)
            return [c.key for c in picked], "随机放置 %d 个障碍物：%s" % (want, names)
        clear_obstacles()

    # 极端情况下退化为 1 个障碍物再试
    if want > 1:
        return random_obstacles(start_key, count=1, rng=rng, max_tries=max_tries)
    return [], "随机放置失败（找不到不堵死目标的方案）"


# ----------------------------------------------------------------------------
# 3b. 目标集合与行驶计划（先设定目标，再一次性跑完）
# ----------------------------------------------------------------------------

def goal_key_by_name(name):
    for key, (n, _c, _m) in GOAL_INFO.items():
        if n == name:
            return key
    return None


def target_selection_text(targets):
    """按访问顺序列出目标：① 红色区域 → ② 白色区域1 …"""
    circled = "①②③④⑤⑥⑦⑧⑨"
    return "、".join("%s %s" % (circled[i] if i < len(circled) else "%d." % (i + 1),
                              GRID[k].name)
                     for i, k in enumerate(targets))


def build_plan(start_key, targets, returning=True):
    """把“起点 → 目标1 → 目标2 → …（→ 回起点）”拼成完整行驶计划。

    返回 (segments, info)：
        segments —— 每一段的格子列表（含该段起点与终点），按行驶顺序；
        info     —— 汇总信息 dict（总格数/总步数/失败原因/每段格数）。
    任何一段不可达就返回 ([], {"error": ...})。
    """
    if not targets:
        return [], {"error": "还没有选择任何目标区域"}

    waypoints = [start_key] + list(targets)
    if returning:
        waypoints.append(start_key)

    segments = []
    for i in range(len(waypoints) - 1):
        a, b = waypoints[i], waypoints[i + 1]
        if a == b:
            continue
        path, err = shortest_path(a, b)
        if err:
            return [], {"error": "%s → %s 无法到达：%s" % (GRID[a].name, GRID[b].name, err)}
        segments.append(path)

    if not segments:
        return [], {"error": "所有目标都与出发点重合"}

    total_steps = sum(len(s) - 1 for s in segments)
    info = {
        "segments": len(segments),
        "total_steps": total_steps,
        "total_cells": sum(len(s) for s in segments) - (len(segments) - 1),
        "targets": list(targets),
        "returning": returning,
        "error": "",
    }
    return segments, info


def plan_text(segments, info):
    """把整段计划写成多行文字，便于打印/记录。"""
    lines = []
    for i, seg in enumerate(segments):
        dest = seg[-1]
        lines.append("  第 %d 段：%s → %s，%d 步"
                     % (i + 1, seg[0].name, dest.name, len(seg) - 1))
    lines.append("  合计 %d 步" % info["total_steps"])
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 4. 仿真界面
# ----------------------------------------------------------------------------

CELL_PX = 140          # 基准格子边长（像素），屏幕较小时会自动缩小
MARGIN = 26            # 画布留白
CAR_R = 26             # 小车半径（画布像素）
STEP_SECONDS = 0.30    # 走一格的基础耗时（秒），受速度滑块影响

FONT_FAMILY = "Microsoft YaHei"


def cell_px_for_screen(root, panel_width=330, chrome=110):
    """按屏幕大小挑一个能完整放下的格子边长（地图 + 右侧面板不超过屏幕）。"""
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    panel = min(panel_width, int(sw * 0.30))          # 窄屏时面板也用窄一点
    fit_w = (sw - panel - 2 * MARGIN - 40) * 200.0 / MAP_PX_W
    fit_h = (sh - chrome - 2 * MARGIN - 20) * 200.0 / MAP_PX_H
    return int(max(70, min(CELL_PX, fit_w, fit_h)))


class Simulator:
    """界面与流程。

    三个阶段（phase）：
        setup    —— 比赛准备①：手动点击或“随机障碍物”按钮放置 1~2 个障碍物
        targets  —— 比赛准备②：勾选本次要到达的目标区域，并确定访问顺序
        run      —— 自动连跑：依次到各目标 → 回到出发点 → 结束
    """

    MAX_OBSTACLES = 2

    def __init__(self, root, start_key, obstacles=None, targets=None):
        self.root = root
        self.start_key = start_key
        self.car_cell = GRID[start_key]
        self.cell_px = cell_px_for_screen(root)
        set_active_start(start_key)   # 另一个蓝色出发点从此可以放障碍物

        self.phase = "setup"          # "setup" 障碍物 / "targets" 选目标 / "run" 行驶中
        self.obstacle_keys = []       # 当前放置的障碍物格子
        # 本次要到达的目标区域，列表顺序 = 访问顺序；默认全选，按 GOAL_INFO 顺序
        self.targets = list(targets) if targets else list(DEFAULT_TARGETS)
        self.plan = []                # 行驶计划：每一段的格子列表
        self.plan_info = {}           # 计划汇总（总步数等）
        self.plan_idx = 0             # 当前执行到第几段
        self.move = None              # 当前移动状态
        self.trail = [start_key]      # 走过的格子
        self.steps = 0                # 已走格子数
        self.visited_goals = []       # 已到达过的目标地点
        self.hover_key = None
        self.preview_path = []
        self.finished = False
        self.bad_goals = []           # 当前障碍物下不可达的目标（用于界面告警）

        clear_obstacles()             # 新的一次仿真从零开始
        if obstacles:                 # 允许外部先摆好障碍物（自动演示用）
            self.obstacle_keys = place_obstacles(obstacles)

        self._build_ui()
        self._draw_static()
        self._draw_car()
        self.log("出发点：%s（蓝色格子）" % self.car_cell.name)
        self.enter_setup(first=True)

    # ---------------------------------------------------------------- 界面 --
    def _build_ui(self):
        self.root.title("避障比赛地图仿真 —— 小车路径规划")
        self.root.configure(bg="#20242b")

        self.f_ui = tkfont.Font(family=FONT_FAMILY, size=10)
        self.f_small = tkfont.Font(family=FONT_FAMILY, size=9)
        self.f_bold = tkfont.Font(family=FONT_FAMILY, size=10, weight="bold")
        self.f_cell = tkfont.Font(family=FONT_FAMILY, size=11, weight="bold")
        self.f_title = tkfont.Font(family=FONT_FAMILY, size=13, weight="bold")
        self.f_mono = tkfont.Font(family="Consolas", size=9)

        root = self.root
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # ---- 左侧：画布 ----
        self.k = self.cell_px / 200.0
        self.cw = int(MAP_PX_W * self.k) + 2 * MARGIN
        self.ch = int(MAP_PX_H * self.k) + 2 * MARGIN
        self.canvas = tk.Canvas(root, width=self.cw, height=self.ch,
                                bg="#ffffff", highlightthickness=0, cursor="hand2")
        self.canvas.grid(row=0, column=0, padx=(12, 6), pady=12)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Button-1>", self.on_click)

        # ---- 右侧：控制面板 ----
        panel = tk.Frame(root, bg="#20242b")
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

        tk.Label(panel, text="避障比赛仿真", bg="#20242b", fg="#e8ecf1",
                 font=self.f_title).pack(anchor="w")
        tk.Label(panel, text="绿色圆 = 小车　黄色 = 禁止通行　棕色 = 障碍物", bg="#20242b",
                 fg="#98a2b3", font=self.f_small).pack(anchor="w", pady=(2, 10))

        self.lbl_mode = tk.Label(panel, text="", bg="#20242b", fg="#4ade80",
                                 font=self.f_bold, justify="left")
        self.lbl_mode.pack(anchor="w")
        self.lbl_status = tk.Label(panel, text="", bg="#20242b", fg="#cbd5e1",
                                   font=self.f_ui, justify="left", wraplength=250)
        self.lbl_status.pack(anchor="w", pady=(4, 0))
        self.lbl_stat = tk.Label(panel, text="", bg="#20242b", fg="#7dd3fc",
                                 font=self.f_small, justify="left")
        self.lbl_stat.pack(anchor="w", pady=(6, 0))

        tk.Frame(panel, bg="#39404d", height=1).pack(fill="x", pady=10)

        # ---- 阶段导航：① 放障碍物 → ② 选目标区域 → ③ 自动仿真 ----
        self.nav = tk.Frame(panel, bg="#20242b")
        self.nav.pack(anchor="w", fill="x")
        self.btn_step1 = self._button(self.nav, "① 障碍物", self.enter_setup)
        self.btn_step1.pack(side="left")
        self.btn_step2 = self._button(self.nav, "② 目标区域", self.enter_targets)
        self.btn_step2.pack(side="left", padx=6)

        # ---- ① 放置障碍物 ----
        self.frm_setup = tk.Frame(panel, bg="#20242b")
        tk.Label(self.frm_setup, text="点格子放置/取消障碍物（1~2 个），或点“随机障碍物”",
                 bg="#20242b", fg="#98a2b3", font=self.f_small,
                 wraplength=250, justify="left").pack(anchor="w", pady=(6, 4))
        r1 = tk.Frame(self.frm_setup, bg="#20242b")
        r1.pack(anchor="w", fill="x")
        self.btn_random = self._button(r1, "随机障碍物", self.randomize_obstacles)
        self.btn_random.pack(side="left")
        self.btn_clear = self._button(r1, "清空", self.clear_obstacle_ui)
        self.btn_clear.pack(side="left", padx=6)
        self.btn_to_targets = self._button(r1, "下一步", self.enter_targets)
        self.btn_to_targets.pack(side="left")
        self.lbl_obs = tk.Label(self.frm_setup, text="", bg="#20242b", fg="#7dd3fc",
                                font=self.f_small, justify="left", wraplength=250)
        self.lbl_obs.pack(anchor="w", pady=(6, 0))

        # ---- ② 选择目标区域（顺序即访问顺序）----
        self.frm_targets = tk.Frame(panel, bg="#20242b")
        tk.Label(self.frm_targets, text="勾选本次要到达的目标区域（顺序 = 跑的顺序）",
                 bg="#20242b", fg="#98a2b3", font=self.f_small,
                 wraplength=250, justify="left").pack(anchor="w", pady=(6, 4))
        self.var_targets = {}
        self.lbl_target = {}
        for key, (name, _color, _mark) in GOAL_INFO.items():
            var = tk.BooleanVar(value=key in self.targets)
            self.var_targets[key] = var
            row = tk.Frame(self.frm_targets, bg="#20242b")
            row.pack(anchor="w", fill="x")
            cb = tk.Checkbutton(row, text=name, variable=var, command=self.on_target_toggle,
                                bg="#20242b", fg="#e8ecf1", selectcolor="#39404d",
                                activebackground="#20242b", activeforeground="#ffffff",
                                font=self.f_ui, anchor="w", highlightthickness=0)
            cb.pack(side="left")
            lbl = tk.Label(row, text="", bg="#20242b", fg="#facc15", font=self.f_small)
            lbl.pack(side="left", padx=4)
            self.lbl_target[key] = lbl
        r3 = tk.Frame(self.frm_targets, bg="#20242b")
        r3.pack(anchor="w", fill="x", pady=(4, 0))
        self.btn_up = self._button(r3, "▲ 提前", lambda: self.move_target(-1))
        self.btn_up.pack(side="left")
        self.btn_down = self._button(r3, "▼ 延后", lambda: self.move_target(1))
        self.btn_down.pack(side="left", padx=6)
        self.btn_plan = self._button(r3, "③ 开始仿真", self.begin_simulation)
        self.btn_plan.pack(side="left")
        self.lbl_plan = tk.Label(self.frm_targets, text="", bg="#20242b", fg="#7dd3fc",
                                 font=self.f_small, justify="left", wraplength=250)
        self.lbl_plan.pack(anchor="w", pady=(6, 0))

        tk.Frame(panel, bg="#39404d", height=1).pack(fill="x", pady=10)

        row = tk.Frame(panel, bg="#20242b")
        row.pack(anchor="w", fill="x")
        tk.Label(row, text="速度", bg="#20242b", fg="#cbd5e1",
                 font=self.f_ui).pack(side="left")
        self.var_speed = tk.DoubleVar(value=1.0)
        tk.Scale(row, from_=0.4, to=3.0, resolution=0.1, orient="horizontal",
                 variable=self.var_speed, bg="#20242b", fg="#cbd5e1",
                 troughcolor="#39404d", highlightthickness=0, length=170,
                 showvalue=False).pack(side="left", padx=6)
        self.lbl_speed = tk.Label(row, text="1.0x", bg="#20242b", fg="#cbd5e1",
                                  font=self.f_small, width=5)
        self.lbl_speed.pack(side="left")
        self.var_speed.trace_add("write", lambda *_: self.lbl_speed.config(
            text="%.1fx" % self.var_speed.get()))

        btns = tk.Frame(panel, bg="#20242b")
        btns.pack(anchor="w", fill="x", pady=(10, 0))
        self.btn_finish = self._button(btns, "结束本次仿真", self.finish)
        self.btn_finish.pack(side="left")
        self._button(btns, "重新开始", self.restart).pack(side="left", padx=6)

        tk.Label(panel, text="行驶记录", bg="#20242b", fg="#e8ecf1",
                 font=self.f_bold).pack(anchor="w", pady=(14, 4))
        box = tk.Frame(panel, bg="#20242b")
        box.pack(fill="both", expand=True)
        self.txt = tk.Text(box, width=38, height=8, bg="#151920", fg="#cbd5e1",
                           font=self.f_mono, relief="flat", wrap="word",
                           insertbackground="#cbd5e1")
        sb = tk.Scrollbar(box, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        self.txt.configure(state="disabled")

        self.lbl_hint = tk.Label(panel, text="", bg="#20242b", fg="#98a2b3",
                                 font=self.f_small, wraplength=250, justify="left")
        self.lbl_hint.pack(anchor="w", pady=(8, 0))

        # 屏幕矮的时候把日志框压矮，保证面板能完整放下
        avail = self.ch - 700
        self.txt.config(height=max(3, min(8, avail // 14)))

    def _button(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, font=self.f_ui,
                         bg="#2f3742", fg="#e8ecf1", activebackground="#3d4757",
                         activeforeground="#ffffff", relief="flat", padx=8, pady=4,
                         cursor="hand2")

    # ------------------------------------------------------------ 坐标换算 --
    def to_canvas(self, x, y):
        return MARGIN + x * self.k, MARGIN + y * self.k

    def cell_at_canvas(self, px, py):
        x, y = (px - MARGIN) / self.k, (py - MARGIN) / self.k
        if x < 0 or y < 0 or x > MAP_PX_W or y > MAP_PX_H:
            return None
        for c in range(1, COLS + 1):
            if X_BOUNDS[c - 1] <= x < X_BOUNDS[c] or (c == COLS and x >= X_BOUNDS[c - 1]):
                for r in range(1, ROWS + 1):
                    if Y_BOUNDS[r - 1] <= y < Y_BOUNDS[r] or (r == ROWS and y >= Y_BOUNDS[r - 1]):
                        return GRID[(r, c)]
        return None

    # ---------------------------------------------------------------- 绘制 --
    def _draw_static(self):
        cv = self.canvas
        cv.delete("all")

        # 画出所有格子（按原图比例）
        for r in range(1, ROWS + 1):
            for c in range(1, COLS + 1):
                cell = GRID[(r, c)]
                x0, y0 = self.to_canvas(cell.x0, cell.y0)
                x1, y1 = self.to_canvas(cell.x1, cell.y1)
                cv.create_rectangle(x0, y0, x1, y1, fill=cell.color,
                                    outline="", tags=("cellbg", "c%d_%d" % (r, c)))
                if cell.goal_name:
                    color = "#20242b" if cell.mark in ("1", "2") else "#ffffff"
                    cv.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                                   text=cell.mark, font=self.f_cell,
                                   fill=color, tags=("celltxt",))
                elif cell.kind == START:
                    cv.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                                   text=cell.mark, font=self.f_cell,
                                   fill="#ffffff", tags=("celltxt",))

        # 黑色网格线
        for x in X_BOUNDS:
            cx, _ = self.to_canvas(x, 0)
            _, cy0 = self.to_canvas(0, 0)
            _, cy1 = self.to_canvas(0, MAP_PX_H)
            cv.create_line(cx, cy0, cx, cy1, fill=C_GRID, width=5, tags=("grid",))
        for y in Y_BOUNDS:
            _, cy = self.to_canvas(0, y)
            cx0, _ = self.to_canvas(0, 0)
            cx1, _ = self.to_canvas(MAP_PX_W, 0)
            cv.create_line(cx0, cy, cx1, cy, fill=C_GRID, width=5, tags=("grid",))

        # 起点/终点提示
        for key in START_CELLS:
            self._ring(key, "#ffffff", 2)
        for key in GOAL_INFO:
            self._ring(key, "#ffd166", 2, dash=(6, 4))

        self.cv_overlay = None
        self.cv_car = None
        self.cv_path = []

    def _ring(self, key, color, width, dash=None):
        cell = GRID[key]
        x0, y0 = self.to_canvas(cell.x0 + 4, cell.y0 + 4)
        x1, y1 = self.to_canvas(cell.x1 - 4, cell.y1 - 4)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=width,
                                     dash=dash, tags=("ring",))

    def _draw_path(self, path, color=C_PATH, width=4, dash=None, clear=True):
        if clear:
            self.canvas.delete("path")
            self.cv_path = []
        pts = []
        for cell in path:
            cx, cy = self.to_canvas(cell.cx, cell.cy)
            pts += [cx, cy]
        if len(pts) >= 4:
            self.cv_path.append(self.canvas.create_line(
                *pts, fill=color, width=width, dash=dash, capstyle="round",
                joinstyle="round", tags=("path",), smooth=False))
        for cell in path:
            cx, cy = self.to_canvas(cell.cx, cell.cy)
            self.cv_path.append(self.canvas.create_oval(
                cx - 5, cy - 5, cx + 5, cy + 5, fill=color, outline="",
                tags=("path",)))

    def _draw_car(self):
        self.canvas.delete("car")
        self.draw_obstacles()
        cx, cy = self.to_canvas(self.car_cell.cx, self.car_cell.cy)
        self.draw_car_at(cx, cy)

    def draw_obstacles(self):
        """画障碍物，以及“放完之后目标不可达”的告警框。"""
        cv = self.canvas
        cv.delete("obs")
        cv.delete("warn")
        for key in self.obstacle_keys:
            cell = GRID[key]
            x0, y0 = self.to_canvas(cell.x0, cell.y0)
            x1, y1 = self.to_canvas(cell.x1, cell.y1)
            cv.create_rectangle(x0, y0, x1, y1, fill=C_OBSTACLE, outline="",
                                tags=("obs",))
            cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="障碍",
                           font=self.f_cell, fill="#ffffff", tags=("obs",))
        # 可达性告警：不可达的目标用红框标出
        _, bad = reachable_goals(self.car_cell.key)
        self.bad_goals = bad
        for name in bad:
            key = next(k for k, (n, _c, _m) in GOAL_INFO.items() if n == name)
            cell = GRID[key]
            x0, y0 = self.to_canvas(cell.x0 + 3, cell.y0 + 3)
            x1, y1 = self.to_canvas(cell.x1 - 3, cell.y1 - 3)
            cv.create_rectangle(x0, y0, x1, y1, outline=C_BAD, width=4,
                                dash=(4, 3), tags=("warn",))
        self.canvas.tag_raise("grid")
        self.canvas.tag_raise("ring")
        self.canvas.tag_raise("hover")
        self.canvas.tag_raise("path")
        self.canvas.tag_raise("car")

    def draw_car_at(self, cx, cy):
        self.canvas.delete("car")
        g = self.canvas.create_oval(cx - CAR_R, cy - CAR_R, cx + CAR_R, cy + CAR_R,
                                    fill=C_CAR, outline="#0b6b1a", width=3, tags=("car",))
        h = self.canvas.create_oval(cx - CAR_R * 0.4, cy - CAR_R * 0.4,
                                    cx + CAR_R * 0.4, cy + CAR_R * 0.4,
                                    fill="#e9fff0", outline="", tags=("car",))
        return g, h

    # ---------------------------------------------------------------- 交互 --
    def status(self, text):
        self.lbl_status.config(text=text)

    # ------------------------------------------------- 阶段①：放置障碍物 --
    def enter_setup(self, first=False):
        """进入比赛准备①：放置 1~2 个障碍物。"""
        self.phase = "setup"
        self.lbl_mode.config(text="① 放置障碍物", fg="#facc15")
        self.frm_targets.pack_forget()
        self.frm_setup.pack(anchor="w", fill="x", after=self.nav)
        self.btn_random.config(state="normal")
        self.btn_clear.config(state="normal")
        self.btn_step1.config(state="disabled")
        self.btn_step2.config(state="normal")
        self.lbl_hint.config(text="① 点格子放置/取消障碍物（1~2 个）\n"
                                  "② 点“下一步”去勾选目标区域\n"
                                  "③ 点“开始仿真”后小车才出发")
        self._refresh_obstacle_panel()
        if first:
            self.status("比赛准备①：请放置 1~2 个障碍物。\n"
                        "可以自己点格子，也可以点“随机障碍物”模拟比赛随机放置。\n"
                        "另一个蓝色出发点已视为普通路径，也可以放障碍物。")

    def _refresh_obstacle_panel(self):
        n = len(self.obstacle_keys)
        self.lbl_obs.config(text="已放置障碍物：%d 个（上限 %d）" % (n, self.MAX_OBSTACLES))
        _, bad = reachable_goals(self.car_cell.key)
        if bad:
            self.lbl_obs.config(
                text="已放置 %d 个障碍物 ⚠ 目标不可达：%s\n请调整障碍物后再继续"
                     % (n, "、".join(bad)),
                fg=C_BAD)
            self.btn_to_targets.config(state="disabled")
            self.status("⚠ 这样摆放会让 %s 走不到！\n请取消或换一个障碍物位置。"
                        % "、".join(bad))
        else:
            self.lbl_obs.config(
                text="已放置障碍物：%d 个　目标全部可达 ✔" % n, fg="#7dd3fc")
            self.btn_to_targets.config(state="normal" if n >= 1 else "disabled")
            if n == 0:
                self.status("请至少放置 1 个障碍物（或点“随机障碍物”）。")
            else:
                self.status("已放置 %d 个障碍物，目标全部可达。\n"
                            "点“下一步”去勾选目标区域。" % n)

    def toggle_obstacle(self, cell):
        if cell.key in self.obstacle_keys:
            self.obstacle_keys.remove(cell.key)
            cell.obstacle = False
            self.log("取消障碍物：%s" % cell.name)
        elif cell.can_hold_obstacle:
            if len(self.obstacle_keys) >= self.MAX_OBSTACLES:
                self.status("最多只能放 %d 个障碍物。\n先取消一个，或点“随机障碍物”重新随机。"
                            % self.MAX_OBSTACLES)
                return
            cell.obstacle = True
            self.obstacle_keys.append(cell.key)
            self.log("放置障碍物：%s" % cell.name)
        else:
            self.status("%s 不能放障碍物：\n黄色禁行区和四个目标区域都不允许。"
                        % cell.name)
            return
        self._draw_car()
        self._refresh_obstacle_panel()

    def randomize_obstacles(self):
        keys, msg = random_obstacles(self.car_cell.key)
        self.obstacle_keys = keys
        self._draw_car()
        self._refresh_obstacle_panel()
        self.log("🎲 " + msg)
        if keys:
            self.status("🎲 %s\n目标全部可达。可以再换一组，或点“下一步”勾选目标区域。" % msg)
        else:
            self.status("随机放置失败：%s" % msg)

    def clear_obstacle_ui(self):
        clear_obstacles()
        self.obstacle_keys = []
        self._draw_car()
        self._refresh_obstacle_panel()
        self.log("已清空障碍物")

    # --------------------------------------------------- 阶段②：选择目标 --
    def enter_targets(self):
        """进入比赛准备②：勾选本次要到达的目标区域（顺序即访问顺序）。"""
        if self.phase == "setup":
            _, bad = reachable_goals(self.car_cell.key)
            if not self.obstacle_keys:
                self.status("请先放 1~2 个障碍物（或点“随机障碍物”），再选目标区域。")
                return
            if bad:
                self.status("⚠ 当前障碍物会让 %s 走不到，请先调整障碍物。" % "、".join(bad))
                return
        self.phase = "targets"
        self.lbl_mode.config(text="② 选择目标区域", fg="#facc15")
        self.frm_setup.pack_forget()
        self.frm_targets.pack(anchor="w", fill="x", after=self.nav)
        self.btn_step1.config(state="normal")
        self.btn_step2.config(state="disabled")
        self.lbl_hint.config(text="① 勾选需要到达的目标区域\n"
                                  "② “▲ 提前 / ▼ 延后”调整访问顺序\n"
                                  "③ 点“开始仿真”自动跑完全程并回到出发点")
        self._refresh_target_panel()
        self.status("比赛准备②：勾选本次要到达的目标区域。\n"
                    "勾选先后决定访问顺序，也可以用“▲ 提前 / ▼ 延后”调整。")

    def _refresh_target_panel(self):
        # 每个目标显示它在访问顺序里的序号
        for i, key in enumerate(self.targets):
            self.lbl_target[key].config(text="第 %d 个" % (i + 1))
        for key in GOAL_INFO:
            if key not in self.targets:
                self.lbl_target[key].config(text="不前往")
        if not self.targets:
            self.lbl_plan.config(text="还没有勾选目标区域（至少选 1 个）", fg=C_BAD)
            self.btn_plan.config(state="disabled")
            return

        self.btn_plan.config(state="normal")
        segments, info = build_plan(self.car_cell.key, self.targets)
        if info.get("error"):
            self.lbl_plan.config(text="⚠ %s\n请回上一步调整障碍物" % info["error"], fg=C_BAD)
            self.btn_plan.config(state="disabled")
            self.status("⚠ %s" % info["error"])
            return
        self.plan, self.plan_info = segments, info
        self.lbl_plan.config(
            text="访问顺序：%s\n预计总里程：%d 步（%d 段）"
                 % (target_selection_text(self.targets), info["total_steps"], info["segments"]),
            fg="#7dd3fc")
        self.status("已选 %d 个目标：%s\n点“③ 开始仿真”后小车会一次跑完并回到出发点。"
                    % (len(self.targets), target_selection_text(self.targets)))
        self._draw_plan_preview()

    def on_target_toggle(self, *_):
        """勾选框变化 → 更新目标集合与访问顺序。"""
        for key, var in self.var_targets.items():
            on = bool(var.get())
            if on and key not in self.targets:
                self.targets.append(key)          # 后勾选的排在后面
                self.log("目标区域加入计划：%s" % GRID[key].name)
            elif not on and key in self.targets:
                self.targets.remove(key)
                self.log("目标区域移出计划：%s" % GRID[key].name)
        self._refresh_target_panel()

    def move_target(self, delta):
        """把选中的某个目标在访问顺序里提前/延后。"""
        if len(self.targets) < 2:
            self.status("至少要选 2 个目标才能调顺序。")
            return
        # 用当前焦点/最简单的方式：按列表顺序整体轮转，便于快速调整
        self.targets = self.targets[delta:] + self.targets[:delta]
        self.log("访问顺序调整为：%s" % target_selection_text(self.targets))
        self._refresh_target_panel()

    def _draw_plan_preview(self):
        """把整段计划用黄色虚线一次性画在地图上。"""
        self.canvas.delete("preview")
        for i, seg in enumerate(self.plan):
            before = len(self.canvas.find_all())
            self._draw_path(seg, color="#facc15" if i % 2 == 0 else "#ffa53b",
                            width=3, dash=(5, 4), clear=False)
            for item in self.canvas.find_all()[before:]:
                self.canvas.addtag_withtag("preview", item)

    # ------------------------------------------------- 阶段③：自动连跑 --
    def begin_simulation(self):
        """按设定好的目标顺序开始仿真：依次到达各目标，最后回到出发点。"""
        if self.phase == "run":
            return
        if self.phase == "setup":
            self.status("请先勾选要到达的目标区域（点“② 目标区域”）。")
            return
        if not self.obstacle_keys:
            self.status("请至少放置 1 个障碍物再开始（点“① 障碍物”）。")
            return

        for key in self.targets:                 # 先检查每个目标自己能不能进
            if not GRID[key].passable:
                self.status("⚠ %s 被障碍物占住了，请调整。" % GRID[key].name)
                return

        segments, info = build_plan(self.car_cell.key, self.targets)
        if info.get("error"):
            self.status("⚠ %s\n请回上一步调整障碍物或目标。" % info["error"])
            return

        self.plan, self.plan_info = segments, info
        self.plan_idx = 0
        self.phase = "run"
        self.canvas.delete("preview")
        self.btn_random.config(state="disabled")
        self.btn_clear.config(state="disabled")
        self.btn_to_targets.config(state="disabled")
        self.btn_plan.config(state="disabled")
        self.btn_up.config(state="disabled")
        self.btn_down.config(state="disabled")
        self.btn_step1.config(state="disabled")
        self.btn_step2.config(state="disabled")
        self.btn_finish.config(state="disabled")
        self.lbl_mode.config(text="③ 自动仿真中……", fg="#facc15")
        self.lbl_hint.config(text="小车正在按计划依次到达各目标，最后回到出发点")
        self.log("—— 开始仿真 ——")
        self.log("出发点：%s　障碍物：%s"
                 % (self.car_cell.name,
                    "、".join(GRID[k].name for k in self.obstacle_keys) or "无"))
        self.log("访问顺序：%s" % target_selection_text(self.targets))
        for line in plan_text(segments, info).split("\n"):
            self.log(line)
        self.status("比赛开始！\n访问顺序：%s\n预计 %d 步，最后回到出发点。"
                    % (target_selection_text(self.targets), info["total_steps"]))
        self.update_stat()
        self.root.after(300, self.run_next_segment)

    def run_next_segment(self):
        """跑计划的下一段；跑完就回出发点并结束。"""
        if self.finished or self.phase != "run":
            return
        if self.plan_idx >= len(self.plan):
            self.status("所有目标都到过了，正在返回出发点……")
            return

        seg = self.plan[self.plan_idx]
        dest = seg[-1]
        is_last_target = self.plan_idx == len(self.plan) - 1
        self.log("▶ 第 %d/%d 段：%s → %s（%d 步）"
                 % (self.plan_idx + 1, len(self.plan), seg[0].name, dest.name, len(seg) - 1))
        self.status("第 %d/%d 段：驶向 %s%s"
                    % (self.plan_idx + 1, len(self.plan), dest.name,
                       "（最后一段，跑完回出发点）" if is_last_target else ""))
        self.start_move(dest, auto=True)

    def on_plan_segment_done(self, dest):
        """一段跑完：记录到达，然后继续下一段。"""
        if self.finished:
            return
        self.plan_idx += 1
        if self.plan_idx >= len(self.plan):
            self.return_to_start()
        else:
            self.root.after(250, self.run_next_segment)

    def return_to_start(self):
        """所有目标跑完，回到出发点并结束。"""
        if self.finished:
            return
        if self.car_cell.key == self.start_key:
            self.finish()
            return
        self.log("↩ 返回出发点 %s" % self.car_cell.name.replace(self.car_cell.name, "")
                 + GRID[self.start_key].name)
        self.status("所有目标都到过了，正在返回出发点……")
        self.lbl_mode.config(text="返回出发点……", fg="#facc15")
        self.start_move(GRID[self.start_key], returning=True)

    # ---------------------------------------------------------------- 交互 --
    def update_stat(self):
        obs = len(self.obstacle_keys)
        self.lbl_stat.config(text="已走格子数：%d　障碍物：%d\n已到达目标：%s"
                                  % (self.steps, obs,
                                     "、".join(self.visited_goals) if self.visited_goals else "无"))

    def log(self, text):
        self.txt.configure(state="normal")
        self.txt.insert("end", text + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def on_motion(self, event):
        if self.finished:
            return
        cell = self.cell_at_canvas(event.x, event.y)
        key = cell.key if cell else None
        if key == self.hover_key:
            return
        self.hover_key = key
        self.canvas.delete("hover")
        self.canvas.delete("preview")
        self.preview_path = []

        if cell is None:
            self.canvas.config(cursor="arrow")
            return

        # ---- 准备阶段：鼠标在提示可以/不可以放障碍物 ----
        if self.phase == "setup":
            if cell.key in self.obstacle_keys:
                self.canvas.config(cursor="hand2")
                self._highlight(cell, "#ffd166")
                self.status("点一下取消这个障碍物（%s）" % cell.name)
            elif cell.can_hold_obstacle:
                self.canvas.config(cursor="hand2")
                self._highlight(cell, "#f0a020")
                self.status("点一下在这里放障碍物（%s）" % cell.name)
            else:
                self.canvas.config(cursor="X_cursor")
                self._highlight(cell, "#ff5c5c")
                self.status("%s 不允许放障碍物" % cell.name)
            return

        # ---- 目标区域阶段：鼠标只做说明，勾选在右侧面板 ----
        if self.phase == "targets":
            if cell.goal_name:
                self.canvas.config(cursor="hand2")
                order = self.targets.index(cell.key) + 1 if cell.key in self.targets else 0
                self._highlight(cell, "#4ade80" if order else "#8aa0b8")
                self.status("%s：%s\n在右侧勾选框里选择是否前往。"
                            % (cell.name, "第 %d 个访问" % order if order else "当前不在计划内"))
            else:
                self.canvas.config(cursor="arrow")
                self._highlight(cell, "#8aa0b8") if cell.passable else None
                self.status("本次只需前往勾选的目标区域")
            return

        # ---- 仿真阶段：鼠标只做说明 ----
        if self.phase == "run":
            self.canvas.config(cursor="watch")
            self._highlight(cell, "#8aa0b8")
            self.status("小车正在按计划行驶，请稍候……\n访问顺序：%s"
                        % target_selection_text(self.targets))
            return

        if not cell.passable:
            self.canvas.config(cursor="X_cursor")
            self._highlight(cell, "#ff5c5c")
            self.status("该格子不可通行")
            return

    def _highlight(self, cell, color):
        x0, y0 = self.to_canvas(cell.x0 + 3, cell.y0 + 3)
        x1, y1 = self.to_canvas(cell.x1 - 3, cell.y1 - 3)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=4,
                                     tags=("hover",))

    def on_leave(self, _event):
        self.hover_key = None
        self.canvas.delete("hover")
        self.canvas.delete("preview")
        self.preview_path = []
        if self.finished or self.phase == "run":
            return
        if self.phase == "setup":
            self._refresh_obstacle_panel()
        elif self.phase == "targets":
            self._refresh_target_panel()

    def on_click(self, event):
        if self.finished or self.phase == "run":
            return
        cell = self.cell_at_canvas(event.x, event.y)
        if cell is None:
            return

        if self.phase == "setup":
            self.toggle_obstacle(cell)
            return
        # 目标区域阶段：勾选在右侧面板里做
        if self.phase == "targets":
            self.status("请在右侧勾选框中选择目标区域（勾选先后决定访问顺序）。")

    # ---------------------------------------------------------------- 运动 --
    def start_move(self, target, returning=False, auto=False):
        """规划并开始行驶到 target。

        returning=True —— 这是“回出发点”的最后一段，到站后结束仿真；
        auto=True      —— 自动连跑模式，到站后继续下一段（由 on_plan_segment_done 接手）。
        """
        if target.key == self.car_cell.key:
            # 已经站在目标格上
            if returning:
                self.finish()
            elif auto:
                self.on_plan_segment_done(target)
            else:
                self.on_arrive(target)
            return

        path, err = shortest_path(self.car_cell.key, target.key)
        if err:
            self.log("无法到达 %s：%s" % (target.name, err))
            self.status("无法到达：%s" % err)
            return

        self.canvas.delete("path")
        self.canvas.delete("hover")
        self.canvas.delete("preview")
        self.preview_path = []

        # 显示规划出的最短路径
        self._draw_path(path, color=C_PATH, width=4)
        self.log("规划路径 %s → %s：%s" % (self.car_cell.name, target.name, path_text(path)))
        self.log("  经过 %d 个格子，需要行驶 %d 步%s"
                 % (len(path), len(path) - 1,
                    "（已绕开 %d 个障碍物）" % len(self.obstacle_keys)
                    if self.obstacle_keys else ""))

        self.phase = "run" if (auto or self.phase == "run") else "move"
        self.lbl_mode.config(text="返回出发点……" if returning else
                             ("自动仿真中……" if auto else "行驶中……"), fg="#facc15")
        self.status("正在返回出发点 %s，到达后本次仿真结束" % target.name if returning
                    else ("第 %d/%d 段：驶向 %s" % (self.plan_idx + 1, len(self.plan), target.name)
                          if auto else "正在驶向 %s" % target.name))
        self.move = {
            "path": path, "idx": 1, "from": path[0], "to": path[1],
            "t0": None, "cell_sec": STEP_SECONDS,
            "returning": returning, "auto": auto,
        }
        self._last = None
        self.root.after(16, self.tick)

    def tick(self):
        mv = self.move
        if mv is None or self.finished:
            return
        import time
        now = time.perf_counter()
        if mv["t0"] is None:
            mv["t0"] = now
        cell_sec = mv["cell_sec"] / max(0.1, self.var_speed.get())
        u = min(1.0, (now - mv["t0"]) / cell_sec)

        a, b = mv["from"], mv["to"]
        ax, ay = self.to_canvas(a.cx, a.cy)
        bx, by = self.to_canvas(b.cx, b.cy)
        self.draw_car_at(ax + (bx - ax) * u, ay + (by - ay) * u)

        if u >= 1.0:
            arrived = mv["to"]
            self.car_cell = arrived
            self.trail.append(arrived.key)
            self.steps += 1
            self.update_stat()
            mv["idx"] += 1
            if mv["idx"] >= len(mv["path"]):
                self.move = None
                if mv.get("returning"):
                    # 车已经停在出发点格心，再结束仿真
                    self._draw_car()
                    self.finish()
                elif mv.get("auto"):
                    # 自动连跑：记录到达后继续下一段
                    self._draw_car()
                    self.on_plan_segment_done(arrived)
                else:
                    self.on_arrive(arrived)
                return
            mv["from"], mv["to"] = arrived, mv["path"][mv["idx"]]
            mv["t0"] = now

        self.root.after(16, self.tick)

    def on_arrive(self, cell):
        """手动模式的到达处理（保留给外部脚本/调试使用）。"""
        self._draw_car()
        hit = cell.goal_name
        if hit:
            if hit not in self.visited_goals:
                self.visited_goals.append(hit)
            self.log("★ 已到达目标地点：%s" % hit)
        else:
            self.log("已到达 %s（非目标地点）" % cell.name)
        self.phase = "targets"
        self.lbl_mode.config(text="② 选择目标区域", fg="#4ade80")
        self.status("已到达 %s。" % cell.name)
        self.update_stat()

    def on_plan_segment_done(self, dest):
        """自动连跑模式：一段跑完，记录到达并继续下一段。"""
        hit = dest.goal_name
        if hit:
            if hit not in self.visited_goals:
                self.visited_goals.append(hit)
            self.log("★ 第 %d/%d 段完成，已到达：%s"
                     % (self.plan_idx + 1, len(self.plan), hit))
        else:
            self.log("第 %d/%d 段完成，停在 %s"
                     % (self.plan_idx + 1, len(self.plan), dest.name))
        self.update_stat()
        self.plan_idx += 1
        if self.plan_idx >= len(self.plan):
            self.root.after(350, self.return_to_start)
        else:
            self.root.after(350, self.run_next_segment)

    # ------------------------------------------------------------ 结束/重来 --
    def finish(self):
        """结束本次仿真。

        正常流程是小车先开回出发点（`tick` 到站后调用这里），此时车就停在出发点格心；
        “结束本次仿真”按钮可以直接结束，不要求小车在出发点。
        """
        if self.finished:
            return
        self.finished = True
        self.phase = "done"
        self.move = None
        self.canvas.delete("path")
        self.canvas.delete("hover")
        self.canvas.delete("preview")
        self.canvas.delete("car")
        self._draw_car()
        self.lbl_mode.config(text="仿真结束", fg="#f87171")
        self.btn_finish.config(state="disabled")
        self.update_stat()

        at_start = self.car_cell.key == self.start_key
        visited = set(self.visited_goals)
        planned = [GRID[k].goal_name for k in self.targets]
        missing = [n for n in planned if n not in visited]
        summary = ("出发点：%s\n障碍物：%s\n计划访问：%s\n行驶格数：%d\n小车位置：%s\n"
                   "已到达目标：%s\n未到达目标：%s"
                   % (GRID[self.start_key].name,
                      "、".join(GRID[k].name for k in self.obstacle_keys)
                      if self.obstacle_keys else "无",
                      "、".join(planned) if planned else "无",
                      self.steps,
                      GRID[self.start_key].name if at_start else
                      "%s（未回到出发点）" % self.car_cell.name,
                      "、".join(self.visited_goals) if self.visited_goals else "无",
                      "、".join(missing) if missing else "无"))
        if at_start:
            self.log("—— 小车已回到出发点，本次仿真结束 ——")
        else:
            self.log("—— 本次仿真结束（小车停在 %s，未回到出发点）——" % self.car_cell.name)
        for line in summary.split("\n"):
            self.log("   " + line)
        self.status(summary)

        self._end_dialog(summary)

    def _end_dialog(self, summary):
        win = tk.Toplevel(self.root)
        win.title("仿真结束")
        win.configure(bg="#20242b")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="本次仿真结束", bg="#20242b", fg="#f87171",
                 font=self.f_title).pack(padx=24, pady=(18, 6))
        tk.Label(win, text=summary, bg="#20242b", fg="#e8ecf1", font=self.f_ui,
                 justify="left").pack(padx=24, pady=(0, 14))
        row = tk.Frame(win, bg="#20242b")
        row.pack(pady=(0, 18))
        self._button(row, "重新开始", lambda: (win.destroy(), self.restart())).pack(side="left")
        self._button(row, "关闭", lambda: (win.destroy(), self.root.destroy())).pack(side="left", padx=8)

    def restart(self):
        self.root.destroy()
        main()


# ----------------------------------------------------------------------------
# 4. 出发点选择弹窗
# ----------------------------------------------------------------------------

BLUE = "#0b02cb"
YELLOW = "#f0d000"


class StartDialog:
    """弹出地图，让用户点击蓝色格子选择出发点。"""

    def __init__(self, root):
        self.root = root
        self.choice = None

        self.top = tk.Toplevel(root)
        self.top.title("选择出发点")
        self.top.configure(bg="#20242b")
        self.top.transient(root)
        self.top.protocol("WM_DELETE_WINDOW", self._cancel)

        f_title = tkfont.Font(family=FONT_FAMILY, size=13, weight="bold")
        f_ui = tkfont.Font(family=FONT_FAMILY, size=10)
        f_small = tkfont.Font(family=FONT_FAMILY, size=9)
        f_cell = tkfont.Font(family=FONT_FAMILY, size=12, weight="bold")

        tk.Label(self.top, text="请用鼠标点击一个蓝色正方形作为出发点",
                 bg="#20242b", fg="#e8ecf1", font=f_title).pack(padx=22, pady=(18, 2))
        tk.Label(self.top, text="两个蓝色格子出发点是等价的，比赛时随机二选一",
                 bg="#20242b", fg="#98a2b3", font=f_small).pack(pady=(0, 10))

        k = 480.0 / MAP_PX_W
        w, h = int(MAP_PX_W * k), int(MAP_PX_H * k)
        self.k, self.margin = k, 10
        self.canvas = tk.Canvas(self.top, width=w + 20, height=h + 20,
                                bg="#ffffff", highlightthickness=0, cursor="hand2")
        self.canvas.pack(padx=22)
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda e: (self.canvas.delete("hover"),
                                               self.lbl.config(text="请点击蓝色格子")))

        self.lbl = tk.Label(self.top, text="请点击蓝色格子", bg="#20242b",
                            fg="#7dd3fc", font=f_ui)
        self.lbl.pack(pady=(10, 0))
        tk.Button(self.top, text="取消", command=self._cancel, font=f_ui,
                  bg="#2f3742", fg="#e8ecf1", relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(pady=(6, 16))

        self.f_cell = f_cell
        self._draw()
        # 画面就绪后再抓输入焦点（不要用 wait_visibility，主窗口不可见时会死等）
        self.top.update_idletasks()
        self.top.after_idle(self._activate)

    def _activate(self):
        """弹窗真正显示后再设置模态抓取，并确保它被带到前台。"""
        try:
            if self.top.winfo_viewable():
                self.top.grab_set()
        except tk.TclError:
            pass
        try:
            self.top.lift()
            self.top.focus_force()
        except tk.TclError:
            pass

    def _tc(self, x, y):
        return self.margin + x * self.k, self.margin + y * self.k

    def _draw(self):
        cv = self.canvas
        for r in range(1, ROWS + 1):
            for c in range(1, COLS + 1):
                cell = GRID[(r, c)]
                x0, y0 = self._tc(cell.x0, cell.y0)
                x1, y1 = self._tc(cell.x1, cell.y1)
                cv.create_rectangle(x0, y0, x1, y1, fill=cell.color, outline="")
                if cell.kind == START:
                    cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=cell.mark,
                                   font=self.f_cell, fill="#ffffff")
                elif cell.goal_name and cell.mark in ("1", "2"):
                    cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=cell.mark,
                                   font=self.f_cell, fill="#20242b")
        for x in X_BOUNDS:
            cx, _ = self._tc(x, 0)
            _, cy0 = self._tc(0, 0)
            _, cy1 = self._tc(0, MAP_PX_H)
            cv.create_line(cx, cy0, cx, cy1, fill=C_GRID, width=4)
        for y in Y_BOUNDS:
            _, cy = self._tc(0, y)
            cx0, _ = self._tc(0, 0)
            cx1, _ = self._tc(MAP_PX_W, 0)
            cv.create_line(cx0, cy, cx1, cy, fill=C_GRID, width=4)
        for key in START_CELLS:
            self._ring(key, "#ffffff", 2)

    def _ring(self, key, color, width):
        cell = GRID[key]
        x0, y0 = self._tc(cell.x0 + 3, cell.y0 + 3)
        x1, y1 = self._tc(cell.x1 - 3, cell.y1 - 3)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=width,
                                     tags=("ring",))

    def _cell_at(self, px, py):
        x, y = (px - self.margin) / self.k, (py - self.margin) / self.k
        for r in range(1, ROWS + 1):
            for c in range(1, COLS + 1):
                cell = GRID[(r, c)]
                if cell.x0 <= x < cell.x1 and cell.y0 <= y < cell.y1:
                    return cell
        return None

    def _motion(self, event):
        cell = self._cell_at(event.x, event.y)
        self.canvas.delete("hover")
        if cell is None:
            return
        if cell.kind == START:
            self.canvas.config(cursor="hand2")
            self.lbl.config(text="点击选定：%s" % cell.name)
            x0, y0 = self._tc(cell.x0 + 3, cell.y0 + 3)
            x1, y1 = self._tc(cell.x1 - 3, cell.y1 - 3)
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="#4ade80",
                                         width=4, tags=("hover",))
        else:
            self.canvas.config(cursor="X_cursor")
            self.lbl.config(text="只能选择蓝色正方形作为出发点")

    def _click(self, event):
        cell = self._cell_at(event.x, event.y)
        if cell is None or cell.kind != START:
            self.lbl.config(text="请点击蓝色正方形！", fg="#f87171")
            return
        self.choice = cell.key
        self.top.destroy()

    def _cancel(self):
        self.choice = None
        self.top.destroy()


# ----------------------------------------------------------------------------
# 5. 启动
# ----------------------------------------------------------------------------

def open_start_dialog():
    """弹出出发点选择窗口，返回选中的格子坐标（取消则返回 None）。

    注意：不能在建 Toplevel 之前把 root withdraw 掉 —— Tk 在 Windows 上会让
    “master 不可见的 transient 窗口”保持 withdrawn，出发点弹窗就永远不显示。
    所以这里先把 root 做成透明无边框的临时窗口顶一下，弹窗显示后再收起。
    """
    root = tk.Tk()
    root.overrideredirect(True)
    try:
        root.attributes("-alpha", 0.0)
    except tk.TclError:
        pass
    root.geometry("1x1+-100+-100")
    root.update()

    dlg = StartDialog(root)
    root.wait_window(dlg.top)
    root.withdraw()              # 弹窗已显示，把临时 root 收起来
    choice = dlg.choice
    root.destroy()
    return choice


def main():
    choice = open_start_dialog()
    if choice is None:
        return
    win = tk.Tk()
    Simulator(win, choice)
    win.mainloop()


if __name__ == "__main__":
    main()
