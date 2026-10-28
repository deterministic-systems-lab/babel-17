"""WP5's verifier, before WP3's types: the goal spike's goals, cached and reported (D17, D22-D25, D63).

    uv run --no-project b17c/verify.py [--seeds N] [--cache DIR] [--report FILE] FILE

checks every goal of FILE, prints each one that isn't proved, and a summary. With
--report it also writes the run's trusted base section as JSON. It exits 0 only when
every goal is proved under the canonical seed and every shuffled seed (D23).

Each goal is sent as its canonical query (interface 11, D63): the spike's SMT-LIB text
with b17c's generated names renamed in order of first occurrence, so alpha-equivalent
definitions send the same bytes. Verdicts are cached under D22's key, so unchanged
code, renamed code and the callers of a changed body are never solved again.
"""
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import goals as G
import hashing as H
from syntax import Form, Sym, _head, parse

HERE = Path(__file__).resolve().parent
SEEDS = 10
CACHE = Path(".b17c/cache")
# b17c's generated SMT names: constants (x!12), bound variables (k!b3), ghost-fn parameters
# (n!p), and ghost-fn functions and requires (g!fib, p!fib).
GENERATED = re.compile(r"(?<![\w.!])(?:[a-z_][a-z0-9_]*!(?:b?\d+|p)|[gp]![a-z_][a-z0-9_]*)(?![\w.!])")


def canonical(query):
    """Interface 11: generated names become k!0, k!1, ... in order of first occurrence (D63)."""
    names = {}
    return GENERATED.sub(lambda m: names.setdefault(m[0], f"k!{len(names)}"), query)


def _sha(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else p.encode())
        h.update(b"\0")
    return h.hexdigest()


def config(seeds):
    """D22's verification configuration: b17c, the prelude, the solver and its options."""
    z3 = subprocess.run(["z3", "--version"], capture_output=True, text=True).stdout.strip()
    binary = subprocess.run(["which", "z3"], capture_output=True, text=True).stdout.strip()
    return {
        "b17c": _sha(*(Path(HERE, f).read_bytes() for f in ("goals.py", "verify.py")))[:16],
        "prelude": _sha(G.PRELUDE, G.VDIV, (HERE / "core.b17").read_bytes())[:16],
        "solver": z3,
        "solver_sha256": _sha(Path(binary).read_bytes())[:16] if binary else "",
        "budget": G.RLIMIT,
        "seeds": seeds,
    }


def _node_ids(module):
    """id(node) -> D56's node ID prefix: the item's kind and name, and the child-index path."""
    ids = {}

    def walk(x, item, path):
        ids[id(x)] = (item, path)
        if isinstance(x, Form):
            for k, c in enumerate(x.items):
                walk(c, item, path + (k,))

    for it in module.items[3:]:
        walk(it, f"{it.items[0].text} {it.items[1].text}", ())
    return ids


def _node(ids, x):
    item, path = ids.get(id(x), ("module", ()))
    return f"{item}{'/' + '.'.join(map(str, path)) if path else ''}@{x.pos[0]}:{x.pos[1]}"


def _references(x, names):
    if isinstance(x, Sym):
        return {x.text} & names
    return set().union(*(_references(c, names) for c in x.items)) if isinstance(x, Form) else set()


def verify(module, seeds=SEEDS, cache=CACHE):
    """Every goal of module: its node, family, verdict, resource units and whether it came
    from the cache, plus the run's configuration."""
    gen = G.Gen(module)
    goals = gen.check(module)
    hashes, ids, cfg = H.hashes(module), _node_ids(module), config(seeds)
    items = set(gen.defs)
    cfg_key = json.dumps(cfg, sort_keys=True)

    def key(g):
        name, part = g[0], g[6]
        kind, spec, impl = hashes[name]
        d = gen.defs[name]
        own = [d[k] for k in d if (k in ("spec", "lemma", "ghost-fn") or part == "impl")]
        deps = sorted(hashes.get(r, H.hashes(G.CORE).get(r, ("", "", None)))[1]
                      for r in set().union(*(_references(x, items) for x in own)) - {name})
        q = canonical(G.query(gen, g[3], g[4], name))
        return _sha("b17c-proof 0", spec if part == "spec" or impl is None else impl, *deps, q, cfg_key), q

    def check(g):
        k, q = key(g)
        path = Path(cache, k[:2], k + ".json")
        if path.exists():
            return json.loads(path.read_text()) | {"cached": True}
        verdict, units = G.solve_stats(q)
        held = 0
        if verdict == "proved":
            held = sum(G.solve(q, s) == "proved" for s in range(1, seeds + 1))
            if held < seeds:
                verdict = f"brittle: proved under {held} of {seeds} shuffled seeds"
        out = {"verdict": verdict, "units": units}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out))
        return out | {"cached": False}

    with cf.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(check, goals))
    rows = [{"node": _node(ids, g[5]), "family": g[1], **r} for g, r in zip(goals, results)]
    return rows, cfg


def report(module, rows, cfg):
    """The run's part of the trusted base report (D24, D25): goals by node ID, and the
    axioms they rest on. Until the kernel exists, every proved goal is solver-trusted."""
    laws = sorted(it.items[1].text for it in G.CORE.items[3:] if _head(it) == "lemma")
    by = lambda pred: [r["node"] for r in rows if pred(r["verdict"])]
    return {
        "module": module.items[1].text,
        **cfg,
        "solver_trusted": by(lambda v: v == "proved"),
        "brittle": by(lambda v: v.startswith("brittle")),
        "failed": [{"node": r["node"], "family": r["family"], "verdict": r["verdict"]}
                   for r in rows if r["verdict"] != "proved" and not r["verdict"].startswith("brittle")],
        "admitted": [],
        "axioms": {"core": laws, "encoding": f"b17c prelude {cfg['prelude']} (D61)"},
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
    module = parse(Path(argv[0]).read_bytes())
    rows, cfg = verify(module, seeds, cache)
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
