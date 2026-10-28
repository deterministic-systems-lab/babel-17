"""Spike: B17-0's proof goals (docs/b17-0.md §7, §9), one Z3 query each.

    uv run --no-project b17c/goals.py [--seeds N] FILE...

prints each file's goals that aren't proved, and checks them against the suite label
its path implies: an accept program must prove every goal, and an E-PROOF-<FAMILY>
reject must fail only goals of that family. With --seeds N, a goal counts as proved only
if it is also proved under N shuffled seeds (D23); one that isn't is reported as brittle.

This tests the suite's proof labels before WP1a freezes (D44). It isn't WP5: it
assumes the program passes tier 0, does no type checking, and its encoding is one
guess at interface 11.

Encoding (§9): sequences are an uninterpreted sort per element type, SI and SB, and
§9's background facts are their only axioms, with triggers. Z3's own sequence theory
times out on quantified invariants over prefixes (find's, in 60 s); this proves them in
milliseconds. Multisets are count arrays. The one fact that can't be a trigger without
a matching loop, take s (k+1) = concat (take s k) [s[k]], is added at each take term.
"""
import concurrent.futures as cf
import subprocess
import sys
from pathlib import Path

from syntax import Form, Int, Sym, _head, parse

CORE = parse((Path(__file__).parent / "core.b17").read_bytes())
LIM = "9223372036854775808"
RLIMIT = 10_000_000
MIN = f"(- {LIM})"
MSUM = "(_ map (+ (Int Int) Int))"
ZERO = "((as const (Array Int Int)) 0)"
PRELUDE = f"""(set-option :smt.random_seed 0)
(define-fun tdiv ((a Int) (b Int)) Int
  (ite (>= a 0) (ite (> b 0) (div a b) (- (div a (- b)))) (ite (> b 0) (- (div (- a) b)) (div (- a) (- b)))))
(define-fun tmod ((a Int) (b Int)) Int (- a (* b (tdiv a b))))
"""
# Division by a variable: D37's truncation facts. Only queries that divide by a variable
# get them, because their nonlinear term switches Z3 to slower strategies for the whole query.
VDIV = """(declare-fun vdiv (Int Int) Int)
(declare-fun vmod (Int Int) Int)
(assert (forall ((a Int) (b Int)) (! (=> (not (= b 0)) (and (= a (+ (* b (vdiv a b)) (vmod a b)))
  (=> (>= a 0) (and (<= 0 (vmod a b)) (< (vmod a b) (abs b)))) (=> (< a 0) (and (< (- (abs b)) (vmod a b)) (<= (vmod a b) 0)))))
  :pattern ((vdiv a b)) :pattern ((vmod a b)))))
"""
for E, X in (("Int", "I"), ("Bool", "B")):
    PRELUDE += f"""(declare-sort S{X} 0)
(declare-fun len.{X} (S{X}) Int)
(declare-fun nth.{X} (S{X} Int) {E})
(declare-fun take.{X} (S{X} Int) S{X})
(declare-fun drop.{X} (S{X} Int) S{X})
(declare-fun cat.{X} (S{X} S{X}) S{X})
(declare-fun unit.{X} ({E}) S{X})
(declare-const empty.{X} S{X})
(assert (forall ((s S{X})) (! (>= (len.{X} s) 0) :pattern ((len.{X} s)))))
(assert (= (len.{X} empty.{X}) 0))
(assert (forall ((x {E})) (! (and (= (len.{X} (unit.{X} x)) 1) (= (nth.{X} (unit.{X} x) 0) x)) :pattern ((unit.{X} x)))))
(assert (forall ((s S{X}) (t S{X})) (! (= (len.{X} (cat.{X} s t)) (+ (len.{X} s) (len.{X} t))) :pattern ((cat.{X} s t)))))
(assert (forall ((s S{X}) (t S{X}) (j Int)) (! (=> (and (<= 0 j) (< j (+ (len.{X} s) (len.{X} t))))
  (= (nth.{X} (cat.{X} s t) j) (ite (< j (len.{X} s)) (nth.{X} s j) (nth.{X} t (- j (len.{X} s)))))) :pattern ((nth.{X} (cat.{X} s t) j)))))
(assert (forall ((s S{X}) (k Int)) (! (=> (and (<= 0 k) (<= k (len.{X} s))) (= (len.{X} (take.{X} s k)) k)) :pattern ((take.{X} s k)))))
(assert (forall ((s S{X}) (k Int)) (! (=> (and (<= 0 k) (<= k (len.{X} s))) (= (len.{X} (drop.{X} s k)) (- (len.{X} s) k))) :pattern ((drop.{X} s k)))))
(assert (forall ((s S{X}) (k Int) (j Int)) (! (=> (and (<= 0 j) (< j k) (<= k (len.{X} s))) (= (nth.{X} (take.{X} s k) j) (nth.{X} s j)))
  :pattern ((nth.{X} (take.{X} s k) j)) :pattern ((take.{X} s k) (nth.{X} s j)))))
(assert (forall ((s S{X}) (k Int) (j Int)) (! (=> (and (<= 0 k) (<= 0 j) (< j (- (len.{X} s) k))) (= (nth.{X} (drop.{X} s k) j) (nth.{X} s (+ j k))))
  :pattern ((nth.{X} (drop.{X} s k) j)))))
(assert (forall ((s S{X}) (k Int)) (! (=> (= k (len.{X} s)) (= (take.{X} s k) s)) :pattern ((take.{X} s k)))))
(assert (forall ((s S{X}) (k Int)) (! (=> (= k 0) (= (take.{X} s k) empty.{X})) :pattern ((take.{X} s k)))))
(assert (forall ((s S{X}) (k Int) (j Int)) (! (=> (and (<= 0 j) (<= j k) (<= k (len.{X} s))) (= (take.{X} (take.{X} s k) j) (take.{X} s j)))
  :pattern ((take.{X} (take.{X} s k) j)))))
(declare-fun has.{X} (S{X} {E}) Bool)
(assert (forall ((s S{X}) (x {E})) (! (= (has.{X} s x) (exists ((i Int)) (and (<= 0 i) (< i (len.{X} s)) (= (nth.{X} s i) x))))
  :pattern ((has.{X} s x)))))
(assert (forall ((s S{X}) (t S{X}) (x {E})) (! (= (has.{X} (cat.{X} s t) x) (or (has.{X} s x) (has.{X} t x))) :pattern ((has.{X} (cat.{X} s t) x)))))
(assert (forall ((y {E}) (x {E})) (! (= (has.{X} (unit.{X} y) x) (= x y)) :pattern ((has.{X} (unit.{X} y) x)))))
(assert (forall ((x {E})) (! (not (has.{X} empty.{X} x)) :pattern ((has.{X} empty.{X} x)))))
"""
PRELUDE += f"""(declare-fun ms (SI) (Array Int Int))
(assert (= (ms empty.I) {ZERO}))
(assert (forall ((x Int)) (! (= (ms (unit.I x)) (store {ZERO} x 1)) :pattern ((ms (unit.I x))))))
(assert (forall ((s SI) (t SI)) (! (= (ms (cat.I s t)) ({MSUM} (ms s) (ms t))) :pattern ((ms (cat.I s t))))))
"""
ELEM = {"SI": "Int", "SB": "Bool"}


def sort(t):
    if isinstance(t, Sym):
        return "Bool" if t.text == "bool" else "Int"
    h = _head(t)
    if h == "multiset":
        return f"(Array {sort(t.items[1])} Int)"
    if h == "ref":
        t = t.items[1]
    return "SB" if sort(t.items[1]) == "Bool" else "SI"


def fn(op, srt, *args):
    """A sequence function on sequences of sort srt, such as (len.I s)."""
    return f"({op}.{srt[1]} {' '.join(args)})"


def app(f, args):
    """f applied to args; an SMT constant takes no parentheses."""
    return f"({f} {' '.join(args)})" if args else f


def num(v):
    return str(v) if v >= 0 else f"(- {-v})"


def in_i64(t):
    return f"(and (<= {MIN} {t}) (< {t} {LIM}))"


def wrap(guard, g):
    """g under the conditions and binders of the expression it came from."""
    for kind, x in reversed(guard):
        g = f"(=> {x} {g})" if kind == "if" else f"(forall ({x}) {g})"
    return g


def clauses(item, head):
    return [c.items[1:] for c in item.items if _head(c) == head]


class State:
    def __init__(self, env, facts):
        self.env, self.facts = env, facts  # env: name -> (term, type)

    def copy(self):
        return State(dict(self.env), list(self.facts))


class Gen:
    def __init__(self, module):
        self.defs = {}
        for m in (CORE, module):
            for it in m.items[3:]:
                self.defs.setdefault(it.items[1].text, {})[it.items[0].text] = it
        self.decls, self.goals, self.n = [], [], 0
        self.quiet = False
        self.item = None    # (name, measure at entry or None, its params) while checking an item
        self.funs = self.ghost_fns()

    # Names.
    def fresh(self, base, srt):
        self.n += 1
        name = f"{base}!{self.n}"
        self.decls.append(f"(declare-const {name} {srt})")
        return name

    def bound(self, base):
        self.n += 1
        return f"{base}!b{self.n}"

    def var(self, st, name, typ, base=None):
        c = self.fresh(base or name, sort(typ))
        st.env[name] = (c, typ)
        st.facts += self.type_facts(c, typ)
        return c

    def type_facts(self, t, typ):
        """Background facts: every i64 value, and every vector or slice length, fits (§9)."""
        if isinstance(typ, Sym):
            return [in_i64(t)] if typ.text == "i64" else []
        if _head(typ) == "multiset":
            return []
        elem = (typ.items[1].items[1] if _head(typ) == "ref" else typ.items[1])
        srt = sort(typ)
        out = [] if _head(typ) == "seq" else [f"(< {fn('len', srt, t)} {LIM})"]
        if isinstance(elem, Sym) and elem.text == "i64":
            k = self.bound("k")
            out.append(f"(forall (({k} Int)) (! (=> (and (<= 0 {k}) (< {k} {fn('len', srt, t)})) "
                       f"{in_i64(fn('nth', srt, t, k))}) :pattern ({fn('nth', srt, t, k)})))")
        return out

    # Goals and facts.
    def goal(self, st, guard, family, x, g):
        if self.quiet:
            return
        g = wrap(guard, g)
        self.goals.append((self.item[0], family, x.pos, list(st.facts), g))
        st.facts.append(g)  # every goal is assumed once generated (§9)

    def fact(self, st, guard, f):
        if st is not None and not any(k == "all" for k, _ in guard):
            st.facts.append(wrap(guard, f))

    # Expressions: (SMT term, SMT sort).
    def expr(self, x, st, ghost, guard=(), want="SI"):
        if isinstance(x, Int):
            return num(x.value), "Int"
        if isinstance(x, Sym):
            if x.text in ("true", "false"):
                return x.text, "Bool"
            t, typ = st.env[x.text]
            return t, sort(typ)
        h, a = _head(x), x.items[1:]
        e = lambda y, g=guard, w="SI": self.expr(y, st, ghost, g, w)
        if h in ("+", "-", "*"):
            (l, _), (r, _) = e(a[0]), e(a[1])
            t = f"({h} {l} {r})"
            if not ghost:
                self.goal(st, guard, "OVERFLOW", x, in_i64(t))
            return t, "Int"
        if h in ("/", "%"):
            (l, _), (r, _) = e(a[0]), e(a[1])
            g = f"(not (= {r} 0))" if ghost else f"(and (not (= {r} 0)) (not (and (= {l} {MIN}) (= {r} (- 1)))))"
            self.goal(st, guard, "DIV", x, g)
            # A constant divisor keeps division linear. A variable one would make it nonlinear,
            # which stalls Z3 (gcd), so it gets D37's truncation facts as axioms instead.
            op = ("tdiv" if h == "/" else "tmod") if isinstance(a[1], Int) else ("vdiv" if h == "/" else "vmod")
            return f"({op} {l} {r})", "Int"
        if h in ("<", "<=", ">", ">=", "==", "!="):
            (l, srt), (r, _) = e(a[0]), e(a[1])
            if srt in ELEM:  # §9: sequences are equal when their lengths and elements are
                j = self.bound("j")
                eq = (f"(and (= {fn('len', srt, l)} {fn('len', srt, r)}) (forall (({j} Int)) (! (=> (and (<= 0 {j}) "
                      f"(< {j} {fn('len', srt, l)})) (= {fn('nth', srt, l, j)} {fn('nth', srt, r, j)})) "
                      f":pattern ({fn('nth', srt, l, j)}) :pattern ({fn('nth', srt, r, j)}))))")
                return (eq if h == "==" else f"(not {eq})"), "Bool"
            op = {"==": "=", "!=": "distinct"}.get(h, h)
            return f"({op} {l} {r})", "Bool"
        if h in ("and", "or", "=>"):
            l, _ = e(a[0])
            r, _ = e(a[1], guard + (("if", l if h != "or" else f"(not {l})"),))
            return f"({h} {l} {r})", "Bool"
        if h == "not":
            return f"(not {e(a[0])[0]})", "Bool"
        if h == "neg":
            t, _ = e(a[0])
            if not ghost:
                self.goal(st, guard, "OVERFLOW", x, f"(not (= {t} {MIN}))")
            return f"(- {t})", "Int"
        if h == "if":
            c, _ = e(a[0])
            l, srt = e(a[1], guard + (("if", c),), want)
            r, _ = e(a[2], guard + (("if", f"(not {c})"),), want)
            return f"(ite {c} {l} {r})", srt
        if h == "len":
            s, srt = e(a[0])
            return fn("len", srt, s), "Int"
        if h == "idx":
            (s, srt), (i, _) = e(a[0]), e(a[1])
            self.goal(st, guard, "BOUNDS", x, f"(and (<= 0 {i}) (< {i} {fn('len', srt, s)}))")
            return fn("nth", srt, s, i), ELEM[srt]
        if h == "borrow":
            return e(a[0])
        if h in ("vec-new",) or (h == "seq-lit" and not a):
            return f"empty.{want[1]}", want
        if h == "seq-lit":
            parts = [e(y) for y in a]
            srt = "SB" if parts[0][1] == "Bool" else "SI"
            out = fn("unit", srt, parts[0][0])
            for t, _ in parts[1:]:
                out = fn("cat", srt, out, fn("unit", srt, t))
            return out, srt
        if h in ("take", "drop"):
            (s, srt), (k, _) = e(a[0]), e(a[1])
            self.goal(st, guard, "BOUNDS", x, f"(and (<= 0 {k}) (<= {k} {fn('len', srt, s)}))")
            t = fn(h, srt, s, k)
            if h == "take":  # §9's step fact, which as a trigger would loop
                prev = fn("cat", srt, fn("take", srt, s, f"(- {k} 1)"), fn("unit", srt, fn("nth", srt, s, f"(- {k} 1)")))
                self.fact(st, guard, f"(=> (and (< 0 {k}) (<= {k} {fn('len', srt, s)})) (= {t} {prev}))")
            return t, srt
        if h == "concat":
            (s, srt), (t, _) = e(a[0]), e(a[1])
            return fn("cat", srt, s, t), srt
        if h == "last":
            s, srt = e(a[0])
            self.goal(st, guard, "BOUNDS", x, f"(> {fn('len', srt, s)} 0)")
            return fn("nth", srt, s, f"(- {fn('len', srt, s)} 1)"), ELEM[srt]
        if h == "contains":
            (s, srt), (v, _) = e(a[0]), e(a[1])
            return fn("has", srt, s, v), "Bool"
        if h == "multiset":
            return f"(ms {e(a[0])[0]})", "(Array Int Int)"
        if h == "msum":
            return f"({MSUM} {e(a[0])[0]} {e(a[1])[0]})", "(Array Int Int)"
        if h == "occurrences":
            return f"(select (ms {e(a[0])[0]}) {e(a[1])[0]})", "Int"
        if h in ("forall", "exists"):
            inner, decl = State(dict(st.env), st.facts), []
            for b in a[0].items:
                v = self.bound(b.items[0].text)
                inner.env[b.items[0].text] = (v, b.items[1])
                decl.append(f"({v} {sort(b.items[1])})")
            decl = " ".join(decl)
            body, _ = self.expr(a[1], inner, True, guard + (("all", decl),))
            return f"({h} ({decl}) {body})", "Bool"
        if h == "seq-build":
            n, _ = e(a[0])
            self.goal(st, guard, "BOUNDS", x, f"(>= {n} 0)")
            name = a[1].items[1].items[0].text
            i = self.bound(name)
            inner = State(dict(st.env), st.facts)
            inner.env[name] = (i, Sym("int"))
            rng = f"(and (<= 0 {i}) (< {i} {n}))"
            body, srt = self.expr(a[1].items[2], inner, ghost, guard + (("all", f"({i} Int)"), ("if", rng)))
            ss = "SB" if srt == "Bool" else "SI"
            r = self.fresh("seq", ss)
            self.fact(st, guard, f"(= {fn('len', ss, r)} {n})")
            self.fact(st, guard, f"(forall (({i} Int)) (! (=> {rng} (= {fn('nth', ss, r, i)} {body})) :pattern ({fn('nth', ss, r, i)})))")
            return r, ss
        # (NAME e*): a ghost-fn call
        f = self.defs[h]["ghost-fn"]
        args = [e(y)[0] for y in a]
        if clauses(f, "requires"):
            self.goal(st, guard, "PRE", x, app(f"p!{h}", args))
        if self.item and h == self.item[0]:
            self.term_goal(st, guard, x, f, args)
        return app(f"g!{h}", args), sort(f.items[3])

    def term_goal(self, st, guard, x, item, args):
        """At a recursive call: 0 <= callee measure < caller measure (§7)."""
        name, d0, params = self.item
        dec = clauses(item, "decreases")
        if not dec or d0 is None:
            return
        callee = State(dict(st.env), st.facts)
        for p, t in zip(params, args):
            callee.env[p.items[0].text] = (t, p.items[1])
        q, self.quiet = self.quiet, True
        d, _ = self.expr(dec[0][0], callee, True)
        self.quiet = q
        self.goal(st, guard, "TERM", x, f"(and (<= 0 {d}) (< {d} {d0}))")

    def ghost_fns(self):
        """Each ghost-fn as an SMT function, callees first, with its requires as p!NAME."""
        out, done = [], set()

        def emit(name):
            if name in done:
                return
            done.add(name)
            f = self.defs[name]["ghost-fn"]
            for callee in self.calls(f):
                if callee != name:
                    emit(callee)
            st = State({}, [])
            ps = []
            for p in f.items[2].items:
                v = f"{p.items[0].text}!p"
                st.env[p.items[0].text] = (v, p.items[1])
                ps.append(f"({v} {sort(p.items[1])})")
            q, self.quiet = self.quiet, True
            body, _ = self.expr(clauses(f, "body")[0][0], st, True)
            pre = [self.expr(c[0], st, True)[0] for c in clauses(f, "requires")]
            self.quiet = q
            ret, pre = sort(f.items[3]), f"(and true {' '.join(pre)})"
            if name not in self.calls(f):
                out.append((None, f"(define-fun g!{name} ({' '.join(ps)}) {ret} {body})"))
                out.append((None, f"(define-fun p!{name} ({' '.join(ps)}) Bool {pre})"))
                return
            # Recursive: its equation holds only under its requires, and the ghost-fn's own goals
            # are checked without it (see query). A definition that doesn't terminate could
            # otherwise be contradictory, and prove everything, its own TERM goal included.
            sorts = " ".join(p.split(" ", 1)[1][:-1] for p in ps)
            args = [p[1:].split(" ", 1)[0] for p in ps]
            out.append((None, f"(declare-fun g!{name} ({sorts}) {ret})"))
            out.append((None, f"(define-fun p!{name} ({' '.join(ps)}) Bool {pre})"))
            eq = f"(=> {app('p!' + name, args)} (= {app('g!' + name, args)} {body}))"
            out.append((name, f"(assert (forall ({' '.join(ps)}) (! {eq} :pattern ({app('g!' + name, args)}))))"
                        if ps else f"(assert {eq})"))

        for name, d in self.defs.items():
            if "ghost-fn" in d:
                emit(name)
        return out

    def calls(self, x):
        if isinstance(x, Form):
            h = _head(x)
            if h in self.defs and "ghost-fn" in self.defs[h]:
                yield h
            for c in x.items:
                yield from self.calls(c)

    # Statements: the state after a normal exit, or None when no path continues.
    def block(self, stmts, st, ghost):
        for s in stmts:
            if st is None:
                break
            st = self.stmt(s, st, ghost)
        return st

    def stmt(self, x, st, ghost):
        h, a = _head(x), x.items[1:]
        if h in ("let", "let-mut", "ghost-let", "ghost-let-mut"):
            g = ghost or h.startswith("ghost")
            if isinstance(a[0], Form):  # (let (param+) (call NAME e*))
                self.call(a[1], st, g, a[0].items)
                return st
            t, _ = self.expr(a[2], st, g, want=sort(a[1]))
            c = self.var(st, a[0].text, a[1])
            st.facts.append(f"(= {c} {t})")
            return st
        if h in ("set", "ghost-set"):
            t, _ = self.expr(a[1], st, ghost or h == "ghost-set", want=sort(st.env[a[0].text][1]))
            c = self.var(st, a[0].text, st.env[a[0].text][1])
            st.facts.append(f"(= {c} {t})")
            return st
        if h in ("set-idx", "push"):
            old, typ = st.env[a[0].text]
            srt = sort(typ)
            if h == "push":  # §9: after (push v e), v is (concat v (seq-lit e))
                v, _ = self.expr(a[1], st, ghost)
                new = self.var(st, a[0].text, typ)
                st.facts.append(f"(= {new} {fn('cat', srt, old, fn('unit', srt, v))})")
                return st
            (i, _), (v, _) = self.expr(a[1], st, ghost), self.expr(a[2], st, ghost)
            self.goal(st, (), "BOUNDS", x, f"(and (<= 0 {i}) (< {i} {fn('len', srt, old)}))")
            new = self.var(st, a[0].text, typ)
            k = self.bound("k")
            st.facts += [f"(= {fn('len', srt, new)} {fn('len', srt, old)})",  # §9's set-idx facts
                         f"(forall (({k} Int)) (! (=> (and (<= 0 {k}) (< {k} {fn('len', srt, old)}) (not (= {k} {i}))) "
                         f"(= {fn('nth', srt, new, k)} {fn('nth', srt, old, k)})) :pattern ({fn('nth', srt, new, k)})))",
                         f"(= {fn('nth', srt, new, i)} {v})"]
            if srt == "SI":
                ov = fn("nth", srt, old, i)
                m1 = f"(store (ms {old}) {ov} (- (select (ms {old}) {ov}) 1))"
                st.facts.append(f"(= (ms {new}) (store {m1} {v} (+ (select {m1} {v}) 1)))")
            return st
        if h == "if":
            c, _ = self.expr(a[0], st, ghost)
            yes, no = st.copy(), st.copy()
            yes.facts.append(c)
            no.facts.append(f"(not {c})")
            return self.join(st, c, self.stmt(a[1], yes, ghost), self.stmt(a[2], no, ghost))
        if h == "block":
            return self.block(a, st, ghost)
        if h == "while":
            return self.loop(x, st, ghost)
        if h == "call":
            self.call(x, st, ghost, ())
            return st
        if h == "assert":
            t, _ = self.expr(a[0], st, True)
            self.goal(st, (), "ASSERT", x, t)
            return st
        if h == "return":
            self.ret(x, a, st, ghost)
            return None
        if h == "panic":
            return None
        if h == "print":
            self.expr(a[0], st, ghost)
            return st
        raise NotImplementedError(h)

    def join(self, base, c, yes, no):
        if yes is None or no is None:
            return yes or no
        st = State(dict(base.env), list(base.facts))
        n = len(base.facts)
        st.facts.append(f"(=> {c} (and true {' '.join(yes.facts[n:])}))")
        st.facts.append(f"(=> (not {c}) (and true {' '.join(no.facts[n:])}))")
        for name, (t, typ) in base.env.items():
            if yes.env[name][0] != no.env[name][0]:
                m = self.var(st, name, typ)
                st.facts.append(f"(ite {c} (= {m} {yes.env[name][0]}) (= {m} {no.env[name][0]}))")
        return st

    def loop(self, x, st, ghost):
        """§9's while rule: invariants on entry, one arbitrary iteration, then I and not c."""
        cond, rest = x.items[1], x.items[2:]
        invs = [s.items[1] for s in rest if _head(s) == "invariant"]
        dec = next(s.items[1] for s in rest if _head(s) == "decreases")
        body = [s for s in rest if _head(s) not in ("invariant", "decreases")]
        self.expr(cond, st, ghost)  # c's own goals on entry
        for inv in invs:
            t, _ = self.expr(inv, st, True)
            self.goal(st, (), "INV-ENTRY", inv, t)
        it = st.copy()
        for name in sorted(self.assigned(body) & set(st.env)):
            self.var(it, name, st.env[name][1])  # what an iteration forgets
        for inv in invs:
            it.facts.append(self.expr(inv, it, True)[0])
        c, _ = self.expr(cond, it, ghost)
        after = it.copy()
        it.facts.append(c)
        d0, _ = self.expr(dec, it, True)
        self.goal(it, (), "TERM", dec, f"(<= 0 {d0})")
        end = self.block(body, it, ghost)
        if end is not None:
            for inv in invs:
                q, self.quiet = self.quiet, True
                t, _ = self.expr(inv, end, True)
                self.quiet = q
                self.goal(end, (), "INV-KEEP", inv, t)
            q, self.quiet = self.quiet, True
            d, _ = self.expr(dec, end, True)
            self.quiet = q
            self.goal(end, (), "TERM", dec, f"(< {d} {d0})")
        after.facts.append(f"(not {c})")
        return after

    def assigned(self, stmts):
        out = set()
        for s in stmts:
            if isinstance(s, Form):
                if _head(s) in ("set", "set-idx", "push", "ghost-set"):
                    out.add(s.items[1].text)
                out |= self.assigned(s.items[1:])
        return out

    def call(self, x, st, ghost, results):
        name, args = x.items[1].text, x.items[2:]
        d = self.defs[name]
        callee = d.get("spec") or d["lemma"]
        g = ghost or "lemma" in d
        params = clauses(callee, "params")[0]
        terms = [self.expr(y, st, g, want=sort(p.items[1]))[0] for y, p in zip(args, params)]
        env = State(dict(st.env), st.facts)
        for p, t in zip(params, terms):
            env.env[p.items[0].text] = (t, p.items[1])
        q, self.quiet = self.quiet, True
        pres = [self.expr(c, env, True)[0] for cl in clauses(callee, "requires") for c in cl]
        self.quiet = q
        for pre in pres:
            self.goal(st, (), "PRE", x, pre)
        if self.item and name == self.item[0]:
            self.term_goal(st, (), x, d.get("def") or callee, terms)
        for r, p in zip(results, clauses(callee, "returns")[0] if "spec" in d else ()):
            env.env[p.items[0].text] = (self.var(st, r.items[0].text, r.items[1]), p.items[1])
        q, self.quiet = self.quiet, True
        st.facts += [self.expr(c, env, True)[0] for cl in clauses(callee, "ensures") for c in cl]
        self.quiet = q

    def ret(self, x, a, st, ghost):
        spec = self.defs[self.item[0]].get("spec") or self.defs[self.item[0]]["lemma"]
        results = clauses(spec, "returns")[0] if _head(spec) == "spec" else ()
        env = State(dict(st.env), st.facts)
        for y, p in zip(a, results):
            env.env[p.items[0].text] = (self.expr(y, st, ghost, want=sort(p.items[1]))[0], p.items[1])
        self.post(x, spec, env, st)

    def post(self, x, spec, env, st):
        for cl in clauses(spec, "ensures"):
            for c in cl:
                q, self.quiet = self.quiet, True
                t, _ = self.expr(c, env, True)
                self.quiet = q
                self.goal(st, (), "POST", x, t)
                env.facts = st.facts

    # Items.
    def contracts(self, item, st, results):
        """A spec's or lemma's clauses, checked in order, each assuming the ones before (§7)."""
        for c in [c for cl in clauses(item, "requires") for c in cl]:
            st.facts.append(self.expr(c, st, True)[0])
        for p in results:
            self.var(st, p.items[0].text, p.items[1])
        for c in [c for cl in clauses(item, "ensures") for c in cl]:
            st.facts.append(self.expr(c, st, True)[0])

    def params(self, st, ps):
        for p in ps:
            self.var(st, p.items[0].text, p.items[1])

    def check(self, module):
        for it in module.items[3:]:
            kind, name = it.items[0].text, it.items[1].text
            st = State({}, [])
            self.item = (name, None, ())
            if kind == "ghost-fn":
                ps = it.items[2].items
                self.params(st, ps)
                for c in clauses(it, "requires"):
                    st.facts.append(self.expr(c[0], st, True)[0])
                dec = clauses(it, "decreases")
                d0 = self.expr(dec[0][0], st, True)[0] if dec else None
                self.item = (name, d0, ps)
                self.expr(clauses(it, "body")[0][0], st, True)
            elif kind in ("spec", "lemma"):
                ps = clauses(it, "params")[0]
                self.params(st, ps)
                self.contracts(it, st, clauses(it, "returns")[0] if kind == "spec" else ())
                if kind == "lemma":
                    st = State({}, [])
                    self.params(st, ps)
                    q, self.quiet = self.quiet, True
                    st.facts += [self.expr(c, st, True)[0] for cl in clauses(it, "requires") for c in cl]
                    self.quiet = q
                    self.body(it, ps, st, True)
            else:
                spec = self.defs[name]["spec"]
                ps = clauses(spec, "params")[0]
                self.params(st, ps)
                q, self.quiet = self.quiet, True
                st.facts += [self.expr(c, st, True)[0] for cl in clauses(spec, "requires") for c in cl]
                self.quiet = q
                self.body(it, ps, st, False)
        return self.goals

    def body(self, it, ps, st, ghost):
        dec = clauses(it, "decreases")
        d0 = self.expr(dec[0][0], st, True)[0] if dec else None
        self.item = (it.items[1].text, d0, ps)
        end = self.block(clauses(it, "body")[0], st, ghost)
        if end is not None and ghost:  # a lemma's ensures at the end of its body
            self.post(it, it, State(dict(end.env), end.facts), end)


def query(gen, facts, g, item=None):
    """One goal's query. A recursive ghost-fn's own goals don't get its definition."""
    body = "\n".join([*gen.decls, *(t for name, t in gen.funs if name is None or name != item), *(f"(assert {f})" for f in facts), f"(assert (not {g}))", "(check-sat)"])
    return PRELUDE + (VDIV if "(vdiv " in body or "(vmod " in body else "") + body


def solve(text, seed=0):
    if seed:  # D23's shuffled seeds: the SMT core's and the SAT core's
        text = text.replace("(set-option :smt.random_seed 0)",
                            f"(set-option :smt.random_seed {seed})\n(set-option :sat.random_seed {seed})", 1)
    # D23: a resource budget, not seconds, so verdicts don't depend on load. The most a proved
    # suite goal needs is about 0.84M units; the time limit is only a backstop.
    r = subprocess.run(["z3", f"rlimit={RLIMIT}", "-T:300", "-in"], input=text, capture_output=True, text=True)
    out = r.stdout.strip().splitlines()
    if any(line.startswith("(error") for line in out) or r.stderr:
        return "error: " + (r.stdout + r.stderr)[:300]
    return {"unsat": "proved", "sat": "failed"}.get(out[-1] if out else "", "unknown: " + (r.stdout + r.stderr)[-200:])


def run(path, seeds=0):
    gen = Gen(m := parse(Path(path).read_bytes()))
    goals = gen.check(m)

    def verdict(g):
        q = query(gen, g[3], g[4], g[0])
        v = solve(q)
        if v != "proved":
            return v
        held = sum(solve(q, k) == "proved" for k in range(1, seeds + 1))
        return v if held == seeds else f"brittle: proved under {held} of {seeds} shuffled seeds"

    with cf.ThreadPoolExecutor(8) as pool:
        verdicts = list(pool.map(verdict, goals))
    return [(item, fam, pos, v) for (item, fam, pos, _, _), v in zip(goals, verdicts)]


if __name__ == "__main__":
    bad, args, seeds = 0, sys.argv[1:], 0
    if args[:1] == ["--seeds"]:
        seeds, args = int(args[1]), args[2:]
    for path in args:
        results = run(path, seeds)
        open_ = [(item, fam, pos, v) for item, fam, pos, v in results if v != "proved"]
        name = Path(path).name
        want = name.split("-")[2] if name.startswith("E-PROOF-") else None
        want = "-".join(name.split("-")[2:4]) if want == "INV" else want
        fams = {fam for _, fam, _, _ in open_}
        ok = not open_ if "accept" in path else (fams == {want} if want else None)
        bad += ok is False
        print(f"{'ok ' if ok else 'BAD' if ok is False else '-- '} {path}: {len(results)} goals, "
              f"{len(results) - len(open_)} proved" + "".join(
                  f"\n      {fam} {item} {pos[0]}:{pos[1]} {v}" for item, fam, pos, v in open_))
    sys.exit(1 if bad else 0)
