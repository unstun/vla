"""Four-cell behavioral reduction; not a native C++ integration test.

Supplied by the independent read-only reviewer. The native recorded-input
trace separately establishes that the same unqueued-free state occurs.
"""
import heapq
import math

S, A, C, G = (0, 0), (0, 1), (1, 1), (2, 1)


def search(mark_before_collision, initial_g=1 >> 20):
    nodes = {S: [1, 1, 0.0]}  # rounds, state, g
    queue = [(0.0, S)]
    while queue:
        _, point = heapq.heappop(queue)
        if point == G:
            return True
        nodes[point][1] = 2
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == dy == 0:
                    continue
                neighbor = (point[0] + dx, point[1] + dy)
                node = nodes.setdefault(neighbor, [0, 3, initial_g])
                explored = node[0] == 1
                if explored and node[1] == 2:
                    continue
                if mark_before_collision:
                    node[0] = 1
                blocked = neighbor not in {S, A, C, G} or (neighbor == C and dy != 0)
                if blocked:
                    continue
                if not mark_before_collision:
                    node[0] = 1
                cost = nodes[point][2] + math.hypot(dx, dy)
                if not explored:
                    node[1], node[2] = 1, cost
                    heapq.heappush(queue, (cost + math.dist(neighbor, G), neighbor))
                elif cost < node[2]:
                    node[2] = cost  # Native update branch does not enqueue.
    return False


if __name__ == "__main__":
    assert search(True, 0) is False
    assert search(True, math.inf) is False
    assert search(False, 0) is True
    assert search(False, math.inf) is True
    print("Counterexample confirmed: blocked-first bookkeeping loses a reachable gateway.")
