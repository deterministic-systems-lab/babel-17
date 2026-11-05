"""WP4b's spec workbench, the design spec's `mfl spec` (D121): checks that a spec says what's meant.

    uv run --no-project b17c/spec.py [--subset 0|1] vacuity FILE
    uv run --no-project b17c/spec.py [--subset 0|1] witness FILE NAME
    uv run --no-project b17c/spec.py [--subset 0|1] [--seeds N] mutants FILE NAME
    uv run --no-project b17c/spec.py [--subset 0|1] english FILE
    uv run --no-project b17c/spec.py [--subset 0|1] sign FILE NAME REVIEWER
    uv run --no-project b17c/spec.py [--subset 0|1] unsigned FILE

Each prints JSON, and exits 1 when it finds a problem.
- vacuity: each spec's and lemma's requires can hold, and no spec's ensures clause follows from them alone.
- witness: D88's first inputs for spec NAME, each with the output its def gives and nearby outputs
  the spec forbids, or, with no def, whether any output meets the ensures.
- mutants: small bugs put in def NAME, each killed by a property test or the verifier, or surviving.
- english: Codex renders each spec in plain English and lists where they and the module's header
  disagree (back-translation). Its reply isn't deterministic, so it's recorded with the model.
- sign records a reviewer's signature on spec NAME's hash, beside FILE; unsigned lists the specs
  with none. Editing a spec, or a ghost-fn it uses, changes its hash, so its signature lapses.

A requires no input meets, or an input no output serves, comes with a spec challenge (interface 9).
"""
import datetime
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import check as C
import goals as G
import hashing as H
import interp as I
import verify as V
from syntax import SUBSET, Form, Int, ParseError, Sym, _head, _print, canonical, parse

WITNESSES = 3    # inputs per witness report
OUTPUTS = 1_000  # D88 draws of outputs that a spec with no def is searched with, per input
# The harness's Codex, with no tools, its reply read from a file (D121).
CODEX = ["codex", "exec", "--ignore-user-config", "--ephemeral", "--ignore-rules", "--disable", "shell_tool",
         "--disable", "unified_exec", "-m", "gpt-5.6-sol", "-c", "model_reasoning_effort=high", "-s", "read-only",
         "--skip-git-repo-check", "-o", "{reply}", "-"]


def _items(module, kinds):
    return [it for it in module.items[3:] if it.items[0].text in kinds]


def _seed(module, name, subset):
    """D88's seed for spec name: its spec hash's first 16 hex digits."""
    return int(H.hashes(module, subset)[name][1].split(":")[1][:16], 16)


def _challenge(kind, module, name, subset, query, **evidence):
    """A spec challenge (interface 9, D121): the proof that a spec can't be met."""
    return {"kind": kind, "spec": name, "spec_hash": H.hashes(module, subset)[name][1],
            "query_sha256": hashlib.sha256(V.canonical(query).encode()).hexdigest(), "verdict": "proved", **evidence}


def _state(gen, item):
    """A state with item's parameters and its requires as facts."""
    st = G.State({}, [])
    gen.item, gen.part = (item.items[1].text, None, ()), "spec"
    gen.params(st, G.clauses(item, "params")[0])
    for c in [c for cl in G.clauses(item, "requires") for c in cl]:
        st.facts.append(gen.expr(c, st, True)[0])
    return st


def vacuity(module, subset=SUBSET):
    """For each spec and lemma: whether its requires can hold, shown by the solver or by one of D88's
    inputs; and for a spec, each ensures clause that its requires and the results' types prove alone.
    A lemma's claim always follows from its requires, so proving one alone only shows it isn't needed."""
    gen, out = G.Gen(module, subset), []
    gen.quiet = True  # the item's goals are verify.py's; these queries are of their own
    for it in _items(module, ("spec", "lemma")):
        kind, name = it.items[0].text, it.items[1].text
        st = _state(gen, it)
        q = G.query(gen, st.facts, "false")
        v, _ = G.solve_stats(q)
        entry = {"item": f"{kind} {name}"}
        if v == "proved":
            entry["requires"] = {"verdict": "vacuous", "challenge": _challenge("requires-unsatisfiable", module, name, subset, q)}
        elif v == "failed":
            entry["requires"] = {"verdict": "satisfiable", "by": "solver"}
        else:  # a lemma's parameters may be ghost types, which D88 doesn't draw
            found = I.spec_inputs(module, name, _seed(module, name, subset), 1, subset) if kind == "spec" else []
            entry["requires"] = ({"verdict": "satisfiable", "by": "input", "input": [I._term(a) for a in found[0]]}
                                 if found else {"verdict": "unknown", "solver": v})
        for p in G.clauses(it, "returns")[0] if kind == "spec" else ():
            gen.var(st, p.items[0].text, p.items[1])  # results with only their types' facts
        entry["ensures"] = []
        for c in [c for cl in G.clauses(it, "ensures") for c in cl] if kind == "spec" else ():  # each trivial under a vacuous requires
            s = st.copy()
            t, _ = gen.expr(c, s, True)
            v = G.solve_stats(G.query(gen, s.facts, t))[0] if entry["requires"]["verdict"] != "vacuous" else None
            entry["ensures"].append({"clause": _print(c), "trivial": None if v is None else v == "proved"})
        out.append(entry)
    return out


def _smt(gen, v, t):
    """Interpreter value v of type t as an SMT term."""
    t = gen.ty(t)
    if t == C.BOOL:
        return "true" if v else "false"
    if t in (C.I64, C.INT):
        return G.num(v)
    if t[0] in C.SEQUENCES:
        srt = gen.tsort(t)
        out = G.fname("empty", srt)
        for x in v:
            out = G.fn("cat", srt, out, G.fn("unit", srt, _smt(gen, x, t[1])))
        return out
    if t[0] == "tuple":
        return f"(mk.{gen.tuple(len(t) - 1)} {' '.join(_smt(gen, x, u) for x, u in zip(v.items, t[1:]))})"
    c, fs = gen.ctor(t, v.ctor)
    return G.app(c, [_smt(gen, x, f[2]) for x, f in zip(v.fields, fs)])


def _nearby(v, t, small):
    """Values of ground type t a step from v: each a likely bug's output."""
    h = t[0]
    if h == "bool":
        return [not v]
    if h == "i64":
        return [x for x in (v + 1, v - 1) if I.MIN <= x <= I.MAX]
    if h in ("vec", "slice"):
        out = [v[:-1], v + v[-1:]] if v else [(small(t[1]),)]
        out += [(w,) + v[1:] for w in _nearby(v[0], t[1], small)[:1]] if v else []
        k = next((k for k in range(len(v) - 1) if v[k] != v[k + 1]), None)
        return out + ([v[:k] + (v[k + 1], v[k]) + v[k + 2:]] if k is not None else [])
    if h == "tuple":
        return [I.Tup(v.items[:k] + (w,) + v.items[k + 1:]) for k, u in enumerate(t[1:]) for w in _nearby(v.items[k], u, small)[:1]]
    return [x for x in small(t, other=v.ctor)] + [
        I.Data(v.ctor, v.fields[:k] + (w,) + v.fields[k + 1:]) for k, u in enumerate(small(t, fields=v.ctor))
        for w in _nearby(v.fields[k], u, small)[:1]]


def _leaves(v):
    """The integers and booleans in a value, in order."""
    if isinstance(v, int):
        return [abs(int(v))]
    return [x for part in (v.items if isinstance(v, I.Tup) else v.fields if isinstance(v, I.Data) else v) for x in _leaves(part)]


def _readable(args):
    """A witness input reads best with small integers and a few of them: sort key, least first."""
    xs = _leaves(args)
    return max(xs, default=0) > 10, -min(len(xs), 4), sum(xs)


def witness(module, name, subset=SUBSET, k=WITNESSES):
    """The k smallest of D88's first inputs for spec name, each with its def's output and the nearby outputs the
    spec forbids, with the clause each breaks, and any nearby ones it also allows. With no def, each
    says whether an output meets the ensures: if none does, that's a spec challenge."""
    spec = I._spec(module, name)
    has_def = any(it.items[1].text == name for it in _items(module, ("def",)))
    p = I._Program(module, subset)
    draws = I._Draws(p, 0)

    def small(t, other=None, fields=None):  # a type's smallest value, another constructor's, or a constructor's field types
        if other is None and fields is None:
            return draws.smallest(t)[1]
        ctors = draws.ctors(t)
        if fields is not None:
            return next(fs for c, fs in ctors if c == fields)
        return [I.Data(c, tuple(draws.smallest(f)[1] for f in fs)) for c, fs in ctors
                if c != other and all(draws.smallest(f) for f in fs)]

    gen, types = G.Gen(module, subset), [I._ground(t, {}) for t in I._types(I._clauses(spec, "returns"))]
    gen.quiet = True
    out = []
    kept = I.spec_inputs(module, name, _seed(module, name, subset), I.KEPT, subset)  # the tests' inputs
    for args in sorted(dict.fromkeys(kept), key=_readable)[:k]:
        entry = {"input": [I._term(a) for a in args]}
        if has_def:
            r = I.run(module, name, args, check=True, subset=subset)
            if not isinstance(r, I.Ok):
                entry["outcome"] = I.text_of(r)
                out.append(entry)
                continue
            entry["allowed"] = [I._term(v) for v in r.results]
            entry["forbidden"], entry["also_allowed"] = [], []
            for j, (v, t) in enumerate(zip(r.results, types)):
                for w in _nearby(v, t, small):
                    res = r.results[:j] + (w,) + r.results[j + 1:]
                    ens = [(e, x) for kind, e, x in I.holds(module, name, args, res, subset) if kind == "ensures"]
                    bad = next((e for e, x in ens if x is False), None)
                    if bad is not None:
                        entry["forbidden"].append({"output": [I._term(x) for x in res], "breaks": _print(bad)})
                    elif all(x is True for _, x in ens):
                        entry["also_allowed"].append([I._term(x) for x in res])
        else:  # does any output meet the ensures at this input?
            st = G.State({}, [])
            gen.item, gen.part = (name, None, ()), "spec"
            for prm, a in zip(G.clauses(spec, "params")[0], args):
                st.facts.append(f"(= {gen.var(st, prm.items[0].text, prm.items[1])} {_smt(gen, a, prm.items[1])})")
            for prm in G.clauses(spec, "returns")[0]:
                gen.var(st, prm.items[0].text, prm.items[1])
            facts = st.facts + [gen.expr(c, st, True)[0] for cl in G.clauses(spec, "ensures") for c in cl]
            q = G.query(gen, facts, "false")
            v, _ = G.solve_stats(q)
            if v == "proved":
                entry["output"], entry["challenge"] = "none", _challenge("no-output", module, name, subset, q, input=entry["input"])
                out.append(entry)
                continue
            # The solver rarely finds a model under the sequence axioms, so look for an output instead.
            found = next((res for res in (tuple(draws.value(t) for t in types) for _ in range(OUTPUTS))
                          if all(x is True for kind, _, x in I.holds(module, name, args, res, subset) if kind == "ensures")), None)
            entry["output"] = "exists" if v == "failed" or found else "unknown"
            if found:
                entry["allowed"] = [I._term(x) for x in found]
        out.append(entry)
    return out


OPS = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "==", "+": "-", "-": "+", "and": "or", "or": "and"}
GHOST = {"invariant", "decreases", "assert", "ghost-let", "ghost-let-mut", "ghost-set", "forall", "obtain"}
DROPPED = {"set", "set-idx", "push", "print"}  # statements a mutant may leave out


def _mutations(x, lemmas, path=()):
    """(path, replacement) for each small bug in x's runtime code: an operator swapped, a literal
    off by one, an if's branches swapped, or a statement left out. Ghost code isn't mutated, since
    it doesn't change what runs."""
    if isinstance(x, Int):
        yield from ((path, Int(n)) for n in (x.value + 1, x.value - 1) if I.MIN <= n <= I.MAX)
        return
    if not isinstance(x, Form) or not x.items or not isinstance(x.items[0], Sym):
        return
    h = x.items[0].text
    if h in GHOST or (h == "call" and x.items[1].text in lemmas):
        return
    if h in OPS:
        yield path, Form((Sym(OPS[h]),) + x.items[1:])
    if h == "if":
        yield path, Form(x.items[:2] + (x.items[3], x.items[2]))
    if h in ("body", "block", "while"):
        for k, s in enumerate(x.items):
            if _head(s) in DROPPED:
                yield path, Form(x.items[:k] + x.items[k + 1:])
    for k, c in enumerate(x.items[1:], 1):
        yield from _mutations(c, lemmas, path + (k,))


def _put(x, path, new):
    return new if not path else Form(x.items[:path[0]] + (_put(x.items[path[0]], path[1:], new),) + x.items[path[0] + 1:])


def mutants(module, name, subset=SUBSET, seeds=V.SEEDS, cache=V.CACHE):
    """Each mutant of def name that passes tier 0: killed by a property test, with the family of the
    goal it refutes, the input and outcome; or by the verifier, with a goal it doesn't prove; or
    surviving, since it verifies. A survivor says whether it computes differently from the def on the
    tests' inputs, and if it does, the spec allows its bug. A mutant keeps the def's invariants,
    asserts and measures, and can be killed through them alone, so a weak spec can hide behind a
    strong proof: only a survivor shows a spec is weak (D121)."""
    k = next(j for j, it in enumerate(module.items) if _head(it) == "def" and it.items[1].text == name)
    lemmas = {it.items[1].text for it in _items(module, ("lemma",))} | {it.items[1].text for it in G.CORE.items[3:]}
    seed, seen, out, inputs = _seed(module, name, subset), {canonical(module)}, [], None
    for path, new in _mutations(module.items[k], lemmas):
        text = canonical(Form(module.items[:k] + (_put(module.items[k], path, new),) + module.items[k + 1:]))
        if text in seen:
            continue
        seen.add(text)
        try:
            m = parse(text, subset)
            C.types(m, subset)
        except (ParseError, ValueError):  # fails tier 0, so it isn't a program
            continue
        entry = {"change": f"{_print(_get(module.items[k], path))} -> {_print(new)}", "path": ".".join(map(str, path))}
        _, _, refuted = I.test_def(m, name, seed, subset)
        if refuted:
            key, (given, outcome) = next(iter(refuted.items()))
            out.append({**entry, "killed": "test", "goal": key[0], "input": given, "outcome": outcome})
            continue
        rows, _ = V.verify(m, seeds, cache, subset)
        failed = next((r for r in rows if r["verdict"] != "proved"), None)
        if failed:
            out.append({**entry, "killed": "verifier", "goal": f"{failed['family']} {failed['node']}"})
            continue
        inputs = inputs if inputs is not None else I.spec_inputs(module, name, seed, I.KEPT, subset)
        differs = next((a for a in inputs if I.run(module, name, a, subset=subset) != I.run(m, name, a, subset=subset)), None)
        out.append({**entry, "killed": None, "differs_at": None if differs is None else [I._term(x) for x in differs]})
    return out


def _get(x, path):
    return x if not path else _get(x.items[path[0]], path[1:])


ENGLISH = """Below is a module in B17, a language for verified programs. Its header is a prose contract: \
purpose, invariants and failures. Its specs give each function's parameters, results, requires (what a \
caller must ensure), ensures (what the function guarantees) and effects. Its ghost-fns, data types and \
lemmas exist only for specs and proofs, and its implementations are left out.

Some of B17's notation: (len s) and (idx s i) are a sequence's length and its element i, counting from \
0; (take s k) and (drop s k) are its first k elements and the rest; (last s); (concat s t); \
(seq-build n (fn (i) e)) is the sequence of e for i from 0 to n - 1; (multiset s) is its elements with \
their counts, and (msum m n) adds two multisets' counts; (occurrences s x); (contains s x) is membership \
in a sequence or set, or a key of a map. i64 is a 64-bit integer and int an unbounded one; (vec T) and \
(ref (slice T)) hold sequences at run time, and (seq T) only in specs. (=> p q) is implication. The core \
library defines:
{core}

The module:
{module}

1. For each spec, say in a short plain-English paragraph what a caller must ensure and what the function \
guarantees, for a reviewer who doesn't read B17. Say what each ghost-fn it uses means rather than naming it.
2. List each way the specs and the header disagree: something the header promises that no spec states, \
or a spec that says more, less or otherwise than the header. Give an empty list if they agree.

Reply with JSON only: {{"specs": {{"NAME": "..."}}, "disagreements": ["..."]}}"""


def english(module, cli=CODEX, timeout=1800):
    """Back-translation (D121): the CLI's English for each spec and the disagreements it finds with
    the header, recorded with the CLI, its version and the prompt's hash."""
    shown = [module.items[2]] + [Form(tuple(c for c in it.items if _head(c) not in ("decreases", "body")))
                                 if it.items[0].text == "lemma" else it for it in _items(module, ("data", "ghost-fn", "spec", "lemma"))]
    core = "\n".join(_print(it) for it in G.CORE.items[3:] if it.items[0].text == "ghost-fn")
    prompt = ENGLISH.format(core=core, module="\n".join(_print(x) for x in shown))
    with tempfile.TemporaryDirectory() as d:
        reply = Path(d, "reply.txt")
        try:
            r = subprocess.run([a.replace("{reply}", str(reply)) for a in cli], input=prompt, capture_output=True,
                               text=True, timeout=timeout)
            text, error = (reply.read_text() if reply.exists() else r.stdout), (r.stderr[-2000:] if r.returncode else None)
        except (OSError, subprocess.TimeoutExpired) as e:
            text, error = "", str(e)
    try:
        version = subprocess.run([cli[0], "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        version = None
    rec = {"cli": cli[0], "model": cli[cli.index("-m") + 1] if "-m" in cli else None, "version": version,
           "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "reply": text, "error": error}
    try:
        body = json.loads(text.strip().removeprefix("```json").removeprefix("```").removesuffix("```"))
        rec |= {"specs": body["specs"], "disagreements": body["disagreements"]}
    except (ValueError, KeyError, TypeError):
        rec |= {"specs": None, "disagreements": None, "error": error or "the reply isn't the JSON asked for"}
    return rec


def sign(path, module, name, reviewer, subset=SUBSET):
    """Record reviewer's signature on spec name's current hash, beside path (D121)."""
    entry = {"name": name, "spec": H.hashes(module, subset)[name][1], "by": reviewer,
             "date": datetime.date.today().isoformat()}
    V.signatures_path(path).write_text(json.dumps(V.signatures(path) + [entry], indent=1) + "\n")
    return entry


def main(argv):
    subset, seeds = SUBSET, V.SEEDS
    while argv[:1] in (["--subset"], ["--seeds"]) and argv[1:2] and argv[1].isdecimal():
        subset, seeds = (int(argv[1]), seeds) if argv[0] == "--subset" else (subset, int(argv[1]))
        argv = argv[2:]
    shapes = {"vacuity": 1, "witness": 2, "mutants": 2, "english": 1, "sign": 3, "unsigned": 1}
    if not argv or argv[0] not in shapes or len(argv) != shapes[argv[0]] + 1 or subset not in (0, 1):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    cmd, path, *rest = argv
    try:
        module = G.read(path, subset)
        C.types(module, subset)
    except ParseError as e:
        print(f"{path}:{e.line}:{e.col}: {e.code}: {e.reason}")
        return 1
    except ValueError as e:  # tier 0 failed
        print("\n".join(f"{path}:{d}" for d in str(e).splitlines()))
        return 1
    kind = "def" if cmd == "mutants" else "spec"
    if rest and rest[0] not in {it.items[1].text for it in _items(module, (kind,))}:
        print(f"{path}: no {kind} named {rest[0]}", file=sys.stderr)
        return 2
    if cmd == "vacuity":
        out = vacuity(module, subset)
        bad = any(e["requires"]["verdict"] == "vacuous" or any(c["trivial"] for c in e["ensures"]) for e in out)
    elif cmd == "witness":
        out = witness(module, rest[0], subset)
        bad = any("challenge" in e or "outcome" in e for e in out)
    elif cmd == "mutants":
        out = mutants(module, rest[0], subset, seeds)
        bad = any(e["killed"] is None and e["differs_at"] for e in out)  # the spec allows a change in behaviour
    elif cmd == "english":
        out = english(module)
        bad = out["error"] is not None or bool(out["disagreements"])
    elif cmd == "sign":
        out, bad = sign(path, module, rest[0], rest[1], subset), False
    else:
        out = V.unsigned(path, module, subset)
        bad = bool(out)
    print(json.dumps(out, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
