"""WP7's self-check: emitted Rust compiles, forbids unsafe code, and matches the reference
interpreter on differential tests (D18, D95-D97): uv run --no-project b17c/test_rust.py

Needs rustc on PATH. CI installs the version the README pins.
"""
import concurrent.futures as cf
import io
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import interp as i
import rust as r
from check import check
from syntax import ParseError, parse

SUITE = Path(__file__).resolve().parent.parent / "suite"
TMP = Path(tempfile.mkdtemp(prefix="b17c-rust-"))
r.CACHE = TMP / "cache"
MIN, MAX = i.MIN, i.MAX
HEAD = '(module t (header (purpose "p") (invariants "i") (failures "f"))'
FUEL = 20_000  # a run the interpreter can't finish in this many steps is skipped (D59, D97)
STRICT = ("-D", "warnings")  # past the lints an emitted crate allows (D95), a warning is a backend bug
BOOL, I64 = r.BOOL, r.I64
VEC_I, VEC_B, SLICE_I, SLICE_B = ("vec", I64), ("vec", BOOL), ("slice", I64), ("slice", BOOL)

assert shutil.which("rustc"), "test_rust.py needs rustc on PATH (README: Getting started)"
failures = []
compared = Counter()  # outcome kind -> runs compared


def module(*items):
    return parse(HEAD + "\n" + "\n".join(items) + ")")


def build_all(sources):
    """{name: source} -> {name: binary}, compiled in parallel with warnings denied."""
    def one(item):
        return item[0], r.build(item[1], TMP / item[0], flags=STRICT)
    with cf.ThreadPoolExecutor(os.cpu_count() or 4) as pool:
        return dict(pool.map(one, sources.items()))


def signature(m, name):
    spec = next(it for it in m.items[3:] if it.items[0].text == "spec" and it.items[1].text == name)
    return [r._type(p.items[1]) for p in r._args(spec, "params")]


def interpreted(m, name, args):
    """The interpreter's text for a run (§8, check off), "refused", or None past FUEL steps."""
    try:
        out = i.run(m, name, args, fuel=FUEL)
    except ValueError:
        return "refused"
    return None if isinstance(out, i.Limit) else i.text_of(out)


def differential(m, binary, cases, label):
    """Each run of cases, (def name, args), that the interpreter finishes must give the
    binary the same text, line for line."""
    runs, want = [], []
    for name, args in cases:
        text = interpreted(m, name, args)
        if text is None:
            compared["skipped: limit"] += 1
            continue
        runs.append((name, [i._term(a) for a in args]))
        want.append(text)
    for (name, args), w, got in zip(runs, want, r.batch(binary, runs, timeout=120)):
        compared["refused" if w == "refused" else w.split("\n")[-1].split(" ")[0]] += 1
        if w == got or (w == "refused" and got.startswith("refused: ")):
            continue
        failures.append(f"{label}: {name} {' '.join(args)}\n    interpreter: {w!r}\n    rust:        {got!r}")


EDGE = [0, 1, -1, 2, -2, 3, 7, 10, 100, MAX, MIN, MAX - 1, MIN + 1, 2**31, -2**31, 2**32, 3037000499, 3037000500,
        2**62, -2**62]


def value(rng, t):
    """A random value of runtime type t: mostly small, sometimes at an i64 edge."""
    if t == BOOL:
        return rng.random() < 0.5
    if t == I64:
        k = rng.random()
        return rng.choice(EDGE) if k < 0.3 else rng.randint(-12, 12) if k < 0.85 else rng.randint(MIN, MAX)
    items = [value(rng, t[1]) if t[1] == BOOL or rng.random() < 0.15 else rng.randint(-6, 6)
             for _ in range(rng.choice([0, 0, 1, 2, 3, 4, 5, 8]))]
    if t[1] == I64 and rng.random() < 0.4:
        items.sort()
    return tuple(items)


def cases(m, rng, per_def):
    out = []
    for it in m.items[3:]:
        if it.items[0].text == "def":
            types = signature(m, it.items[1].text)
            out += [(it.items[1].text, [value(rng, t) for t in types]) for _ in range(per_def)]
    return out


# 1. The suite: every program that passes tier 0 compiles, and runs as the interpreter does.

programs = {f"suite-{p.stem}": parse(p.read_bytes())
            for p in sorted((SUITE / "accept").glob("*.b17")) + sorted((SUITE / "reject").glob("E-PROOF-*.b17"))}
assert len(programs) == 29, len(programs)
sources = {name: r.emit(m) for name, m in programs.items()}


# 2. Corners: each runtime construct, the failures §8 names, and the lowering's own risks.

CORNERS = module(
    "(lemma ghost_only (params (n int)) (body))",
    "(spec arith (params (a i64) (b i64)) (returns (s i64) (d i64) (p i64) (q i64) (m i64) (n i64)) (effects))",
    "(def arith (body (return (+ a b) (- a b) (* a b) (/ a b) (% a b) (neg a))))",
    # set-idx evaluates its index, then its value, then checks the index (D56); push and
    # set-idx may read the vector they change
    "(spec order (params (v (vec i64)) (i i64) (e i64)) (returns (r (vec i64))) (effects alloc))",
    "(def order (body (let-mut w (vec i64) v) (set-idx w (+ i 1) (/ 100 e)) "
    "(set-idx w (- (len w) 1) (idx w 0)) (push w (len w)) (return w)))",
    "(spec lazy (params (v (ref (slice i64))) (i i64)) (returns (a bool) (o bool) (m bool)) (effects))",
    "(def lazy (body (return (and (< i (len v)) (== (idx v i) 0)) (or (>= i (len v)) (== (idx v i) 0)) "
    "(=> (< i (len v)) (> (idx v i) (/ 7 i))))))",
    "(spec show (params (x i64)) (returns) (effects io))",
    "(def show (body (print x) (print (* x 2)) (return)))",
    "(spec trace (params (n i64)) (returns (r i64)) (effects panic io))",
    "(def trace (body (let-mut i i64 0) (while (< i n) (invariant true) (decreases (- n i)) (call show i) "
    "(set i (+ i 1))) (if (> n 3) (panic \"too \\\"big\\\" \\\\ naïve\") (block)) "
    "(if (< n 0) (panic \"neg ‮ ✓\") (block)) (return (* n 4611686018427387904))))",
    "(spec total (params (s (ref (slice i64)))) (returns (t i64)) (effects))",
    "(def total (body (let-mut t i64 0) (let-mut k i64 0) (while (< k (len s)) (decreases (- (len s) k)) "
    "(set t (+ t (idx s k))) (set k (+ k 1))) (return t)))",
    "(spec pass_on (params (s (ref (slice i64))) (z i64)) (returns (t i64)) (effects))",
    "(def pass_on (body (let ((t i64)) (call total s)) (return (+ t z))))",
    "(spec use_total (params (v (vec i64))) (returns (r (vec i64)) (t i64)) (effects))",
    "(def use_total (body (let ((t i64)) (call total (borrow v))) (let-mut ((u i64)) (call pass_on (borrow v) t)) "
    "(set u (+ u t)) (return v u)))",
    # names Rust reserves, and names the crate itself uses (D95)
    "(spec main (params (self i64) (crate i64) (super bool)) (returns (match i64)) (effects))",
    "(def main (body (let-mut loop i64 self) (let type i64 crate) (if super (set loop (+ loop type)) (block)) "
    "(return loop)))",
    "(spec rt (params (unsafe (vec i64)) (std i64)) (returns (r (vec i64))) (effects alloc))",
    "(def rt (body (let-mut gen (vec i64) unsafe) (push gen std) (return gen)))",
    "(spec dispatch (params) (returns (r i64)) (effects))",
    "(def dispatch (body (let ((m i64)) (call main 1 2 true)) (return m)))",
    "(spec program (params (async bool) (await (vec bool))) (returns (dyn (vec bool)) (impl i64)) (effects alloc))",
    "(def program (body (let-mut yield (vec bool) await) (push yield async) (let-mut where i64 0) "
    "(let-mut trait i64 0) (while (< trait (len yield)) (decreases (- (len yield) trait)) "
    "(if (idx yield trait) (set where (+ where 1)) (block)) (set-idx yield trait (not (idx yield trait))) "
    "(set trait (+ trait 1))) (return yield where)))",
    # unreachable code that Rust would reject: v is used after it moved (D77)
    "(spec dead (params (v (vec i64))) (returns (r (vec i64))) (effects panic))",
    "(def dead (body (if (> (len v) 2) (return v) (panic \"short\")) (let w (vec i64) v) (return w)))",
    # element types a (vec-new) leaves open, and literals Rust would type as i32 (D70)
    "(spec open (params (n i64) (b bool)) (returns (l i64) (k i64) (c bool) (e bool)) (effects alloc))",
    "(def open (body (return (len (vec-new)) (len (seq-build n (fn (i) (idx (vec-new) i)))) "
    "(if b (idx (vec-new) 0) false) (== (idx (vec-new) n) (idx (vec-new) 1)))))",
    "(spec literals (params (b bool)) (returns (x bool) (y bool) (z bool) (w i64)) (effects))",
    "(def literals (body (return (< 5000000000 6) (== (if b 5000000000 2) 3) "
    "(!= -9223372036854775808 9223372036854775807) -9223372036854775808)))",
    "(spec fact (params (n i64)) (returns (r i64)) (requires (>= n 0)) (effects))",
    "(def fact (decreases n) (body (if (<= n 1) (return 1) (block (let ((m i64)) (call fact (- n 1))) "
    "(return (* n m))))))",
    "(spec find2 (params (v (ref (slice i64))) (k i64)) (returns (r i64)) (effects panic))",
    "(def find2 (body (let-mut i i64 0) (while (< i (len v)) (decreases (- (len v) i)) (let-mut j i64 i) "
    "(while (< j (len v)) (decreases (- (len v) j)) (if (== (+ (idx v i) (idx v j)) k) "
    "(return (+ (* i 1000) j)) (block)) (set j (+ j 1))) (set i (+ i 1))) (return -1)))",
    # ghost code is erased: a false assert, and a lemma call whose argument divides by zero
    "(spec ghosts (params (x i64)) (returns (r i64)) (effects))",
    "(def ghosts (body (assert false) (ghost-let g int (+ x 1)) (ghost-let-mut h int g) (ghost-set h (* h h)) "
    "(call law_i64_range x) (call ghost_only (/ x 0)) (if (> x 0) (assert (> g 1)) (assert true)) "
    "(return (- x 1))))",
    "(spec builds (params (n i64) (d i64)) (returns (v (vec i64)) (w (vec bool))) (effects alloc))",
    "(def builds (body (let v (vec i64) (seq-build n (fn (k) (/ 10 (- k d))))) "
    "(let w (vec bool) (seq-build (len v) (fn (k) (> (idx v k) 0)))) (return v w)))",
    "(spec chain (params (x i64)) (returns (r i64)) (effects panic))",
    "(def chain (body (if (< x 0) (return -1) (if (== x 0) (return 0) (if (< x 10) (return 1) (return 2))))))",
    "(spec negate (params (x i64)) (returns (r i64)) (requires (!= x 0)) (effects))",
    "(def negate (body (return (neg x))))",
    "(spec divide (params (a i64) (b i64)) (returns (m i64) (q i64)) (effects))",
    "(def divide (body (return (% a b) (/ a b))))",
    "(spec nothing (params) (returns) (effects))",
    "(def nothing (body (return)))",
    # (while true ...) and recursion that never ends, which Rust warns about (D95)
    "(spec spin (params (n i64)) (returns (r i64)) (requires (>= n 0)) (effects panic))",
    "(def spin (body (let-mut i i64 0) (while true (decreases 0) (if (>= i n) (return i) (block)) (set i (+ i 1))) "
    "(panic \"unreachable\")))",
    "(spec forever (params (n i64)) (returns (r i64)) (requires (> n 100)) (effects))",
    "(def forever (decreases n) (body (let ((r i64)) (call forever n)) (return r)))",
    # a comparison with an i64 limit, and a name Rust wouldn't call snake case
    "(spec limits (params (a__b i64)) (returns (r bool)) (effects))",
    "(def limits (body (return (and (<= a__b 9223372036854775807) (>= a__b -9223372036854775808)))))",
    # line and paragraph separators, which a string may hold (D50) but Python splits lines at
    "(spec seps (params (b bool)) (returns) (effects panic))",
    "(def seps (body (if b (panic \"a b c\u0085d\") (block)) (return)))",
    "(spec unbuilt (params (x i64)) (returns (r i64)) (requires (> x 0)) (effects))",
)
assert check(CORNERS) == [], check(CORNERS)
sources["corners"] = r.emit(CORNERS)

# Recursion as deep as D59 lets the interpreter go, through a frame that holds 450 vectors,
# whether or not the branch that declares them runs. 1,000 such frames overflow the 8 MiB a
# main thread gets, so a run needs a stack of its own (D96). Found in WP7's review.
DEEP = module(
    "(spec deep (params (n i64) (big bool)) (returns (r i64)) (requires (>= n 0)) (effects alloc io))",
    "(def deep (decreases n) (body (if (<= n 0) (return 0) (block)) (if big (block "
    + " ".join(f"(let v{k} (vec i64) (seq-build n (fn (k{k}) (+ k{k} {k}))))" for k in range(450))
    + " (let ((r1 i64)) (call deep (- n 1) big)) " + " ".join(f"(print (idx v{k} 0))" for k in range(450))
    + " (return r1)) (block)) (let ((r2 i64)) (call deep (- n 1) big)) (return (+ r2 1))))")
sources["deep"] = r.emit(DEEP)

# Each line: a run, then what the interpreter and the binary must both print. An expectation
# with "err " in it is a regular expression, so that \S+ can stand for the node's line and
# column, which only the module's layout fixes. Any other must match exactly.
EXPECT = [
    ("arith 3 -2", "ok 1 5 -6 -1 1 -3"),
    ("arith -7 2", "ok -5 -9 -14 -3 -1 7"),
    ("arith 9223372036854775807 1", r"err OVERFLOW at def arith/2\.1\.1@\d+:\d+: "
                                    r"\(\+ 9223372036854775807 1\) = 9223372036854775808 leaves i64"),
    ("arith -9223372036854775808 -1", r"err OVERFLOW at def arith/2\.1\.1@\S+ \(\+ -9223372036854775808 -1\) = "
                                      r"-9223372036854775809 leaves i64"),
    ("arith 5 0", r"err DIV at def arith/2\.1\.4@\S+ \(/ 5 0\) divides by zero"),
    ("arith -9223372036854775808 2", r"err OVERFLOW at def arith/2\.1\.2@\S+ \(- -9223372036854775808 2\) = "
                                     r"-9223372036854775810 leaves i64"),
    ("arith 4611686018427387904 -2", "ok 4611686018427387902 4611686018427387906 -9223372036854775808 "
                                     "-2305843009213693952 0 -4611686018427387904"),
    ("arith 4611686018427387904 2", r"err OVERFLOW at def arith/2\.1\.3@\S+ \(\* 4611686018427387904 2\) = "
                                    r"9223372036854775808 leaves i64"),
    ("arith -9223372036854775807 -1", "ok -9223372036854775808 -9223372036854775806 9223372036854775807 "
                                      "9223372036854775807 0 9223372036854775807"),
    ("negate -9223372036854775808", r"err OVERFLOW at def negate/2\.1\.1@\S+ \(neg -9223372036854775808\) leaves i64"),
    ("negate -9223372036854775807", "ok 9223372036854775807"),
    ("divide -9223372036854775808 -1", r"err DIV at def divide/2\.1\.1@\S+ \(% -9223372036854775808 -1\) leaves i64"),
    ("divide -9223372036854775807 -1", "ok 0 9223372036854775807"),
    ("divide 7 -2", "ok 1 -3"),
    ("divide -7 2", "ok -1 -3"),
    ("divide -7 -2", "ok -1 3"),
    ("divide 5 0", r"err DIV at def divide/2\.1\.1@\S+ \(% 5 0\) divides by zero"),
    ("order (seq-lit 1 2 3) 5 0", r"err DIV at def order/2\.2\.3@\S+ \(/ 100 0\) divides by zero"),
    ("order (seq-lit 1 2 3) 9223372036854775807 0", r"err OVERFLOW at def order/2\.2\.2@\S+ "
                                                    r"\(\+ 9223372036854775807 1\) = 9223372036854775808 leaves i64"),
    ("order (seq-lit 1 2 3) 5 1", r"err BOUNDS at def order/2\.2@\S+ \(set-idx w 6 \.\.\.\) on a vector of length 3"),
    ("order (seq-lit 1 2 3) 0 1", "ok (seq-lit 1 100 1 3)"),
    ("order (seq-lit) -1 1", r"err BOUNDS at def order/2\.2@\S+ \(set-idx w 0 \.\.\.\) on a vector of length 0"),
    ("lazy (seq-lit 0 5) 7", "ok false true true"),
    ("lazy (seq-lit 0 5) 1", "ok false false false"),
    ("lazy (seq-lit 0 5) 0", r"err DIV at def lazy/2\.1\.3\.2\.2@\S+ \(/ 7 0\) divides by zero"),
    ("lazy (seq-lit 0 5) -1", r"err BOUNDS at def lazy/2\.1\.1\.2\.1@\S+ \(idx s -1\) on a sequence of length 2"),
    ("trace 1", "print 0\nprint 0\nok 4611686018427387904"),
    ("trace 3", r"print 0\nprint 0\nprint 1\nprint 2\nprint 2\nprint 4\nerr OVERFLOW at def trace/2\.5\.1@\S+ "
                r"\(\* 3 4611686018427387904\) = 13835058055282163712 leaves i64"),
    ("trace 4", "print 0\nprint 0\nprint 1\nprint 2\nprint 2\nprint 4\nprint 3\nprint 6\n"
                "panic \"too \\\"big\\\" \\\\ naïve\""),
    ("trace -1", "panic \"neg ‮ ✓\""),
    ("use_total (seq-lit 1 2 3)", "ok (seq-lit 1 2 3) 18"),
    ("main 5 6 true", "ok 11"),
    ("main 5 6 false", "ok 5"),
    ("rt (seq-lit 1) 2", "ok (seq-lit 1 2)"),
    ("dispatch", "ok 3"),
    ("program true (seq-lit true false)", "ok (seq-lit false true false) 2"),
    ("dead (seq-lit 1 2 3)", "ok (seq-lit 1 2 3)"),
    ("dead (seq-lit 1)", "panic \"short\""),
    ("open 0 false", r"err BOUNDS at def open/2\.1\.4\.1@\S+ \(idx s 0\) on a sequence of length 0"),
    ("open 2 true", r"err BOUNDS at def open/2\.1\.2\.1\.2\.2@\S+ \(idx s 0\) on a sequence of length 0"),
    ("open -1 true", r"err BOUNDS at def open/2\.1\.2\.1@\S+ \(seq-build -1 \.\.\.\) has a negative length"),
    ("literals true", "ok false false true -9223372036854775808"),
    ("fact 5", "ok 120"),
    ("fact 21", r"err OVERFLOW at def fact/3\.1\.3\.2\.1@\S+ \(\* 21 2432902008176640000\) = 51090942171709440000 "
                r"leaves i64"),
    ("fact -3", "ok 1"),
    ("find2 (seq-lit 1 2 3) 5", "ok 1002"),
    ("find2 (seq-lit 1 2) 100", "ok -1"),
    ("ghosts 5", "ok 4"),
    ("ghosts -9223372036854775808", r"err OVERFLOW at def ghosts/\S+ \(- -9223372036854775808 1\) = "
                                    r"-9223372036854775809 leaves i64"),
    ("builds 5 2", r"err DIV at def builds/2\.1\.3\.2\.2@\S+ \(/ 10 0\) divides by zero"),
    ("builds 3 9", "ok (seq-lit -1 -1 -1) (seq-lit false false false)"),
    ("chain 50", "ok 2"),
    ("chain -50", "ok -1"),
    ("nothing", "ok"),
    ("limits -9223372036854775808", "ok true"),
    ("seps true", "panic \"a b c\u0085d\""),
    ("seps false", "ok"),
    ("spin 3", "ok 3"),
    ("spin -1", "ok 0"),
    ("total (seq-lit)", "ok 0"),
    ("total ( seq-lit 1\t2 )", "ok 3"),
    # arguments the binary refuses, as the interpreter does (D96)
    ("unbuilt 1", "refused"),
    ("arith 1", "refused"),
    ("arith 1 2 3", "refused"),
    ("arith 9223372036854775808 1", "refused"),
    ("arith true 1", "refused"),
    ("arith 007 1", "refused"),
    ("arith -0 1", "refused"),
    ("arith +5 1", "refused"),
    ("arith 5x 1", "refused"),
    ("arith 5  1", "refused"),  # whitespace B17-0 doesn't have (D48)
    ("arith 　5 1", "refused"),
    ("arith \x0b5 1", "refused"),
    ("main 1 2 maybe", "refused"),
    ("total (seq-lit 1 true)", "refused"),
    ("total (seq-lit (seq-lit 1))", "refused"),
    ("total (seq-lit 01)", "refused"),
    ("total (seq-lit 1 2", "refused: unbalanced ( in total (seq-lit 1 2"),
    ("total (seq-lit 1 2))", "refused: unbalanced ) in total (seq-lit 1 2))"),
    ("total (vec-lit 1)", "refused"),
]


# 3. Programs generated at random, to reach combinations no hand-written test does.

class Gen:
    """Random defs that pass tier 0 by construction. Their bodies use every runtime
    statement and expression, keep §5's ownership rules, and call the defs before them."""

    TYPES = [I64, I64, BOOL, VEC_I, VEC_B, SLICE_I, SLICE_B]
    LITERALS = [0, 1, 2, 3, 5, 7, 10, -1, -2, -3, 100, MAX, MIN, 2**62, -2**62, 3037000500]

    def __init__(self, rng):
        self.rng, self.count = rng, 0

    def fresh(self, prefix):
        self.count += 1
        return f"{prefix}{self.count}"

    @staticmethod
    def show(t):
        if t[0] == "slice":
            return f"(ref (slice {t[1][0]}))"
        return f"(vec {t[1][0]})" if t[0] == "vec" else t[0]

    def module(self, count):
        items, self.sigs = ["(lemma l0 (params (n int)) (body))"], []
        for k in range(count):
            params = [(self.fresh("p"), self.rng.choice(self.TYPES)) for _ in range(self.rng.randint(0, 3))]
            results = [self.rng.choice([I64, BOOL, VEC_I, VEC_B]) for _ in range(self.rng.randint(0, 2))]
            body = self.body(params, results)
            ps = " ".join(f"({n} {self.show(t)})" for n, t in params)
            rs = " ".join(f"({self.fresh('r')} {self.show(t)})" for t in results)
            # the requires is never checked at run time; it keeps specs distinct (D45)
            items += [f"(spec f{k} (params {ps}) (returns {rs}) (requires (== {k} {k})) (effects alloc panic io))",
                      f"(def f{k} (body {body}))"]
            self.sigs.append((f"f{k}", [t for _, t in params], results))
        return HEAD + "\n" + "\n".join(items) + ")"

    def body(self, params, results):
        self.vars = {n: [t, False, True] for n, t in params}  # name -> [type, settable, live]
        self.results, self.outer = results, None  # outer: what a loop body may not move (E-OWN-004)
        stmts, ended = self.block(self.rng.randint(1, 6), 0)
        return " ".join(stmts + ([] if ended else [self.ret()]))

    def block(self, n, depth):
        out = []
        for _ in range(n):
            s, ended = self.stmt(depth)
            out.append(s)
            if ended:
                return out, True
        return out, False

    def live(self, t=None, movable=False):
        return [n for n, (vt, _, alive) in self.vars.items()
                if alive and (t is None or vt == t) and not (movable and self.outer and n in self.outer)]

    def stmt(self, depth):
        rng = self.rng
        kinds = ["let", "let", "set", "set-idx", "push", "print", "call", "call", "ghost"]
        kinds += ["if", "if", "while"] if depth < 2 else []
        kinds += ["return", "panic"] if depth > 0 else []
        kind = rng.choice(kinds)
        if kind == "let":
            t, name, mut = rng.choice([I64, I64, BOOL, VEC_I, VEC_B]), self.fresh("x"), rng.random() < 0.6
            init = self.vector(t, set()) if t[0] == "vec" else self.expr(t)
            self.vars[name] = [t, mut, True]
            return f"({'let-mut' if mut else 'let'} {name} {self.show(t)} {init})", False
        if kind == "set":
            targets = [n for n, (t, settable, alive) in self.vars.items()
                       if settable and (t[0] != "vec" or alive or not (self.outer and n in self.outer))]
            if targets:
                x = rng.choice(targets)
                t = self.vars[x][0]
                value = self.vector(t, set()) if t[0] == "vec" else self.expr(t)
                self.vars[x][2] = True
                return f"(set {x} {value})", False
        if kind in ("set-idx", "push"):
            vs = [n for n in self.live() if self.vars[n][1] and self.vars[n][0][0] == "vec"]
            if vs:
                v = rng.choice(vs)
                e = self.expr(self.vars[v][0][1])
                if kind == "push":
                    return f"(push {v} {e})", False
                i = rng.choice(["0", "1", f"(- (len {v}) 1)", f"(len {v})", self.expr(I64)])
                return f"(set-idx {v} {i} {e})", False
        if kind == "call" and self.sigs:
            s = self.call(rng.choice(self.sigs))
            if s:
                return s, False
        if kind == "ghost":
            return rng.choice([f"(assert {self.expr(BOOL)})", f"(ghost-let {self.fresh('g')} int {self.expr(I64)})",
                               f"(call l0 {self.expr(I64)})"]), False
        if kind == "if":
            return self.branches(depth)
        if kind == "while":
            return self.loop(depth), False
        if kind == "return":
            return self.ret(), True
        if kind == "panic":
            return f"(panic \"{self.fresh('stop ')}\")", True
        return f"(print {self.expr(I64)})", False

    def branches(self, depth):
        cond, before = self.expr(BOOL), {n: list(v) for n, v in self.vars.items()}
        arms = []
        for _ in range(2):
            self.vars = {n: list(v) for n, v in before.items()}
            stmts, ended = self.block(self.rng.randint(0, 3), depth + 1)
            arms.append((f"(block {' '.join(stmts)})", ended, self.vars))
        going = [vs for _, ended, vs in arms if not ended]
        self.vars = {n: v for n, v in before.items()}  # what the branches declared is out of scope
        for n in self.vars:  # a vector moved on either branch that goes on is moved after (§5)
            self.vars[n][2] = all(vs[n][2] for vs in going) if going else self.vars[n][2]
        return f"(if {cond} {arms[0][0]} {arms[1][0]})", not going

    def loop(self, depth):
        c, limit = self.fresh("c"), self.rng.randint(1, 4)
        cond = self.expr(BOOL)
        saved_vars, saved_outer = {n: list(v) for n, v in self.vars.items()}, self.outer
        self.vars[c] = [I64, False, True]
        self.outer = set(self.vars)
        stmts, _ = self.block(self.rng.randint(1, 4), depth + 1)
        self.vars, self.outer = saved_vars, saved_outer
        return (f"(let-mut {c} i64 0) (while (and (< {c} {limit}) {cond}) (decreases (- {limit} {c})) "
                f"(set {c} (+ {c} 1)) {' '.join(stmts)})")

    def call(self, sig):
        name, params, results = sig
        taken, args = set(), []
        for t in params:
            if t[0] == "vec":
                vs = [v for v in self.live(t, movable=True) if v not in taken]
                if not vs:
                    return None
                args.append(self.rng.choice(vs))
            elif t[0] == "slice":
                vs = [v for v in self.live() if self.vars[v][0] in (("vec", t[1]), t) and v not in taken]
                if not vs:
                    return None
                v = self.rng.choice(vs)
                args.append(v if self.vars[v][0] == t else f"(borrow {v})")
            else:
                seen = set()
                args.append(self.expr(t, avoid=taken, seen=seen))
                taken |= seen
                continue
            taken.add(v if t[0] == "slice" else args[-1])
        for a, t in zip(args, params):
            if t[0] == "vec":
                self.vars[a][2] = False  # moved into the callee
        call = f"(call {name} {' '.join(args)})"
        if not results:
            return call
        names = [self.fresh("y") for _ in results]
        mut = self.rng.random() < 0.5
        for n, t in zip(names, results):
            self.vars[n] = [t, mut, True]
        return f"({'let-mut' if mut else 'let'} ({' '.join(f'({n} {self.show(t)})' for n, t in zip(names, results))}) {call})"

    def ret(self):
        taken, values = set(), []
        for t in self.results:
            seen = set()
            if t[0] == "vec":
                vs = [v for v in self.live(t) if v not in taken]
                values.append(self.rng.choice(vs) if vs and self.rng.random() < 0.6 else self.vector(t, taken, seen, own=False))
                seen.add(values[-1])
            else:
                values.append(self.expr(t, avoid=taken, seen=seen))
            taken |= seen
        return f"(return {' '.join(values)})"

    def vector(self, t, avoid, seen=None, own=True):
        """A value for a vector destination: (vec-new), a seq-build, or, with own, a variable that moves."""
        k = self.rng.random()
        vs = [v for v in self.live(t, movable=True) if v not in avoid] if own else []
        if vs and k < 0.4:
            v = self.rng.choice(vs)
            self.vars[v][2] = False
            return v
        if k < 0.6:
            return "(vec-new)"
        return self.build(t[1], avoid, seen if seen is not None else set())

    def build(self, elem, avoid, seen):
        n = self.rng.choice(["0", "1", "2", "3", "4", self.expr(I64, 2, avoid, seen)])
        b = self.fresh("k")
        self.vars[b] = [I64, False, True]
        body = self.expr(elem, 1, avoid, seen)
        del self.vars[b]
        return f"(seq-build {n} (fn ({b}) {body}))"

    def sequence(self, elem, depth, avoid, seen):
        """An operand for len or idx: a live vector or slice, or now and then a built or empty
        one. An empty one's elements are i64 unless a destination says otherwise (D70), and
        not every place an element goes is a destination, so only i64 ones are empty."""
        vs = [v for v in self.live() if self.vars[v][0][0] in ("vec", "slice") and self.vars[v][0][1] == elem
              and v not in avoid]
        k = self.rng.random()
        if vs and k < 0.8:
            v = self.rng.choice(vs)
            seen.add(v)
            return v
        return "(vec-new)" if k < 0.9 and elem == I64 else self.build(elem, avoid, seen)

    def expr(self, t, depth=0, avoid=frozenset(), seen=None):
        """A runtime expression of type t that reads no vector in avoid, adding the vectors it reads to seen."""
        rng, seen = self.rng, seen if seen is not None else set()
        sub = lambda u: self.expr(u, depth + 1, avoid, seen)
        if depth >= 3 or rng.random() < 0.3:
            names = self.live(t)
            if names and rng.random() < 0.6:
                return rng.choice(names)
            if t == BOOL:
                return rng.choice(["true", "false"])
            return str(rng.choice(self.LITERALS) if rng.random() < 0.3 else rng.randint(-4, 9))
        k = rng.randrange(6)
        if k == 0:
            return f"(if {sub(BOOL)} {sub(t)} {sub(t)})"
        if k == 1:
            s = self.sequence(t, depth, avoid, seen)
            return f"(idx {s} {rng.choice(['0', '1', sub(I64)])})"
        if t == I64:
            if k == 2:
                return f"(len {self.sequence(rng.choice([I64, BOOL]), depth, avoid, seen)})"
            if k == 3:
                a = sub(I64)
                return f"(neg {a})" if a[0] == "(" or a[0].isalpha() else f"(neg (+ {a} 0))"  # (neg INT) doesn't parse
            return f"({rng.choice(['+', '-', '*', '/', '%'])} {sub(I64)} {sub(I64)})"
        if k == 2:
            return f"(not {sub(BOOL)})"
        if k == 3:
            return f"({rng.choice(['and', 'or', '=>'])} {sub(BOOL)} {sub(BOOL)})"
        u = rng.choice([I64, I64, BOOL])
        op = rng.choice(["==", "!="] + (["<", "<=", ">", ">="] if u == I64 else []))
        return f"({op} {sub(u)} {sub(u)})"


generated = {}
for seed in range(4):
    text = Gen(random.Random(seed)).module(30)
    m = parse(text)
    found = check(m)
    if found:
        failures.append(f"generated module {seed} doesn't pass tier 0, a generator bug: {found[:3]}")
        continue
    generated[f"generated-{seed}"] = m
    sources[f"generated-{seed}"] = r.emit(m)


# Every emitted crate forbids unsafe code, has no unsafe code, and is emitted the same way twice.

for name, source in sources.items():
    assert source.splitlines()[2] == "#![forbid(unsafe_code)]", name
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', source)  # names in string literals aren't code
    assert not re.search(r"(?<![#\w])unsafe(?!_code)\b", code), name
for name, m in list(programs.items())[:3] + [("corners", CORNERS)]:
    assert r.emit(m) == sources[name], name
assert "        } else if x < 10 {\n            return 1;\n" in sources["corners"]  # chains read as written

binaries = build_all(sources)  # with warnings denied

for name, m in programs.items():
    differential(m, binaries[name], cases(m, random.Random(name), 150), name)
for name, m in generated.items():
    differential(m, binaries[name], cases(m, random.Random(name), 25), name)
differential(CORNERS, binaries["corners"], cases(CORNERS, random.Random(7), 60), "corners")
deep_runs = [("deep", [n, big]) for n, big in [(999, False), (998, False), (0, False), (3, True), (2, True)]]
differential(DEEP, binaries["deep"], deep_runs, "deep")
assert interpreted(DEEP, "deep", [999, False]) == "ok 999"  # so the deepest run was compared, not skipped

def words(text):
    """A run's words: the def's name, then each argument, which may be in parentheses."""
    out, depth, word = [], 0, ""
    for c in text:
        if c == " " and depth == 0:
            out, word = out + [word] * bool(word), ""
            continue
        depth += (c == "(") - (c == ")")
        word += c
    return out + [word] * bool(word)


runs = [(w[0], w[1:]) for w in (words(line) for line, _ in EXPECT)]
for (line, want), (name, args), got in zip(EXPECT, runs, r.batch(binaries["corners"], runs, timeout=120)):
    try:
        values = [i.value(CORNERS, a) for a in args]
    except (ValueError, ParseError):
        values = None
    text = "refused" if values is None else interpreted(CORNERS, name, values)
    if want.startswith("refused"):
        ok = text == "refused" and got.startswith(want)
    else:
        ok = text == got and (re.fullmatch(want, got, re.S) is not None if "err " in want else got == want)
    if not ok:
        failures.append(f"corners: {line}\n    expected:    {want!r}\n    interpreter: {text!r}\n    rust:        {got!r}")


# 4. What emit() refuses (D96).

for bad, why in [
    (module("(spec f (params (x i64)) (returns (r i64)) (effects))", "(def f (body (return (+ x true))))"),
     "doesn't pass tier 0: 3:27: E-TYPE-001"),
    (module("(spec g (params (x i64)) (returns (r i64)) (effects))",
            "(spec f (params (x i64)) (returns (r i64)) (requires true) (effects))",
            "(def f (body (let ((y i64)) (call g x)) (return y)))"), "g is a spec with no def"),
]:
    try:
        r.emit(bad)
    except ValueError as e:
        assert why in str(e), e
    else:
        failures.append(f"emitted a module it should refuse: {why}")
# A module with no defs is a crate whose driver knows no names.
empty = r.build(r.emit(module("(ghost-fn twice ((x int)) int (body (* 2 x)))")), TMP / "empty", flags=STRICT)
assert r.batch(empty, [("twice", ["1"])]) == ["refused: no def named 'twice'"]
# Arguments that aren't UTF-8 can't start a run, on the command line or in a batch (D96).
p = subprocess.run([str(binaries["corners"]), b"\xff", b"1"], capture_output=True)
assert p.returncode == 2 and p.stdout == b"", p
p = subprocess.run([str(binaries["corners"]), "--batch"], input=b"arith \xff 1\narith 3 -2\n", capture_output=True)
lines = p.stdout.decode().split("\n")
assert p.returncode == 0 and lines[0].startswith("refused: ") and lines[1:] == ["ok 1 5 -6 -1 1 -3", ""], p


# 5. The command line: the same text and exit code as interp.py's.

def cli(module_main, *argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module_main(list(argv))
    return code, out.getvalue(), err.getvalue()


abs_file, merge_file = str(SUITE / "accept/abs.b17"), str(SUITE / "accept/merge_sorted.b17")
for argv in [(abs_file, "abs", "-5"), (abs_file, "abs", "-9223372036854775808"),
             (merge_file, "merge_sorted", "(seq-lit 1 3)", "(seq-build 2 (fn (i) (* i 2)))"),
             (abs_file, "abs", "(neg 5)"), (abs_file, "abs", "9223372036854775808"), (abs_file, "nope", "1"),
             (abs_file, "abs"), (abs_file, "\udcff", "1"), (str(SUITE / "accept/isqrt.b17"), "isqrt", "-4")]:
    want, got = cli(i.main, *argv), cli(r.main, "--run", *argv)
    assert got[:2] == want[:2], (argv, want, got)
    assert (got[2] == "") == (want[2] == ""), (argv, want, got)
code, text, _ = cli(r.main, abs_file)
assert code == 0 and text.startswith("// Emitted by b17c's Rust backend") and "pub fn abs(x: i64) -> i64" in text
assert cli(r.main, str(SUITE / "reject/E-OWN-001-use-after-move.b17"))[0] == 2
assert cli(r.main, "--run", str(SUITE / "reject/E-OWN-001-use-after-move.b17"), "f")[0] == 2
assert cli(r.main)[0] == 2 and cli(r.main, "--report", "x.json", abs_file)[0] == 2

# -o builds; --report writes the backend's fields into the trusted base report (D25, D97).
report, binary = TMP / "abs.json", TMP / "abs-cli"
report.write_text(json.dumps({"module": "abs", "input_sha256": r.sha256(r.canonical(parse(Path(abs_file).read_bytes()))),
                              "level": "L3-S"}))
assert cli(r.main, "-o", str(binary), "--report", str(report), abs_file)[0] == 0
data = json.loads(report.read_text())
assert data["level"] == "L3-S", data  # verify.py's fields stay
backend = data["backend"]
assert backend["rustc"].startswith("rustc ") and backend["target"] and backend["flags"] == list(r.FLAGS), backend
assert backend["binary_sha256"] == r.sha256(binary.read_bytes()), backend
assert backend["rust_sha256"] == r.sha256(r.emit(parse(Path(abs_file).read_bytes())).encode()), backend
r.build(sources["suite-abs"], TMP / "abs-again")
assert (TMP / "abs-again").read_bytes() == binary.read_bytes()  # a build is reproducible
code, _, err = cli(r.main, "-o", str(binary), "--report", str(report), merge_file)
assert code == 2 and "report of a different input" in err, err
assert r.sha256(binary.read_bytes()) == backend["binary_sha256"]  # refused before building


shutil.rmtree(TMP, ignore_errors=True)
if failures:
    print(f"{len(failures)} failures:")
    for f in failures[:40]:
        print(f)
    raise SystemExit(1)
total = sum(n for k, n in compared.items() if not k.startswith("skipped"))
print(f"Rust backend self-checks passed: {len(sources) + 1} crates built with warnings denied; "
      f"{total:,} differential runs matched the interpreter ({', '.join(f'{k} {n:,}' for k, n in sorted(compared.items()))}); "
      f"{r.toolchain()['rustc']}")
