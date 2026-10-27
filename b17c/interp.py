"""B17-0's reference interpreter (docs/b17-0.md §8, D28, D56-D59).

    uv run --no-project b17c/interp.py [--check] [--fuel N] FILE NAME ARG...

runs the def NAME in FILE on the ARGs, each a closed B17-0 expression such as 5 or
(seq-lit 1 2 3), and prints the run's trace and outcome in interface 10's text form
(D56). It exits 0 on ok, 1 on any other outcome, and 2 when the run can't start.

run() assumes the program passes tier 0 (WP3). With check=False it is §8: ghost code is
erased. With check=True it also evaluates contracts, invariants, measures, asserts,
ghost locals and ghost-fn calls, and stops at the first clause the run refutes (D57).
A quantifier whose range can't be read off its guard is never assumed (D58).
"""
import operator
import sys
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

from syntax import Form, Int, ParseError, Str, Sym, _head, _print, parse, parse_expr

CORE = parse((Path(__file__).parent / "core.b17").read_bytes())
MIN, MAX = -2**63, 2**63 - 1
FUEL, DEPTH = 1_000_000, 1_000  # D59: steps per run, and nested def and ghost-fn calls


class _Unknown:
    def __repr__(self):
        return "UNKNOWN"


UNKNOWN = _Unknown()  # a quantifier whose range can't be read off its guard, and what it touches (D58)
_PENDING = object()  # a call's measure, until its requires hold or a recursive call needs it (D57)


@dataclass(frozen=True)
class Multiset:
    """A ghost multiset: (element, count) pairs in element order, so equal multisets are equal."""
    counts: tuple

    @staticmethod
    def of(counter):
        return Multiset(tuple(sorted(counter.items())))

    def count(self, x):
        return dict(self.counts).get(x, 0)


@dataclass(frozen=True)
class Node:
    """A node's ID: its item, its child-index path within the item (D22), and where it is."""
    item: str
    path: tuple
    pos: tuple

    def __str__(self):
        path = "/" + ".".join(map(str, self.path)) if self.path else ""
        return f"{self.item}{path}@{self.pos[0]}:{self.pos[1]}"


# Outcomes (D56). Each carries the trace up to where the run stopped, and the clauses it
# couldn't evaluate (D58).

@dataclass(frozen=True)
class Ok:
    results: tuple
    trace: tuple = ()
    unchecked: tuple = ()


@dataclass(frozen=True)
class Panic:
    message: str
    trace: tuple = ()
    unchecked: tuple = ()


@dataclass(frozen=True)
class Err:
    """§8's stuck state. reason is the §9 family whose goal rules it out: OVERFLOW, DIV or BOUNDS."""
    reason: str
    node: Node
    detail: str
    trace: tuple = ()
    unchecked: tuple = ()


@dataclass(frozen=True)
class Contract:
    """check=True only: clause, checked at node, fails for this run. kind is its §9 family (D57)."""
    kind: str
    clause: Node
    node: Node
    detail: str
    trace: tuple = ()
    unchecked: tuple = ()


@dataclass(frozen=True)
class Limit:
    """The run used up its steps or its call depth (D59). Not an outcome of §8."""
    kind: str
    node: Node
    trace: tuple = ()
    unchecked: tuple = ()


@dataclass(frozen=True)
class Unchecked:
    """A clause that came out unknown at node, so it was neither trusted nor refuted (D58)."""
    kind: str
    clause: Node
    node: Node


def run(module, name, args, check=False, fuel=FUEL, depth=DEPTH):
    """Run the def name of module (a tree, or source text) on args per §8, or with check=True
    with its contracts evaluated too (D57). Args are bools, ints and tuples (or lists)."""
    if not isinstance(module, Form):
        module = parse(module)
    p = _Program(module)
    fn = p.fns.get(name)
    if fn is None or fn.kind != "def":
        raise ValueError(f"no def named {name!r}")
    args = tuple(_value(a) for a in args)
    if len(args) != len(fn.params):
        raise ValueError(f"{name} takes {len(fn.params)} argument{'' if len(fn.params) == 1 else 's'}, "
                         f"got {len(args)}")
    for a, t, param in zip(args, fn.types, fn.params):
        if not _fits(a, t):
            raise ValueError(f"argument {param}: {_term(a)} is not a value of type {_print(t)}")
    r = _Run(p, check, fuel, depth)
    with _deep(depth):
        try:
            out = Ok(r.invoke(fn, args, fn.item))
        except _Stop as e:
            out = e.outcome
        except _Unbound as e:
            raise ValueError(f"'{e.name}' at {e.node} {e.why}") from None
    return replace(out, trace=tuple(r.trace), unchecked=tuple(r.unchecked))


def value(module, text):
    """The value of a closed B17-0 expression, such as a command-line argument, in ghost context."""
    tree = parse_expr(text)
    r = _Run(_Program(module), True, FUEL, DEPTH)
    with _deep(DEPTH):
        try:
            v = r.eval(tree, {}, True)
        except _Stop as e:
            raise ValueError(f"{text}: {text_of(e.outcome)}") from None
        except _Unbound as e:  # here the argument is at fault, not the program
            raise ValueError(f"{text}: '{e.name}' {e.why.split(';')[0]}") from None
    if v is UNKNOWN:
        raise ValueError(f"{text}: its value can't be computed (D58)")
    return v


def text_of(out):
    """Interface 10's text form (D56): a line per print, then unchecked clauses, then the outcome."""
    lines = [f"print {_term(v)}" for v in out.trace]
    lines += [f"unchecked {u.kind} {u.clause} at {u.node}" for u in out.unchecked]
    if isinstance(out, Ok):
        last = " ".join(["ok"] + [_term(v) for v in out.results])
    elif isinstance(out, Panic):
        last = "panic " + _print(Str(out.message))
    elif isinstance(out, Err):
        last = f"err {out.reason} at {out.node}: {out.detail}"
    elif isinstance(out, Contract):
        last = f"contract {out.kind} {out.clause} at {out.node}: {out.detail}"
    else:
        last = f"limit {out.kind} at {out.node}"
    return "\n".join(lines + [last])


def _term(v):
    """A value as a B17-0 term."""
    if v is True or v is False:
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, tuple):
        return "(" + " ".join(["seq-lit"] + [_term(x) for x in v]) + ")"
    if isinstance(v, Multiset):
        return f"(multiset {_term(tuple(x for x, n in v.counts for _ in range(n)))})"
    return "unknown"


def _value(a):
    return tuple(_value(x) for x in a) if isinstance(a, (list, tuple)) else a


def _fits(v, t):
    """Whether v is a value of the runtime or ghost type t."""
    if isinstance(t, Sym):
        if t.text == "bool":
            return type(v) is bool
        return type(v) is int and (t.text == "int" or MIN <= v <= MAX)
    inner = t.items[1].items[1] if t.items[0].text == "ref" else t.items[1]
    return type(v) is tuple and all(_fits(x, inner) for x in v)


@contextmanager
def _deep(depth):
    """Room on Python's stack for depth nested calls; the limit that counts is D59's, not Python's."""
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 300 * (depth + 1)))
    try:
        yield
    finally:
        sys.setrecursionlimit(old)


# The program.

@dataclass(frozen=True)
class _Fn:
    """What running needs from a def and its spec (D39), a ghost-fn or a lemma."""
    kind: str
    name: str
    item: Form
    params: tuple    # names
    types: tuple     # their types
    results: tuple   # a def's result names
    requires: tuple
    ensures: tuple
    decreases: object  # an expression, or None
    body: object       # statements, or a ghost-fn's expression


def _clauses(item, head):
    """The arguments of item's clauses with this head, in order."""
    return tuple(a for c in item.items[2:] if _head(c) == head for a in c.items[1:])


def _one(item, head):
    args = _clauses(item, head)
    return args[0] if args else None


def _names(params):
    return tuple(p.items[0].text for p in params)


def _types(params):
    return tuple(p.items[1] for p in params)


class _Program:
    """A module's runnable items, with the core library's, and the ID of every node (D56)."""

    def __init__(self, module):
        self.fns, self.ids, specs, defs = {}, {}, {}, {}
        for m in (CORE, module):
            for item in m.items[3:]:
                kind, name = item.items[0].text, item.items[1].text
                self._index(item, f"{kind} {name}", ())
                if kind == "spec":
                    specs[name] = item
                elif kind == "def":
                    defs[name] = item
                elif kind == "ghost-fn":
                    ps = item.items[2].items
                    self.fns[name] = _Fn(kind, name, item, _names(ps), _types(ps), (),
                                         _clauses(item, "requires"), (), _one(item, "decreases"),
                                         _one(item, "body"))
                else:
                    ps = _clauses(item, "params")
                    self.fns[name] = _Fn(kind, name, item, _names(ps), _types(ps), (),
                                         _clauses(item, "requires"), _clauses(item, "ensures"),
                                         _one(item, "decreases"), _clauses(item, "body"))
        for name, item in defs.items():
            if name not in specs:
                raise ValueError(f"def {name} has no spec; the program doesn't pass tier 0 (E-TYPE-002)")
            spec = specs[name]
            ps = _clauses(spec, "params")
            self.fns[name] = _Fn("def", name, item, _names(ps), _types(ps),
                                 _names(_clauses(spec, "returns")), _clauses(spec, "requires"),
                                 _clauses(spec, "ensures"), _one(item, "decreases"), _clauses(item, "body"))

    def _index(self, x, item, path):
        self.ids[id(x)] = (item, path)
        if isinstance(x, Form):
            for k, c in enumerate(x.items):
                self._index(c, item, path + (k,))

    def node(self, x):
        item, path = self.ids.get(id(x), ("argument", ()))
        return Node(item, path, x.pos)


class _Stop(Exception):
    """Ends a run with an outcome other than ok."""

    def __init__(self, outcome):
        self.outcome = outcome


class _Unbound(Exception):
    """A name with nothing to run: undefined (a program that fails tier 0, or a bad argument),
    or a spec with no def."""

    def __init__(self, name, node, why="isn't defined"):
        self.name, self.node, self.why = name, node, why


# Running. Values are bools, ints, tuples (sequences) and Multisets; UNKNOWN only in ghost code.
# Expressions are evaluated with g, true in ghost context: integers are unbounded there and a
# failed goal is a contract outcome, while in runtime context integers are i64 and a failed
# goal is err. Recursive paths avoid generator calls, which would use C stack (D59).

class _Run:
    def __init__(self, program, check, fuel, depth):
        self.p, self.check, self.fuel, self.depth = program, check, fuel, depth
        self.trace = []
        self.unchecked = {}  # Unchecked -> None: first-seen order, each once
        self.frames = []     # [fn, measure] of every def and ghost-fn call in progress
        self.memo = {}       # (ghost-fn name, args) -> value; ghost-fns are pure
        self.active = set()  # (ghost-fn name, args) of the ghost-fn calls in progress
        self.clause = None   # the clause being evaluated, to which a failure inside it belongs

    def tick(self, x):
        self.fuel -= 1
        if self.fuel < 0:
            raise _Stop(Limit("steps", self.p.node(x)))

    def fail(self, reason, x, detail, g):
        node = self.p.node(x)
        if g:
            clause = self.p.node(self.clause) if self.clause is not None else node
            raise _Stop(Contract(reason, clause, node, detail))
        raise _Stop(Err(reason, node, detail))

    def note(self, kind, clause, site):
        self.unchecked[Unchecked(kind, self.p.node(clause), self.p.node(site))] = None

    # Statements return the results of a return, or None to continue.

    def invoke(self, fn, args, site):
        """Call def fn: its requires on entry, its measure if recursive, then its body (D57)."""
        env, depth = dict(zip(fn.params, args)), len(self.frames)
        try:
            self.enter(fn, env, site)
            r = self.block(fn.body, env)
        finally:
            del self.frames[depth:]  # also when a failure inside is caught and the run goes on
        if r is None:
            raise ValueError(f"def {fn.name} ended without return or panic; it doesn't pass tier 0 (E-RET-001)")
        return r

    def block(self, stmts, env):
        for s in stmts:
            r = self.stmt(s, env)
            if r is not None:
                return r
        return None

    def stmt(self, s, env):
        self.tick(s)
        it = s.items
        h = it[0].text
        if h in ("let", "let-mut"):
            if isinstance(it[1], Form):  # (let ((x T) ...) (call f e*)), one name per result (D43)
                for p, v in zip(it[1].items, self.call(it[2], env)):
                    env[p.items[0].text] = v
            else:
                env[it[1].text] = self.eval(it[3], env, False)
        elif h == "set":
            env[it[1].text] = self.eval(it[2], env, False)
        elif h == "set-idx":
            i, v = self.eval(it[2], env, False), self.eval(it[3], env, False)
            old = env[it[1].text]
            if not 0 <= i < len(old):
                self.fail("BOUNDS", s, f"(set-idx {it[1].text} {i} ...) on a vector of length {len(old)}", False)
            env[it[1].text] = old[:i] + (v,) + old[i + 1:]
        elif h == "push":
            v = self.eval(it[2], env, False)
            env[it[1].text] = env[it[1].text] + (v,)
        elif h == "if":
            return self.stmt(it[2] if self.eval(it[1], env, False) else it[3], env)
        elif h == "block":
            return self.block(it[1:], env)
        elif h == "while":
            return self.loop(s, env)
        elif h == "call":
            self.call(s, env)
        elif h == "return":
            vals = tuple([self.eval(e, env, False) for e in it[1:]])
            if self.check:
                fn = self.frames[-1][0]
                post = {p: env[p] for p in fn.params}  # parameters are immutable, so these are their entry values
                post.update(zip(fn.results, vals))
                for e in fn.ensures:
                    self.holds("POST", e, post, s)
            return vals
        elif h == "panic":
            raise _Stop(Panic(it[1].value))
        elif h == "print":
            self.trace.append(self.eval(it[1], env, False))
        elif self.check:  # assert, ghost-let, ghost-let-mut and ghost-set, erased without check
            if h == "assert":
                self.holds("ASSERT", it[1], env, s)
            else:
                env[it[1].text] = self.ghost(it[-1], env)
        return None

    def loop(self, s, env):
        """§9's while rule, run: invariants on entry and after each normal pass, and a measure
        that is >= 0 whenever the condition holds and drops across each normal pass (D57)."""
        it = s.items
        invs = [c.items[1] for c in it[2:] if _head(c) == "invariant"]
        dec = [c.items[1] for c in it[2:] if _head(c) == "decreases"][0]
        body = [c for c in it[2:] if _head(c) not in ("invariant", "decreases")]
        if self.check:
            for e in invs:
                self.holds("INV-ENTRY", e, env, s)
        while self.eval(it[1], env, False):
            d0 = self.measure(dec, env, s) if self.check else None
            r = self.block(body, env)
            if r is not None:
                return r
            if self.check:
                for e in invs:
                    self.holds("INV-KEEP", e, env, s)
                if d0 is not None:
                    d = self.ghost(dec, env)
                    if d is UNKNOWN:
                        self.note("TERM", dec, s)
                    elif not d < d0:
                        raise _Stop(Contract("TERM", self.p.node(dec), self.p.node(s),
                                             f"the measure went from {d0} to {d}"))
        return None

    def measure(self, dec, env, s):
        d = self.ghost(dec, env)
        if d is UNKNOWN:
            self.note("TERM", dec, s)
            return None
        if d < 0:
            raise _Stop(Contract("TERM", self.p.node(dec), self.p.node(s),
                                 f"the measure is {d} while the loop condition holds"))
        return d

    def call(self, c, env):
        """(call f e*): a def's results, or () for a lemma, whose body never runs (D57)."""
        fn = self.p.fns.get(c.items[1].text)
        if fn is None:  # calls are modular (§7), so a spec need not have a def until it runs
            raise _Unbound(c.items[1].text, self.p.node(c), "is a spec with no def to run")
        if fn.kind == "lemma":
            if self.check:
                lenv = dict(zip(fn.params, [self.ghost(a, env) for a in c.items[2:]]))
                for e in fn.requires:
                    self.holds("PRE", e, lenv, c)
                for e in fn.ensures:
                    self.holds("POST", e, lenv, c)
            return ()
        return self.invoke(fn, [self.eval(a, env, False) for a in c.items[2:]], c)

    def holds(self, kind, e, env, site):
        """Check clause e at site: false ends the run (D57); unknown is recorded, not assumed (D58)."""
        v = self.ghost(e, env)
        if v is UNKNOWN:
            self.note(kind, e, site)
        elif not v:
            raise _Stop(Contract(kind, self.p.node(e), self.p.node(site), f"{_print(e)} is false"))

    def ghost(self, e, env):
        """e's value in ghost context, with any failure inside it charged to e."""
        saved, self.clause = self.clause, e
        try:
            return self.eval(e, env, True)
        finally:
            self.clause = saved

    def quiet(self, e, env):
        """e's value in ghost context, or None where it's undefined or unknown, without failing."""
        try:
            v = self.ghost(e, env)
        except _Stop as stop:
            if isinstance(stop.outcome, Limit):
                raise
            return None
        return None if v is UNKNOWN else v

    def enter(self, fn, env, site):
        """Push fn's frame for the call at site, then check fn's requires and, at a recursive
        call, its measure (D57). The frame goes first so that a recursive call inside the
        requires is seen as one. False when a ghost-fn's requires is unknown, so it can't run."""
        if len(self.frames) >= self.depth:
            raise _Stop(Limit("depth", self.p.node(site)))
        caller = self.frames[-1] if self.frames else None
        frame = [fn, _PENDING if self.check and fn.decreases is not None else None, env]
        self.frames.append(frame)
        if not self.check:
            return True
        for e in fn.requires:
            v = self.ghost(e, env)
            if v is UNKNOWN:
                self.note("PRE", e, site)
                if fn.kind == "ghost-fn":
                    return False
            elif not v:
                raise _Stop(Contract("PRE", self.p.node(e), self.p.node(site), f"{_print(e)} is false"))
        if fn.decreases is not None:
            if frame[1] is None or frame[1] is _PENDING:  # unneeded, or undefined, before the requires held
                m = self.ghost(fn.decreases, env)
                if m is UNKNOWN:
                    self.note("TERM", fn.decreases, site)
                else:
                    frame[1] = m
            if caller is not None and caller[0] is fn:
                self.term(fn, frame[1], self.old(caller), site)
        return True

    def old(self, frame):
        """A caller's measure, evaluated quietly when a recursive call inside its requires first
        needs it, so a measure defined only under the requires is never evaluated early (D57)."""
        if frame[1] is _PENDING:
            frame[1] = self.quiet(frame[0].decreases, frame[2])
        return frame[1]

    def term(self, fn, m, old, site):
        """At a recursive call: 0 <= m < old, each half checked where its values are known (D57)."""
        if m is None:
            return  # recorded as unchecked already
        if m < 0 or (old is not None and m >= old):
            source = "" if old is None else f" from measure {old}"
            raise _Stop(Contract("TERM", self.p.node(fn.decreases), self.p.node(site),
                                 f"the measure is {m} at a recursive call{source}"))
        if old is None:
            self.note("TERM", fn.decreases, site)

    # Expressions.

    def var(self, x, env):
        if x.text not in env:
            raise _Unbound(x.text, self.p.node(x), "isn't defined; the program doesn't pass tier 0")
        return env[x.text]

    def eval(self, x, env, g):
        self.tick(x)
        if isinstance(x, Int):
            return x.value
        if isinstance(x, Sym):
            if x.text == "true":
                return True
            if x.text == "false":
                return False
            return self.var(x, env)
        h = x.items[0].text
        if h in _BINARY:
            return self.binary(h, x, env, g)
        method = _EXPRS.get(h)
        return method(self, x, env, g) if method else self.apply(x, env)

    def operands(self, x, env, g):
        """The values of x's operands, left to right, or None if one is unknown."""
        vals = [self.eval(a, env, g) for a in x.items[1:]]
        return None if any(v is UNKNOWN for v in vals) else vals

    def binary(self, h, x, env, g):
        a = self.eval(x.items[1], env, g)
        if h in ("and", "or", "=>"):  # the right operand only when the left doesn't decide (§7)
            if a is UNKNOWN:
                return UNKNOWN  # the right one may be guarded by the left (D58)
            if h == "and" and not a:
                return False
            if h == "or" and a:
                return True
            if h == "=>" and not a:
                return True
            return self.eval(x.items[2], env, g)
        b = self.eval(x.items[2], env, g)
        if a is UNKNOWN or b is UNKNOWN:
            return UNKNOWN
        if h == "==":
            return a == b
        if h == "!=":
            return a != b
        if h == "<":
            return a < b
        if h == "<=":
            return a <= b
        if h == ">":
            return a > b
        if h == ">=":
            return a >= b
        if h in ("/", "%"):
            if b == 0:
                self.fail("DIV", x, f"({h} {a} 0) divides by zero", g)
            if not g and a == MIN and b == -1:
                self.fail("DIV", x, f"({h} {a} -1) leaves i64", g)
            q = abs(a) // abs(b) if (a < 0) == (b < 0) else -(abs(a) // abs(b))  # toward zero (D37)
            return q if h == "/" else a - b * q  # so % takes the dividend's sign
        r = a + b if h == "+" else a - b if h == "-" else a * b
        if not g and not MIN <= r <= MAX:
            self.fail("OVERFLOW", x, f"({h} {a} {b}) = {r} leaves i64", g)
        return r

    def e_not(self, x, env, g):
        a = self.eval(x.items[1], env, g)
        return UNKNOWN if a is UNKNOWN else not a

    def e_neg(self, x, env, g):
        a = self.eval(x.items[1], env, g)
        if a is UNKNOWN:
            return UNKNOWN
        if not g and a == MIN:
            self.fail("OVERFLOW", x, f"(neg {a}) leaves i64", g)
        return -a

    def e_if(self, x, env, g):
        c = self.eval(x.items[1], env, g)
        if c is UNKNOWN:
            return UNKNOWN
        return self.eval(x.items[2] if c else x.items[3], env, g)

    def e_len(self, x, env, g):
        s = self.eval(x.items[1], env, g)
        return UNKNOWN if s is UNKNOWN else len(s)

    def e_idx(self, x, env, g):
        v = self.operands(x, env, g)
        if v is None:
            return UNKNOWN
        s, i = v
        if not 0 <= i < len(s):
            self.fail("BOUNDS", x, f"(idx s {i}) on a sequence of length {len(s)}", g)
        return s[i]

    def e_borrow(self, x, env, g):
        return self.var(x.items[1], env)  # a slice is the vector's value

    def e_vec_new(self, x, env, g):
        return ()

    def e_seq_build(self, x, env, g):
        n = self.eval(x.items[1], env, g)
        if n is UNKNOWN:
            return UNKNOWN
        if n < 0:
            self.fail("BOUNDS", x, f"(seq-build {n} ...) has a negative length", g)
        fn = x.items[2]
        i, body, inner, out = fn.items[1].items[0].text, fn.items[2], dict(env), []
        for k in range(n):  # exactly 0 <= i < n (D38)
            inner[i] = k
            v = self.eval(body, inner, g)
            if v is UNKNOWN:
                return UNKNOWN
            out.append(v)
        return tuple(out)

    def e_seq_lit(self, x, env, g):
        v = self.operands(x, env, g)
        return UNKNOWN if v is None else tuple(v)

    def e_take(self, x, env, g):
        v = self.operands(x, env, g)
        if v is None:
            return UNKNOWN
        s, k = v
        if not 0 <= k <= len(s):
            self.fail("BOUNDS", x, f"({x.items[0].text} s {k}) on a sequence of length {len(s)}", g)
        return s[:k] if x.items[0].text == "take" else s[k:]

    def e_concat(self, x, env, g):
        v = self.operands(x, env, g)
        return UNKNOWN if v is None else v[0] + v[1]

    def e_last(self, x, env, g):
        s = self.eval(x.items[1], env, g)
        if s is UNKNOWN:
            return UNKNOWN
        if not s:
            self.fail("BOUNDS", x, "(last s) of an empty sequence", g)
        return s[-1]

    def e_contains(self, x, env, g):
        v = self.operands(x, env, g)
        return UNKNOWN if v is None else v[1] in v[0]

    def e_multiset(self, x, env, g):
        s = self.eval(x.items[1], env, g)
        return UNKNOWN if s is UNKNOWN else Multiset.of(Counter(s))

    def e_msum(self, x, env, g):
        v = self.operands(x, env, g)
        if v is None:
            return UNKNOWN
        return Multiset.of(Counter(dict(v[0].counts)) + Counter(dict(v[1].counts)))

    def e_occurrences(self, x, env, g):
        v = self.operands(x, env, g)
        return UNKNOWN if v is None else v[0].count(v[1])  # a sequence's count, or a multiset's

    def e_quantifier(self, x, env, g):
        """forall or exists over the ranges its guard gives its binders, at every point (D58)."""
        q, binders, body = x.items[0].text, x.items[1].items, x.items[2]
        names = [b.items[0].text for b in binders]
        ints = {b.items[0].text for b in binders if b.items[1].text == "int"}
        if q == "forall":
            guard = body.items[1] if _head(body) == "=>" else None
        else:
            guard = body if _head(body) == "and" else None
        seen = [False, False]  # a point that decides the result; a point or range that's unknown
        self.points(q == "exists", names, ints, [] if guard is None else _conjuncts(guard), body, dict(env), 0, seen)
        if seen[0]:
            return q == "exists"  # forall has a false point, or exists a true one
        return UNKNOWN if seen[1] else q == "forall"

    def points(self, want, names, ints, guard, body, env, k, seen):
        """Evaluate body at every point, fixing the binders in order. Points after the result
        is decided are still evaluated, so that an undefined one is found (D58)."""
        if k == len(names):
            v = self.eval(body, env, True)
            if v is UNKNOWN:
                seen[1] = True
            elif v == want:
                seen[0] = True
            return
        x = names[k]
        values = self.span(x, names[k:], ints, guard, env) if x in ints else (False, True)
        if values is None:
            seen[1] = True
            return
        for v in values:
            env[x] = v
            self.points(want, names, ints, guard, body, env, k + 1, seen)

    def span(self, x, free, ints, guard, env):
        """The values the guard allows int binder x, with the binders before it fixed in env:
        a range, or None if it has no finite bounds (D58). Bounds come only from the guard's
        leading conjuncts that can't fail, so a point they exclude makes the guard false at
        a conjunct whose evaluation can't fail, and skipping it hides nothing."""
        lo = {n: None for n in free if n in ints}
        hi = dict(lo)
        steps = []  # (a, b, gap): a + gap <= b, between binders not yet fixed
        for c in guard:
            op = _head(c)
            if op not in _FLIP or len(c.items) != 3:  # not a comparison
                v = None if _mentions(c, free) else self.quiet(c, env)
                if v is False:
                    return range(0)  # false wherever it's reached: the guard holds nowhere
                if v is not True:
                    break  # it might fail at some point, so later conjuncts can't bound
                continue
            sides = []  # a binder not yet fixed, by name, or a value; values are never strings
            for s in c.items[1:]:
                if isinstance(s, Sym) and s.text in free:
                    sides.append(s.text)
                    continue
                v = None if _mentions(s, free) else self.quiet(s, env)
                if v is None:
                    break
                sides.append(v)
            if len(sides) < 2:
                break  # a side that might fail, or that uses a binder in a way that bounds nothing
            a, b = sides
            if not isinstance(a, str) and not isinstance(b, str):
                if not _COMPARE[op](a, b):
                    return range(0)
                continue
            if isinstance(b, str) and not isinstance(a, str):
                a, b, op = b, a, _FLIP[op]  # read E op x as x op' E
            if op == "!=" or a not in ints:
                continue  # can't fail, but bounds nothing
            if isinstance(b, str):
                if b in ints:
                    steps += _steps(a, op, b)
            elif type(b) is int:
                if op in ("<", "<=", "=="):
                    _tighten(hi, a, b - 1 if op == "<" else b, min)
                if op in (">", ">=", "=="):
                    _tighten(lo, a, b + 1 if op == ">" else b, max)
            if not _settle(lo, hi, steps):
                return range(0)  # no point passes the conjuncts so far, so later ones never run
        if not _settle(lo, hi, steps):
            return range(0)
        if lo[x] is None or hi[x] is None:
            return None
        return range(lo[x], hi[x] + 1)

    def apply(self, x, env):
        """A ghost-fn call: its requires, its measure if recursive, then its body, memoized (D57)."""
        name = x.items[0].text
        fn = self.p.fns.get(name)
        if fn is None:
            raise _Unbound(name, self.p.node(x), "isn't defined; the program doesn't pass tier 0")
        args = tuple([self.eval(a, env, True) for a in x.items[1:]])
        if any(a is UNKNOWN for a in args):
            return UNKNOWN
        fenv, key = dict(zip(fn.params, args)), (fn.name, args)
        caller = self.frames[-1] if self.frames else None
        if key in self.active:  # g(A) needs g(A) again, so the recursion can't descend
            m = self.quiet(fn.decreases, fenv) if fn.decreases is not None else None
            if m is not None:
                self.term(fn, m, m, x)  # fails, since m < m doesn't hold
            clause = fn.decreases if fn.decreases is not None else fn.item
            raise _Stop(Contract("TERM", self.p.node(clause), self.p.node(x),
                                 "a recursive call with its caller's own arguments"))
        if key in self.memo:  # its requires held before; a recursive call still checks its measure
            if self.check and fn.decreases is not None and caller is not None and caller[0] is fn:
                m = self.ghost(fn.decreases, fenv)
                if m is UNKNOWN:
                    self.note("TERM", fn.decreases, x)
                else:
                    self.term(fn, m, self.old(caller), x)
            return self.memo[key]
        depth = len(self.frames)
        self.active.add(key)
        try:
            if not self.enter(fn, fenv, x):
                return UNKNOWN
            v = self.ghost(fn.body, fenv)
        finally:
            del self.frames[depth:]
            self.active.discard(key)
        self.memo[key] = v
        return v


_BINARY = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "and", "or", "=>"}
_EXPRS = {
    "not": _Run.e_not, "neg": _Run.e_neg, "if": _Run.e_if, "len": _Run.e_len, "idx": _Run.e_idx,
    "borrow": _Run.e_borrow, "vec-new": _Run.e_vec_new, "seq-build": _Run.e_seq_build,
    "seq-lit": _Run.e_seq_lit, "take": _Run.e_take, "drop": _Run.e_take, "concat": _Run.e_concat,
    "last": _Run.e_last, "contains": _Run.e_contains, "multiset": _Run.e_multiset,
    "msum": _Run.e_msum, "occurrences": _Run.e_occurrences,
    "forall": _Run.e_quantifier, "exists": _Run.e_quantifier,
}
_FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!="}
_COMPARE = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq,
            "!=": operator.ne}


def _conjuncts(x):
    if _head(x) == "and":
        return _conjuncts(x.items[1]) + _conjuncts(x.items[2])
    return [x]


def _steps(x, op, y):
    """x op y between two binders, as (a, b, gap) meaning a + gap <= b."""
    return {"<": [(x, y, 1)], "<=": [(x, y, 0)], ">": [(y, x, 1)], ">=": [(y, x, 0)],
            "==": [(x, y, 0), (y, x, 0)]}[op]


def _tighten(bounds, x, v, pick):
    bounds[x] = v if bounds[x] is None else pick(bounds[x], v)


def _mentions(x, names):
    if isinstance(x, Sym):
        return x.text in names
    return isinstance(x, Form) and any(_mentions(c, names) for c in x.items)


def _settle(lo, hi, steps):
    """Pass bounds along each a + gap <= b until none changes; False if some range is empty."""
    for _ in range(len(lo) + 1):
        changed = False
        for a, b, gap in steps:
            if hi[b] is not None and (hi[a] is None or hi[b] - gap < hi[a]):
                hi[a], changed = hi[b] - gap, True
            if lo[a] is not None and (lo[b] is None or lo[a] + gap > lo[b]):
                lo[b], changed = lo[a] + gap, True
        if not changed:
            break
    return all(lo[n] is None or hi[n] is None or lo[n] <= hi[n] for n in lo)


def main(argv):
    check, fuel = False, FUEL
    while argv and argv[0] in ("--check", "--fuel"):
        if argv.pop(0) == "--check":
            check = True
        elif argv and argv[0].isdigit():
            fuel = int(argv.pop(0))
        else:
            argv = []
    if len(argv) < 2:
        print("usage: uv run --no-project b17c/interp.py [--check] [--fuel N] FILE NAME ARG...", file=sys.stderr)
        return 2
    path, name, *exprs = argv
    try:
        module = parse(Path(path).read_bytes())
    except OSError as e:
        print(f"{path}: {e.strerror}", file=sys.stderr)
        return 2
    except ParseError as e:
        print(f"{path}:{e}", file=sys.stderr)
        return 2
    try:
        args = []
        for k, expr in enumerate(exprs, 1):
            try:
                args.append(value(module, expr))
            except ParseError as e:
                raise ValueError(f"argument {k}:{e}") from None
        out = run(module, name, args, check=check, fuel=fuel)
    except ValueError as e:
        print(f"{path}: {e}", file=sys.stderr)
        return 2
    print(text_of(out))
    return 0 if isinstance(out, Ok) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
