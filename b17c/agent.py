"""WP6, the agent protocol: diagnostics in interface 3's schema, and interface 8's five queries (D93, D94).

    uv run --no-project b17c/agent.py [--subset 0|1] [--seeds N] [--cache DIR] check FILE
    uv run --no-project b17c/agent.py [--subset 0|1] [--seeds N] [--cache DIR] obligations FILE NAME
    uv run --no-project b17c/agent.py [--subset 0|1] explain CODE
    uv run --no-project b17c/agent.py [--subset 0|1] [--seeds N] [--cache DIR] impact FILE CHANGED
    uv run --no-project b17c/agent.py [--subset 0|1] [--seeds N] [--cache DIR] search FILE QUERY
    uv run --no-project b17c/agent.py [--subset 0|1] simulate FILE NAME ARG...

Each prints one JSON document. CHANGED is a module whose items replace FILE's items of the
same kind and name. QUERY is a module holding one spec; search finds FILE's specs that
guarantee it. Each ARG of simulate is a closed expression, as for interp.py. The subset is
B17-1 by default, the newest frozen one, and B17-0 with --subset 0 (D101, D112).
"""
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

import check as C
import goals as G
import interp as I
import verify as V
from syntax import SUBSET, Form, ParseError, Sym, _head, _print, parse

ROOT = Path(__file__).resolve().parent.parent
MIN = "-9223372036854775808"
SHOWN = 8  # sequence elements a counterexample shows; a longer one shows its length and a prefix


# Interface 3: diagnostics.

def diagnostics(module, seeds=V.SEEDS, cache=V.CACHE, subset=SUBSET):
    """Every tier 0 error of module, or once tier 0 passes, every goal that isn't proved."""
    if errors := tier0(module, subset):
        return errors
    gen, goals, rows, _ = V.verify_goals(module, seeds, cache, subset)
    out = []
    for g, r in zip(goals, rows):
        if r["verdict"] == "proved":
            continue
        d = {"code": f"E-PROOF-{g[1]}", "severity": "error", "node": r["node"],
             "message": f"the {g[1]} goal is {r['verdict']}", "goal": goal_text(gen, g)}
        if r["verdict"] in ("failed", "unknown") and (cex := counterexample(module, gen, g, subset)):
            d["counterexample"], d["reproduced"] = cex
        d |= {"context": context(gen, g), "repairs": [],  # typed edits wait for interface 2 (WP2)
              "dependents": sum(g[4] in h[3] for h in goals if h is not g and h[0] == g[0] and h[6] == g[6]),
              "budget_used": r["units"]}
        out.append(d)
    return out


def goal_text(gen, g):
    """The goal as a B17-0 ghost expression over the program's own names."""
    family, x, clause = g[1], g[5], g[7]
    h, a = _head(x), x.items[1:] if isinstance(x, Form) else ()
    p = lambda *parts: " ".join(map(_print, parts))
    if family == "BOUNDS":
        if h in ("idx", "set-idx"):
            return f"(and (<= 0 {p(a[1])}) (< {p(a[1])} (len {p(a[0])})))"
        if h in ("take", "drop"):
            return f"(and (<= 0 {p(a[1])}) (<= {p(a[1])} (len {p(a[0])})))"
        if h == "last":
            return f"(> (len {p(a[0])}) 0)"
        if h == "seq-build":
            return f"(>= {p(a[0])} 0)"
    if family == "OVERFLOW":
        return f"(in_i64 {p(x)})"
    if family == "DIV":
        nonzero = f"(!= {p(a[1])} 0)"
        return nonzero if id(x) in gen.ghost else f"(and {nonzero} (not (and (== {p(a[0])} {MIN}) (== {p(a[1])} -1))))"
    if family == "ASSERT":  # an obtain's goal is its ∃ (docs/b17-1.md §9)
        return f"(exists {p(a[0])} {p(a[1])})" if h == "obtain" else p(a[0])
    if family == "BOUNDS" and h == "lookup":  # a map lookup's key is in the map
        return f"(contains {p(a[0])} {p(a[1])})"
    if family == "FIELD":  # the value was built by the constructor that has the field
        item = gen.datas[gen.types[id(a[0])][1]]
        ctor = next(c.items[0] for c in item.items[3:] if any(f.items[0].text == a[1].text for f in c.items[1:]))
        return f"(is {p(ctor)} {p(a[0])})"
    if family == "PRE":  # the callee's requires at the call's arguments
        callee = x.items[1].text if h == "call" else h
        f = next(iter(gen.defs[callee].values()))
        params = f.items[2].items if _head(f) == "ghost-fn" else G.clauses(f, "params")[0]
        args = dict(zip((q.items[0].text for q in params), x.items[2:] if h == "call" else x.items[1:]))
        reqs = [clause] if clause is not None else [c for cl in G.clauses(f, "requires") for c in cl]
        text = [p(_subst(c, args)) for c in reqs]
        return text[0] if len(text) == 1 else f"(and {' '.join(text)})"
    if family == "TERM":  # §9: a loop's measure starts ≥ 0 and drops across a pass; a recursive call descends
        if clause is not None:  # D93: "D falls across a pass", the one goal B17-0 can't write, having no old values
            return f"(decreases {p(x)})"
        if h != "call" and h != g[0]:  # a loop's measure, which may itself call a ghost-fn
            return f"(<= 0 {p(x)})"
        callee = x.items[1].text if h == "call" else h
        item = gen.defs[callee]
        d = next(c.items[1] for f in item.values() for c in f.items if _head(c) == "decreases")
        params = next(G.clauses(f, "params")[0] if _head(f) in ("spec", "lemma") else f.items[2].items
                      for f in item.values() if _head(f) in ("spec", "lemma", "ghost-fn"))
        args = dict(zip((q.items[0].text for q in params), x.items[2:] if h == "call" else x.items[1:]))
        return f"(and (<= 0 {p(_subst(d, args))}) (< {p(_subst(d, args))} {p(d)}))"
    return p(clause if clause is not None else x)


def _subst(x, env):
    """x with each name in env replaced by its expression, or x unchanged when one of its
    binders would capture a name an expression uses."""
    def names(y):
        return {y.text} if not isinstance(y, Form) and hasattr(y, "text") else set().union(*map(names, y.items)) if isinstance(y, Form) else set()
    def binders(y):
        if not isinstance(y, Form):
            return set()
        own = {b.items[0].text for b in y.items[1].items} if _head(y) in ("forall", "exists") else \
              {y.items[1].items[0].text} if _head(y) == "fn" else set()
        return own.union(*map(binders, y.items))
    if binders(x) & set().union(*map(names, env.values())):
        return x
    def go(y):
        if isinstance(y, Form):
            return Form(tuple(go(c) for c in y.items), y.pos, y.end)
        return env.get(getattr(y, "text", None), y)
    return go(x)


def context(gen, g):
    """The goal's item and every item it refers to: the slice an agent needs to fix it."""
    name, items = g[0], set(gen.defs)
    own = list(gen.defs[name].values())
    refs = set().union(*(V._references(x, items) for x in own)) - {name}
    return [f"{k} {name}" for k in gen.defs[name]] + sorted(f"{next(iter(gen.defs[r]))} {r}" for r in refs)


def counterexample(module, gen, g, subset=SUBSET):
    """The solver's model of a failed goal, as the item's parameter values, and whether a checked
    run of the def on them fails too (D57). None when no parameter appears in the query, or a
    parameter's type can't be shown. A tuple or data value is a B17-1 term, such as
    "(node 5 (leaf) (leaf))", which a run reads as simulate reads its arguments (D112)."""
    q = _trimmed(G.query(gen, g[3], g[4], g[0]))
    # A validity predicate's axioms (D103, D105) quantify over every value of a data type, so Z3
    # never builds a model under them. Without them a model may break an i64 range, which
    # the check below and the interpreter's run then catch.
    oks = set(gen.oks.values())
    q = "\n".join(l for l in q.split("\n") if not (l.startswith("(assert (forall") and oks & set(G.TOKEN.findall(l))))
    used = set(G.TOKEN.findall(q))
    names = {smt: c for d in gen.dts.values() for c, (smt, _) in d["ctors"].items()}
    shapes, terms, cex = {}, [], {}
    complete = True
    for name, (t, typ) in g[8].items():
        ty, srt = gen.ty(typ), gen.sort(typ)
        if t not in used:  # the goal doesn't constrain it, so any value will do
            cex[name] = False if srt == "Bool" else 0 if srt == "Int" else [] if ty[0] in C.SEQUENCES else None
            complete &= cex[name] is not None
            continue
        if _shown(gen, ty):
            ts = [t]
        elif ty[0] in C.SEQUENCES and _shown(gen, ty[1]):
            ts = [G.fn("len", srt, t)] + [G.fn("nth", srt, t, str(k)) for k in range(SHOWN)]
        else:  # a set, map or multiset, or a sequence inside a value: no model term shows it
            return None
        shapes[name], terms = (len(terms), len(ts)), terms + ts
    values = []
    if terms:
        r = subprocess.run(["z3", f"rlimit={G.RLIMIT}", "-T:60", "-in"], input=f"{q}\n(get-value ({' '.join(terms)}))",
                           capture_output=True, text=True)
        lines = r.stdout.strip().split("\n", 1)
        if lines[0] not in ("sat", "unknown") or len(lines) < 2 or lines[1].startswith("(error") or "(let " in lines[1]:
            return None
        values = [_smt_value(pair[1], names) for pair in _sexp(lines[1])]
        if any(not -2 ** 63 <= int(n) < 2 ** 63 for v in values if isinstance(v, str) for n in re.findall(r"-?\d+", v)):
            return None  # a value outside its type, which the dropped validity axioms rule out
    for name, (start, n) in shapes.items():
        vs = values[start:start + n]
        if n == 1:
            cex[name] = vs[0]
        else:
            length, elems = vs[0], vs[1:1 + min(vs[0], SHOWN)]
            cex[name] = elems if length <= SHOWN else {"len": length, "prefix": elems}
            complete &= length <= SHOWN
    reproduced = None
    cex = {k: cex[k] for k in g[8]}  # in parameter order
    if g[6] == "impl" and "def" in gen.defs[g[0]] and complete:
        try:
            args = [[_read(module, x, subset) for x in v] if isinstance(v, list) else _read(module, v, subset)
                    for v in cex.values()]
            out = I.run(module, g[0], args, check=True, subset=subset)
            reproduced = not isinstance(out, I.Ok)
        except ValueError:
            pass
    return cex, reproduced


def _shown(gen, t, seen=()):
    """Whether a model term shows a value of type t: a bool, an integer, or a tuple or data value
    with no sequence, set, map or multiset inside, whose terms name every part."""
    if t in (C.BOOL, C.I64, C.INT):
        return True
    if t[0] == "tuple":
        return all(_shown(gen, u, seen) for u in t[1:])
    if t[0] == "data":
        return t in seen or all(_shown(gen, f[2], seen + (t,)) for _, fs in gen.data(t)["ctors"].values() for f in fs)
    return False


def _read(module, v, subset):
    """A counterexample's value as the interpreter runs it: a term is read as simulate's arguments are."""
    return I.value(module, v, subset) if isinstance(v, str) else v


def _trimmed(q):
    """q with only the prelude axioms whose symbols its own part uses. The full prelude's
    quantifiers keep Z3 from ever answering sat, so it gives no model. This is only for finding
    one: the verdict still comes from the full query, and the interpreter checks the model."""
    prelude = q[:len(G.PRELUDE)]
    forms, depth, start = [], 0, 0
    for k, ch in enumerate(prelude):
        if ch == "(":
            depth, start = depth + 1, start if depth else k
        elif ch == ")":
            depth -= 1
            if not depth:
                forms.append(prelude[start:k + 1])
    declared = {m[1] for f in forms if (m := G.DEFINES.match(f))}
    used = set(G.TOKEN.findall(q[len(G.PRELUDE):])) & declared
    keep = [f for f in forms if not f.startswith("(assert") or set(G.TOKEN.findall(f)) & declared <= used]
    return "\n".join(keep) + "\n" + q[len(G.PRELUDE):]


def _sexp(text):
    tokens, stack = re.findall(r"\(|\)|[^\s()]+", text), [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t)
    return stack[0][0]


def _smt_value(v, names=None):
    """A model value: a bool or an integer, or a tuple or data value as a B17-1 term."""
    if not isinstance(v, list):
        return v == "true" if v in ("true", "false") else int(v) if v.lstrip("-").isdigit() else f"({names[v]})"
    if v[0] == "-":  # (- n)
        return -int(v[1])
    head = "tuple" if v[0].startswith("mk.T") else names[v[0]]
    return "(" + " ".join([head] + [str(x).lower() if isinstance(x, bool) else str(x) for x in (_smt_value(y, names) for y in v[1:])]) + ")"


# Interface 8: the five queries.

def obligations(module, name, seeds=V.SEEDS, cache=V.CACHE, subset=SUBSET):
    """Every proof goal of the item name, with its verdict."""
    gen, goals, rows, _ = V.verify_goals(module, seeds, cache, subset)
    if name not in gen.defs:
        raise ValueError(f"no item named {name!r}")
    return [{"node": r["node"], "family": r["family"], "goal": goal_text(gen, g), "verdict": r["verdict"],
             "cached": r["cached"], "budget_used": r["units"]} for g, r in zip(goals, rows) if g[0] == name]


def explain(code, subset=SUBSET):
    """The rule behind a code, from docs/b17-0.md and, in B17-1, docs/b17-1.md, whose table
    changes it where it says so, with the suite's labelled program for it."""
    docs = [(ROOT / "docs" / n).read_text() for n in ("b17-0.md", "b17-1.md")[:subset + 1]]
    rules = {}
    for doc in docs:  # B17-1's rows come second, so they replace B17-0's
        for first, last, text in re.findall(r"^\| `(E-[A-Z0-9-]+)`(?: to `(E-[A-Z0-9-]+)`)? \| (.+?) \|$", doc, re.M):
            if last:  # a range, such as E-OWN-001 to E-OWN-006
                stem, lo, hi = first[:-3], int(first[-3:]), int(last[-3:])
                rules |= {f"{stem}{k:03}": text for k in range(lo, hi + 1)}
            else:
                rules[first] = text
    if code not in rules:
        raise ValueError(f"no code {code!r} in {' or '.join(('docs/b17-0.md', 'docs/b17-1.md')[:subset + 1])} §9")
    # A rule's own statement, where the text gives one with the code in parentheses (§5, §7).
    details = [s.strip() for doc in docs for s in re.findall(rf"^\s*(?:\d+\.|-) (.*?\(`{re.escape(code)}`.*?)$", doc, re.M)]
    suites = [ROOT / "suite" / "b17-1" / "reject"][:subset] + [ROOT / "suite" / "reject"]
    examples = [f for d in suites for f in sorted(d.glob(f"{code}-*.b17"))]
    return {"code": code, "rule": rules[code], "details": details,
            "examples": [{"file": str(f.relative_to(ROOT)), "program": f.read_text()} for f in examples[:1]]}


def impact(module, changed, seeds=V.SEEDS, cache=V.CACHE, subset=SUBSET):
    """Which goals break when changed's items replace module's: callers first, then the items
    themselves. A goal breaks when it was proved before and isn't now."""
    new = {(it.items[0].text, it.items[1].text): it for it in changed.items[3:]}
    items = tuple(new.pop((it.items[0].text, it.items[1].text), it) for it in module.items[3:])
    if new:
        raise ValueError("not in the module: " + ", ".join(f"{k} {n}" for k, n in new))
    after = Form(module.items[:3] + items, module.pos, module.end)
    names = {it.items[1].text for it in changed.items[3:]}
    if diags := tier0(after, subset):
        return {"changed": sorted(names), "tier0": diags}
    key = lambda r: (re.sub(r"@\d+:\d+", "", r["node"]), r["family"])  # paths survive moves; positions don't (D56)
    before = {key(r): r["verdict"] for r in V.verify(module, seeds, cache, subset)[0]}
    broken = [r for r in V.verify(after, seeds, cache, subset)[0] if r["verdict"] != "proved"
              and before.get(key(r), "proved") == "proved"]
    return {"changed": sorted(names),
            "callers": sorted({_item(r["node"]) for r in broken} - names),
            "broken": [{"node": r["node"], "family": r["family"], "verdict": r["verdict"]}
                       for r in sorted(broken, key=lambda r: _item(r["node"]) in names)]}


def tier0(module, subset=SUBSET):
    """module's tier 0 errors, as interface 3 diagnostics."""
    ids = V._node_ids(module, G.CORE)
    return [{"code": d.code, "severity": "error", "node": V._node(ids, d.node), "message": d.message}
            for d in C.check(module, subset)]


def search(module, query, seeds=V.SEEDS, cache=V.CACHE, subset=SUBSET):
    """The module's specs that guarantee the query spec: the same parameter and result types in
    order, and a probe that implements the query by calling the candidate verifies (D94)."""
    if len(query.items) != 4 or _head(query.items[3]) != "spec":
        raise ValueError("a query module holds exactly one spec")
    q = query.items[3]
    params, results = (G.clauses(q, k)[0] for k in ("params", "returns"))
    items = {it.items[1].text for it in module.items[3:]}
    if clash := sorted({p.items[0].text for p in params + results} & items):
        raise ValueError(f"the query's names {', '.join(clash)} are also FILE's items (D41)")
    taken = items | {p.items[0].text for p in params + results}

    def fresh(base):
        name = next(f"{base}_{n}" for n in itertools.count() if f"{base}_{n}" not in taken)
        taken.add(name)
        return name
    probe_name = fresh("query")  # the probe's spec and def, named apart from FILE's items
    spec = _print(Form((q.items[0], Sym(probe_name, q.items[1].pos)) + q.items[2:], q.pos, q.end))
    found = [fresh("found") for _ in results]
    sig = lambda s: [tuple(_print(p.items[1]) for p in G.clauses(s, k)[0]) for k in ("params", "returns")]
    out = []
    for cand in module.items[3:]:
        if _head(cand) != "spec" or sig(cand) != sig(q):
            continue
        name = cand.items[1].text
        args = " ".join(p.items[0].text for p in params)
        binds = " ".join(f"({f} {_print(r.items[1])})" for f, r in zip(found, results))
        body = (f"(let ({binds}) (call {name} {args})) (return {' '.join(found)})" if results
                else f"(call {name} {args}) (return)")
        probe = parse(f"(module probe (header (purpose \"p\") (invariants \"i\") (failures \"f\")) "
                      f"{spec} (def {probe_name} (body {body})))".encode(), subset)
        trial = Form(module.items + probe.items[3:], module.pos, module.end)
        if diags := tier0(trial, subset):
            same = [d for d in diags if "is identical to" in d["message"] and f"'{name}'" in d["message"]]
            out.append({"name": name, "guarantees": bool(same) and len(same) == len(diags),
                        "why": "identical spec" if same else [d["code"] for d in diags]})
            continue
        # Every goal of the probe counts: its def's, and its spec's own well-definedness.
        failed = [r["family"] for r in V.verify(trial, seeds, cache, subset)[0]
                  if _item(r["node"]) == probe_name and r["verdict"] != "proved"]
        out.append({"name": name, "guarantees": not failed, **({"why": failed} if failed else {})})
    return {"query": q.items[1].text, "candidates": sorted(out, key=lambda c: not c["guarantees"])}


def _item(node):
    """The item a node ID belongs to: `def two/2.2@5:45 ...` is `two`."""
    return re.match(r"[a-z-]+ ([a-z][a-z0-9_]*)", node)[1]


def simulate(module, name, args, subset=SUBSET):
    """A checked run of def name in the reference interpreter (D57), as interface 10 reports it."""
    out = I.run(module, name, [I.value(module, a, subset) for a in args], check=True, subset=subset)
    kind = type(out).__name__.lower()
    fields = {k: _json(getattr(out, k)) for k in out.__dataclass_fields__ if k not in ("trace", "unchecked")}
    return {"outcome": kind, **fields, "trace": [_json(v) for v in out.trace],
            "unchecked": [{"kind": u.kind, "clause": str(u.clause), "node": str(u.node)} for u in out.unchecked],
            "text": I.text_of(out)}


def _json(v):
    if isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, (tuple, list)):
        return [_json(x) for x in v]
    return str(v)


def main(argv):
    seeds, cache, subset = V.SEEDS, V.CACHE, SUBSET
    while argv[:1] in (["--subset"], ["--seeds"], ["--cache"]) and len(argv) > 1:
        if argv[0] == "--subset" and argv[1] in ("0", "1"):
            subset = int(argv[1])
        elif argv[0] == "--seeds":
            seeds = int(argv[1])
        elif argv[0] == "--cache":
            cache = Path(argv[1])
        else:
            print(__doc__, file=sys.stderr)
            return 2
        argv = argv[2:]
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "explain" and len(args) == 1:
            result = explain(args[0], subset)
        elif cmd == "check" and len(args) == 1:
            result = diagnostics(G.read(args[0], subset), seeds, cache, subset)
        elif cmd == "obligations" and len(args) == 2:
            result = obligations(G.read(args[0], subset), args[1], seeds, cache, subset)
        elif cmd in ("impact", "search") and len(args) == 2:
            a, b = G.read(args[0], subset), G.read(args[1], subset)
            result = {"impact": impact, "search": search}[cmd](a, b, seeds, cache, subset)
        elif cmd == "simulate" and len(args) >= 2:
            result = simulate(G.read(args[0], subset), args[1], args[2:], subset)
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except ParseError as e:
        if cmd != "check":  # a query can't run on a module that doesn't parse (D94)
            print(json.dumps({"error": f"{e.code} at {e.line}:{e.col}: {e.reason}"}, indent=2))
            return 2
        result = [{"code": e.code, "severity": "error", "node": f"module@{e.line}:{e.col}", "message": e.reason}]
    except ValueError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 1 if cmd == "check" and result else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
