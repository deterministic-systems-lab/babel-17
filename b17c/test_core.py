"""WP16's witness examples (D28): uv run --no-project b17c/test_core.py

Every law in b17c/core.b17 is evaluated by the reference interpreter at every point of a
small grid, and must hold wherever its requires does, at enough points to show it isn't
vacuous. Every ghost-fn has inputs where it's true and inputs where it's false.
"""
import itertools
from pathlib import Path

import interp as i
from syntax import Form, Int, Sym, _head, parse_expr

CORE = i.CORE
PROGRAM = i._Program(CORE)  # built once; value() would rebuild it for every point
SEQS = [()] + [s for n in (1, 2, 3) for s in itertools.product((0, 1, 2), repeat=n)]  # 40 sequences
INTS = range(-1, 5)


def term(v):
    return Form((Sym("seq-lit"),) + tuple(Int(x) for x in v)) if isinstance(v, tuple) else Int(v)


def subst(x, env):
    if isinstance(x, Sym) and x.text in env:
        return env[x.text]
    if isinstance(x, Form):
        return Form(tuple(subst(c, env) for c in x.items))
    return x


def conj(xs):
    out = Sym("true")
    for x in xs:
        out = Form((Sym("and"), out, x))
    return out


def holds(x):
    """x's value in ghost context, with checking on, as the interpreter computes it (D59)."""
    if isinstance(x, str):
        x = parse_expr(x)
    v = i._Run(PROGRAM, True, i.FUEL, i.DEPTH).eval(x, {}, True)
    assert type(v) is bool, (x, v)  # never UNKNOWN: every law is evaluable on the grid (D58)
    return v


lemmas = [it for it in CORE.items[3:] if _head(it) == "lemma"]
assert len(lemmas) == 30, len(lemmas)
for lemma in lemmas:
    name = lemma.items[1].text
    params = next(c for c in lemma.items if _head(c) == "params").items[1:]
    pre = conj(e for c in lemma.items if _head(c) == "requires" for e in c.items[1:])
    post = conj(e for c in lemma.items if _head(c) == "ensures" for e in c.items[1:])
    grids = [SEQS if _head(p.items[1]) == "seq" else INTS for p in params]
    witnesses = 0
    for point in itertools.product(*grids):
        env = {p.items[0].text: term(v) for p, v in zip(params, point)}
        if not holds(subst(pre, env)):
            continue
        assert holds(subst(post, env)), f"{name} fails at {point}"
        witnesses += 1
    assert witnesses >= 3, f"{name} holds at only {witnesses} points: it may be vacuous"

# Each ghost-fn is true somewhere and false somewhere.
for text, want in [
    ("(sorted (seq-lit))", True), ("(sorted (seq-lit 1 1 2))", True), ("(sorted (seq-lit 2 1))", False),
    ("(sorted (seq-lit 1 3 2))", False),
    ("(in_i64 -9223372036854775808)", True), ("(in_i64 9223372036854775807)", True),
    ("(in_i64 -9223372036854775809)", False), ("(in_i64 9223372036854775808)", False),
    ("(== (seq_update (seq-lit 1 2 3) 1 9) (seq-lit 1 9 3))", True),
    ("(== (seq_update (seq-lit 1 2 3) 0 9) (seq-lit 1 2 3))", False),
]:
    assert holds(text) is want, text

print(f"core library: {len(lemmas)} laws confirmed on the grid, and every ghost-fn's witnesses")
