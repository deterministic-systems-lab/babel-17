"""WP5's verifier: goals from WP3's types, cached and reported (D17, D22-D25, D63).

    uv run --no-project b17c/verify.py [--subset 0|1] [--seeds N] [--cache DIR] [--level L0|L1|L2|L3] [--report FILE] FILE

checks every goal of FILE, prints each one that isn't proved, and a summary. A FILE that
fails tier 0 has no goals: its diagnostics are printed instead, as `b17c/check.py` prints them. With
--report it also writes the module's trusted base report as JSON (D25). It exits 0 only
when every goal is proved under the canonical seed and every shuffled seed (D23), or with
--level, when the module reaches that level (D80, docs/b17-1.md §10). Either option works out
the level, which runs property tests and solves goals again if any goal isn't proved.

Each goal is sent as its canonical query (interface 11, D63): goals.py's SMT-LIB text
with b17c's generated names renamed in order of first occurrence, so alpha-equivalent
definitions send the same bytes. Verdicts are cached under D22's key, so unchanged
code, renamed code and the callers of a changed body are never solved again.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

import goals as G
import hashing as H
import interp as I
from syntax import SUBSET, Form, ParseError, Sym, _head, canonical as canonical_bytes

HERE = Path(__file__).resolve().parent
SEEDS = 10
CACHE = Path(".b17c/cache")
RUNTIME = {"BOUNDS", "OVERFLOW", "DIV", "PRE", "TERM", "FIELD"}  # L2's "no runtime errors" families
ABORTS = RUNTIME - {"PRE", "TERM"}  # those emitted Rust checks, and aborts at, below L2 (D80)
# b17c's generated SMT names: constants (x!12), bound variables (k!B3), ghost-fn parameters
# (n!P4), ghost-fn functions and requires (g!fib, p!fib), and B17-1's sorts, constructors,
# selectors and functions (d!3, c!4, f!5, s!6, len!6, rank!7).
GENERATED = re.compile(r"(?<![\w.!])(?:[a-z][a-z0-9_]*![BP]?[0-9]+|[gp]![a-z][a-z0-9_]*)(?![\w.!])")


def canonical(query):
    """Interface 11: generated names become k!0, k!1, ... in order of first occurrence (D63)."""
    names = {}
    return GENERATED.sub(lambda m: names.setdefault(m[0], f"k!{len(names)}"), query)


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def cache_key(definition, deps, query, cfg):
    """D63's cache key: a format tag, the definition's hash, the sorted spec hashes it refers
    to, the canonical query and the configuration, each length-prefixed."""
    parts = ["b17c-proof 0", definition, *sorted(deps), query, json.dumps(cfg, sort_keys=True)]
    return sha256(b"".join(len(p.encode()).to_bytes(8, "big") + p.encode() for p in parts))


def config(seeds):
    """D22's verification configuration: b17c, the prelude, the solver and its options. The
    solver's hash covers its resolved binary and the libz3 beside it (D23)."""
    found = shutil.which("z3")
    binary = Path(found).resolve() if found else None
    libs = sorted((binary.parent.parent / "lib").glob("libz3*")) if binary else []
    solver = hashlib.sha256()
    for f in [binary, *libs] if binary else []:
        solver.update(f.read_bytes())
    z3 = os.popen("z3 --version").read().strip() if binary else ""
    return {
        "b17c": sha256(b"".join(Path(HERE, f).read_bytes() for f in ("goals.py", "verify.py"))),
        "prelude": sha256(G.PRELUDE + G.VDIV + (HERE / "core.b17").read_text()),
        "solver": z3,
        "solver_sha256": solver.hexdigest() if binary else "",
        "budget": G.RLIMIT,
        "seeds": seeds,
    }


def _node_ids(*modules):
    """id(node) -> D56's node ID prefix: the item's kind and name, and the child-index path."""
    ids = {}

    def walk(x, item, path):
        ids[id(x)] = (item, path)
        if isinstance(x, Form):
            for k, c in enumerate(x.items):
                walk(c, item, path + (k,))

    for m in modules:
        for it in m.items[3:]:
            walk(it, f"{it.items[0].text} {it.items[1].text}", ())
    return ids


def _node(ids, x):
    item, path = ids.get(id(x), ("module", ()))
    return f"{item}{'/' + '.'.join(map(str, path)) if path else ''}@{x.pos[0]}:{x.pos[1]}"


def _references(x, names):
    if isinstance(x, Sym):
        return {x.text} & names
    return set().union(*(_references(c, names) for c in x.items)) if isinstance(x, Form) else set()


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None  # missing, or a partial write from a crashed run: a miss


def _write(path, entry):
    """Publish atomically, so a parallel run never reads a partial entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(entry, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def verify(module, seeds=SEEDS, cache=CACHE, subset=SUBSET):
    """Every goal of module: its node, contract clause, family, verdict, resource units and
    whether it came from the cache, plus the run's configuration. Raises ValueError, listing
    the diagnostics, if module fails tier 0."""
    return verify_goals(module, seeds, cache, subset)[2:]


def checker(module, gen, cfg, cache, subset):
    """A function from a goal to its verdict and units, solved or from the cache: on the goal's own
    query, or on one with these facts and with these ghost-fns' equations left out (D91)."""
    hashes, core = H.hashes(module, subset), H.hashes(G.CORE, 0)
    items, seeds = set(gen.defs), cfg["seeds"]

    def check(g, facts=None, opaque=()):
        name, part = g[0], g[6]
        kind, spec, impl = hashes[name]
        d = gen.defs[name]
        own = [d[k] for k in d if k in ("spec", "lemma", "ghost-fn") or part == "impl"]
        deps = [{**core, **hashes}[r][1] for r in set().union(*(_references(x, items) for x in own)) - {name}]
        q = canonical(G.query(gen, g[3] if facts is None else facts, g[4], name, opaque))
        k = cache_key(spec if part == "spec" or impl is None else impl, deps, q, cfg)
        path = Path(cache, k[:2], k + ".json")
        if (hit := _read(path)) is not None:
            return hit | {"cached": True}
        verdict, units = G.solve_stats(q)
        runs = [verdict]
        if verdict == "proved":
            for s in range(1, seeds + 1):
                v, u = G.solve_stats(q, s)
                runs.append(v)
                units += u
            held = runs.count("proved") - 1
            if held < seeds:
                verdict = f"brittle: proved under {held} of {seeds} shuffled seeds"
        entry = {"verdict": verdict, "units": units}
        # D23: only verdicts reached within the resource budget are kept. A wall-clock
        # timeout or a process error depends on the machine, so it's solved again next time.
        if all(r in ("proved", "failed", "unknown") for r in runs):
            _write(path, entry)
        return entry | {"cached": False}
    return check


def verify_goals(module, seeds=SEEDS, cache=CACHE, subset=SUBSET):
    """verify(), with the goal generator and its goals, one per row, for WP6's diagnostics."""
    gen = G.Gen(module, subset)
    goals = gen.check(module)
    ids, cfg = _node_ids(module, G.CORE), config(seeds)
    check = checker(module, gen, cfg, cache, subset)
    with cf.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(check, goals))
    rows, seen = [], Counter()
    for g, r in zip(goals, results):
        node = _node(ids, g[5]) + (f" {_node(ids, g[7])}" if g[7] is not None else "")
        seen[(node, g[1])] += 1  # the same node checked twice, as a loop condition is
        rows.append({"node": node + (f" #{seen[(node, g[1])]}" if seen[(node, g[1])] > 1 else ""),
                     "family": g[1], **r})
    return gen, goals, rows, cfg


def closure(gen, goals, proved, check):
    """L2's goals proved from proved goals alone (D80, D91): of the proved goals, those still proved
    without what rests on a goal that isn't in the set. It starts from all of them and only shrinks,
    so a recursive def's POST goals and a loop's INV-KEEP goals may rest on themselves."""
    owners = {}
    for k, g in enumerate(goals):
        for t in (("item", g[0]), ("post", g[0]) if g[1] == "POST" else None,
                  ("inv", id(g[5])) if g[1].startswith("INV-") else None):
            if t:
                owners.setdefault(t, set()).add(k)
    no_def = {("post", name) for name, d in gen.defs.items() if "spec" in d and "def" not in d}  # nothing proves it
    counted = set(proved)
    while True:
        out = set(range(len(goals))) - counted
        dead = out | no_def | {t for t, ks in owners.items() if ks & out}
        opaque = {t[1] for t in dead if isinstance(t, tuple) and t[0] == "item"}
        order = sorted(counted)
        with cf.ThreadPoolExecutor(8) as pool:
            verdicts = list(pool.map(lambda k: check(goals[k], G.without(goals[k][3], dead), opaque)["verdict"], order))
        gone = {k for k, v in zip(order, verdicts) if v != "proved"}
        if not gone:
            return counted
        counted -= gone


def runtime_goals(gen, goals):
    """The goals L2 needs proved for no runtime errors (D80): a def's RUNTIME goals outside its ghost code."""
    return {k for k, g in enumerate(goals) if g[1] in RUNTIME and g[6] == "impl" and "def" in gen.defs[g[0]]
            and (g[1] == "TERM" or id(g[5]) not in gen.ghost)}  # a def's TERM goals are its loops' and calls'


def levels(module, seeds=SEEDS, cache=CACHE, subset=SUBSET):
    """verify(), with the level the module reaches (D80), and the report's fields that say why
    (docs/b17-1.md §10)."""
    gen, goals, rows, cfg = verify_goals(module, seeds, cache, subset)
    proved = {k for k, r in enumerate(rows) if r["verdict"] == "proved"}
    if len(proved) == len(goals):  # L3-S: nothing is left to test
        return rows, cfg, {"level": "L3-S", "tested": [], "untested": [], "refuted": [], "uncounted": [], "may_abort": []}
    counts, refuted, hashes = Counter(), {}, H.hashes(module, subset)
    for it in module.items[3:]:
        if _head(it) == "def":
            name = it.items[1].text
            seed = int(hashes[name][1].split(":")[1][:16], 16)  # D88
            _, seen, bad = I.test_def(module, name, seed, subset)
            counts.update(seen)
            for k, (given, outcome) in bad.items():
                refuted.setdefault(k, {"def": name, "input": given, "outcome": outcome})
    keys, nth = [], Counter()  # a goal's key, numbered as its name is: a loop's #2 is after a pass
    for g in goals:
        nth[k := (g[1], id(g[5]), None if g[7] is None else id(g[7]))] += 1
        keys.append((*k, nth[k]))
    key = lambda g: keys[g]
    lemma_body = lambda g: g[6] == "impl" and "lemma" in gen.defs[g[0]]  # never runs (D57), so always proved
    tested = {k for k, g in enumerate(goals) if k not in proved and counts[key(k)]
              and key(k) not in refuted and not lemma_body(g)}
    counted = closure(gen, goals, proved, checker(module, gen, cfg, cache, subset))
    runtime = runtime_goals(gen, goals)
    one = len(proved | tested) == len(goals)
    named = lambda k: {"node": rows[k]["node"], "family": rows[k]["family"]}
    first = {}
    for k in range(len(goals)):
        first.setdefault(key(k), k)
    return rows, cfg, {
        "level": "L2-S" if one and runtime <= counted else "L1" if one else "L0",
        "tested": [{**named(k), "inputs": counts[key(k)]} for k in sorted(tested)],
        "untested": [named(k) for k in sorted(set(range(len(goals))) - proved - tested)],
        "refuted": [{"node": rows[first[k]]["node"] if k in first else None, "family": k[0], **v} for k, v in refuted.items()],
        "uncounted": [named(k) for k in sorted(proved - counted)],
        "may_abort": [named(k) for k in sorted(runtime - counted) if goals[k][1] in ABORTS],
    }


def signatures_path(path):
    return Path(str(path) + ".signatures.json")


def signatures(path):
    """The spec signatures recorded beside the module at path (interface 9, D121)."""
    p = signatures_path(path)
    return json.loads(p.read_text()) if p.exists() else []


def unsigned(path, module, subset=SUBSET):
    """The module's specs whose current hash no signature beside path records (D121)."""
    signed = {s["spec"] for s in signatures(path)}
    return [name for name, (kind, spec, _) in H.hashes(module, subset).items() if kind == "spec" and spec not in signed]


def report(module, rows, cfg, reached, unsigned_specs=None):
    """The module's trusted base report (D24, D25), with reached from levels(), and the specs no
    reviewer has signed, where known (D121). Until the kernel exists, every proved goal is
    solver-trusted, so a module whose goals all hold is L3-S, not L3."""
    laws = sorted(it.items[1].text for it in G.CORE.items[3:] if _head(it) == "lemma")
    held = lambda r: r["verdict"] == "proved"
    return {
        "module": module.items[1].text,
        "input_sha256": sha256(canonical_bytes(module)),
        "lockfile_sha256": None,  # B17-0 has no imports, so no lockfile yet (D9, D26)
        **reached,
        **cfg,
        "solver_trusted": [r["node"] for r in rows if held(r)],
        "brittle": [r["node"] for r in rows if r["verdict"].startswith("brittle")],
        "failed": [{"node": r["node"], "family": r["family"], "verdict": r["verdict"]}
                   for r in rows if not held(r) and not r["verdict"].startswith("brittle")],
        "admitted": [],  # B17-0 has no admit or assume
        "unsigned_specs": unsigned_specs,
        "axioms": {"core": laws, "encoding": f"b17c prelude {cfg['prelude'][:16]} (D61)"},
    }


def main(argv):
    seeds, cache, out, subset, level, bad = SEEDS, CACHE, None, SUBSET, None, False
    while argv and argv[0] in ("--subset", "--seeds", "--cache", "--level", "--report") and len(argv) > 1:
        flag, val, argv = argv[0], argv[1], argv[2:]
        if flag == "--subset":
            subset, bad = (int(val), bad) if val in ("0", "1") else (subset, True)
        elif flag == "--seeds":
            seeds, bad = (int(val), bad) if val.isdecimal() else (seeds, True)
        elif flag == "--cache":
            cache = Path(val)
        elif flag == "--level":
            level = val
        else:
            out = Path(val)
    if bad or len(argv) != 1 or level not in (None, "L0", "L1", "L2", "L3"):
        print("usage: uv run --no-project b17c/verify.py [--subset 0|1] [--seeds N] [--cache DIR] [--level L0|L1|L2|L3] "
              "[--report FILE] FILE", file=sys.stderr)
        return 2
    try:
        module = G.read(argv[0], subset)
        rows, cfg, reached = (levels(module, seeds, cache, subset) if level or out
                              else (*verify(module, seeds, cache, subset), None))
    except ParseError as e:
        print(f"{argv[0]}:{e.line}:{e.col}: {e.code}: {e.reason}")
        return 1
    except ValueError as e:  # tier 0 failed, so there are no goals to generate
        print("\n".join(f"{argv[0]}:{d}" for d in str(e).splitlines()))
        return 1
    for r in rows:
        if r["verdict"] != "proved":
            print(f"{r['verdict']}  {r['family']}  {r['node']}")
    proved = sum(r["verdict"] == "proved" for r in rows)
    print(f"{argv[0]}: {len(rows)} goals, {proved} proved, {sum(r['cached'] for r in rows)} from the cache, "
          f"{sum(r['units'] for r in rows if not r['cached']):,} units spent")
    if reached:
        print(f"{argv[0]}: reached {reached['level']}: {len(reached['tested'])} tested, {len(reached['untested'])} neither "
              f"proved nor tested, {len(reached['refuted'])} refuted, {len(reached['uncounted'])} proofs that don't count for L2")
    if out:
        out.write_text(json.dumps(report(module, rows, cfg, reached, unsigned(argv[0], module, subset)), indent=2) + "\n")
    if level:
        return 0 if reached["level"][:2] >= level else 1
    return 0 if proved == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
