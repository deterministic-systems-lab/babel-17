"""B17-0's proof goals (docs/b17-0.md §7, §9), one Z3 query each, for WP5's verifier.

    uv run --no-project b17c/goals.py [--subset 1] [--seeds N] FILE...

prints each file's goals that aren't proved, and checks them against the suite label
its path implies: an accept program must prove every goal, and an E-PROOF-<FAMILY>
reject must fail only goals of that family. With --seeds N, a goal counts as proved only
if it is also proved under N shuffled seeds (D23); one that isn't is reported as brittle.

Each expression's sort comes from the type WP3's checker gives it (check.types), so a
program must pass tier 0 first. The encoding is one guess at interface 11.

Encoding (§9): sequences are an uninterpreted sort per element type, SI and SB, and
§9's background facts are their only axioms, with triggers. Z3's own sequence theory
times out on quantified invariants over prefixes (find's, in 60 s); this proves them in
milliseconds. Multisets are count arrays. The one fact that can't be a trigger without
a matching loop, take s (k+1) = concat (take s k) [s[k]], is added at each take term.
"""
import concurrent.futures as cf
import re
import subprocess
import sys
from pathlib import Path

import check as C
from syntax import SUBSET, Form, Int, Sym, _head, parse

CORE = C.CORE
LIM = "9223372036854775808"
RLIMIT = 10_000_000
MIN = f"(- {LIM})"
MSUM = "(_ map (+ (Int Int) Int))"
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
def seq_facts(E, S, f):
    """§9's background facts for sequences of sort S, whose elements have sort E and whose
    functions f names, after S's own declaration."""
    L, N, T, D, C, U, Z, H = map(f, ("len", "nth", "take", "drop", "cat", "unit", "empty", "has"))
    return f"""(declare-fun {L} ({S}) Int)
(declare-fun {N} ({S} Int) {E})
(declare-fun {T} ({S} Int) {S})
(declare-fun {D} ({S} Int) {S})
(declare-fun {C} ({S} {S}) {S})
(declare-fun {U} ({E}) {S})
(declare-const {Z} {S})
(assert (forall ((s {S})) (! (>= ({L} s) 0) :pattern (({L} s)))))
(assert (= ({L} {Z}) 0))
(assert (forall ((x {E})) (! (and (= ({L} ({U} x)) 1) (= ({N} ({U} x) 0) x)) :pattern (({U} x)))))
(assert (forall ((s {S}) (t {S})) (! (= ({L} ({C} s t)) (+ ({L} s) ({L} t))) :pattern (({C} s t)))))
(assert (forall ((s {S}) (t {S}) (j Int)) (! (=> (and (<= 0 j) (< j (+ ({L} s) ({L} t))))
  (= ({N} ({C} s t) j) (ite (< j ({L} s)) ({N} s j) ({N} t (- j ({L} s)))))) :pattern (({N} ({C} s t) j)))))
(assert (forall ((s {S}) (k Int)) (! (=> (and (<= 0 k) (<= k ({L} s))) (= ({L} ({T} s k)) k)) :pattern (({T} s k)))))
(assert (forall ((s {S}) (k Int)) (! (=> (and (<= 0 k) (<= k ({L} s))) (= ({L} ({D} s k)) (- ({L} s) k))) :pattern (({D} s k)))))
(assert (forall ((s {S}) (k Int) (j Int)) (! (=> (and (<= 0 j) (< j k) (<= k ({L} s))) (= ({N} ({T} s k) j) ({N} s j)))
  :pattern (({N} ({T} s k) j)) :pattern (({T} s k) ({N} s j)))))
(assert (forall ((s {S}) (k Int) (j Int)) (! (=> (and (<= 0 k) (<= 0 j) (< j (- ({L} s) k))) (= ({N} ({D} s k) j) ({N} s (+ j k))))
  :pattern (({N} ({D} s k) j)))))
(assert (forall ((s {S}) (k Int)) (! (=> (= k ({L} s)) (= ({T} s k) s)) :pattern (({T} s k)))))
(assert (forall ((s {S}) (k Int)) (! (=> (= k 0) (= ({T} s k) {Z})) :pattern (({T} s k)))))
(assert (forall ((s {S}) (k Int) (j Int)) (! (=> (and (<= 0 j) (<= j k) (<= k ({L} s))) (= ({T} ({T} s k) j) ({T} s j)))
  :pattern (({T} ({T} s k) j)))))
(declare-fun {H} ({S} {E}) Bool)
(assert (forall ((s {S}) (x {E})) (! (= ({H} s x) (exists ((i Int)) (and (<= 0 i) (< i ({L} s)) (= ({N} s i) x))))
  :pattern (({H} s x)))))
(assert (forall ((s {S}) (t {S}) (x {E})) (! (= ({H} ({C} s t) x) (or ({H} s x) ({H} t x))) :pattern (({H} ({C} s t) x)))))
(assert (forall ((y {E}) (x {E})) (! (= ({H} ({U} y) x) (= x y)) :pattern (({H} ({U} y) x)))))
(assert (forall ((x {E})) (! (not ({H} {Z} x)) :pattern (({H} {Z} x)))))
"""


def seq_eq(S, f, same=lambda a, b: f"(= {a} {b})"):
    """§9's equality for sequences of sort S, whose elements compare by same: equal lengths and
    elements make two sequences eq, and eq ones are the same sequence (D108)."""
    L, N, Q = f("len"), f("nth"), f("eq")
    return f"""(declare-fun {Q} ({S} {S}) Bool)
(assert (forall ((s {S}) (t {S})) (! (=> (and (= ({L} s) ({L} t)) (forall ((j Int))
  (=> (and (<= 0 j) (< j ({L} s))) {same(f"({N} s j)", f"({N} t j)")}))) ({Q} s t)) :pattern (({Q} s t)))))
(assert (forall ((s {S}) (t {S})) (! (=> ({Q} s t) (= s t)) :pattern (({Q} s t)))))
"""


def ms_facts(E, S, f):
    """§9's multiset facts for sequences of sort S."""
    M, C, U, Z, ZERO = f("ms"), f("cat"), f("unit"), f("empty"), f"((as const (Array {E} Int)) 0)"
    return f"""(declare-fun {M} ({S}) (Array {E} Int))
(assert (= ({M} {Z}) {ZERO}))
(assert (forall ((x {E})) (! (= ({M} ({U} x)) (store {ZERO} x 1)) :pattern (({M} ({U} x))))))
(assert (forall ((s {S}) (t {S})) (! (= ({M} ({C} s t)) ({MSUM} ({M} s) ({M} t))) :pattern (({M} ({C} s t))))))
"""


for E, X in (("Int", "I"), ("Bool", "B")):
    PRELUDE += f"(declare-sort S{X} 0)\n" + seq_facts(E, f"S{X}", lambda op: f"{op}.{X}")
for E, X in (("Int", "I"), ("Bool", "B")):
    PRELUDE += ms_facts(E, f"S{X}", lambda op: f"{op}.{X}")
ELEM = {"SI": "Int", "SB": "Bool"}
EQ = {X: seq_eq(f"S{X}", lambda op: f"{op}.{X}") for X in "IB"}  # only in queries that compare such sequences
EXPRS_1 = {"match", "is", "field", "tuple", "get", "rank", "iset-lit", "iset-of", "map-lit", "union", "diff", "inter",
           "update", "lookup"}  # B17-1's expressions, apart from constructor calls


def sort(t):
    if isinstance(t, Sym):
        return "Bool" if t.text == "bool" else "Int"
    h = _head(t)
    if h == "multiset":
        return f"(Array {sort(t.items[1])} Int)"
    if h == "ref":
        t = t.items[1]
    return "SB" if sort(t.items[1]) == "Bool" else "SI"


ttype = C.ttype


def norm(t):
    """t as its SMT sort sees it: i64 is int, and vectors and slices are sequences."""
    if t == C.I64:
        return C.INT
    if t[0] in ("vec", "slice"):
        return ("seq", norm(t[1]))
    return (t[0],) + tuple(a if isinstance(a, str) else norm(a) for a in t[1:])


def seq_of(elem):
    """The sort of a sequence of elements of sort elem, Int or Bool."""
    return "SB" if elem == "Bool" else "SI"


def fname(op, srt):
    """A sequence function's name on sequences of sort srt: len.I on SI, or len!3 on a sort
    B17-1 adds, s!3."""
    return f"{op}.{srt[1]}" if srt in ELEM else f"{op}!{srt[2:]}"


def fn(op, srt, *args):
    """A sequence function on sequences of sort srt, such as (len.I s)."""
    return f"({fname(op, srt)} {' '.join(args)})"


def app(f, args):
    """f applied to args; an SMT constant takes no parentheses."""
    return f"({f} {' '.join(args)})" if args else f


def num(v):
    return str(v) if v >= 0 else f"(- {-v})"


def in_i64(t):
    return f"(and (<= {MIN} {t}) (< {t} {LIM}))"


def _walk(x):
    """Every node of x, itself included."""
    yield x
    if isinstance(x, Form):
        for c in x.items:
            yield from _walk(c)


def _binds(decl):
    """The (name, sort) pairs of an SMT binder list such as "(x!b1 Int) (s!b2 (Array Int Bool))"."""
    out, depth, start = [], 0, 0
    for k, ch in enumerate(decl):
        if ch == "(":
            depth += 1
            start = k + 1 if depth == 1 else start
        elif ch == ")":
            depth -= 1
            if depth == 0:
                name, srt = decl[start:k].split(" ", 1)
                out.append((name, srt))
    return out


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
    def __init__(self, module, subset=SUBSET):
        self.sub = subset
        self.types = C.types(module, subset)  # raises if module fails tier 0
        self.defs, self.datas, self.ctors = {}, {}, {}  # data types and constructors are B17-1's (D82)
        for m in (CORE, C.CORE1, module) if subset else (CORE, module):
            for it in m.items[3:]:
                if it.items[0].text == "data":
                    self.datas[it.items[1].text] = it
                    self.ctors.update((c.items[0].text, it) for c in it.items[3:])
                else:
                    self.defs.setdefault(it.items[1].text, {})[it.items[0].text] = it
        self.elems = dict(ELEM)  # sequence sort -> element sort
        self.seqs = {}           # element sort -> sequence sort, for the element sorts B17-1 adds
        self.dts = {}            # data type, normalized -> its SMT datatype (D103)
        self.oks = {}            # data type -> its validity predicate, where i64 and int differ
        self.lifting = None      # while a ghost-fn is emitted: the seq-builds its body lifts out
        self.blocks = []         # (layer, names, text): declarations a query takes when it uses a name
        self.decls, self.goals, self.n = [], [], 0
        self.quiet = False
        self.item = None    # (name, measure at entry or None, its params) while checking an item
        self.part = "spec"  # whose goals: the spec part's or the implementation part's (D45)
        self.inputs = {}    # the current item's parameters: name -> (term, type), for counterexamples
        self.ghost = set()  # ids of the nodes generated in ghost context
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

    def name(self, base):
        """A generated SMT name for a sort, function or constructor B17-1 adds."""
        self.n += 1
        return f"{base}!{self.n}"

    def var(self, st, name, typ, base=None):
        c = self.fresh(base or name, self.sort(typ))
        st.env[name] = (c, typ)
        st.facts += self.type_facts(c, typ)
        return c

    def type_facts(self, t, typ, lengths=True):
        """Background facts that term t is a value of its type: every i64 fits, and so does
        every vector or slice length (§9), inside tuples, data values and sequences too. Inside
        a data value only the i64s count, so lengths=False there (D105)."""
        typ = self.ty(typ)
        if typ == C.I64:
            return [in_i64(t)]
        if typ[0] == "tuple":
            T = self.tuple(len(typ) - 1)
            return [f for i, u in enumerate(typ[1:]) for f in self.type_facts(f"(get.{T}.{i} {t})", u, lengths)]
        if typ[0] == "data":
            return [f"({self.ok(typ)} {t})"] if self.needs(typ) else []
        if typ[0] not in C.SEQUENCES:
            return []
        srt = self.sort(typ)
        out = [] if typ[0] == "seq" or not lengths else [f"(< {fn('len', srt, t)} {LIM})"]
        if self.needs(typ[1]):
            k = self.bound("k")
            each = self.type_facts(fn("nth", srt, t, k), typ[1], lengths)
            out.append(f"(forall (({k} Int)) (! (=> (and (<= 0 {k}) (< {k} {fn('len', srt, t)})) "
                       f"{each[0] if len(each) == 1 else '(and ' + ' '.join(each) + ')'}) :pattern ({fn('nth', srt, t, k)})))")
        return out

    def needs(self, t, seen=()):
        """Whether a value of type t has facts to be one inside it: an i64 there, which must fit.
        A vector's own length fact is its variable's, not part of what holds it, so a recursive
        type with a vector field but no i64, such as a trie's node, has no validity predicate
        guarding its ghost-fns' equations."""
        t = self.ty(t)
        if t == C.I64:
            return True
        if t[0] in C.SEQUENCES or t[0] == "tuple":
            return any(self.needs(u, seen) for u in C.parts(t))
        if t[0] != "data" or t in seen:
            return False
        return any(self.needs(f, seen + (t,)) for _, f in self.fields(t))

    def fields(self, t):
        """Data type t's fields, as (selector, declared type with t's arguments), constructor by constructor."""
        item, d = self.datas[t[1]], self.data(t)
        params = [a.text for a in item.items[2].items]
        env = dict(zip(params, t[2:]))
        return [(sel[1], C.subst(ttype(f.items[1], params), env))
                for c, (_, fs) in zip(item.items[3:], d["ctors"].values()) for f, sel in zip(c.items[1:], fs)]

    def ok(self, t):
        """The predicate that a value of data type t is one of t's values, whose i64s and
        vector lengths fit: as its fields' facts, read from it, and as what builds it."""
        if t not in self.oks:
            P = self.oks[t] = self.name("ok")  # first, so a recursive field finds it
            d = self.data(t)
            D = d["sort"]
            self.declare(3, {P}, f"(declare-fun {P} ({D}) Bool)")
            item, axioms = self.datas[t[1]], []
            types = iter(self.fields(t))
            for c, fs in d["ctors"].values():
                own = [next(types)[1] for _ in fs]
                for f, u in zip(fs, own):  # a valid value's fields are valid
                    for fact in self.type_facts(f"({f[1]} x)", u, False):
                        axioms.append(f"(assert (forall ((x {D})) (! (=> (and ({P} x) ((_ is {c}) x)) {fact}) "
                                      f":pattern (({P} x) ({f[1]} x)))))")
                xs = [f"(a{j} {f[3]})" for j, f in enumerate(fs)]
                built = app(c, [f"a{j}" for j in range(len(fs))])
                facts = [g for j, u in enumerate(own) for g in self.type_facts(f"a{j}", u, False)]
                axioms.append(f"(assert ({P} {built}))" if not xs else  # and valid fields build a valid value
                              f"(assert (forall ({' '.join(xs)}) (! (=> (and true {' '.join(facts)}) ({P} {built})) :pattern ({built}))))")
            self.declare(4, {P}, "\n".join(axioms))
        return self.oks[t]

    def sort_of(self, *xs, default="SI"):
        """The sort tier 0 gives the first of xs whose type an empty literal doesn't leave open."""
        return next((s for s in map(self.tsort, (self.types[id(x)] for x in xs)) if s), default)

    # Sorts. B17-0's are fixed, in the prelude; B17-1's are declared as they're needed, and a
    # query takes the declarations its names use (D89, D103).
    def ty(self, t):
        """A type as check.py writes it, from a type form or one already written so."""
        return ttype(t) if isinstance(t, (Sym, Form)) else t

    def sort(self, t):
        return self.tsort(self.ty(t))

    def tsort(self, t):
        """The SMT sort of a type as check.py writes it, or None where an empty literal leaves
        an element type open."""
        if t == C.BOOL:
            return "Bool"
        if t in (C.I64, C.INT):
            return "Int"
        if t == C.ANY:
            return None
        parts = [self.tsort(a) for a in C.parts(t)]
        if None in parts:
            return None
        h = t[0]
        if h in C.SEQUENCES:
            return self.seq(parts[0])
        if h == "multiset":
            return f"(Array {parts[0]} Int)"
        if h == "iset":
            return f"(Array {parts[0]} Bool)"
        if h == "map":  # D89: arrays from keys to (option V), none outside the map
            return f"(Array {parts[0]} {self.data(('data', 'option', t[2]))['sort']})"
        if h == "tuple":
            return f"({self.tuple(len(parts))} {' '.join(parts)})"
        return self.data(t)["sort"]

    def declare(self, layer, names, text):
        self.blocks.append((layer, set(names), text))

    def seq(self, e):
        """The sort of sequences of elements of sort e, with §9's facts for it (D61, D89)."""
        if e in ("Int", "Bool") or not self.sub:  # B17-0 has no nested sequences
            return seq_of(e)
        if e not in self.seqs:
            S = self.seqs[e] = self.name("s")
            self.elems[S] = e
            f = lambda op: fname(op, S)
            self.declare(0, {S}, f"(declare-sort {S} 0)")
            self.declare(3, map(f, ("len", "nth", "take", "drop", "cat", "unit", "empty", "has")),
                       seq_facts(e, S, f).rstrip())
            self.declare(3, {f("ms")}, ms_facts(e, S, f).rstrip())
            self.declare(3, {f("eq")}, seq_eq(S, f, lambda a, b: self.equal(e, a, b)).rstrip())
        return self.seqs[e]

    def tuple(self, n):
        """Tuples of n components: one parametric datatype per arity (D89)."""
        T = f"T{n}"
        if not any(T in names for _, names, _ in self.blocks):
            ps, gets = [f"A{i}" for i in range(n)], [f"get.{T}.{i}" for i in range(n)]
            fields = " ".join(f"({g} {a})" for g, a in zip(gets, ps))
            self.declare(1, {T, f"mk.{T}", *gets}, f"(declare-datatypes (({T} {n})) ((par ({' '.join(ps)}) ((mk.{T} {fields})))))")
        return T

    def data(self, t):
        """t's SMT datatype, one per instance of a data type (D103): its sort, and for each
        constructor its SMT name and its fields as (name, selector, type, sort)."""
        t = norm(t)
        if t not in self.dts:
            item = self.datas[t[1]]
            params = [a.text for a in item.items[2].items]
            env = dict(zip(params, t[2:]))
            d = self.dts[t] = {"sort": self.name("d"), "ctors": {}}  # first, so a recursive field finds it
            for c in item.items[3:]:
                d["ctors"][c.items[0].text] = (self.name("c"), [
                    [f.items[0].text, self.name("f"), C.subst(ttype(f.items[1], params), env)] for f in c.items[1:]])
            for _, fields in d["ctors"].values():
                for f in fields:
                    f.append(self.tsort(f[2]))
        return self.dts[t]

    def datatypes(self):
        """The datatypes' declarations: one per group whose members refer to each other, as an
        instance and the type it's applied to may, each after the groups it refers to."""
        sorts = {d["sort"]: d for d in self.dts.values()}
        refs = {s: {u for _, fs in d["ctors"].values() for f in fs for u in TOKEN.findall(f[3]) if u in sorts}
                for s, d in sorts.items()}
        reach = {}
        for s in sorts:
            todo, seen = [s], {s}
            while todo:
                for u in refs[todo.pop()] - seen:
                    seen.add(u)
                    todo.append(u)
            reach[s] = seen
        groups, done = [], set()
        for s in sorts:
            if s not in done:
                groups.append([u for u in sorts if u in reach[s] and s in reach[u]])
                done.update(groups[-1])
        out = []
        for g in sorted(groups, key=lambda g: len(reach[g[0]])):  # a group reaches all it refers to, and more
            ds = [sorts[s] for s in g]
            ctors = ["(" + " ".join("(" + " ".join([c, *(f"({f[1]} {f[3]})" for f in fs)]) + ")"
                                    for c, fs in d["ctors"].values()) + ")" for d in ds]
            names = {*g, *(c for d in ds for c, fs in d["ctors"].values()),
                     *(f[1] for d in ds for _, fs in d["ctors"].values() for f in fs)}
            out.append((2, names, f"(declare-datatypes ({' '.join(f'({s} 0)' for s in g)}) ({' '.join(ctors)}))"))
        return out

    def ctor(self, t, name):
        """Constructor name of data type t: its SMT name and fields."""
        return self.data(t)["ctors"][name]

    def option(self, v):
        """The core library's (option v): its none and some constructors, and some's selector."""
        (none, _), (some, fs) = self.data(("data", "option", v))["ctors"].values()
        return none, some, fs[0][1]

    def field(self, t, name):
        """Field name of data type t: the SMT constructor that has it, its fields, and the field."""
        return next((c, fs, f) for c, fs in self.data(t)["ctors"].values() for f in fs if f[0] == name)

    def rank(self, t):
        """rank's function on data type t, with D89's axioms: every rank is at least 0, and each
        data value a constructor's fields reach through tuples and sequences ranks below it."""
        d = self.data(t)
        if "rank" not in d:
            r = d["rank"] = self.name("rank")  # first, so a recursive path finds it
            D = d["sort"]
            self.declare(3, {r}, f"(declare-fun {r} ({D}) Int)")  # before any axiom, since axioms name each other's
            text = [f"(assert (forall ((x {D})) (! (>= ({r} x) 0) :pattern (({r} x)))))"]
            for c, fs in d["ctors"].values():
                for f in fs:
                    for term, u, js in self.paths(f"({f[1]} x)", f[2]):
                        below = f"({self.rank(u)} {term})"
                        conds = " ".join([f"((_ is {c}) x)", *(f"(<= 0 {j}) (< {j} {n})" for j, n in js)])
                        binds = " ".join([f"(x {D})", *(f"({j} Int)" for j, _ in js)])
                        text.append(f"(assert (forall ({binds}) (! (=> (and {conds}) (< {below} ({r} x))) "
                                    f":pattern ({below}))))")
            self.declare(4, {r}, "\n".join(text))
        return d["rank"]

    def paths(self, term, t, js=()):
        """The data values term, of type t, reaches through tuple components and sequence
        elements, stopping at the first: (term, its type, its index binders and their bounds)."""
        t = norm(t)
        if t[0] == "data":
            return [(term, t, js)]
        if t[0] == "tuple":
            T = self.tuple(len(t) - 1)
            return [p for i, u in enumerate(t[1:]) for p in self.paths(f"(get.{T}.{i} {term})", u, js)]
        if t[0] == "seq":
            srt, j = self.tsort(t), f"j{len(js)}"
            return self.paths(fn("nth", srt, term, j), t[1], js + ((j, fn("len", srt, term)),))
        return []

    # Goals and facts.
    def goal(self, st, guard, family, x, g, clause=None):
        if self.quiet:
            return
        g = wrap(guard, g)
        self.goals.append((self.item[0], family, x.pos, list(st.facts), g, x, self.part, clause, self.inputs))
        st.facts.append(g)  # every goal is assumed once generated (§9)

    def fact(self, st, guard, f):
        if st is not None and not any(k == "all" for k, _ in guard):
            st.facts.append(wrap(guard, f))

    # Expressions: (SMT term, SMT sort).
    def expr(self, x, st, ghost, guard=(), want="SI"):
        if ghost:
            self.ghost.add(id(x))
        if isinstance(x, Int):
            return num(x.value), "Int"
        if isinstance(x, Sym):
            if x.text in ("true", "false"):
                return x.text, "Bool"
            t, typ = st.env[x.text]
            return t, self.sort(typ)
        h, a = _head(x), x.items[1:]
        want = self.tsort(self.types[id(x)]) or want  # an open element type takes its context's sort
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
            w = self.sort_of(a[0], a[1])  # where an empty literal is compared, the other side's sort
            (l, srt), (r, _) = e(a[0], w=w), e(a[1], w=w)
            if srt in self.elems:
                eq = self.equal(srt, l, r)
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
        if h == "idx":  # an open sequence takes the sort its element's context gives
            (s, srt), (i, _) = e(a[0], w=self.seq(want)), e(a[1])
            self.goal(st, guard, "BOUNDS", x, f"(and (<= 0 {i}) (< {i} {fn('len', srt, s)}))")
            return fn("nth", srt, s, i), self.elems[srt]
        if h == "borrow":
            return e(a[0])
        if h in ("vec-new",) or (h == "seq-lit" and not a):
            srt = want if want in self.elems else "SI"
            return fname("empty", srt), srt
        if h == "seq-lit":
            parts, srt = [e(y) for y in a], want
            out = fn("unit", srt, parts[0][0])
            for t, _ in parts[1:]:
                out = fn("cat", srt, out, fn("unit", srt, t))
            return out, srt
        if h in ("take", "drop"):
            (s, srt), (k, _) = e(a[0], w=want), e(a[1])
            self.goal(st, guard, "BOUNDS", x, f"(and (<= 0 {k}) (<= {k} {fn('len', srt, s)}))")
            t = fn(h, srt, s, k)
            if h == "take":  # §9's step fact, which as a trigger would loop
                prev = fn("cat", srt, fn("take", srt, s, f"(- {k} 1)"), fn("unit", srt, fn("nth", srt, s, f"(- {k} 1)")))
                self.fact(st, guard, f"(=> (and (< 0 {k}) (<= {k} {fn('len', srt, s)})) (= {t} {prev}))")
            return t, srt
        if h == "concat":
            srt = want if want in self.elems else "SI"
            (s, _), (t, _) = e(a[0], w=srt), e(a[1], w=srt)
            return fn("cat", srt, s, t), srt
        if h == "last":
            s, srt = e(a[0], w=self.seq(want))
            self.goal(st, guard, "BOUNDS", x, f"(> {fn('len', srt, s)} 0)")
            return fn("nth", srt, s, f"(- {fn('len', srt, s)} 1)"), self.elems[srt]
        if h == "contains":
            if self.sub and self.types[id(a[0])][0] in ("iset", "map"):  # a set's member, or a map's key
                (s, _), (v, _) = e(a[0]), e(a[1])
                if self.types[id(a[0])][0] == "iset":
                    return f"(select {s} {v})", "Bool"
                return f"((_ is {self.option(self.types[id(a[0])][2])[1]}) (select {s} {v}))", "Bool"
            (s, srt), (v, _) = e(a[0], w=self.seq(self.sort_of(a[1]))), e(a[1])
            return fn("has", srt, s, v), "Bool"
        if h == "multiset":
            srt = self.sort_of(a[0], default=self.seq(want[7:-5]) if want.startswith("(Array ") else "SI")
            return fn("ms", srt, e(a[0], w=srt)[0]), f"(Array {self.elems[srt]} Int)"
        if h == "msum":
            srt = want if want.startswith("(Array") else "(Array Int Int)"
            return f"({MSUM} {e(a[0], w=srt)[0]} {e(a[1], w=srt)[0]})", srt
        if h == "occurrences":
            s, srt = e(a[0], w=self.seq(self.sort_of(a[1])))
            return f"(select {fn('ms', srt, s)} {e(a[1])[0]})", "Int"
        if h in ("forall", "exists"):
            decl, inner = self.binders(a[0].items, st)
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
            ss = self.seq(srt)
            bound = [b for k, d in guard if k == "all" for b in _binds(d)]
            # A body that doesn't use its index gives every element: the multiset is it, n times.
            same = not any(isinstance(y, Sym) and y.text == name for y in _walk(a[1].items[2]))
            counted = lambda r: f"(= {fn('ms', ss, r)} (store ((as const (Array {srt} Int)) 0) {body} {n}))"
            if not bound and self.lifting is None:
                r = self.fresh("seq", ss)
                self.fact(st, guard, f"(= {fn('len', ss, r)} {n})")
                self.fact(st, guard, f"(forall (({i} Int)) (! (=> {rng} (= {fn('nth', ss, r, i)} {body})) :pattern ({fn('nth', ss, r, i)})))")
                if same:
                    self.fact(st, guard, counted(r))
                return r, ss
            # Under binders, a function of them, with its facts at every point where the length
            # is defined; in a ghost-fn's body, an axiom beside its definition.
            f = self.name("seq")
            r = app(f, [v for v, _ in bound])
            under = guard + (("if", f"(>= {n} 0)"),)
            facts = [wrap(under, f"(= {fn('len', ss, r)} {n})"),
                     wrap(under, f"(forall (({i} Int)) (! (=> {rng} (= {fn('nth', ss, r, i)} {body})) :pattern ({fn('nth', ss, r, i)})))")]
            facts += [wrap(under, counted(r))] if same else []
            decl = f"(declare-fun {f} ({' '.join(srt for _, srt in bound)}) {ss})"
            if self.lifting is not None:
                self.lifting.append((None, "\n".join([decl, *(f"(assert {x})" for x in facts)])))
            elif st is not None:
                self.decls.append(decl)
                st.facts += facts
            return r, ss
        if self.sub and (h in EXPRS_1 or h in self.ctors):
            return self.expr1(x, h, a, st, ghost, guard, want)
        # (NAME e*): a ghost-fn call
        f = self.defs[h]["ghost-fn"]
        args = [e(y, w=self.sort(p.items[1]))[0] for y, p in zip(a, f.items[2].items)]
        if clauses(f, "requires"):
            self.goal(st, guard, "PRE", x, app(f"p!{h}", args))
        if self.item and h == self.item[0]:
            self.term_goal(st, guard, x, f, args)
        return app(f"g!{h}", args), self.sort(f.items[3])

    def equal(self, srt, l, r):
        """l = r at sort srt. Sequences are equal when their lengths and elements are (§9), and
        then they're the same sequence, so every function agrees on them (D108)."""
        return fn("eq", srt, l, r) if srt in self.elems else f"(= {l} {r})"

    def binders(self, bs, st):
        """Bound variables for binders bs: their SMT declaration, and a state that sees them."""
        inner, decl = State(dict(st.env), st.facts), []
        for b in bs:
            v = self.bound(b.items[0].text)
            inner.env[b.items[0].text] = (v, b.items[1])
            decl.append(f"({v} {self.sort(b.items[1])})")
        return " ".join(decl), inner

    def expr1(self, x, h, a, st, ghost, guard, want):
        """B17-1's expressions (docs/b17-1.md §7), encoded as D89 says."""
        e = lambda y, g=guard, w="SI": self.expr(y, st, ghost, g, w)
        t = self.types[id(x)]
        if h in self.ctors:  # a constructor call
            c, fs = self.ctor(t, h)
            return app(c, [e(y, w=f[3])[0] for y, f in zip(a, fs)]), self.data(t)["sort"]
        if h == "tuple":
            return f"(mk.{self.tuple(len(a))} {' '.join(e(y, w=self.tsort(u) or 'SI')[0] for y, u in zip(a, t[1:]))})", \
                self.tsort(t)
        if h == "get":
            s, _ = e(a[0])
            return f"(get.T{len(self.types[id(a[0])]) - 1}.{a[1].value} {s})", self.tsort(t) or want
        if h == "is":
            s, _ = e(a[1])
            return f"((_ is {self.ctor(self.types[id(a[1])], a[0].text)[0]}) {s})", "Bool"
        if h == "field":
            s, _ = e(a[0])
            u = self.types[id(a[0])]
            c, _, f = self.field(u, a[1].text)
            if len(self.data(u)["ctors"]) > 1:  # D89: a selector is guarded by FIELD
                self.goal(st, guard, "FIELD", x, f"((_ is {c}) {s})")
            return f"({f[1]} {s})", f[3]
        if h == "rank":
            s, _ = e(a[0])
            return f"({self.rank(self.types[id(a[0])])} {s})", "Int"
        if h == "match":
            s, _ = e(a[0])
            arms = []
            for case, (test, binds) in zip(a[1:], self.arms(a[0], s, a[1:])):
                inner, g = State(dict(st.env), st.facts), guard + ((("if", test),) if test else ())
                for name, term, u in binds:
                    inner.env[name] = (term, u)
                    for f in self.type_facts(term, u):
                        self.fact(inner, g, f)
                arms.append((test, self.expr(case.items[2], inner, ghost, g, want)))
            out, srt = arms[-1][1]
            for test, (body, _) in reversed(arms[:-1]):
                out = f"(ite {test} {body} {out})"
            return out, srt
        if h == "iset-lit":
            srt, es = self.tsort(t), self.tsort(t[1])
            members = [e(y, w=es)[0] for y in a]
            if es in self.elems and members:  # sequences are equal by their elements, so members are too (D105)
                y = self.bound("y")
                return f"(lambda (({y} {es})) (or {' '.join(self.equal(es, y, m) for m in members)}))", srt
            out = f"((as const {srt}) false)"
            for m in members:
                out = f"(store {out} {m} true)"
            return out, srt
        if h == "iset-of":  # D89: a lambda, whose body's goals hold at every member
            decl, inner = self.binders(a[0].items, st)
            body, _ = self.expr(a[1], inner, True, guard + (("all", decl),))
            return f"(lambda ({decl}) {body})", self.tsort(t)
        if h in ("map-lit", "update", "lookup") or (h == "union" and t[0] == "map"):
            m = t if h != "lookup" else self.types[id(a[0])]
            none, some, value = self.option(m[2])
            ks, vs = self.tsort(m[1]), self.tsort(m[2])
            if h == "map-lit":
                out = f"((as const {self.tsort(m)}) {none})"
                for pair in a:  # a later entry wins
                    out = self.store(out, ks, e(pair.items[0], w=ks)[0], f"({some} {e(pair.items[1], w=vs)[0]})")
                return out, self.tsort(m)
            if h == "update":
                (mt, srt), (k, _), (v, _) = e(a[0]), e(a[1], w=ks), e(a[2], w=vs)
                return self.store(mt, ks, k, f"({some} {v})"), srt
            if h == "lookup":
                (mt, _), (k, _) = e(a[0]), e(a[1], w=ks)
                self.goal(st, guard, "BOUNDS", x, f"((_ is {some}) (select {mt} {k}))")
                return f"({value} (select {mt} {k}))", vs
            (l, srt), (r, _) = e(a[0]), e(a[1])  # union: both maps' keys, the right one's value where both have one
            k = self.bound("k")
            return f"(lambda (({k} {ks})) (ite ((_ is {some}) (select {r} {k})) (select {r} {k}) (select {l} {k})))", srt
        # union, inter and diff of sets: lambdas, which Z3 reduces at each select. As array maps,
        # bst_insert's is_bst proved under only some seeds (D103).
        (l, srt), (r, _) = e(a[0]), e(a[1])
        y = self.bound("y")
        ly, ry = f"(select {l} {y})", f"(select {r} {y})"
        body = f"(or {ly} {ry})" if h == "union" else f"(and {ly} {ry})" if h == "inter" else f"(and {ly} (not {ry}))"
        return f"(lambda (({y} {self.tsort(t[1])})) {body})", srt

    def store(self, m, ks, k, v):
        """Map m with key k mapped to v. A sequence key is one by its elements (D105)."""
        if ks not in self.elems:
            return f"(store {m} {k} {v})"
        y = self.bound("y")
        return f"(lambda (({y} {ks})) (ite {self.equal(ks, y, k)} {v} (select {m} {y})))"

    def arms(self, scrutinee, s, cases):
        """Each arm's test, None where the type has one constructor, and its binders as (name,
        term, type). The terms are s's selectors, so in each arm s equals its constructor
        applied to its binders (D89)."""
        t, out = self.types[id(scrutinee)], []
        for case in cases:
            pat = case.items[1]
            names = [n.text for n in pat.items[1:]]
            if t[0] == "tuple":
                T = self.tuple(len(t) - 1)
                out.append((None, [(n, f"(get.{T}.{i} {s})", u) for i, (n, u) in enumerate(zip(names, t[1:]))]))
            else:
                c, fs = self.ctor(t, pat.items[0].text)
                test = f"((_ is {c}) {s})" if len(self.data(t)["ctors"]) > 1 else None
                out.append((test, [(n, f"({f[1]} {s})", f[2]) for n, f in zip(names, fs)]))
        return out

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
        d, _ = self.expr(dec[0][0], callee, True, guard)  # under a forall statement's binders (D99), no facts
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
                ps.append(f"({v} {self.sort(p.items[1])})")
            q, self.quiet, self.lifting = self.quiet, True, []
            every = (("all", " ".join(ps)),) if ps else ()  # its parameters are variables of the definition
            body, _ = self.expr(clauses(f, "body")[0][0], st, True, every, want=self.sort(f.items[3]))
            pre = [self.expr(c[0], st, True, every)[0] for c in clauses(f, "requires")]
            self.quiet = q
            lifted, self.lifting = self.lifting, None
            ret, pre = self.sort(f.items[3]), f"(and true {' '.join(pre)})"
            if name not in self.calls(f) and not (self.sub and ps):
                out.extend(lifted)
                out.append((None, f"(define-fun g!{name} ({' '.join(ps)}) {ret} {body})"))
                out.append((None, f"(define-fun p!{name} ({' '.join(ps)}) Bool {pre})"))
                return
            if name not in self.calls(f):
                # B17-1 (D106): a function with a definition triggered by its applications, not a
                # macro, so it unfolds only where a proof applies it. Inlined into a quantified
                # invariant, a body with its own quantifiers multiplies the instantiations of
                # every query that carries the invariant.
                sorts = " ".join(p.split(" ", 1)[1][:-1] for p in ps)
                args = [p[1:].split(" ", 1)[0] for p in ps]
                out.extend(lifted)
                out.append((None, f"(declare-fun g!{name} ({sorts}) {ret})\n"
                                  f"(assert (forall ({' '.join(ps)}) (! (= {app('g!' + name, args)} {body}) "
                                  f":pattern ({app('g!' + name, args)}))))"))
                out.append((None, f"(define-fun p!{name} ({' '.join(ps)}) Bool {pre})"))
                return
            # Recursive: its equation holds only under its requires, and the ghost-fn's own goals
            # are checked without it (see query). A definition that doesn't terminate could
            # otherwise be contradictory, and prove everything, its own TERM goal included.
            sorts = " ".join(p.split(" ", 1)[1][:-1] for p in ps)
            args = [p[1:].split(" ", 1)[0] for p in ps]
            out.append((None, f"(declare-fun g!{name} ({sorts}) {ret})"))
            out.extend(lifted)  # after the declaration, since a lifted seq-build may call it
            out.append((None, f"(define-fun p!{name} ({' '.join(ps)}) Bool {pre})"))
            # Its measure is proved only for values of its parameter types, so its equation holds
            # only for those: an SMT value may have an i64 field out of range, where recursion
            # needn't descend.
            typed = [g for p, a in zip(f.items[2].items, args) for g in self.type_facts(a, p.items[1])]
            pre_ = app('p!' + name, args) if not typed else f"(and {' '.join(typed)} {app('p!' + name, args)})"
            eq = f"(=> {pre_} (= {app('g!' + name, args)} {body}))"
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
        if self.sub and (h in ("match", "forall", "obtain") or (h in ("set-idx", "push") and isinstance(a[0], Form))
                         or (h in ("let", "let-mut") and _head(a[-1]) == "replace")):
            return self.stmt1(x, h, a, st, ghost)
        if h in ("let", "let-mut", "ghost-let", "ghost-let-mut"):
            g = ghost or h.startswith("ghost")
            if isinstance(a[0], Form):  # (let (param+) (call NAME e*))
                self.call(a[1], st, g, a[0].items)
                return st
            t, _ = self.expr(a[2], st, g, want=self.sort(a[1]))
            c = self.var(st, a[0].text, a[1])
            st.facts.append(f"(= {c} {t})")
            return st
        if h in ("set", "ghost-set"):
            t, _ = self.expr(a[1], st, ghost or h == "ghost-set", want=self.sort(st.env[a[0].text][1]))
            c = self.var(st, a[0].text, st.env[a[0].text][1])
            st.facts.append(f"(= {c} {t})")
            return st
        if h in ("set-idx", "push"):
            old, typ = st.env[a[0].text]
            srt = self.sort(typ)
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
            ov, ms = fn("nth", srt, old, i), fname("ms", srt)
            m1 = f"(store ({ms} {old}) {ov} (- (select ({ms} {old}) {ov}) 1))"
            st.facts.append(f"(= ({ms} {new}) (store {m1} {v} (+ (select {m1} {v}) 1)))")
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

    def stmt1(self, x, h, a, st, ghost):
        """B17-1's statements (docs/b17-1.md §7): updates through places, match, and D99's
        forall and D100's obtain."""
        if h in ("set-idx", "push", "let", "let-mut"):  # indices, then the value, then each step's goal (§5)
            root, steps = self.place(a[-1].items[1] if h.startswith("let") else a[0], st, ghost)
            if h == "set-idx":
                i, _ = self.expr(a[1], st, ghost)
            v, _ = (self.expr(a[-1].items[2], st, ghost, want=self.sort(a[1])) if h.startswith("let") else
                    self.expr(a[-1], st, ghost))
            old, t, path = self.walk(st, root, steps)
            srt = self.tsort(t)
            if h == "set-idx":
                self.goal(st, (), "BOUNDS", x, f"(and (<= 0 {i}) (< {i} {fn('len', srt, old)}))")
                v = self.stored(st, old, srt, i, v)
            elif h == "push":
                v = fn("cat", srt, old, fn("unit", srt, v))
            else:  # (let y T (replace p e)): y is p's old value, and p is e
                st.facts.append(f"(= {self.var(st, a[0].text, a[1])} {old})")
            self.rebuild(st, root, path, v)
            return st
        if h == "match":
            s, _ = self.expr(a[0], st, ghost)
            outs = []
            for case, (test, binds) in zip(a[1:], self.arms(a[0], s, a[1:])):
                arm = st.copy()
                if test:
                    arm.facts.append(test)
                for name, term, u in binds:
                    arm.env[name] = (term, u)
                    arm.facts += self.type_facts(term, u)
                outs.append((test, self.stmt(case.items[2], arm, ghost)))
            end = outs[-1][1]
            for test, arm in reversed(outs[:-1]):  # the arms join as an if's branches do
                end = self.join(st, test, arm, end)
            return end
        decl, inner = self.binders(a[0].items, st)
        if h == "obtain":  # D100: e's goals at every point, then ∃x. e; then x names a witness
            t, _ = self.expr(a[1], inner, True, (("all", decl),))
            self.goal(st, (), "ASSERT", x, f"(exists ({decl}) {t})")
            for b in a[0].items:
                self.var(st, b.items[0].text, b.items[1])
            q, self.quiet = self.quiet, True
            st.facts.append(self.expr(a[1], st, True)[0])
            self.quiet = q
            return st
        # D99: (forall ((x T) ...) (call L e*)): the arguments' goals at every point, L's measure
        # where L applies itself, then ∀x. requires => ensures
        c = a[1]
        name, lemma = c.items[1].text, self.defs[c.items[1].text]["lemma"]
        params = clauses(lemma, "params")[0]
        every = (("all", decl),)
        terms = [self.expr(y, inner, True, every, self.sort(p.items[1]))[0] for y, p in zip(c.items[2:], params)]
        env = State(dict(inner.env), inner.facts)
        for p, t in zip(params, terms):
            env.env[p.items[0].text] = (t, p.items[1])
        q, self.quiet = self.quiet, True
        req, ens = (" ".join(self.expr(c2, env, True, every)[0] for cl in clauses(lemma, k) for c2 in cl)
                    for k in ("requires", "ensures"))
        self.quiet = q
        if self.item and name == self.item[0]:
            self.term_goal(st, every + (("if", f"(and true {req})"),), c, lemma, terms)
        st.facts.append(f"(forall ({decl}) (=> (and true {req}) (and true {ens})))")
        return st

    def place(self, p, st, ghost):
        """Place p's root, and its steps from the root out as (form, index term or None), with
        each index evaluated in source order (§5 rule 3)."""
        forms = []
        while isinstance(p, Form):
            forms.append(p)
            p = p.items[1]
        return p.text, [(f, self.expr(f.items[2], st, ghost)[0] if _head(f) == "idx" else None) for f in reversed(forms)]

    def walk(self, st, root, steps):
        """The part of root's value at steps, with each step's goal on the way down: its term,
        its type, and the path to it as (parent term, parent type, form, index)."""
        cur, t = st.env[root][0], self.ty(st.env[root][1])
        path = []
        for f, i in steps:
            path.append((cur, t, f, i))
            if _head(f) == "idx":
                srt = self.tsort(t)
                self.goal(st, (), "BOUNDS", f, f"(and (<= 0 {i}) (< {i} {fn('len', srt, cur)}))")
                cur, t = fn("nth", srt, cur, i), t[1]
            elif _head(f) == "get":
                cur, t = f"(get.{self.tuple(len(t) - 1)}.{f.items[2].value} {cur})", t[1 + f.items[2].value]
            else:
                c, _, fd = self.field(t, f.items[2].text)
                if len(self.data(t)["ctors"]) > 1:
                    self.goal(st, (), "FIELD", f, f"((_ is {c}) {cur})")
                cur, t = f"({fd[1]} {cur})", fd[2]
        return cur, t, path

    def rebuild(self, st, root, path, new):
        """Bind root to its value with the part at the end of path replaced by new (§8)."""
        for cur, t, f, i in reversed(path):
            if _head(f) == "idx":
                new = self.stored(st, cur, self.tsort(t), i, new)
            elif _head(f) == "get":
                T, k = self.tuple(len(t) - 1), f.items[2].value
                new = f"(mk.{T} {' '.join(new if j == k else f'(get.{T}.{j} {cur})' for j in range(len(t) - 1))})"
            else:
                c, fs, fd = self.field(t, f.items[2].text)
                new = app(c, [new if g is fd else f"({g[1]} {cur})" for g in fs])
        st.facts.append(f"(= {self.var(st, root, st.env[root][1])} {new})")

    def stored(self, st, old, srt, i, v):
        """A sequence of sort srt equal to old but for v at i: §9's set-idx facts."""
        new, k = self.fresh("seq", srt), self.bound("k")
        st.facts += [f"(= {fn('len', srt, new)} {fn('len', srt, old)})",
                     f"(forall (({k} Int)) (! (=> (and (<= 0 {k}) (< {k} {fn('len', srt, old)}) (not (= {k} {i}))) "
                     f"(= {fn('nth', srt, new, k)} {fn('nth', srt, old, k)})) :pattern ({fn('nth', srt, new, k)})))",
                     f"(= {fn('nth', srt, new, i)} {v})"]
        ov, ms = fn("nth", srt, old, i), fname("ms", srt)
        m1 = f"(store ({ms} {old}) {ov} (- (select ({ms} {old}) {ov}) 1))"
        st.facts.append(f"(= ({ms} {new}) (store {m1} {v} (+ (select {m1} {v}) 1)))")
        return new

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
        for name in [n for n in self.assigned(body) if n in st.env]:  # in a name-independent order (D63)
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
            self.goal(end, (), "TERM", dec, f"(< {d} {d0})", clause=x)  # the drop across a pass
        after.facts.append(f"(not {c})")
        return after

    def assigned(self, stmts):
        """The names the statements assign, in order of first assignment."""
        out = {}
        for s in stmts:
            if isinstance(s, Form):
                if _head(s) in ("set", "set-idx", "push", "ghost-set", "replace"):
                    root = s.items[1]
                    while isinstance(root, Form):  # a place's root (B17-1)
                        root = root.items[1]
                    out[root.text] = None
                out.update(dict.fromkeys(self.assigned(s.items[1:])))
        return list(out)

    def call(self, x, st, ghost, results):
        name, args = x.items[1].text, x.items[2:]
        d = self.defs[name]
        callee = d.get("spec") or d["lemma"]
        g = ghost or "lemma" in d
        params = clauses(callee, "params")[0]
        terms = [self.expr(y, st, g, want=self.sort(p.items[1]))[0] for y, p in zip(args, params)]
        env = State(dict(st.env), st.facts)
        for p, t in zip(params, terms):
            env.env[p.items[0].text] = (t, p.items[1])
        q, self.quiet = self.quiet, True
        pres = [(c, self.expr(c, env, True)[0]) for cl in clauses(callee, "requires") for c in cl]
        self.quiet = q
        for c, pre in pres:
            self.goal(st, (), "PRE", x, pre, clause=c)
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
            env.env[p.items[0].text] = (self.expr(y, st, ghost, want=self.sort(p.items[1]))[0], p.items[1])
        self.post(x, spec, env, st)

    def post(self, x, spec, env, st):
        for cl in clauses(spec, "ensures"):
            for c in cl:
                q, self.quiet = self.quiet, True
                t, _ = self.expr(c, env, True)
                self.quiet = q
                self.goal(st, (), "POST", x, t, clause=c)
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
        self.inputs = {}
        for p in ps:
            self.var(st, p.items[0].text, p.items[1])
            self.inputs[p.items[0].text] = st.env[p.items[0].text]

    def check(self, module):
        for it in module.items[3:]:
            kind, name = it.items[0].text, it.items[1].text
            if kind == "data":  # its declarations are the datatype's, and it has no goals
                continue
            st = State({}, [])
            self.item, self.part = (name, None, ()), "spec"
            if kind == "ghost-fn":
                ps = it.items[2].items
                self.params(st, ps)
                dec = clauses(it, "decreases")
                if dec:  # a recursive call in its requires or measure is one too (D57), against this measure
                    q, self.quiet = self.quiet, True
                    self.item = (name, self.expr(dec[0][0], st, True)[0], ps)
                    self.quiet = q
                for c in clauses(it, "requires"):
                    st.facts.append(self.expr(c[0], st, True)[0])
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
        self.part = "impl"
        d0 = self.expr(dec[0][0], st, True)[0] if dec else None
        self.item = (it.items[1].text, d0, ps)
        end = self.block(clauses(it, "body")[0], st, ghost)
        if end is not None and ghost:  # a lemma's ensures at the end of its body
            self.post(it, it, State(dict(end.env), end.facts), end)


def query(gen, facts, g, item=None):
    """One goal's query: only the declarations and ghost-fns it uses, so an edit elsewhere in
    the module leaves it unchanged (D22, D63). A recursive ghost-fn's own goals don't get its
    definition."""
    asserts = [*(f"(assert {f})" for f in facts), f"(assert (not {g}))", "(check-sat)"]
    used = set(TOKEN.findall(" ".join(asserts)))
    funs = [(name, t) for name, t in gen.funs if name is None or name != item]
    keep, grew = set(), True
    while grew:  # the ghost-fns the query uses, and the ones they use
        grew = False
        for k, (name, t) in enumerate(funs):
            sym = f"g!{name}" if name else DEFINES.match(t)[1]
            if k not in keep and sym in used:
                keep.add(k)
                used |= set(TOKEN.findall(t))
                grew = True
    decls = [d for d in gen.decls if d.split()[1] in used]
    # B17-1's sorts, datatypes, sequence facts and rank's functions and axioms that those use, in layers so
    # each comes after what it names (D103)
    blocks = sorted(gen.blocks + (gen.datatypes() if gen.dts else []), key=lambda b: b[0])
    used |= set(TOKEN.findall(" ".join(decls)))
    taken, grew = set(), True
    while grew:
        grew = False
        for k, (_, names, t) in enumerate(blocks):
            if k not in taken and names & used:
                taken.add(k)
                used |= set(TOKEN.findall(t))
                grew = True
    body = "\n".join([*(t for k, (_, _, t) in enumerate(blocks) if k in taken), *decls,
                      *(t for k, (_, t) in enumerate(funs) if k in keep), *asserts])
    return (PRELUDE + (VDIV if "(vdiv " in body or "(vmod " in body else "")
            + "".join(t for X, t in EQ.items() if f"(eq.{X} " in body) + body)


TOKEN = re.compile(r"[^\s()]+")
DEFINES = re.compile(r"\((?:define-fun|declare-fun) (\S+)")


def solve(text, seed=0):
    return solve_stats(text, seed)[0]


def solve_stats(text, seed=0):
    """The verdict on one query, and the resource units Z3 spent on it."""
    if seed:  # D23's shuffled seeds: the SMT core's and the SAT core's
        text = text.replace("(set-option :smt.random_seed 0)",
                            f"(set-option :smt.random_seed {seed})\n(set-option :sat.random_seed {seed})", 1)
    # D23: a resource budget, not seconds, so verdicts don't depend on load. The most a proved
    # suite goal needs is about 0.84M units; the time limit is only a backstop.
    r = subprocess.run(["z3", f"rlimit={RLIMIT}", "-T:300", "-st", "-in"], input=text, capture_output=True, text=True)
    out = r.stdout.strip().splitlines()
    units = next((int(line.split()[-1].rstrip(")")) for line in out if ":rlimit-count" in line), 0)
    if any(line.startswith("(error") for line in out) or r.stderr:
        return "error: " + (r.stdout + r.stderr)[:300], units
    first = out[0] if out else ""
    return {"unsat": "proved", "sat": "failed", "unknown": "unknown"}.get(first, "unknown: " + first), units


def read(path, subset=SUBSET):
    """The module at path; the core library is the one object tier 0 typed, so its goals can be checked."""
    m = parse(Path(path).read_bytes(), subset)
    return CORE if m == CORE else m


def run(path, seeds=0, subset=SUBSET):
    gen = Gen(m := read(path, subset), subset)
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
    return [g[:3] + (v,) for g, v in zip(goals, verdicts)]


if __name__ == "__main__":
    bad, args, seeds, subset = 0, sys.argv[1:], 0, SUBSET
    while args[:1] in (["--seeds"], ["--subset"]) and args[1:2] and args[1].isdigit():
        if args[0] == "--seeds":
            seeds = int(args[1])
        else:
            subset = int(args[1])
        args = args[2:]
    for path in args:
        results = run(path, seeds, subset)
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
