"""WP5's verifier: goals from WP3's types, cached and reported (D17, D22-D25, D63).

    uv run --no-project b17c/verify.py [--seeds N] [--cache DIR] [--report FILE] FILE

checks every goal of FILE, prints each one that isn't proved, and a summary. A FILE that
fails tier 0 has no goals: its diagnostics are printed instead, as `b17c/check.py` prints them. With
--report it also writes the module's trusted base report as JSON (D25). It exits 0 only
when every goal is proved under the canonical seed and every shuffled seed (D23).

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
from syntax import Form, ParseError, Sym, _head, canonical as canonical_bytes

HERE = Path(__file__).resolve().parent
SEEDS = 10
CACHE = Path(".b17c/cache")
RUNTIME = {"BOUNDS", "OVERFLOW", "DIV", "PRE", "TERM"}  # L2's "no runtime errors" families
# b17c's generated SMT names: constants (x!12), bound variables (k!b3), ghost-fn parameters
# (n!p), and ghost-fn functions and requires (g!fib, p!fib).
GENERATED = re.compile(r"(?<![\w.!])(?:[a-z_][a-z0-9_]*!(?:b?\d+|p)|[gp]![a-z_][a-z0-9_]*)(?![\w.!])")


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


def verify(module, seeds=SEEDS, cache=CACHE):
    """Every goal of module: its node, contract clause, family, verdict, resource units and
    whether it came from the cache, plus the run's configuration. Raises ValueError, listing
    the diagnostics, if module fails tier 0."""
    gen = G.Gen(module)
    goals = gen.check(module)
    hashes, core = H.hashes(module), H.hashes(G.CORE)
    ids, cfg, items = _node_ids(module, G.CORE), config(seeds), set(gen.defs)

    def check(g):
        name, part = g[0], g[6]
        kind, spec, impl = hashes[name]
        d = gen.defs[name]
        own = [d[k] for k in d if k in ("spec", "lemma", "ghost-fn") or part == "impl"]
        deps = [{**core, **hashes}[r][1] for r in set().union(*(_references(x, items) for x in own)) - {name}]
        q = canonical(G.query(gen, g[3], g[4], name))
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

    with cf.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(check, goals))
    rows, seen = [], Counter()
    for g, r in zip(goals, results):
        node = _node(ids, g[5]) + (f" {_node(ids, g[7])}" if g[7] is not None else "")
        seen[(node, g[1])] += 1  # the same node checked twice, as a loop condition is
        rows.append({"node": node + (f" #{seen[(node, g[1])]}" if seen[(node, g[1])] > 1 else ""),
                     "family": g[1], **r})
    return rows, cfg


def report(module, rows, cfg):
    """The module's trusted base report (D24, D25). Until the kernel exists, every proved
    goal is solver-trusted, so a module whose goals all hold is L3-S, not L3."""
    laws = sorted(it.items[1].text for it in G.CORE.items[3:] if _head(it) == "lemma")
    held = lambda r: r["verdict"] == "proved"
    level = ("L3-S" if all(map(held, rows)) else
             "L2-S" if all(held(r) for r in rows if r["family"] in RUNTIME) else "below L2")
    return {
        "module": module.items[1].text,
        "input_sha256": sha256(canonical_bytes(module)),
        "lockfile_sha256": None,  # B17-0 has no imports, so no lockfile yet (D9, D26)
        "level": level,
        **cfg,
        "solver_trusted": [r["node"] for r in rows if held(r)],
        "brittle": [r["node"] for r in rows if r["verdict"].startswith("brittle")],
        "failed": [{"node": r["node"], "family": r["family"], "verdict": r["verdict"]}
                   for r in rows if not held(r) and not r["verdict"].startswith("brittle")],
        "admitted": [],  # B17-0 has no admit or assume
        "axioms": {"core": laws, "encoding": f"b17c prelude {cfg['prelude'][:16]} (D61)"},
    }


def main(argv):
    seeds, cache, out = SEEDS, CACHE, None
    while argv and argv[0] in ("--seeds", "--cache", "--report"):
        flag, val, argv = argv[0], argv[1], argv[2:]
        if flag == "--seeds":
            seeds = int(val)
        elif flag == "--cache":
            cache = Path(val)
        else:
            out = Path(val)
    if len(argv) != 1:
        print("usage: uv run --no-project b17c/verify.py [--seeds N] [--cache DIR] [--report FILE] FILE", file=sys.stderr)
        return 2
    try:
        module = G.read(argv[0])
        rows, cfg = verify(module, seeds, cache)
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
    if out:
        out.write_text(json.dumps(report(module, rows, cfg), indent=2) + "\n")
    return 0 if proved == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
