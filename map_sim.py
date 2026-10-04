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
    白格子   (r5c1) ................ 目标地点：白色区域 1
    白格子   (r5c3) ................ 目标地点：白色区域 2
    其余格子 ....................... 可通行（白色区域）

任务流程：
    选择出发点 -> 选择目标地点 -> 小车用最短路径行驶过去 -> 再选下一个目标
    -> …… -> 用户点回出发点，本次仿真结束。

路径规划：BFS（广度优先搜索）在 5x5 格子图上求最短路径，以“走过的格子数”
          作为距离度量，黄色禁止通行格子不可进入。

运行：  python map_sim.py
"""

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
C_FLOOR = "#c6c7c1"      # 可通行区域（原图浅灰白）
C_WALL = "#f0d000"       # 禁止通行（黄）
C_START = "#0b02cb"      # 出发点（蓝）
C_GOAL_RED = "#eb0301"   # 红色目标
C_GRID = "#111111"       # 网格黑线
C_CAR = "#18c832"        # 小车（绿）
C_PATH = "#0e7a1e"       # 规划路径

# 特殊格子标注
START_CELLS = [(1, 5), (5, 5)]                       # (行, 列)，从 1 开始
WALL_CELLS = [(2, 2), (2, 4), (4, 2), (4, 4)]
GOAL_INFO = {
    (1, 3): ("红色区域", C_GOAL_RED, "红"),
    (5, 1): ("白色区域1", C_FLOOR, "1"),
    (5, 3): ("白色区域2", C_FLOOR, "2"),
}


class Cell:
    """一个格子。"""

    def __init__(self, r, c):
        self.r = r                      # 行号 1..5
        self.c = c                      # 列号 1..5
        self.kind = FLOOR
        self.color = C_FLOOR
        self.goal_name = None           # 目标地点名称
        self.mark = ""                  # 格子内显示的字符
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
        return self.kind != WALL

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

    return grid


GRID = build_grid()

# ----------------------------------------------------------------------------
# 2. 路径规划：BFS 最短路（4 邻域，黄色格子禁行）
# ----------------------------------------------------------------------------

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]   # 上 下 左 右


def neighbors(cell):
    for dr, dc in DIRS:
        nxt = GRID.get((cell.r + dr, cell.c + dc))
        if nxt is not None and nxt.passable:
            yield nxt


def shortest_path(start_key, goal_key):
    """BFS 求最短路径。

    返回 (路径格子列表, 说明信息)。列表含起点与终点；
    若不可达则返回 ([], 原因)。
    """
    s, t = GRID.get(start_key), GRID.get(goal_key)
    if s is None or t is None:
        return [], "格子不存在"
    if not s.passable or not t.passable:
        return [], "起点或终点位于禁止通行区域"
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
        return [], "目标不可达"

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
# 3. 仿真界面
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
    def __init__(self, root, start_key):
        self.root = root
        self.start_key = start_key
        self.car_cell = GRID[start_key]
        self.cell_px = cell_px_for_screen(root)

        self.mode = "select"          # "move" 行驶中 / "select" 等待选择
        self.move = None              # 当前移动状态
        self.trail = [start_key]      # 走过的格子
        self.steps = 0                # 已走格子数
        self.visited_goals = []       # 已到达过的目标地点
        self.hover_key = None
        self.preview_path = []
        self.finished = False

        self._build_ui()
        self._draw_static()
        self._draw_car()
        self.log("出发点：%s（蓝色格子）" % self.car_cell.name)
        self.log("请点击地图上的目标格子（红色区域 / 白色区域1 / 白色区域2）")
        self.status("请选择目标地点")

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
        tk.Label(panel, text="绿色圆 = 小车　　黄色 = 禁止通行", bg="#20242b",
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
        self._button(btns, "结束本次仿真", self.finish).pack(side="left")
        self._button(btns, "重新选择出发点", self.restart).pack(side="left", padx=6)

        tk.Label(panel, text="行驶记录", bg="#20242b", fg="#e8ecf1",
                 font=self.f_bold).pack(anchor="w", pady=(14, 4))
        box = tk.Frame(panel, bg="#20242b")
        box.pack(fill="both", expand=True)
        self.txt = tk.Text(box, width=38, height=14, bg="#151920", fg="#cbd5e1",
                           font=self.f_mono, relief="flat", wrap="word",
                           insertbackground="#cbd5e1")
        sb = tk.Scrollbar(box, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        self.txt.configure(state="disabled")

        tk.Label(panel, text="左键点击格子选择；点击出发点所在格子即结束仿真",
                 bg="#20242b", fg="#98a2b3", font=self.f_small,
                 wraplength=250, justify="left").pack(anchor="w", pady=(8, 0))

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
        cx, cy = self.to_canvas(self.car_cell.cx, self.car_cell.cy)
        self.draw_car_at(cx, cy)

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

    def update_stat(self):
        self.lbl_stat.config(text="已走格子数：%d　　到达目标：%s"
                                  % (self.steps,
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

        if cell.key == self.start_key:
            self.canvas.config(cursor="hand2")
            self._highlight(cell, "#ffd166")
            self.status("点击此处 → 结束本次仿真（回到出发点）")
            return

        if not cell.passable:
            self.canvas.config(cursor="X_cursor")
            self._highlight(cell, "#ff5c5c")
            self.status("黄色区域禁止通行，不能作为目标")
            return

        if self.mode == "move":
            self.canvas.config(cursor="watch")
            self._highlight(cell, "#8aa0b8")
            self.status("小车正在行驶，请稍候……")
            return

        # 预览最短路径
        self.canvas.config(cursor="hand2")
        self._highlight(cell, "#4ade80")
        path, err = shortest_path(self.car_cell.key, cell.key)
        if err:
            self.status("%s：%s" % (cell.name, err))
            return
        self.preview_path = path
        self._draw_path(path, color="#facc15", width=3, dash=(5, 4))
        self.status("%s\n最短路径：经过 %d 个格子（含起终点）\n%s"
                    % (cell.name, len(path), path_text(path)))

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
        if self.mode == "select" and not self.finished:
            self.status("请选择目标地点")

    def on_click(self, event):
        if self.finished or self.mode != "select":
            return
        cell = self.cell_at_canvas(event.x, event.y)
        if cell is None or not cell.passable:
            return

        if cell.key == self.start_key:
            self.finish()
            return
        self.start_move(cell)

    # ---------------------------------------------------------------- 运动 --
    def start_move(self, target):
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
        self.log("  经过 %d 个格子，需要行驶 %d 步" % (len(path), len(path) - 1))

        if len(path) == 1:
            self.on_arrive(target)
            return

        self.mode = "move"
        self.lbl_mode.config(text="行驶中……", fg="#facc15")
        self.status("正在驶向 %s" % target.name)
        self.move = {
            "path": path, "idx": 1, "from": path[0], "to": path[1],
            "t0": None, "cell_sec": STEP_SECONDS,
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
                self.on_arrive(arrived)
                return
            mv["from"], mv["to"] = arrived, mv["path"][mv["idx"]]
            mv["t0"] = now

        self.root.after(16, self.tick)

    def on_arrive(self, cell):
        self._draw_car()
        hit = cell.goal_name
        if hit:
            if hit not in self.visited_goals:
                self.visited_goals.append(hit)
            self.log("★ 已到达目标地点：%s" % hit)
        else:
            self.log("已到达 %s（非目标地点）" % cell.name)

        self.mode = "select"
        self.lbl_mode.config(text="等待选择", fg="#4ade80")
        self.status("已到达 %s。\n请选择下一个目标地点（或点击出发点结束仿真）" % cell.name)
        self.update_stat()
        self.canvas.config(cursor="hand2")

    # ------------------------------------------------------------ 结束/重来 --
    def finish(self):
        if self.finished:
            return
        self.finished = True
        self.move = None
        self.canvas.delete("path")
        self.canvas.delete("hover")
        self.canvas.delete("preview")
        self.canvas.delete("car")
        self._draw_car()
        self.lbl_mode.config(text="仿真结束", fg="#f87171")
        self.update_stat()

        visited = set(self.visited_goals)
        all_goals = set(name for name, _c, _m in GOAL_INFO.values())
        missing = all_goals - visited
        summary = ("出发点：%s\n行驶格数：%d\n到达过的目标：%s\n未到达的目标：%s"
                   % (GRID[self.start_key].name, self.steps,
                      "、".join(self.visited_goals) if self.visited_goals else "无",
                      "、".join(sorted(missing)) if missing else "无"))
        self.log("—— 本次仿真结束 ——")
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
FLOOR_C = "#c6c7c1"


class StartDialog:
    """弹出地图，让用户点击蓝色格子选择出发点。"""

    def __init__(self, root):
        self.root = root
        self.choice = None

        self.top = tk.Toplevel(root)
        self.top.title("选择出发点")
        self.top.configure(bg="#20242b")
        self.top.transient(root)
        self.top.grab_set()
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

def main():
    root = tk.Tk()
    root.withdraw()

    dlg = StartDialog(root)
    root.wait_window(dlg.top)

    if dlg.choice is None:
        root.destroy()
        return

    root.destroy()
    win = tk.Tk()
    Simulator(win, dlg.choice)
    win.mainloop()


if __name__ == "__main__":
    main()
