#!/usr/bin/env python3
"""The run-time audit of verified programs (D118): uv run --no-project gym/audit.py RUN_ID

Runs every verified B17 program of an M3 run in the interpreter, on random valid inputs and with a
step limit, against a reference written separately in Python. A verdict can't show a trick that makes
the proof vacuous, or a search that verifies but never finishes. One in five inputs is large enough
that a program searching every answer runs out of steps, where a real algorithm doesn't.

The limit is just above the slowest real algorithm recorded, a `kruskal` that scans every possible
weight, at about 400M steps. So stuck means read the program: it needn't be a trick or a search.

Exits 1 if a program isn't right on all its inputs. Dafny's programs aren't run.
"""
import argparse
import json
import math
import random
import sys
from collections import Counter
from itertools import accumulate
from pathlib import Path

import harness as h

sys.path.insert(0, str(h.B17C))
import interp as i
import syntax

INPUTS, STEPS, DEPTH = 25, 500_000_000, 5000
D, T = i.Data, i.Tup
NONE, some = D("none", ()), lambda x: D("some", (x,))


def py(x):
    """An interpreter value as plain tuples, a data value's constructor first."""
    if isinstance(x, D):
        return (x.ctor, *map(py, x.fields))
    if isinstance(x, (T, tuple)):
        return tuple(map(py, x.items if isinstance(x, T) else x))
    return x


def ints(r, n=12, lo=-20, hi=20, least=0):
    return tuple(r.randint(lo, hi) for _ in range(r.randint(least, n)))


def in_a(a, key, k):
    return k == -1 and key not in a or 0 <= k < len(a) and a[k] == key


# B17-0's seed tasks. Each case gives the args and a check of the results.
def abs_(r, big):
    x = r.choice([r.randint(-100, 100), 1 - 2**63, 2**63 - 1])
    return (x,), lambda y: y == abs(x)


def all_positive(r, big):
    a = ints(r, lo=-2) if r.random() < 0.5 else ints(r, lo=1)
    return (a,), lambda b: b == all(v > 0 for v in a)


def binary_search(r, big):
    a, key = tuple(sorted(ints(r))), r.randint(-20, 20)
    return (a, key), lambda k: in_a(a, key, k)


def count(r, big):
    a, x = ints(r, lo=-3, hi=3), r.randint(-3, 3)
    return (a, x), lambda c: c == a.count(x)


def dedup_sorted(r, big):
    a = tuple(sorted(ints(r, lo=-5, hi=5)))
    return (a,), lambda o: o == tuple(sorted(set(a)))


def fib_iter(r, big):
    n = r.randint(0, 90)
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return (n,), lambda f: f == a


def find(r, big):
    a, key = ints(r, lo=-5, hi=5), r.randint(-5, 5)
    return (a, key), lambda k: in_a(a, key, k)


def gcd_iter(r, big):
    a, b = r.randint(0, 10**5), r.randint(0, 10**5)
    return (a, b), lambda g: g == math.gcd(a, b)


def insertion_sort(r, big):
    a = ints(r)
    return (a,), lambda o: o == tuple(sorted(a))


def is_sorted(r, big):
    a = tuple(sorted(ints(r))) if r.random() < 0.5 else ints(r, n=4)
    return (a,), lambda b: b == (a == tuple(sorted(a)))


def isqrt(r, big):
    n = r.randint(0, 10**6)
    return (n,), lambda k: k == math.isqrt(n)


def max_element(r, big):
    a = ints(r, least=1)
    return (a,), lambda m: m == max(a)


def merge_sorted(r, big):
    a, b = tuple(sorted(ints(r))), tuple(sorted(ints(r)))
    return (a, b), lambda o: o == tuple(sorted(a + b))


def min_index(r, big):
    a = ints(r, least=1)
    return (a,), lambda m: 0 <= m < len(a) and a[m] == min(a)


def partition(r, big):
    a, pivot = ints(r), r.randint(-20, 20)
    return (a, pivot), lambda o, k: (0 <= k <= len(o) and sorted(o) == sorted(a)
                                     and all(v < pivot for v in o[:k]) and all(v >= pivot for v in o[k:]))


def power(r, big):
    b, e = r.randint(-5, 5), r.randint(0, 20)
    return (b, e), lambda p: p == b**e


def prefix_sums(r, big):
    a = ints(r)
    return (a,), lambda p: p == tuple(accumulate(a, initial=0))


def reverse(r, big):
    a = ints(r)
    return (a,), lambda o: o == a[::-1]


def sum_(r, big):
    a = ints(r)
    return (a,), lambda s: s == sum(a)


# B17-1's AlgoVeri ports.
def rand_rows(r, n, p, lo, hi):
    """A graph's adjacency rows: at most one edge from u to each v, as well_formed asks."""
    return [[(v, r.randint(lo, hi)) for v in r.sample(range(n), n) if r.random() < p] for _ in range(n)]


def graph(rows, name="weighted_graph"):
    return D(name, (tuple(tuple(T(e) for e in row) for row in rows),))


def shortest(rows, s):
    """Distances from s, None where unreachable, and whether a negative cycle is reachable."""
    n = len(rows)
    d = [None] * n
    d[s] = 0
    for _ in range(n):
        for u in range(n):
            if d[u] is not None:
                for v, w in rows[u]:
                    if d[v] is None or d[u] + w < d[v]:
                        d[v] = d[u] + w
    reach = any(d[u] is not None and any(d[v] is None or d[u] + w < d[v] for v, w in rows[u]) for u in range(n))
    return tuple(("none",) if x is None else ("some", x) for x in d), reach


def negative_cycle(rows):
    d = [0] * len(rows)
    for _ in rows:
        for u, row in enumerate(rows):
            for v, w in row:
                d[v] = min(d[v], d[u] + w)
    return any(d[u] + w < d[v] for u, row in enumerate(rows) for v, w in row)


def dijkstra(r, big):
    rows = rand_rows(r, 12, 0.5, 0, 9) if big else rand_rows(r, r.randint(1, 6), 0.45, 0, 9)
    s = r.randrange(len(rows))
    want = shortest(rows, s)[0]
    return (graph(rows), s), lambda o: o == want


def bellman_ford(r, big):
    rows = rand_rows(r, 12, 0.5, 0, 9) if big else rand_rows(r, r.randint(1, 6), 0.35, -4, 9)
    s = r.randrange(len(rows))
    d, reach = shortest(rows, s)
    # With a negative cycle that s can't reach, the spec allows either answer.
    allowed = [("none",)] if reach else [("some", d), ("none",)] if negative_cycle(rows) else [("some", d)]
    return (graph(rows), s), lambda o: o in allowed


def mst(r, big):
    n = 10 if big else r.randint(1, 6)
    adj = [{} for _ in range(n)]
    order = r.sample(range(n), n)
    for k in range(1, n):  # connected both ways, though the two directions may weigh differently
        u, v = order[k], order[r.randrange(k)]
        adj[u][v] = r.randint(-5, 9)
        adj[v][u] = adj[u][v] if r.random() < 0.7 else r.randint(-5, 9)
    for _ in range(n * 4 if big else r.randint(0, n * 2)):
        u, v = r.randrange(n), r.randrange(n)
        adj[u][v] = r.randint(-5, 9)
        adj[v][u] = adj[v].get(u, r.randint(-5, 9))
    rows = [list(a.items()) for a in adj]

    def joined(edges):
        """How many components the edges leave, and their weight."""
        p = list(range(n))

        def top(x):
            while p[x] != x:
                x = p[x]
            return x
        total = 0
        for u, v, w in edges:
            if top(u) != top(v):
                p[top(u)] = top(v)
                total += w
        return len({top(x) for x in range(n)}), total
    want = joined(sorted(((u, v, w) for u in range(n) for v, w in rows[u]), key=lambda e: e[2]))[1]  # Kruskal's

    def ok(o):
        return (len(o) == n - 1 and all((v, w) in rows[u] for u, v, w in o)
                and joined(o)[0] == 1 and sum(w for *_, w in o) == want)
    return (graph(rows),), ok


def max_flow(r, big):
    rows = rand_rows(r, 8, 0.5, 0, 100) if big else rand_rows(r, r.randint(2, 6), 0.45, 0, 9)
    s, t = r.sample(range(len(rows)), 2)
    n = len(rows)
    c = [[0] * n for _ in range(n)]
    for u in range(n):
        for v, w in rows[u]:
            if u != v:
                c[u][v] = w
    want = 0
    while True:  # Edmonds-Karp
        par = [-1] * n
        par[s] = s
        q = [s]
        for u in q:
            for v in range(n):
                if par[v] < 0 and c[u][v] > 0:
                    par[v] = u
                    q.append(v)
        if par[t] < 0:
            break
        path = [t]
        while path[-1] != s:
            path.append(par[path[-1]])
        b = min(c[par[v]][v] for v in path[:-1])
        for v in path[:-1]:
            c[par[v]][v] -= b
            c[v][par[v]] += b
        want += b
    return (graph(rows, "capacity_graph"), s, t), lambda o: o == want


def rand_tree(r, values, leaf):
    """A binary tree of any shape holding the values, built from D(node, (v, left, right))."""
    if not values:
        return D(leaf, ())
    k = r.randrange(len(values))
    return D("node", (values[k], rand_tree(r, values[:k], leaf), rand_tree(r, values[k + 1:], leaf)))


def tree_values(t):
    return () if len(t) == 1 else (*tree_values(t[2]), t[1], *tree_values(t[3]))


def bst_insert(r, big):
    vals = sorted(r.sample(range(-20, 40), r.randint(0, 12)))
    x = r.randint(0, 39)

    def ok(o):
        v = tree_values(o)
        return v == tuple(sorted({*vals, x}))  # in order, so sorted exactly when it's a search tree
    return (rand_tree(r, vals, "leaf"), x), ok


def bst_search(r, big):
    vals = sorted(r.sample(range(-20, 40), r.randint(0, 12)))
    x = r.randint(0, 39)
    return (rand_tree(r, vals, "leaf"), x), lambda b: b == (x in vals)


def coin_change(r, big):
    coins = tuple(r.randint(3 if big else 1, 50 if big else 30) for _ in range(r.randint(1, 8)))
    amount = 1000 if big else r.randint(-2, 200)
    best = [0] + [None] * max(amount, 0)
    for a in range(1, amount + 1):
        best[a] = min((best[a - c] + 1 for c in coins if c <= a and best[a - c] is not None), default=None)
    want = -1 if amount < 0 or best[amount] is None else best[amount]
    return (coins, amount), lambda m: m == want


def discrete_log(r, big):
    g, h_, p = r.randint(0, 50), r.randint(0, 60), r.randint(2, 3000 if big else 300)
    x, want = 1, ("none",)
    for k in range(p):
        if x == h_ % p:
            want = ("some", k)
            break
        x = g * x % p
    return (g, h_, p), lambda o: o == want


def lca(r, big):
    vals = r.sample(range(40), r.randint(1, 30 if big else 12))
    tree = rand_tree(r, vals, "nil")
    p, q = r.choice(vals), r.choice(vals)

    def path(t, x):
        if t.ctor == "nil":
            return None
        if t.fields[0] == x:
            return [x]
        sub = path(t.fields[1], x) or path(t.fields[2], x)
        return [t.fields[0], *sub] if sub else None
    a, b = path(tree, p), path(tree, q)
    want = next(u for u, v in zip(reversed(a[:len(b)]), reversed(b[:len(a)])) if u == v)
    return (tree, p, q), lambda o: o == ("some", want)


def longest_palindrome(r, big):
    s = tuple(r.randint(0, 2) for _ in range(80 if big else r.randint(0, 30)))
    n = len(s)
    want = max(m for k in range(n + 1) for m in range(n - k + 1) if s[k:k + m] == s[k:k + m][::-1])

    def ok(o):
        k, m = o
        return 0 <= k and 0 <= m == want and k + m <= n and s[k:k + m] == s[k:k + m][::-1]
    return (s,), ok


def segment_tree(r, big):
    low = r.randint(0, 5)
    a = tuple(r.randint(0, 50) for _ in range(r.randint(1, 64 if big else 12)))

    def build(lo, hi):
        if hi == lo + 1:
            return D("node", (a[lo - low], lo, hi, NONE, NONE))
        mid = (lo + hi) // 2
        left, right = build(lo, mid), build(mid, hi)
        return D("node", (max(left.fields[0], right.fields[0]), lo, hi, some(left), some(right)))
    ql = r.randrange(low, low + len(a))
    qr = r.randint(ql + 1, low + len(a))
    return (build(low, low + len(a)), ql, qr), lambda v: v == max(a[ql - low:qr - low])


def trie_insert(r, big):
    keys = {tuple(r.randint(0, 3) for _ in range(r.randint(0, 5))) for _ in range(r.randint(0, 6))}
    key = tuple(r.randint(0, 3) for _ in range(r.randint(0, 5)))

    def build(prefix):
        kids = {k[len(prefix)] for k in keys if len(k) > len(prefix) and k[:len(prefix)] == prefix}
        return D("node", (prefix in keys, tuple(some(build((*prefix, c))) if c in kids else NONE for c in range(256))))

    def held(node, prefix=()):
        """The node's keys, or None if it isn't well formed: 256 children, and no empty child."""
        _, end, kids = node
        if len(kids) != 256:
            return None
        out = {prefix} if end else set()
        for c, kid in enumerate(kids):
            if kid != ("none",):
                sub = held(kid[1], (*prefix, c))
                if not sub:
                    return None
                out |= sub
        return out
    return (some(build(())) if keys else NONE, key), lambda o: held(o) == keys | {key}


CASES = {f"b17/{name}": case for name, case in {
    "abs": abs_, "all_positive": all_positive, "binary_search": binary_search, "count": count,
    "dedup_sorted": dedup_sorted, "fib": fib_iter, "find": find, "gcd": gcd_iter, "insertion_sort": insertion_sort,
    "is_sorted": is_sorted, "isqrt": isqrt, "max_element": max_element, "merge_sorted": merge_sorted,
    "min_index": min_index, "partition": partition, "power": power, "prefix_sums": prefix_sums,
    "reverse": reverse, "reverse_in_place": reverse, "sum": sum_}.items()} | {f"b17-1/{name}": case for name, case in {
    "bellman_ford": bellman_ford, "bst_insert": bst_insert, "bst_search": bst_search, "coin_change": coin_change,
    "dijkstra": dijkstra, "discrete_logarithm": discrete_log, "edmond_karp": max_flow, "kruskal": mst, "lca": lca,
    "longest_palindrome_substring": longest_palindrome, "prim": mst, "push_relabel": max_flow,
    "segmenttree_query": segment_tree, "trie_insert": trie_insert}.items()}


def audit(task, module, inputs=INPUTS):
    """How a parsed module's def does on the task's inputs: (verdict, inputs passed, detail).
    The verdict is right, or the first input's wrong, stuck or failed."""
    r = random.Random(f"{task['id']}/audit")
    for k in range(inputs):
        args, ok = CASES[task["id"]](r, k % 5 == 4)
        out = i.run(module, task["name"], args, fuel=STEPS, depth=DEPTH, subset=task.get("subset", 0))
        if isinstance(out, i.Limit):
            return "stuck", k, f"out of {out.kind} on input {k}"
        if not isinstance(out, i.Ok):
            return "failed", k, f"input {k}: {i.text_of(out)[:200]}"
        try:
            good = ok(*map(py, out.results))
        except (IndexError, TypeError, ValueError):  # an answer not even of the expected shape
            good = False
        if not good:
            return "wrong", k, f"input {k}: {py(args)} gave {py(out.results)}"[:400]
    return "right", inputs, ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id")
    ap.add_argument("--inputs", type=int, default=INPUTS)
    args = ap.parse_args()
    recs = [r for r in h.read_records(h.RUNS / args.run_id) if r["stage"] == "verified"]
    tasks = {t["id"]: t for t in h.load_tasks(sorted({r["task"] for r in recs if r["task"] in CASES}))}
    tally = Counter()
    for rec in sorted(recs, key=lambda r: (r["task"], r["cli"], r["sample"])):
        if rec["task"] not in CASES:
            tally["not audited"] += 1
            continue
        t = tasks[rec["task"]]
        verdict, passed, detail = audit(t, syntax.parse((t["frozen"][:-1] + "\n" + rec["code"] + ")").encode(), t.get("subset", 0)), args.inputs)
        tally[verdict] += 1
        print(rec["task"], rec["cli"], f"sample {rec['sample']} round {rec['iter']}: {verdict}, {passed} of {args.inputs}", detail, flush=True)
    print(", ".join(f"{n} {v}" for v, n in sorted(tally.items())) or "no verified programs")
    return 1 if set(tally) - {"right", "not audited"} else 0


if __name__ == "__main__":
    sys.exit(main())
