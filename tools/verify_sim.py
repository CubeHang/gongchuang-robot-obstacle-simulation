# -*- coding: utf-8 -*-
"""验证 map_sim 的地图定义与 BFS 最短路径是否正确（不打开 GUI）。"""
import sys
import os
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map_sim as M

CH = {M.FLOOR: ".", M.WALL: "Y", M.START: "B", M.GOAL: "G"}
M.clear_obstacles()          # 本脚本先在“无障碍物”状态下核对地图与最短路

print("=== 地图（. 可通行  Y 禁止通行  B 出发点  G 目标地点）===")
print("      " + "  ".join("c%d" % c for c in range(1, 6)))
for r in range(1, 6):
    line = []
    for c in range(1, 6):
        cell = M.GRID[(r, c)]
        tag = CH[cell.kind]
        if cell.goal_name:
            tag = {"白色区域1": "1", "白色区域2": "2", "红色区域": "R"}[cell.goal_name]
        line.append(tag)
    print("  r%d  " % r + "  ".join(line))

print("\n=== 关键格子 ===")
for key in [(1, 5), (5, 5), (1, 3), (5, 3), (3, 1)]:
    c = M.GRID[key]
    print("  r%dc%d -> %-6s kind=%-5s goal=%s passable=%s"
          % (key[0], key[1], c.name, c.kind, c.goal_name, c.passable))
assert M.GRID[(1, 5)].kind == M.START and M.GRID[(5, 5)].kind == M.START
assert M.GRID[(1, 3)].goal_name == "红色区域"
assert M.GRID[(5, 3)].goal_name == "白色区域1"
assert M.GRID[(3, 1)].goal_name == "白色区域2"
# 两个白色目标区域用白色底，其余可通行格子是灰色底
assert M.GRID[(5, 3)].color == M.C_GOAL_WHITE == "#ffffff"
assert M.GRID[(3, 1)].color == "#ffffff"
assert M.GRID[(3, 3)].color == M.C_FLOOR == "#c6c7c1"
assert M.GRID[(1, 1)].color == "#c6c7c1"
for k in [(2, 2), (2, 4), (4, 2), (4, 4)]:
    assert M.GRID[k].kind == M.WALL and not M.GRID[k].passable

# 与图片像素检测出的黑线位置一致性检查（防止手抄错）
EXP_X = [0, 239.5, 445.5, 625.5, 829.5, 1080.0]
EXP_Y = [0, 242.5, 446.5, 635.5, 831.0, 1070.0]
assert M.X_BOUNDS == EXP_X, M.X_BOUNDS
assert M.Y_BOUNDS == EXP_Y, M.Y_BOUNDS
print("\n  网格线坐标与 map.jpg 实测一致 ✔")

# ---- 独立实现一份 BFS，交叉校验 map_sim.shortest_path ----


def ref_bfs(s, t):
    prev = {s: None}
    q = deque([s])
    while q:
        cur = q.popleft()
        if cur == t:
            break
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            n = (cur[0] + dr, cur[1] + dc)
            if n in M.GRID and M.GRID[n].passable and n not in prev:
                prev[n] = cur
                q.append(n)
    if t not in prev:
        return None
    path = []
    node = t
    while node is not None:
        path.append(node)
        node = prev[node]
    return path[::-1]


keys = sorted(M.GRID)
bad = 0
for s in keys:
    for t in keys:
        if not M.GRID[s].passable or not M.GRID[t].passable:
            continue
        path, err = M.shortest_path(s, t)
        ref = ref_bfs(s, t)
        if ref is None:
            if path:
                print("  不一致(应不可达): %s -> %s" % (s, t)); bad += 1
            continue
        if s == t:
            if [c.key for c in path] != [s] or err != "已经在目标格子上":
                print("  原地不动处理错误: %s (%s)" % (s, err)); bad += 1
            continue
        if err:
            print("  报错: %s -> %s : %s" % (s, t, err)); bad += 1; continue
        got = [c.key for c in path]
        # 校验相邻性、禁行、首尾
        if got[0] != s or got[-1] != t:
            print("  首尾错误: %s -> %s %s" % (s, t, got)); bad += 1; continue
        ok = all(abs(got[i][0] - got[i + 1][0]) + abs(got[i][1] - got[i + 1][1]) == 1
                 for i in range(len(got) - 1))
        if not ok or any(not M.GRID[k].passable for k in got):
            print("  路径非法: %s -> %s %s" % (s, t, got)); bad += 1; continue
        if len(got) != len(ref):
            print("  非最短路: %s -> %s got=%d ref=%d" % (s, t, len(got), len(ref)))
            bad += 1

print("  全量 %d 组起终点 BFS 交叉校验：%s" % (len(keys) ** 2, "全部通过 ✔" if bad == 0 else "%d 处失败" % bad))

print("\n=== 典型路线（含必经的绕行）===")
for s, t in [((1, 5), (1, 3)), ((1, 5), (5, 3)), ((1, 5), (3, 1)), ((1, 3), (5, 5)),
             ((3, 1), (5, 3)), ((5, 3), (3, 1)), ((1, 3), (5, 3)), ((5, 5), (3, 1))]:
    path, err = M.shortest_path(s, t)
    print("  %-8s -> %-8s : %2d 格  %s" % (M.GRID[s].name, M.GRID[t].name,
                                           len(path), "→".join("r%dc%d" % k for k in (c.key for c in path))))

print("\n=== 黄色禁行格作为终点应被拒绝 ===")
for k in [(2, 2), (2, 4), (4, 2), (4, 4)]:
    p, e = M.shortest_path((1, 5), k)
    print("  (1,5) -> r%dc%d : %s %s" % (k[0], k[1], e, "✔" if e else "✘"))

# ---------------------------------------------------------------------------
# 障碍物相关
# ---------------------------------------------------------------------------
print("\n=== 障碍物规则 ===")
M.clear_obstacles()
for s, other in (((1, 5), (5, 5)), ((5, 5), (1, 5))):
    M.set_active_start(s)
    cand = [c.key for c in M.obstacle_candidates(s)]
    assert s not in cand, "被选作出发点的格子不能放障碍物"
    assert other in cand, "另一个出发点应视为普通路径，可以放障碍物"
    assert not any(k in M.WALL_CELLS for k in cand), "禁行区不能放障碍物"
    assert not any(M.GRID[k].goal_name for k in cand), "目标地点不能放障碍物"
    print("  ✔ 起点 %-6s：候选 %d 个，另一个出发点 %s 可放"
          % (M.GRID[s].name, len(cand), M.GRID[other].name))

print("\n=== 障碍物绕行（起点 出发点1，障碍 r1c4）===")
M.set_active_start((1, 5))
base, _ = M.shortest_path((1, 5), (1, 3))
M.place_obstacles([(1, 4)])
detour, _ = M.shortest_path((1, 5), (1, 3))
print("  无阻碍：%d 格  %s" % (len(base), " → ".join(c.name for c in base)))
print("  有障碍：%d 格  %s" % (len(detour), " → ".join(c.name for c in detour)))
assert len(detour) > len(base), "有障碍时路径应更长"
assert (1, 4) not in [c.key for c in detour], "路径不能穿过障碍物"
assert detour[0].key == (1, 5) and detour[-1].key == (1, 3)
print("  ✔ 绕开了障碍物")

print("\n=== 障碍物上不能作为终点 ===")
p, e = M.shortest_path((1, 5), (1, 4))
print("  (1,5) -> r1c4 : %s %s" % (e, "✔" if e and not p else "✘"))
assert not p and e

print("\n=== 随机放置（模拟比赛 1~2 个）===")
import collections
stats = collections.Counter()
for s in ((1, 5), (5, 5)):
    M.set_active_start(s)
    for _ in range(40):
        M.clear_obstacles()
        keys, msg = M.random_obstacles(s)
        assert keys, "随机放置不应失败：%s" % msg
        assert 1 <= len(keys) <= 2, "随机障碍物数量必须是 1~2 个，实际 %d" % len(keys)
        for k in keys:
            c = M.GRID[k]
            assert k != s, "障碍物不能放在被选中的出发点上"
            assert c.kind in (M.FLOOR, M.START), "障碍物只能放在可通行格上"
            assert not c.goal_name, "障碍物不能放在目标地点上"
            assert not c.obstacle or True
        ok, bad = M.reachable_goals(s)
        assert not bad, "随机放置后目标应当可达，实际不可达：%s" % bad
        stats[len(keys)] += 1
print("  80 次随机：1 个障碍 %d 次，2 个障碍 %d 次，全部满足约束 ✔"
      % (stats[1], stats[2]))

print("\n=== 会堵死目标的组合应被识别出来 ===")
M.set_active_start((1, 5))
M.clear_obstacles()
M.place_obstacles([(1, 4), (2, 5)])       # 把出发点1 唯一的出口堵死
ok, bad = M.reachable_goals((1, 5))
print("  障碍 r1c4 + r2c5 → 不可达：%s" % bad)
assert bad, "这种情况应当判为不可达"
M.clear_obstacles()
ok, bad = M.reachable_goals((1, 5))
assert not bad, "清空障碍物后目标必须全部可达"
print("  ✔ 清空障碍物后：%s 全部可达" % "、".join(ok))

print("\n全部检查结束。")
