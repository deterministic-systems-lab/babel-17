"""WP7's self-check: emitted Rust compiles, forbids unsafe code, and matches the reference
interpreter on differential tests (D18, D95-D97), for B17-0 and for B17-1 under subset 1
(D101, D110, D111): uv run --no-project b17c/test_rust.py

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
from check import check, show, subst
import syntax
from syntax import ParseError


def parse(text, subset=0):  # B17-0's tests name their subset (D101)
    return syntax.parse(text, subset)


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
compared_1 = Counter()  # B17-1's runs compared


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


def interpreted(m, name, args, subset=0):
    """The interpreter's text for a run (§8, check off), "refused", or None past FUEL steps."""
    try:
        out = i.run(m, name, args, fuel=FUEL, subset=subset)
    except ValueError:
        return "refused"
    return None if isinstance(out, i.Limit) else i.text_of(out)


def differential(m, binary, cases, label, subset=0):
    """Each run of cases, (def name, args), that the interpreter finishes must give the
    binary the same text, line for line."""
    runs, want = [], []
    for name, args in cases:
        text = interpreted(m, name, args, subset)
        if text is None:
            compared["skipped: limit"] += 1
            continue
        runs.append((name, [i._term(a) for a in args]))
        want.append(text)
    for (name, args), w, got in zip(runs, want, r.batch(binary, runs, timeout=120)):
        compared["refused" if w == "refused" else w.split("\n")[-1].split(" ")[0]] += 1
        compared_1[subset] += 1
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


def cases(m, rng, per_def, subset=0):
    datas, out = r.data_types(m) if subset else None, []
    for it in m.items[3:]:
        if it.items[0].text == "def":
            types = signature(m, it.items[1].text)
            out += [(it.items[1].text, [value1(rng, t, datas) if subset else value(rng, t) for t in types])
                    for _ in range(per_def)]
    return out


# 1. The suite: every program that passes tier 0 compiles, and runs as the interpreter does.

programs = {f"suite-{p.stem}": parse(p.read_bytes())
            for p in sorted((SUITE / "accept").glob("*.b17")) + sorted((SUITE / "reject").glob("E-PROOF-*.b17"))}
assert len(programs) == 29, len(programs)
sources = {name: r.emit(m, subset=0) for name, m in programs.items()}


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
assert check(CORNERS, subset=0) == [], check(CORNERS, subset=0)
sources["corners"] = r.emit(CORNERS, subset=0)

# Recursion as deep as D59 lets the interpreter go, through a frame that holds 450 vectors,
# whether or not the branch that declares them runs. 1,000 such frames overflow the 8 MiB a
# main thread gets, so a run needs a stack of its own (D96). Found in WP7's review.
DEEP = module(
    "(spec deep (params (n i64) (big bool)) (returns (r i64)) (requires (>= n 0)) (effects alloc io))",
    "(def deep (decreases n) (body (if (<= n 0) (return 0) (block)) (if big (block "
    + " ".join(f"(let v{k} (vec i64) (seq-build n (fn (k{k}) (+ k{k} {k}))))" for k in range(450))
    + " (let ((r1 i64)) (call deep (- n 1) big)) " + " ".join(f"(print (idx v{k} 0))" for k in range(450))
    + " (return r1)) (block)) (let ((r2 i64)) (call deep (- n 1) big)) (return (+ r2 1))))")
sources["deep"] = r.emit(DEEP, subset=0)

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
    found = check(m, subset=0)
    if found:
        failures.append(f"generated module {seed} doesn't pass tier 0, a generator bug: {found[:3]}")
        continue
    generated[f"generated-{seed}"] = m
    sources[f"generated-{seed}"] = r.emit(m, subset=0)


# 4. B17-1, under subset 1 (docs/b17-1.md, D101, D110, D111): its suite, corners and generated
# programs, emitted with the others and compared the same way below.

def module1(*items):
    return parse(HEAD + "\n" + "\n".join(items) + ")", 1)


def instance(datas, t):
    """Data type t's constructors, [(name, [(field, type)])], with its type arguments in place."""
    d = datas[t[1]]
    env = dict(zip(d.params, t[2:]))
    return [(c.text, [(f.text, subst(ft, env)) for f, ft in fs]) for c, fs in d.ctors]


def value1(rng, t, datas, depth=0):
    """A random value of B17-1 runtime type t: B17-0's, and tuples and data values a few
    levels deep. Deeper, each data value takes a constructor with the fewest fields that hold
    data, and vectors get shorter, so every value ends."""
    if t in (BOOL, I64) or t[0] in ("vec", "slice") and t[1] in (BOOL, I64):
        return value(rng, t)
    if t[0] in ("vec", "slice"):
        n = rng.choice([0, 1, 2, 3] if depth < 3 else [0, 1] if depth < 6 else [0])
        return tuple(value1(rng, t[1], datas, depth + 1) for _ in range(n))
    if t[0] == "tuple":
        return i.Tup(tuple(value1(rng, a, datas, depth + 1) for a in t[1:]))
    ctors = instance(datas, t)
    if depth >= 4:
        holding = lambda c: sum(holds_data(ft) for _, ft in c[1])
        ctors = [c for c in ctors if holding(c) == min(map(holding, ctors))]
    c, fields = rng.choice(ctors)
    return i.Data(c, tuple(value1(rng, ft, datas, depth + 1) for _, ft in fields))


def holds_data(t):
    return t[0] == "data" or any(holds_data(a) for a in t[1:] if isinstance(a, tuple))


SUITE_1 = SUITE / "b17-1"
programs_1 = {f"suite1-{p.stem}": parse(p.read_bytes(), 1)
              for p in sorted((SUITE_1 / "accept").glob("*.b17")) + sorted((SUITE_1 / "reject").glob("E-PROOF-*.b17"))}
assert len(programs_1) == 17, len(programs_1)
for name, m in programs_1.items():
    sources[name] = r.emit(m, 1)

# The accept programs' inputs from test_interp.py's ACCEPT_1 and OUTSIDE_1: each spec's own
# examples, then inputs outside its requires, which run into the err paths with checking off.
D, T = i.Data, i.Tup
NONE, LEAF, NIL = D("none", ()), D("leaf", ()), D("nil", ())


def some(v):
    return D("some", (v,))


def node(v, left=LEAF, right=LEAF):
    return D("node", (v, left, right))


def seg(lo, hi, vals):
    if hi - lo == 1:
        return D("node", (vals[lo], lo, hi, NONE, NONE))
    left, right = seg(lo, (lo + hi) // 2, vals), seg((lo + hi) // 2, hi, vals)
    return D("node", (max(left.fields[0], right.fields[0]), lo, hi, some(left), some(right)))


def trie(*keys):
    kids = [NONE] * 256
    for c in sorted({k[0] for k in keys if k}):
        kids[c] = some(trie(*[k[1:] for k in keys if k and k[0] == c]))
    return D("node", (() in keys, tuple(kids)))


BST, SEG = node(5, node(2), node(9, node(7))), seg(0, 4, [3, 1, 4, 1])
TREE = D("node", (1, D("node", (2, D("node", (4, NIL, NIL)), D("node", (5, NIL, NIL)))), D("node", (3, NIL, NIL))))
GRAPH = D("graph", (((1,), (2,), (), (0,)),))
WEIGHTED = D("weighted_graph", (((T((1, 4)), T((2, 1))), (T((0, 4)), T((2, 2))), (T((0, 1)), T((1, 2)))),))
ACCEPT_1 = {
    "bst_insert": ("insert", [(LEAF, 5), (BST, 8), (BST, 5), (node(5, node(7)), 1), (LEAF, -1)]),
    "bst_search": ("search", [(LEAF, 5), (BST, 7), (BST, 6), (node(5, LEAF, node(3)), 3)]),
    "discrete_logarithm": ("discrete_log_naive", [(2, 8, 11), (2, 3, 7), (0, 0, 5), (3, 1, 2), (2, 3, 1), (MAX, 1, 3)]),
    "longest_palindrome_substring": ("longest_palindromic_substring", [((1, 2, 1, 3),), ((),), ((4, 4),)]),
    "segmenttree_query": ("query", [(SEG, 1, 3), (SEG, 0, 4), (SEG, 3, 4), (SEG, 2, 2), (SEG, 0, 5)]),
    "trie_insert": ("insert", [(NONE, (1, 2)), (some(trie((5,))), (5, 7)), (some(trie((5,))), ()), (NONE, (256,)),
                               (some(trie()), (1,))]),
    "lca": ("lowest_common_ancestor", [(TREE, 4, 5), (TREE, 4, 3), (TREE, 2, 4), (TREE, 4, 6)]),
    "bfs": ("bfs_shortest_path", [(GRAPH, 0, 2), (GRAPH, 2, 0), (GRAPH, 3, 3), (GRAPH, 0, 4),
                                  (D("graph", (((5,),),)), 0, 0)]),
    "kruskal": ("kruskal_mst", [(WEIGHTED,), (D("weighted_graph", ((),)),)]),
    "prim": ("prim_mst", [(WEIGHTED,), (D("weighted_graph", ((),)),)]),
    "coin_change": ("coin_change", [((1, 2, 5), 11), ((2,), 3), ((3,), 0), ((), 1), ((0,), 1)]),
}
assert sorted(ACCEPT_1) == sorted(p.stem for p in (SUITE_1 / "accept").glob("*.b17"))
# The proof rejects whose fault a def shows on a concrete input (test_interp.py): replace at
# an index out of range, and a field the constructor lacks. Of the other three, one's fault is
# in a ghost-fn, which the binary erases, and two are lemmas, whose bodies never run (D57).
PROOF_1 = {"E-PROOF-BOUNDS-replace-out-of-range": [("swap_in", [(), 5]), ("swap_in", [(1,), 5])],
           "E-PROOF-FIELD-wrong-constructor": [("root", [LEAF]), ("root", [node(4)])]}
named_1 = {f"suite1-{p}": [(d, list(args)) for args in runs] for p, (d, runs) in ACCEPT_1.items()}
named_1.update((f"suite1-{p}", runs) for p, runs in PROOF_1.items())

CORNERS_1 = module1(
    # Names Rust reserves or its prelude uses, as types, constructors and fields (D95, D110).
    "(data type () (loop) (self (crate i64) (super (vec type))))",
    "(data rt () (rt (std i64)))",
    "(data str () (usize (u8 bool)) (main))",
    # A parameter no value holds, which Rust would reject, alone and beside one that's held,
    # and recursion through option, which is boxed.
    "(data ph (a) (pc (x i64)))",
    "(data pp (a b) (pp (v a)))",
    "(data lst () (lst (head i64) (tail (option lst))))",
    "(data tree () (leaf) (node (val i64) (left tree) (right tree)))",
    "(data sh () (dot) (circ (r i64)) (rect (w i64) (h i64)))",
    "(data bag () (bag (items (vec i64)) (tag (option i64))))",
    "(data box (a) (box (inner a) (more (vec a))))",
    "(data glist (a) (gnil) (gcons (h a) (t (glist a))))",
    "(data samename () (sn (k i64) (on bool)))",  # a type and a def may share a name (D82)

    "(spec kw (params (t type)) (returns (r i64) (u type)) (effects alloc))",
    """(def kw (body
      (match t
        (case (loop) (return 0 (self 1 (vec-new))))
        (case (self c s)
          (block (let-mut v (vec type) s) (push v (loop)) (let n i64 (+ c (len v))) (return n (self c v)))))))""",
    "(spec names (params (a rt) (b str)) (returns (r i64) (s str)) (effects))",
    """(def names (body
      (if (is usize b)
        (return (field a std) (usize (not (field b u8))))
        (return (neg (field a std)) b))))""",
    "(spec phantom (params (p (ph (vec i64))) (q (pp bool (vec i64)))) (returns (r (ph int)) (s (pp bool (iset int)))) (effects))",
    """(def phantom (body
      (let x (ph int) (pc (+ (field p x) 1)))
      (match q (case (pp v) (return x (pp (not v)))))))""",
    "(spec count (params (l lst)) (returns (n i64)) (effects))",
    """(def count (decreases (rank l))
      (body
        (match l
          (case (lst h t)
            (match t
              (case (none) (return 1))
              (case (some rest) (block (let ((m i64)) (call count rest)) (return (+ m 1)))))))))""",
    "(spec make (params (n i64)) (returns (l lst)) (effects alloc))",
    """(def make (decreases n)
      (body
        (if (<= n 1)
          (return (lst n (none)))
          (block (let ((rest lst)) (call make (- n 1))) (return (lst n (some rest)))))))""",
    # Reading through a moving value, which never moves it (§5 rule 3).
    "(spec peek (params (l lst) (b bag) (k i64)) (returns (r i64) (s bool) (o (option i64))) (effects))",
    """(def peek (body
      (let r i64 (+ (field l head) (idx (field b items) k)))
      (let s bool (is some (field l tail)))
      (return r s (field b tag))))""",
    # Fields a constructor lacks: err FIELD, in an expression and through a place (§8).
    "(spec area (params (s sh)) (returns (a i64)) (effects))",
    "(def area (body (if (is circ s) (return (* (field s r) (field s r))) (return (* (field s w) (field s h))))))",
    "(spec grow (params (b bag) (s (vec sh)) (k i64) (e i64)) (returns (c2 bag) (t2 (vec sh))) (effects alloc io))",
    """(def grow (body
      (let-mut c bag b)
      (let-mut t (vec sh) s)
      (push (field c items) e)
      (set-idx (field c items) k e)
      (let old i64 (replace (field (idx t k) w) e))
      (print old)
      (return c t)))""",
    # The order a place's update runs in: its indices, the statement's index and value, then the
    # checks from the root out, then the change (§8).
    "(spec order (params (v (vec (vec i64))) (i i64) (j i64) (x i64)) (returns (r (vec (vec i64)))) (effects alloc))",
    """(def order (body
      (let-mut w (vec (vec i64)) v)
      (set-idx (idx w (/ 10 i)) (/ 10 j) (+ x 1))
      (push (idx w (- i 1)) (* x 2))
      (return w)))""",
    "(spec order3 (params (v (vec (vec (vec i64)))) (i i64) (j i64)) (returns (r (vec (vec (vec i64))))) (effects alloc))",
    "(def order3 (body (let-mut w (vec (vec (vec i64))) v) (push (idx (idx w (/ 10 i)) (/ 10 j)) 7) (return w)))",
    "(spec order2 (params (s (vec sh)) (i i64) (x i64)) (returns (r (vec sh)) (o i64)) (effects))",
    """(def order2 (body
      (let-mut t (vec sh) s)
      (let o i64 (replace (field (idx t i) r) (+ x 1)))
      (return t o)))""",
    # replace at a variable, and in a let-mut (§5 rule 3).
    "(spec taken (params (v (vec i64))) (returns (r (vec i64)) (s (vec i64))) (effects alloc))",
    """(def taken (body
      (let-mut w (vec i64) v)
      (let-mut old (vec i64) (replace w (seq-build 2 (fn (i) (* i 10)))))
      (push old 7)
      (return w old)))""",
    # Tuples of several sizes, nested and holding vectors, read and printed.
    "(spec tuples (params (a (tuple i64 bool)) (b (tuple (tuple i64 bool) (vec i64) i64 bool sh))) (returns (r (tuple i64 (tuple bool i64) (vec i64)))) (effects alloc))",
    """(def tuples (body
      (let-mut c (tuple (tuple i64 bool) (vec i64) i64 bool sh) b)
      (push (get c 1) (get a 0))
      (set-idx (get c 1) 0 (get (get c 0) 0))
      (match c
        (case (tuple t v n f s)
          (block (let ((ar i64)) (call area1 s)) (return (tuple (+ n (get t 0)) (tuple (and f (get a 1)) ar) v)))))))""",
    "(spec area1 (params (s sh)) (returns (a i64)) (requires true) (effects))",
    "(def area1 (body (return (match s (case (dot) 0) (case (circ r) (* 3 r)) (case (rect w h) (* w h))))))",
    # Open type arguments take i64 (§4), and a generic type holds what it's given.
    "(spec open (params (b (box (option i64)))) (returns (r bool) (s (box (option i64))) (t (option bool))) (effects alloc))",
    """(def open (body
      (let-mut c (box (option i64)) b)
      (push (field c more) (none))
      (push (field c more) (some (len (field c more))))
      (let s bool (is some (field c inner)))
      (return (is none (none)) c (some s))))""",
    # match: as the last statement, every arm returning; on a copied value, which stays usable;
    # and as an expression.
    "(spec arms (params (o (option i64)) (t tree)) (returns (r i64)) (effects io))",
    """(def arms (body
      (match o (case (none) (block)) (case (some v) (print v)))
      (print (match o (case (none) -1) (case (some w) (* w 2))))
      (match t
        (case (leaf) (return 0))
        (case (node nv l r) (block (if (is leaf l) (return nv) (return (+ nv (field l val)))))))
      (print 99)))""",
    # A tree built and taken apart by recursion, its boxed fields moved out of their boxes.
    "(spec insert (params (t tree) (x i64)) (returns (out tree)) (effects alloc))",
    """(def insert (decreases (rank t))
      (body
        (match t
          (case (leaf) (return (node x (leaf) (leaf))))
          (case (node v l r)
            (if (< x v)
              (block (let ((l2 tree)) (call insert l x)) (return (node v l2 r)))
              (block (let ((r2 tree)) (call insert r x)) (return (node v l r2))))))))""",
    "(spec build (params (xs (ref (slice i64)))) (returns (t tree)) (effects alloc))",
    """(def build (body
      (let-mut t tree (leaf))
      (let-mut i i64 0)
      (while (< i (len xs)) (decreases (- (len xs) i))
        (let ((u tree)) (call insert t (idx xs i)))
        (set t u)
        (set i (+ i 1)))
      (return t)))""",
    "(spec height (params (xs (ref (slice i64)))) (returns (n i64)) (effects alloc))",
    "(def height (body (let ((t tree)) (call build xs)) (let ((n i64)) (call depth t)) (return n)))",
    "(spec depth (params (t tree)) (returns (n i64)) (effects))",
    """(def depth (decreases (rank t))
      (body
        (match t
          (case (leaf) (return 0))
          (case (node v l r)
            (block
              (let ((a i64)) (call depth l))
              (let ((b i64)) (call depth r))
              (return (+ 1 (if (> a b) a b))))))))""",
    # seq-build of data values, and of moving ones (§7).
    "(spec built (params (n i64)) (returns (r (vec (option i64))) (s (vec tree))) (effects alloc))",
    """(def built (body
      (let r (vec (option i64)) (seq-build n (fn (i) (if (== (% i 2) 0) (some i) (none)))))
      (return r (seq-build (- n 1) (fn (j) (node j (leaf) (leaf)))))))""",
    # A copied data value: Rust copies it, so the old one is still there (§5 rule 1).
    "(spec copies (params (s sh) (v (vec sh))) (returns (a sh) (b sh) (c (vec sh))) (effects alloc))",
    """(def copies (body
      (let-mut w (vec sh) v)
      (push w s)
      (push w s)
      (let t sh (idx w 0))
      (set-idx w 0 (circ 7))
      (return t s w)))""",
    "(spec samename (params (s samename)) (returns (r samename)) (effects))",
    "(def samename (body (return (sn (+ (field s k) 1) (not (field s on))))))",
    "(spec gsum (params (l (glist (tuple i64 bool)))) (returns (n i64) (m (glist i64))) (effects alloc))",
    """(def gsum (decreases (rank l))
      (body
        (match l
          (case (gnil) (return 0 (gnil)))
          (case (gcons h t)
            (block (let ((n i64) (m (glist i64))) (call gsum t)) (return (+ n (get h 0)) (gcons (if (get h 1) 1 0) m)))))))""",
    # A list as long as a run likes, built and walked by loops, which Rust drops by recursion.
    "(spec chain (params (n i64) (walk bool)) (returns (k i64)) (effects alloc))",
    """(def chain (body
      (let-mut l lst (lst 0 (none)))
      (let-mut i i64 1)
      (while (< i n) (decreases (- n i))
        (set l (lst i (some l)))
        (set i (+ i 1)))
      (if (not walk) (return i) (block))
      (let-mut k i64 1)
      (while (is some (field l tail)) (decreases (rank l))
        (let rest (option lst) (replace (field l tail) (none)))
        (match rest (case (none) (block)) (case (some x) (set l x)))
        (set k (+ k 1)))
      (return k)))""",
)
assert check(CORNERS_1, 1) == [], check(CORNERS_1, 1)
sources["corners1"] = r.emit(CORNERS_1, 1)

# As EXPECT, for B17-1.
EXPECT_1 = [
    ("kw (loop)", "ok 0 (self 1 (seq-lit))"),
    ("kw (self 5 (seq-lit (loop) (self 1 (seq-lit))))", "ok 8 (self 5 (seq-lit (loop) (self 1 (seq-lit)) (loop)))"),
    ("names (rt 4) (usize true)", "ok 4 (usize false)"),
    ("names (rt 4) (main)", "ok -4 (main)"),
    ("phantom (pc 3) (pp true)", "ok (pc 4) (pp false)"),
    ("count (lst 1 (some (lst 2 (some (lst 3 (none))))))", "ok 3"),
    ("make 4", "ok (lst 4 (some (lst 3 (some (lst 2 (some (lst 1 (none))))))))"),
    ("peek (lst 5 (none)) (bag (seq-lit 1 2) (some 9)) 1", "ok 7 false (some 9)"),
    ("peek (lst 5 (none)) (bag (seq-lit 1 2) (none)) 2", r"err BOUNDS at def peek/\S+: \(idx s 2\) on a sequence of length 2"),
    ("area (circ 3)", "ok 9"),
    ("area (dot)", r"err FIELD at def area/\S+: a dot value has no field w"),
    ("grow (bag (seq-lit) (none)) (seq-lit (rect 1 2)) 0 5", "print 1\nok (bag (seq-lit 5) (none)) (seq-lit (rect 5 2))"),
    ("grow (bag (seq-lit) (none)) (seq-lit (rect 1 2)) 1 5", r"err BOUNDS at def grow/\S+: \(set-idx \(field c items\) 1 \.\.\.\) on a vector of length 1"),
    ("grow (bag (seq-lit 0) (none)) (seq-lit (rect 1 2)) 1 5", r"err BOUNDS at def grow/\S+: \(idx t 1\) on a vector of length 1"),
    ("grow (bag (seq-lit) (none)) (seq-lit (circ 1)) 0 5", r"err FIELD at def grow/\S+: a circ value has no field w"),
    # The place's index, the statement's index, then the value, and only then the checks.
    ("order (seq-lit (seq-lit 1) (seq-lit 2) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 6)) 2 20 4", "ok (seq-lit (seq-lit 1) (seq-lit 2 8) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 5))"),
    ("order (seq-lit (seq-lit 1) (seq-lit 2) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 6)) 0 20 4", r"err DIV at def order/\S+: \(/ 10 0\) divides by zero"),
    ("order (seq-lit (seq-lit 1) (seq-lit 2) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 6)) 2 0 4", r"err DIV at def order/\S+: \(/ 10 0\) divides by zero"),
    ("order (seq-lit (seq-lit 1) (seq-lit 2) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 6)) 1 20 9223372036854775807", r"err OVERFLOW at def order/\S+: \(\+ 9223372036854775807 1\) = 9223372036854775808 leaves i64"),
    ("order (seq-lit (seq-lit 1) (seq-lit 2) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 6)) 2 0 9223372036854775807", r"err DIV at def order/\S+: \(/ 10 0\) divides by zero"),
    ("order3 (seq-lit) 0 0", r"err DIV at def order3/2\.2\.1\.1\.2@\S+: \(/ 10 0\) divides by zero"),
    ("order3 (seq-lit (seq-lit) (seq-lit (seq-lit 1))) 10 20", "ok (seq-lit (seq-lit) (seq-lit (seq-lit 1 7)))"),
    ("order3 (seq-lit (seq-lit) (seq-lit (seq-lit 1))) 5 10", r"err BOUNDS at def order3/\S+: \(idx w 2\) on a vector of length 2"),
    ("order (seq-lit (seq-lit 1) (seq-lit 2) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 6)) 1 20 4", r"err BOUNDS at def order/\S+: \(idx w 10\) on a vector of length 6"),
    ("order (seq-lit (seq-lit 1) (seq-lit 2) (seq-lit 3) (seq-lit 4) (seq-lit 5) (seq-lit 6)) 2 5 4", r"err BOUNDS at def order/\S+: \(set-idx \(idx w \(/ 10 i\)\) 2 \.\.\.\) on a vector of length 1"),
    ("order2 (seq-lit (dot)) 0 9223372036854775807", r"err OVERFLOW at def order2/\S+: \(\+ 9223372036854775807 1\) = 9223372036854775808 leaves i64"),
    ("order2 (seq-lit (dot)) 5 9223372036854775807", r"err OVERFLOW at def order2/\S+: \(\+ 9223372036854775807 1\) = 9223372036854775808 leaves i64"),
    ("order2 (seq-lit (dot)) 5 1", r"err BOUNDS at def order2/\S+: \(idx t 5\) on a vector of length 1"),
    ("order2 (seq-lit (dot)) 0 1", r"err FIELD at def order2/\S+: a dot value has no field r"),
    ("order2 (seq-lit (circ 4)) 0 1", "ok (seq-lit (circ 2)) 4"),
    ("taken (seq-lit 1)", "ok (seq-lit 0 10) (seq-lit 1 7)"),
    ("tuples (tuple 4 true) (tuple (tuple 2 true) (seq-lit 9) 3 true (rect 2 3))", "ok (tuple 5 (tuple true 6) (seq-lit 2 4))"),
    ("open (box (some 1) (seq-lit))", "ok true (box (some 1) (seq-lit (none) (some 1))) (some true)"),
    ("arms (some 4) (node 1 (node 2 (leaf) (leaf)) (leaf))", "print 4\nprint 8\nok 3"),
    ("arms (none) (leaf)", "print -1\nok 0"),
    ("build (seq-lit 5 2 8 1 9 3)", "ok (node 5 (node 2 (node 1 (leaf) (leaf)) (node 3 (leaf) (leaf))) (node 8 (leaf) (node 9 (leaf) (leaf))))"),
    ("height (seq-lit 5 2 8 1 9 3)", "ok 3"),
    ("built 4", "ok (seq-lit (some 0) (none) (some 2) (none)) (seq-lit (node 0 (leaf) (leaf)) (node 1 (leaf) (leaf)) (node 2 (leaf) (leaf)))"),
    ("built -1", r"err BOUNDS at def built/\S+: \(seq-build -1 \.\.\.\) has a negative length"),
    ("copies (dot) (seq-lit (rect 1 1))", "ok (rect 1 1) (dot) (seq-lit (circ 7) (dot) (dot))"),
    # Arguments that aren't values of the parameter's type can't start a run (D96).
    ("area (nope 1)", "refused"),
    ("area dot", "refused"),
    ("area (circ)", "refused"),
    ("area (circ 1 2)", "refused"),
    ("area (circ true)", "refused"),
    ("area (circ 01)", "refused"),
    ("area (circ 1", "refused"),
    ("phantom (pc 3) (pp 1)", "refused"),
    ("tuples (tuple 4) (tuple (tuple 2 true) (seq-lit 9) 3 true (dot))", "refused"),
    ("open (box (some true) (seq-lit))", "refused"),
    ("count (lst 1 (lst 2 (none)))", "refused"),
    ("area (circ -0)", "refused"),
    ("area (circ +1)", "refused"),
    ("area (circ 1x)", "refused"),
    ("area (circ 9223372036854775808)", "refused"),
    ("area (circ\u00a03)", "refused"),  # whitespace B17 doesn't have (D48)
    ("tuples (tuple 4 true false) (tuple (tuple 2 true) (seq-lit 9) 3 true (dot))", "refused"),
    ("grow (bag (vec-lit) (none)) (seq-lit) 0 1", "refused"),
    ("grow (bag (seq-lit) none) (seq-lit) 0 1", "refused"),
    ("count (lst 1(none))", "refused"),  # D49: whitespace between a list's elements
    ("open (box(none) (seq-lit))", "refused"),
    ("open (box (none) (seq-lit (none)(none)))", "refused"),
    ("area (circ  3)", "ok 9"),
    ("area (circ\t3 )", "ok 9"),
    ("samename (sn 4 true)", "ok (sn 5 false)"),
    ("gsum (gcons (tuple 2 true) (gcons (tuple 3 false) (gnil)))", "ok 5 (gcons 1 (gcons 0 (gnil)))"),
    ("chain 5 false", "ok 5"),
    ("chain 300 true", "ok 300"),
    ("chain 0 true", "ok 1"),
]
NESTED = "(lst 1 (none))"  # two levels a list, so 64 of them nest 128 deep, as deep as D55 allows
for _ in range(63):
    NESTED = f"(lst 1 (some {NESTED}))"
ODD = "(loop)"  # one level, then two a self, so 64 selfs nest 129 deep
for _ in range(64):
    ODD = f"(self 1 (seq-lit {ODD}))"
EXPECT_1 += [(f"count {NESTED}", "ok 64"), (f"count (lst 0 (some {NESTED}))", "refused"), (f"kw {ODD}", "refused")]


class Gen1:
    """Random B17-1 defs that pass tier 0 by construction. They declare data types that are
    copied, recursive and boxed, holding vectors, and generic, and their bodies use places,
    replace, match, constructors and tuples with every B17-0 form, keeping §5's ownership
    rules (D84) and calling the defs before them."""

    LITERALS = [0, 1, 2, 3, 5, 7, -1, -2, 100, MAX, MIN, 2**62, -2**62, 3037000500]
    DECLS = ["(data pt () (pt (x i64) (y bool)))",
             "(data sh () (dot) (circ (r i64)) (rect (w i64) (h i64)))",
             "(data tree () (leaf) (node (val i64) (left tree) (right tree)))",
             "(data bag () (bag (items (vec i64)) (tag (option i64)) (kids (vec tree))))",
             "(data pair (a b) (mk (fst a) (snd b)))",
             "(data wrap (a) (empty) (full (inner a) (more (vec a))))"]
    DATAS = r.data_types(module1(*DECLS))  # option's from the core library
    PT, SH, TREE, BAG = ("data", "pt"), ("data", "sh"), ("data", "tree"), ("data", "bag")
    OPT_I, OPT_T = ("data", "option", I64), ("data", "option", TREE)
    PAIR_IB, PAIR_VI = ("data", "pair", I64, BOOL), ("data", "pair", VEC_I, I64)
    TUP_IB, TUP_VI, TUP_PS = ("tuple", I64, BOOL), ("tuple", VEC_I, I64), ("tuple", PT, SH)
    COPIED_DATA = [PT, SH, OPT_I, PAIR_IB]
    SCRUTINEES = COPIED_DATA + [TUP_IB, TUP_PS]  # copied, so a match may take a new one
    COPIED = [I64, I64, BOOL] + SCRUTINEES
    MOVING = [VEC_I, VEC_B, TREE, BAG, OPT_T, PAIR_VI, ("data", "wrap", I64), ("data", "wrap", PT), TUP_VI,
              ("vec", PT), ("vec", TREE), ("vec", VEC_I), ("vec", TUP_IB), ("vec", OPT_T)]
    SLICES = [SLICE_I, ("slice", PT), ("slice", TREE), ("slice", VEC_I)]

    __init__, fresh, block, branches = Gen.__init__, Gen.fresh, Gen.block, Gen.branches
    show = staticmethod(show)

    def ctors(self, t):
        """[(constructor, [(field, type)])] of data type t, its type arguments substituted; a
        tuple type's one constructor is tuple."""
        return [("tuple", [(None, a) for a in t[1:]])] if t[0] == "tuple" else instance(self.DATAS, t)

    def moving(self, t):
        """§5 rule 1: vectors, recursive data types, and anything holding them move."""
        if t[0] in ("vec", "tuple"):
            return t[0] == "vec" or any(self.moving(a) for a in t[1:])
        if t[0] == "data":
            return self.DATAS[t[1]].mv_base or any(self.moving(ft) for _, fs in self.ctors(t) for _, ft in fs)
        return False

    def module(self, count):
        items, self.sigs = self.DECLS + ["(lemma l0 (params (n int)) (body))"], []
        for k in range(count):
            params = [(self.fresh("p"), self.rng.choice(self.COPIED + self.MOVING + self.SLICES)) for _ in range(self.rng.randint(0, 3))]
            results = [self.rng.choice(self.COPIED + self.MOVING) for _ in range(self.rng.randint(0, 2))]
            body = self.body(params, results)
            ps = " ".join(f"({n} {self.show(t)})" for n, t in params)
            rs = " ".join(f"({self.fresh('r')} {self.show(t)})" for t in results)
            items += [f"(spec f{k} (params {ps}) (returns {rs}) (requires (== {k} {k})) (effects alloc panic io))",
                      f"(def f{k} (body {body}))"]
            self.sigs.append((f"f{k}", [t for _, t in params], results))
        return HEAD + "\n" + "\n".join(items) + ")"

    def body(self, params, results):
        self.vars = {n: [t, False, True] for n, t in params}  # name -> [type, settable, live]
        self.results, self.outer = results, None  # outer: the variables a loop body may not move (E-OWN-004)
        stmts, ended = self.block(self.rng.randint(2, 7), 0)
        return " ".join(stmts + ([] if ended else [self.ret()]))

    def live(self, pred=lambda t: True, movable=False):
        return [n for n, (t, _, alive) in self.vars.items()
                if alive and pred(t) and not (movable and self.moving(t) and self.outer is not None and n in self.outer)]

    def take(self, n):
        if self.moving(self.vars[n][0]):
            self.vars[n][2] = False

    # Statements.

    def stmt(self, depth):
        rng = self.rng
        kinds = ["let", "let", "let", "set", "update", "update", "update", "replace", "replace", "replace", "print",
                 "call", "ghost", "match"]
        kinds += ["if", "while", "match"] if depth < 2 else []
        kinds += ["return", "panic"] if depth > 0 else []
        kind = rng.choice(kinds)
        if kind == "let":
            t, name, mut = rng.choice(self.COPIED + self.MOVING + self.MOVING), self.fresh("x"), rng.random() < 0.75
            init = self.owned(t)
            self.vars[name] = [t, mut, True]
            return f"({'let-mut' if mut else 'let'} {name} {self.show(t)} {init})", False
        if kind == "set":
            targets = [n for n, (t, settable, alive) in self.vars.items()
                       if settable and (not self.moving(t) or alive or self.outer is None or n not in self.outer)]
            if targets:
                x = rng.choice(targets)
                value = self.owned(self.vars[x][0], avoid={x} if not self.vars[x][2] else set())
                self.vars[x][2] = True
                return f"(set {x} {value})", False
        if kind == "update":
            found = self.place(lambda t: t[0] == "vec")
            if found:
                p, t, root = found
                if rng.random() < 0.5:
                    return f"(push {p} {self.owned(t[1], avoid={root})})", False
                i = rng.choice(["0", "1", f"(- (len {p}) 1)", self.expr(I64)])
                return f"(set-idx {p} {i} {self.owned(t[1], avoid={root})})", False
        if kind == "replace":
            found = self.place(lambda t: True)
            if found:
                p, t, root = found
                name, mut = self.fresh("w"), rng.random() < 0.3
                value = self.owned(t, avoid={root})
                self.vars[name] = [t, mut, True]
                return f"({'let-mut' if mut else 'let'} {name} {self.show(t)} (replace {p} {value}))", False
        if kind == "call" and self.sigs:
            s = self.call(rng.choice(self.sigs))
            if s:
                return s, False
        if kind == "ghost":  # ghost code types literals as int, so only i64 variables and literals here
            ints = self.live(lambda t: t == I64)
            a = rng.choice(ints) if ints and rng.random() < 0.7 else str(rng.randint(-3, 9))
            return rng.choice([f"(assert (== {a} {a}))", f"(ghost-let {self.fresh('g')} int (+ {a} 1))",
                               f"(call l0 {a})", f"(forall (({self.fresh('q')} int)) (call l0 0))",
                               f"(obtain (({self.fresh('o')} int)) (== {a} {a}))"]), False
        if kind == "match":
            s = self.match(depth)
            if s:
                return s
        if kind == "if":
            return self.branches(depth)
        if kind == "while":
            return self.loop(depth), False
        if kind == "return":
            return self.ret(), True
        if kind == "panic":
            return f"(panic \"{self.fresh('stop ')}\")", True
        return f"(print {self.expr(I64)})", False

    def place(self, want):
        """A place rooted at a live let-mut variable whose type passes want: (text, type, root)."""
        roots = [n for n, (t, settable, alive) in self.vars.items() if settable and alive]
        if not roots:
            return None
        rng = self.rng
        for _ in range(6):
            root = rng.choice(roots)
            p, t = root, self.vars[root][0]
            for _ in range(rng.choice([0, 1, 1, 2, 3])):
                step = self.step(p, t)
                if step is None:
                    break
                p, t = step
                if want(t) and rng.random() < 0.5:
                    break
            if want(t):
                return p, t, root
        return None

    def step(self, p, t):
        """One step into a place or value p of type t: (idx p i), (get p K) or (field p F)."""
        rng = self.rng
        if t[0] in ("vec", "slice"):
            i = rng.choice(["0", "1", f"(- (len {p}) 1)", str(rng.randint(-1, 3))])
            return f"(idx {p} {i})", t[1]
        if t[0] == "tuple":
            k = rng.randrange(len(t) - 1)
            return f"(get {p} {k})", t[k + 1]
        if t[0] == "data":
            fields = [(f, ft) for _, fs in self.ctors(t) for f, ft in fs]
            if fields:
                f, ft = rng.choice(fields)
                return f"(field {p} {f})", ft
        return None

    def match(self, depth):
        """A match statement on a variable, which moves if its type does, or on a copied value."""
        rng = self.rng
        names = self.live(lambda t: t[0] in ("data", "tuple"), movable=True)
        if names and rng.random() < 0.7:
            e = rng.choice(names)
            t = self.vars[e][0]
            self.take(e)
        else:
            t = rng.choice(self.SCRUTINEES)
            e = self.expr(t)
        before = {n: list(v) for n, v in self.vars.items()}
        arms = []
        for c, fs in self.ctors(t):
            self.vars = {n: list(v) for n, v in before.items()}
            binders = [self.fresh("b") for _ in fs]
            for b, (_, ft) in zip(binders, fs):
                self.vars[b] = [ft, False, True]
            stmts, ended = self.block(rng.randint(0, 3), depth + 1)
            arms.append((f"(case ({' '.join([c] + binders)}) (block {' '.join(stmts)}))", ended, self.vars))
        going = [vs for _, ended, vs in arms if not ended]
        self.vars = before
        for n in self.vars:  # moved in any arm that goes on: moved after (§5 rule 5)
            self.vars[n][2] = all(vs[n][2] for vs in going) if going else self.vars[n][2]
        return f"(match {e} {' '.join(a for a, _, _ in arms)})", not going

    def loop(self, depth):
        c, limit = self.fresh("c"), self.rng.randint(1, 3)
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
            if t[0] == "slice":
                vs = [v for v in self.live(lambda u: u in (("vec", t[1]), t)) if v not in taken]
                if not vs:
                    return None
                v = self.rng.choice(vs)
                args.append(v if self.vars[v][0] == t else f"(borrow {v})")
                taken.add(v)
            elif self.moving(t):
                vs = [v for v in self.live(lambda u: u == t, movable=True) if v not in taken]
                if not vs:
                    return None
                args.append(self.rng.choice(vs))
                taken.add(args[-1])
            else:
                seen = set()
                args.append(self.expr(t, avoid=taken, seen=seen))
                taken |= seen
        for a, t in zip(args, params):
            if self.moving(t):
                self.vars[a][2] = False
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
            values.append(self.owned(t, avoid=taken, seen=seen))
            taken |= seen
        return f"(return {' '.join(values)})"

    # Expressions.

    def owned(self, t, avoid=frozenset(), seen=None, depth=0, fresh=False):
        """A value for an owned position of type t: a moving variable moves, unless fresh
        (a seq-build body, which runs once per element and so moves nothing outer)."""
        rng, seen = self.rng, seen if seen is not None else set()
        if not self.moving(t):
            return self.expr(t, depth, avoid, seen)
        names = [] if fresh else [v for v in self.live(lambda u: u == t, movable=True) if v not in avoid and v not in seen]
        if names and rng.random() < 0.45:
            v = rng.choice(names)
            self.take(v)
            seen.add(v)
            return v
        if t[0] == "vec":
            k = rng.random()
            if k < 0.35 or depth > 2:
                return "(vec-new)"
            n = rng.choice(["0", "1", "2", "3", self.expr(I64, 2, avoid, seen)])
            b = self.fresh("k")
            self.vars[b] = [I64, False, True]
            body = self.owned(t[1], avoid, seen, depth + 1, fresh=True)
            del self.vars[b]
            return f"(seq-build {n} (fn ({b}) {body}))"
        return self.build(t, avoid, seen, depth, fresh, own=True)

    def build(self, t, avoid, seen, depth, fresh, own):
        """A constructor call or tuple of type t, its arguments owned when it is."""
        rng = self.rng
        if t[0] == "tuple":
            head, parts = "tuple", list(t[1:])
        else:
            cs = self.ctors(t)
            if depth > 2:  # the constructor with the fewest fields ends the recursion
                cs = sorted(cs, key=lambda c: len(c[1]))[:1]
            head, fs = rng.choice(cs)
            parts = [ft for _, ft in fs]
        args, taken = [], set(avoid)
        for u in parts:
            s = set()
            args.append(self.owned(u, taken, s, depth + 1, fresh) if own else self.expr(u, depth + 1, taken, s))
            taken |= s
            seen |= s
        return f"({' '.join([head] + args)})"

    def reads(self, avoid):
        """Expressions that read the live variables through places, with their types."""
        rng, out = self.rng, []
        for v in self.live():
            if v in avoid:
                continue
            p, t = v, self.vars[v][0]
            out.append((p, t, v))
            for _ in range(2):
                step = self.step(p, t)
                if step is None:
                    break
                p, t = step
                out.append((p, t, v))
        return out

    def pick(self, found, seen):
        """One of found's (place, type, root) reads, its root added to seen if it moves: (place, type)."""
        p, u, v = self.rng.choice(found)
        if self.moving(self.vars[v][0]):
            seen.add(v)
        return p, u

    def expr(self, t, depth=0, avoid=frozenset(), seen=None):
        """A runtime expression of copied type t that reads no moving variable in avoid, adding
        the moving variables it reads to seen."""
        rng, seen = self.rng, seen if seen is not None else set()
        sub = lambda u: self.expr(u, depth + 1, avoid, seen)
        if t[0] == "slice" or self.moving(t):
            raise AssertionError(t)
        reads = [x for x in self.reads(avoid) if x[1] == t]
        if depth >= 3 or rng.random() < 0.35:
            if reads and rng.random() < 0.7:
                return self.pick(reads, seen)[0]
            if t == BOOL:
                return rng.choice(["true", "false"])
            if t == I64:
                return str(rng.choice(self.LITERALS) if rng.random() < 0.3 else rng.randint(-4, 9))
            return self.build(t, avoid, seen, depth + 1, False, own=False)
        k = rng.randrange(8)
        if k == 0:
            return f"(if {sub(BOOL)} {sub(t)} {sub(t)})"
        if k == 1:
            u = rng.choice(self.SCRUTINEES)
            scrut = sub(u)
            arms = []
            for c, fs in self.ctors(u):
                binders = [self.fresh("m") for _ in fs]
                for b, (_, ft) in zip(binders, fs):
                    self.vars[b] = [ft, False, True]
                arms.append(f"(case ({' '.join([c] + binders)}) {sub(t)})")
                for b in binders:
                    del self.vars[b]
            return f"(match {scrut} {' '.join(arms)})"
        if k == 2 and reads:
            return self.pick(reads, seen)[0]
        if t[0] in ("data", "tuple"):
            return self.build(t, avoid, seen, depth + 1, False, own=False)
        if t == I64:
            if k == 3:
                seqs = [x for x in self.reads(avoid) if x[1][0] in ("vec", "slice")]
                if seqs:
                    return f"(len {self.pick(seqs, seen)[0]})"
            if k == 4:
                a = sub(I64)
                return f"(neg {a})" if a[0] == "(" or a[0].isalpha() else f"(neg (+ {a} 0))"
            return f"({rng.choice(['+', '-', '*', '/', '%'])} {sub(I64)} {sub(I64)})"
        if k == 3:
            datas = [x for x in self.reads(avoid) if x[1][0] == "data"]
            if datas and rng.random() < 0.7:
                p, u = self.pick(datas, seen)
            else:
                u = rng.choice(self.COPIED_DATA)
                p = sub(u)
            return f"(is {rng.choice(self.ctors(u))[0]} {p})"
        if k == 4:
            return f"(not {sub(BOOL)})"
        if k == 5:
            return f"({rng.choice(['and', 'or', '=>'])} {sub(BOOL)} {sub(BOOL)})"
        u = rng.choice([I64, I64, BOOL])
        op = rng.choice(["==", "!="] + (["<", "<=", ">", ">="] if u == I64 else []))
        return f"({op} {sub(u)} {sub(u)})"


generated_1 = {}
for seed in range(6):
    text = Gen1(random.Random(seed)).module(16)
    m = parse(text, 1)
    found = check(m, 1)
    if found:
        failures.append(f"generated B17-1 module {seed} doesn't pass tier 0, a generator bug: {found[:3]}")
        continue
    generated_1[f"generated1-{seed}"] = m
    sources[f"generated1-{seed}"] = r.emit(m, 1)


# Every emitted crate forbids unsafe code, has no unsafe code, and is emitted the same way twice.

for name, source in sources.items():
    assert source.splitlines()[2] == "#![forbid(unsafe_code)]", name
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', source)  # names in string literals aren't code
    assert not re.search(r"(?<![#\w])unsafe(?!_code)\b", code), name
for name, m in list(programs.items())[:3] + [("corners", CORNERS)]:
    assert r.emit(m, subset=0) == sources[name], name
assert "        } else if x < 10 {\n            return 1;\n" in sources["corners"]  # chains read as written
for name, m in [("corners1", CORNERS_1), ("suite1-trie_insert", programs_1["suite1-trie_insert"])]:
    assert r.emit(m, 1) == sources[name], name

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


def expected(m, binary, expect, label, subset=0):
    """Each line of expect: a run, then what the interpreter and the binary must both print."""
    runs = [(w[0], w[1:]) for w in (words(line) for line, _ in expect)]
    for (line, want), (name, args), got in zip(expect, runs, r.batch(binary, runs, timeout=120)):
        try:
            values = [i.value(m, a, subset) for a in args]
        except (ValueError, ParseError):
            values = None
        text = "refused" if values is None else interpreted(m, name, values, subset)
        if want.startswith("refused"):
            ok = text == "refused" and got.startswith(want)
        else:
            ok = text == got and (re.fullmatch(want, got, re.S) is not None if "err " in want else got == want)
        if not ok:
            failures.append(f"{label}: {line}\n    expected:    {want!r}\n    interpreter: {text!r}\n    rust:        {got!r}")


expected(CORNERS, binaries["corners"], EXPECT, "corners")


# B17-1's runs: the suite on its own examples and on random inputs, the corners, and the
# generated programs. The proof rejects' runs reach the faults their labels name (§8).
for name, m in programs_1.items():
    differential(m, binaries[name], named_1.get(name, []) + cases(m, random.Random(name), 40, 1), name, subset=1)
assert interpreted(programs_1["suite1-E-PROOF-BOUNDS-replace-out-of-range"], "swap_in", [(), 5], 1) == \
    "err BOUNDS at def swap_in/2.2.3.1@13:27: (idx v 0) on a vector of length 0"
assert interpreted(programs_1["suite1-E-PROOF-FIELD-wrong-constructor"], "root", [LEAF], 1) == \
    "err FIELD at def root/2.1.1@12:19: a leaf value has no field val"
for name, m in generated_1.items():
    differential(m, binaries[name], cases(m, random.Random(name), 25, 1), name, subset=1)
differential(CORNERS_1, binaries["corners1"], cases(CORNERS_1, random.Random(11), 30, 1), "corners1", subset=1)
expected(CORNERS_1, binaries["corners1"], EXPECT_1, "corners1", 1)
# A list a million long, past what the interpreter's steps allow: Rust drops it by recursion,
# which the run's stack holds (D96).
assert r.batch(binaries["corners1"], [("chain", ["1000000", "false"]), ("chain", ["1000000", "true"])],
               timeout=120) == ["ok 1000000"] * 2
# A command-line argument is one term, as for the interpreter: two can't start a run (D96).
for arg in ["(circ 3) (dot)", "3 4", "(circ 3))"]:
    p = subprocess.run([str(binaries["corners1"]), "area", arg], capture_output=True, text=True)
    assert p.returncode == 2 and p.stdout == "" and "is not a value of type sh" in p.stderr, (arg, p)


# 5. What emit() refuses (D96).

for bad, why in [
    (module("(spec f (params (x i64)) (returns (r i64)) (effects))", "(def f (body (return (+ x true))))"),
     "doesn't pass tier 0: 3:27: E-TYPE-001"),
    (module("(spec g (params (x i64)) (returns (r i64)) (effects))",
            "(spec f (params (x i64)) (returns (r i64)) (requires true) (effects))",
            "(def f (body (let ((y i64)) (call g x)) (return y)))"), "g is a spec with no def"),
]:
    try:
        r.emit(bad, subset=0)
    except ValueError as e:
        assert why in str(e), e
    else:
        failures.append(f"emitted a module it should refuse: {why}")
# A module with no defs is a crate whose driver knows no names.
empty = r.build(r.emit(module("(ghost-fn twice ((x int)) int (body (* 2 x)))"), subset=0), TMP / "empty", flags=STRICT)
assert r.batch(empty, [("twice", ["1"])]) == ["refused: no def named 'twice'"]
# Arguments that aren't UTF-8 can't start a run, on the command line or in a batch (D96).
p = subprocess.run([str(binaries["corners"]), b"\xff", b"1"], capture_output=True)
assert p.returncode == 2 and p.stdout == b"", p
p = subprocess.run([str(binaries["corners"]), "--batch"], input=b"arith \xff 1\narith 3 -2\n", capture_output=True)
lines = p.stdout.decode().split("\n")
assert p.returncode == 0 and lines[0].startswith("refused: ") and lines[1:] == ["ok 1 5 -6 -1 1 -3", ""], p

# B17-1: every tier 0 reject of its suite, among them D104's recursion at a growing instance,
# which would need infinitely many Rust types.
for p in sorted((SUITE_1 / "reject").glob("E-*.b17")):
    if not p.name.startswith("E-PROOF-"):
        try:
            r.emit(p.read_bytes(), 1)
        except (ParseError, ValueError):
            continue
        failures.append(f"emitted {p.name}, which fails tier 0")


# 6. The command line: the same text and exit code as interp.py's.

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
    want, got = cli(i.main, "--subset", "0", *argv), cli(r.main, "--subset", "0", "--run", *argv)
    assert got[:2] == want[:2], (argv, want, got)
    assert (got[2] == "") == (want[2] == ""), (argv, want, got)
code, text, _ = cli(r.main, "--subset", "0", abs_file)
assert code == 0 and text.startswith("// Emitted by b17c's Rust backend") and "pub fn abs(x: i64) -> i64" in text
assert cli(r.main, "--subset", "0", str(SUITE / "reject/E-OWN-001-use-after-move.b17"))[0] == 2
assert cli(r.main, "--subset", "0", "--run", str(SUITE / "reject/E-OWN-001-use-after-move.b17"), "f")[0] == 2
assert cli(r.main)[0] == 2 and cli(r.main, "--report", "x.json", abs_file)[0] == 2
# B17-1, with --subset 1 on both command lines (D101).
bst, root_file = str(SUITE_1 / "accept/bst_insert.b17"), str(SUITE_1 / "reject/E-PROOF-FIELD-wrong-constructor.b17")
for argv in [(bst, "insert", "(leaf)", "5"), (bst, "insert", "(node 5 (leaf) (node 9 (leaf) (leaf)))", "(+ 3 4)"),
             (bst, "insert", "(nope)", "1"), (bst, "insert", "(node 05 (leaf) (leaf))", "1"), (bst, "insert", "leaf", "1"),
             (bst, "insert", "(some 1)", "1"), (root_file, "root", "(leaf)"), (root_file, "root", "(node 4 (leaf) (leaf))"),
             (bst, "insert")]:
    want, got = cli(i.main, "--subset", "1", *argv), cli(r.main, "--subset", "1", "--run", *argv)
    assert got[:2] == want[:2], (argv, want, got)
    assert (got[2] == "") == (want[2] == ""), (argv, want, got)
code, text, _ = cli(r.main, bst)  # B17-1 is the default, the newest frozen subset (D101)
assert code == 0 and "    pub enum tree {" in text and "pub fn insert(t: data::tree, x: i64) -> data::tree {" in text, text
assert cli(r.main, "--subset", "0", bst)[0] == 2  # a data item isn't B17-0

# -o builds; --report writes the backend's fields into the trusted base report (D25, D97).
report, binary = TMP / "abs.json", TMP / "abs-cli"
report.write_text(json.dumps({"module": "abs", "input_sha256": r.sha256(r.canonical(parse(Path(abs_file).read_bytes()))),
                              "level": "L3-S"}))
assert cli(r.main, "--subset", "0", "-o", str(binary), "--report", str(report), abs_file)[0] == 0
data = json.loads(report.read_text())
assert data["level"] == "L3-S", data  # verify.py's fields stay
backend = data["backend"]
assert backend["rustc"].startswith("rustc ") and backend["target"] and backend["flags"] == list(r.FLAGS), backend
assert backend["binary_sha256"] == r.sha256(binary.read_bytes()), backend
assert backend["rust_sha256"] == r.sha256(r.emit(parse(Path(abs_file).read_bytes()), subset=0).encode()), backend
r.build(sources["suite-abs"], TMP / "abs-again")
assert (TMP / "abs-again").read_bytes() == binary.read_bytes()  # a build is reproducible
code, _, err = cli(r.main, "--subset", "0", "-o", str(binary), "--report", str(report), merge_file)
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
      f"{total:,} differential runs matched the interpreter, {compared_1[1]:,} of them B17-1's "
      f"({', '.join(f'{k} {n:,}' for k, n in sorted(compared.items()))}); "
      f"{r.toolchain()['rustc']}")
