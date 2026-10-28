"""Self-check for the tier 0 checker: uv run --no-project b17c/test_check.py"""
import io
import re
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

import check as c
from syntax import ParseError, parse

SUITE = Path(__file__).resolve().parent.parent / "suite"
HEAD = '(module m (header (purpose "p") (invariants "i") (failures "f"))'


def diagnose(text, subset=0):
    """check() on text, with a parse error as a diagnostic, as the CLI reports it."""
    try:
        return c.check(parse(text, subset), subset)
    except ParseError as e:
        return [c.Diagnostic(e.line, e.col, e.code, e.reason)]


def module(*items):
    return HEAD + "\n" + "\n".join(items) + ")"


def f(params, returns, body, clauses="", effects="", extra=()):
    """A module whose spec and def are named f, after any extra items."""
    return module(*extra, f"(spec f (params {params}) (returns {returns}) {clauses} (effects {effects}))",
                  f"(def f (body {body}))")


def at(text, snippet, skip=0):
    """The (line, column) of the character skip places into snippet's first occurrence in text."""
    i = text.index(snippet) + skip
    return text.count("\n", 0, i) + 1, i - (text.rfind("\n", 0, i) + 1) + 1


failures = []  # every case that fails, so one run shows them all


def ok(text):
    ds = diagnose(text)
    if ds:
        failures.append(f"expected no diagnostics:\n{text}\n" + "\n".join(map(str, ds)))


def bad(text, code, snippet, count=1, skip=0):
    """text has exactly count diagnostics, all code, the first skip places into snippet."""
    ds = diagnose(text)
    if [d.code for d in ds] != [code] * count or (ds[0].line, ds[0].col) != at(text, snippet, skip):
        failures.append(f"expected {count} {code} at {at(text, snippet, skip)}:\n{text}\n" + "\n".join(map(str, ds)))


# The suite's labels, exactly (§12, D44).
seen = Counter()
for path in sorted(SUITE.glob("*/*.b17")):  # B17-0's accept/ and reject/; suite/b17-1/ waits for B17-1's checker
    ds = diagnose(path.read_bytes())
    if path.parent.name == "accept" or path.name.startswith("E-PROOF-"):
        assert ds == [], (path.name, [str(d) for d in ds])
        seen["accept" if path.parent.name == "accept" else "proof"] += 1
    else:
        code = re.match(r"E-[A-Z]+-\d+", path.name).group()
        assert ds and all(d.code == code for d in ds), (path.name, [str(d) for d in ds])
        seen["parse" if code == "E-PARSE-001" else "tier 0"] += 1
assert seen == {"accept": 20, "proof": 9, "tier 0": 20, "parse": 1}, seen

# E-TYPE-001: a type mismatch.
bad(f("(x i64)", "(r i64)", "(if 1 (return x) (return x))"), "E-TYPE-001", "1 (return")
bad(f("(x i64)", "(r i64)", "(print true) (return x)", effects="io"), "E-TYPE-001", "true)")
bad(f("(x i64)", "(r i64)", "(return x x)"), "E-TYPE-001", "(return x x)")
bad(f("(x i64)", "(r i64)", "(let ((y bool)) (call g x)) (return x)",
      extra=["(spec g (params (y i64)) (returns (z i64)) (effects))"]), "E-TYPE-001", "bool)")
bad(f("(x i64)", "(r i64)", "(call g x) (return x)", extra=["(spec g (params (y i64)) (returns (z i64)) (effects))"]),
    "E-TYPE-001", "(call g x)")  # D74: results are bound, never dropped
bad(f("(x i64)", "(r i64)", "(return (f2 x))", extra=["(spec f2 (params (y i64)) (returns (z i64)) (effects))"]),
    "E-TYPE-001", "f2 x")  # a spec isn't a ghost-fn (D67)
# D53: a runtime literal must fit in i64; a ghost one is an int of any size.
bad(f("(x i64)", "(r i64)", "(return 9223372036854775808)"), "E-TYPE-001", "9223372036854775808)")
bad(f("(x i64)", "(r i64)", "(return (- x -9223372036854775809))"), "E-TYPE-001", "-9223372036854775809")
ok(f("(x i64)", "(r i64)", "(return -9223372036854775808)",
     clauses="(ensures (< r 9223372036854775808) (> (* r 99999999999999999999) -1))"))
bad(f("(x i64)", "(r i64)", "(ghost-let g i64 99999999999999999999) (return x)"), "E-TYPE-001", "9999")
# D70: ghost arithmetic is int, and int isn't i64; (multiset T) has no subtyping.
bad(f("(x i64)", "(r i64)", "(ghost-let g i64 (+ x 1)) (return x)"), "E-TYPE-001", "(+ x 1)")
bad(f("(a (vec i64))", "(r bool)", "(return true)", clauses="(ensures (== (multiset a) (multiset (seq-lit 1))))"),
    "E-TYPE-001", "(== (multiset")
G = ["(ghost-fn g ((n int)) int (body n))"]
for body, snippet in [("(let y i64 true) (return y)", "true)"), ("(return (if (> x 0) 1 true))", "(if"),
                      ("(return (len x))", "x))"), ("(return (idx x 0))", "x 0"), ("(return g)", "g)"),
                      ("(let-mut y i64 0) (push y 1) (return y)", "y 1")]:
    bad(f("(x i64)", "(r i64)", body, extra=G, effects="alloc"), "E-TYPE-001", snippet)
S = ["(spec h (params (s (ref (slice i64))) (k i64)) (returns (n i64)) (ensures (>= n 0)) (effects))"]
for body, snippet in [("(let ((n i64)) (call h (borrow a) 1 2)) (return n)", "(call h"),
                      ("(let ((n i64)) (call h (borrow s) 1)) (return n)", "s) 1)"),
                      ("(let ((n i64)) (call h a 1)) (return n)", "a 1)"),
                      ("(let ((n i64) (m i64)) (call h s 1)) (return n)", "(let ((n")]:
    bad(f("(s (ref (slice i64))) (a (vec i64))", "(r i64)", body, extra=S), "E-TYPE-001", snippet)
for clause, snippet in [("(== (take x 0) (seq-lit))", "x 0)"),
                        ("(== (len (seq-build 2 (fn (i) (seq-lit i)))) 2)", "(seq-lit i)"),
                        ("(== (len (seq-lit (seq-lit 1))) 1)", "(seq-lit 1)"), ("(== (len (seq-lit 1 true)) 2)", "true"),
                        ("(== (len (concat (seq-lit 1) (seq-lit true))) 2)", "(concat"), ("(contains a true)", "true)"),
                        ("(== (msum a a) (multiset a))", "a a)"), ("(sorted a a)", "(sorted a a)"),
                        ("(== (msum (multiset a) (multiset (seq-lit 1))) (multiset a))", "(msum (multiset a)")]:
    bad(f("(x i64) (a (vec i64))", "(r i64)", "(return x)", clauses=f"(ensures {clause})"), "E-TYPE-001", snippet)
bad(module("(lemma l (params (n int)) (body (call g n)))", *G), "E-TYPE-001", "g n)")  # a ghost-fn isn't called
bad(f("(x i64)", "(r i64)", "(return x) (return (+ x true))"), "E-TYPE-001", "true")  # unreachable, still checked
# D68: element and binder types.
bad(f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (forall ((k i64)) true))"), "E-TYPE-001", "i64)) true")
bad(f("(a (vec int))", "(r i64)", "(return 0)"), "E-TYPE-001", "int))")
bad(f("(x i64)", "(r i64)", "(ghost-let s (seq (seq int)) (seq-lit)) (return x)"), "E-TYPE-001", "(seq int)")

# E-TYPE-002: a name error.
bad(f("(x i64)", "(r i64)", "(return y)"), "E-TYPE-002", "y)")
bad(f("(x i64)", "(r i64)", "(let g i64 x) (return x)", extra=["(ghost-fn g ((n int)) int (body n))"]),
    "E-TYPE-002", "g i64 x")  # a local may not take an item's name (D41)
bad(f("(x i64)", "(x i64)", "(return x)"), "E-TYPE-002", "(returns (x", skip=10)  # results and parameters too
bad(module("(ghost-fn sorted ((n int)) int (body n))"), "E-TYPE-002", "sorted")  # D51
bad(module("(ghost-fn g ((n int)) int (body n))", "(lemma g (params) (body))"), "E-TYPE-002", "g (params")
bad(f("(x i64)", "(r i64)", "(return x)", clauses="(requires (forall ((x int)) true))"), "E-TYPE-002", "x int))")
bad(f("(x i64)", "(r i64)", "(return x)", clauses="(requires (> r 0))"), "E-TYPE-002", "r 0)")  # results: ensures only
bad(f("(x i64)", "(r i64)", "(return r)"), "E-TYPE-002", "r)")  # ...so not in the def body either
bad(module("(def orphan (body (return)))"), "E-TYPE-002", "orphan")  # D39, at the def
bad(f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (forall ((r int)) true))"), "E-TYPE-002", "r int")
bad(f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (forall ((k int) (k int)) true))"), "E-TYPE-002",
    "k int)) true")
# D66: a local is visible to the end of the block, loop body or branch that declares it.
bad(f("(x i64)", "(r i64)", "(block (let y i64 x)) (return y)"), "E-TYPE-002", "y)")
bad(f("(x i64)", "(r i64)", "(if (> x 0) (let y i64 x) (block)) (return y)"), "E-TYPE-002", "y)")
bad(f("(x i64)", "(r i64)", "(if (> x 0) (let y i64 x) (let y i64 0)) (return x)"), "E-TYPE-002", "y i64 0")

# E-GHOST-001: a ghost binding in runtime context, or ghost code changing runtime state.
bad(f("(x i64)", "(r i64)", "(ghost-let g i64 x) (let y i64 g) (return y)"), "E-GHOST-001", "g) (return")
bad(f("(x i64)", "(r i64)", "(ghost-let-mut g int 0) (set g 1) (return x)"), "E-GHOST-001", "g 1)")
bad(f("(x i64)", "(r i64)", "(let-mut y i64 0) (ghost-set y 1) (return y)"), "E-GHOST-001", "y 1)")

# E-GHOST-002: a ghost type, ghost-only operation or ghost-fn call in runtime context.
bad(f("(x int)", "(r i64)", "(return 0)"), "E-GHOST-002", "int)")
bad(f("(x i64)", "(r (seq i64))", "(return x)"), "E-GHOST-002", "(seq i64)")
bad(f("(a (vec i64))", "(r i64)", "(return (len (seq-lit 1 2)))"), "E-GHOST-002", "(seq-lit")
bad(f("(a (vec i64)) (b (vec i64))", "(r bool)", "(return (== a b))"), "E-GHOST-002", "(== a b)")  # D71
bad(f("(x i64)", "(r bool)", "(return (in_i64 x))"), "E-GHOST-002", "(in_i64 x)")
bad(f("(a (vec i64))", "(r i64)", "(call sorted a) (return 0)"), "E-GHOST-002", "sorted a")

# E-GHOST-003: a runtime statement in ghost context.
for stmt, snippet in [("(let y i64 0)", "(let y"), ('(panic "no")', "(panic"), ("(print 1)", "(print"),
                      ("(return 1)", "(return 1)")]:
    bad(module(f"(lemma l (params (x int)) (body {stmt}))"), "E-GHOST-003", snippet)

# E-OWN-001 to 006, one case per rule of §5.
# 1. bool, i64 and slices are copied; vectors move.
ok(f("(x i64) (s (ref (slice i64)))", "(r i64)", "(let y i64 x) (let z i64 x) (let ((n i64)) (call g s)) "
     "(let ((m i64)) (call g s)) (return (+ (+ y z) (+ n m)))",
     extra=["(spec g (params (s (ref (slice i64)))) (returns (n i64)) (effects))"]))
bad(f("(a (vec i64))", "(r i64)", "(let b (vec i64) a) (let c (vec i64) a) (return 0)"), "E-OWN-001", "a) (return")
# 2. A vector moves in an owned position (let, set, owned argument, return) and nowhere else.
for body, snippet in [("(let-mut b (vec i64) (vec-new)) (set b a) (return (len a))", "a)))"),
                      ("(let ((n i64)) (call g a)) (return (len a))", "a)))"),
                      ("(let b (vec i64) a) (return (idx a 0))", "a 0)")]:
    bad(f("(a (vec i64))", "(r i64)", body, extra=["(spec g (params (v (vec i64))) (returns (n i64)) (effects))"]),
        "E-OWN-001", snippet)
ok(f("(a (vec i64))", "(r i64)", "(let n i64 (len a)) (let ((m i64)) (call g (borrow a))) (assert (> (len a) -1)) "
     "(return (+ n (+ m (idx a 0))))", extra=["(spec g (params (s (ref (slice i64)))) (returns (n i64)) (effects))"]))
# 3. Use after move is an error in runtime code only, and set makes the variable live again.
ok(f("(a (vec i64))", "(r (vec i64))", "(let-mut b (vec i64) a) (assert (== (len b) (len a))) (set b (vec-new)) "
     "(return b)", clauses="(ensures (>= (len a) 0))"))
ok(f("(a (vec i64))", "(r i64)", "(let-mut b (vec i64) a) (let c (vec i64) b) (set b (vec-new)) (return (len b))"))
bad(f("(a (vec i64))", "(r (vec i64))", "(let-mut b (vec i64) a) (let c (vec i64) b) (return b)"),
    "E-OWN-001", "(return b", skip=8)
# 4. A borrow is only ever a call argument, and slices are never stored or returned.
bad(f("(a (vec i64))", "(r i64)", "(return (len (borrow a)))"), "E-OWN-002", "(borrow a)")
bad(f("(s (ref (slice i64)))", "(r i64)", "(let t (ref (slice i64)) s) (return 0)"), "E-OWN-002", "(ref (slice i64)) s")
bad(module("(ghost-fn g ((s (ref (slice i64)))) int (body (len s)))"), "E-OWN-002", "(ref")  # D69
bad(module("(lemma l (params (x int)) (body (call l2 (borrow x))))", "(lemma l2 (params (x int)) (body))"),
    "E-OWN-002", "(borrow x)")
# 5. Only let-mut locals change.
for body, snippet in [("(let v (vec i64) (vec-new)) (push v 1) (return v)", "v 1)"),
                      ("(set-idx a 0 1) (return a)", "a 0 1"), ("(push a 1) (return a)", "a 1)")]:
    bad(f("(a (vec i64))", "(r (vec i64))", body, effects="alloc"), "E-OWN-003", snippet)
bad(f("(x i64)", "(r i64)", "(ghost-let g int 0) (ghost-set g 1) (return x)"), "E-OWN-003", "g 1)")
# 6. Branches join, ignoring paths that return or panic; a loop body leaves outer variables as it found them.
for branches in ["(let b (vec i64) a) (block)", "(block) (let b (vec i64) a)"]:
    bad(f("(a (vec i64)) (c bool)", "(r i64)", f"(if c {branches}) (return (len a))"), "E-OWN-001", "a)))")
ok(f("(a (vec i64)) (c bool)", "(r (vec i64))", "(if c (return a) (block)) (return a)"))
ok(f("(a (vec i64)) (c bool)", "(r (vec i64))", '(if c (block) (panic "no")) (return a)', effects="panic"))
loop = ("(let-mut v (vec i64) a) (let-mut i i64 0) (while (< i 3) (invariant true) (decreases (- 3 i)) {} "
        "(set i (+ i 1))) (return i)")
bad(f("(a (vec i64))", "(r i64)", loop.format("(let w (vec i64) v)")), "E-OWN-004", "v) (set i")
ok(f("(a (vec i64))", "(r i64)", loop.format("(let w (vec i64) v) (set v (vec-new))")))
ok(f("(a (vec i64))", "(r i64)", loop.format("(let w (vec i64) (vec-new)) (let z (vec i64) w)")))  # w is the body's own
bad(f("(a (vec i64))", "(r i64)", "(let-mut v (vec i64) a) (let w (vec i64) v) (let-mut i i64 0) "
      "(while (< i 3) (invariant true) (decreases (- 3 i)) (set v (vec-new)) (set i (+ i 1))) (return i)"),
    "E-OWN-004", "(while")  # moved before the loop, live after one pass: D76
# 7. A vector appears at most once among a call's arguments or a return's expressions (D72).
bad(f("(a (vec i64))", "(r i64)", "(let ((n i64)) (call g (borrow a) (len a))) (return n)",
      extra=["(spec g (params (s (ref (slice i64))) (k i64)) (returns (n i64)) (effects))"]), "E-OWN-005", "a))) (return")
bad(f("(a (vec i64))", "(r (vec i64)) (k i64)", "(return a (len a))"), "E-OWN-005", "a)))")
# E-OWN-006: a vector comes from a variable, (vec-new), a runtime seq-build or a call (§7, D73).
bad(f("(a (vec i64)) (c bool)", "(r i64)", "(return (len (if c a (vec-new))))"), "E-OWN-006", "(if c")
bad(f("(x i64)", "(r i64)", "(let ((n i64)) (call g (vec-new))) (return n)",
      extra=["(spec g (params (v (vec i64))) (returns (n i64)) (effects))"]), "E-OWN-006", "(vec-new)")
ok(f("(n i64)", "(r (vec i64))", "(let v (vec i64) (seq-build n (fn (i) i))) (return v)",
     clauses="(requires (>= n 0))", effects="alloc"))

# E-EFF-001: a def's effects exceed its spec's.
bad(f("(x i64)", "(r i64)", "(print x) (return x)"), "E-EFF-001", "(print")
bad(f("(x i64)", "(r i64)", '(panic "no")'), "E-EFF-001", "(panic")
bad(f("(n i64)", "(r (vec i64))", "(return (seq-build n (fn (i) i)))"), "E-EFF-001", "(seq-build")
bad(f("(x i64)", "(r i64)", "(let ((y i64)) (call g x)) (return y)",
      extra=["(spec g (params (x i64)) (returns (y i64)) (effects io))"]), "E-EFF-001", "(call g")
ok(f("(x i64)", "(r i64)", "(let ((y i64)) (call g x)) (print y) (return y)", effects="io",
     extra=["(spec g (params (x i64)) (returns (y i64)) (ensures (== y x)) (effects io))"]))

# E-RET-001: a path that doesn't end in return or panic (D40).
bad(f("(x i64)", "(r i64)", "(let-mut i i64 0) (while (< i x) (invariant true) (decreases (- x i)) (return i))"),
    "E-RET-001", "(body")  # D77: a while loop may always end normally
bad(f("(x i64)", "(r i64)", "(if (> x 0) (block (return 1)) (let y i64 0))"), "E-RET-001", "(body")

# E-TERM-001: a recursive call from an item with no decreases.
bad(module("(spec f (params (n i64)) (returns (r i64)) (effects))",
           "(def f (body (let ((r i64)) (call f n)) (return r)))"), "E-TERM-001", "(call f n)")
bad(module("(lemma l (params (n int)) (body (call l n)))"), "E-TERM-001", "(call l n)")
ok(module("(lemma l (params (n int)) (requires (>= n 0)) (decreases n) (body (if (> n 0) (call l (- n 1)) (block))))"))

# E-TERM-002: mutual recursion, reported once per cycle.
bad(module("(ghost-fn a ((n int)) int (decreases n) (body (b n)))",
           "(ghost-fn b ((n int)) int (decreases n) (body (c n)))",
           "(ghost-fn c ((n int)) int (decreases n) (body (a n)))"), "E-TERM-002", "(b n)")
bad(module("(spec p (params (n i64)) (returns) (effects))", "(def p (decreases n) (body (call q n) (return)))",
           "(spec q (params (n i64)) (returns) (effects))", "(def q (decreases n) (body (call p n) (return)))"),
    "E-TERM-002", "(call q n)")

# D45: identical specs, after everything else passes, reported at the later one.
bad(module("(spec q (params (n i64)) (returns) (effects))", "(spec p (params (m i64)) (returns) (effects))"),
    "E-TYPE-002", "p (params")
# ...however long the chain of items a spec refers to: hashing follows one item at a time.
chain = [f"(ghost-fn g{k} ((x bool)) bool (body {'(not ' * 120}(g{k + 1} x){')' * 120}))" for k in range(5)]
ok(module(*chain, "(ghost-fn g5 ((x bool)) bool (body x))"))
ok(module(*[f"(ghost-fn h{k} ((x bool)) bool (body (h{k + 1} x)))" for k in range(400)],
          "(ghost-fn h400 ((x bool)) bool (body x))"))
ok(module(*[f"(lemma l{k} (params) (body (call l{k + 1})))" for k in range(1500)], "(lemma l1500 (params) (body))"))

# Found by review: a binding isn't callable (D67), and a name declared wrongly is reported once (D78).
for text, snippet in [(f("(x i64)", "(r i64)", "(call x) (return x)"), "x) (return"),
                      (f("(x i64)", "(r i64)", "(let ((y i64)) (call x)) (return y)"), "x)) (return"),
                      (f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (x r))"), "x r)"),
                      (module("(lemma l (params (n int)) (body (call n)))"), "n)))"),
                      (f("(x i64)", "(r bool)", "(return true)", clauses="(ensures (forall ((i int)) (i i)))"), "i i)")]:
    bad(text, "E-TYPE-001", snippet)
bad(module("(def helper (body (return 1)))", "(spec f (params (x i64)) (returns (r i64)) (effects))",
           "(def f (body (let ((y i64)) (call helper x)) (return y)))"), "E-TYPE-002", "helper (body")
PAIR = ["(spec helper (params (n i64)) (returns (r i64)) (effects))", "(def helper (body (return n)))",
        "(spec f (params (x i64)) (returns (r i64)) (ensures (> r 0)) (effects))",
        "(def f (body (let ((y i64)) (call helper x)) (return y)))"]
CLASH = "(ghost-fn helper ((n int)) int (body n))"
bad(module(CLASH, *PAIR), "E-TYPE-002", "helper (params")  # either order: once, at the later declaration
bad(module(*PAIR, CLASH), "E-TYPE-002", "helper ((n int)) int")
bad(module(CLASH, *PAIR[:2], "(spec f (params (x i64)) (returns (r bool)) (ensures (== r (== helper 0))) (effects))"),
    "E-TYPE-002", "helper (params")  # nor as a value
for body, snippet in [("(call nope x) (return x)", "nope x)"), ("(let ((y i64)) (call nope x)) (return y)", "nope x)")]:
    bad(f("(x i64)", "(r i64)", body), "E-TYPE-002", snippet)
bad(f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (nope r))"), "E-TYPE-002", "nope r")
bad(module("(spec sorted (params (a (vec i64))) (returns) (effects))", "(def sorted (body (return)))",
           "(spec f (params (a (vec i64))) (returns) (effects))", "(def f (body (call sorted a) (return)))"),
    "E-TYPE-002", "sorted (params")
bad(f("(a (vec i64))", "(r i64)", "(let ((n i64)) (call g (borrow a))) (return n)",
      extra=["(spec g (params (k i64)) (returns (n i64)) (ensures (> n k)) (effects))"]), "E-OWN-002", "(borrow a)")
bad(f("(x i64)", "(r i64)", "(let y i64 0) (let y bool true) (return (+ y 1))"), "E-TYPE-002", "y bool")
bad(f("(x i64)", "(r (vec i64))", "(let-mut v (vec i64) (vec-new)) (push v 1) (push v 2) (push v 3) (return v)"),
    "E-EFF-001", "(push v 1)")
assert len(diagnose((SUITE / "reject/E-OWN-002-slice-in-let.b17").read_bytes())) == 1
ok(f("(x i64)", "(r i64)", "(ghost-let s (seq i64) (seq-lit 1 2)) (call l (seq-lit x)) (return x)",
     extra=["(lemma l (params (s (seq i64))) (body))", "(ghost-fn z () (seq i64) (body (seq-lit 0)))"]))
bad(f("(x i64)", "(r i64)", "(ghost-let s (seq i64) (seq-lit 9223372036854775808)) (return x)"), "E-TYPE-001", "9223")

# What passes: the rules most easily over-applied.
# i64 <: int in ghost code: in contracts, ghost locals, ghost-fn calls and lemma calls (§3).
ok(f("(x i64)", "(r i64)", "(ghost-let g int x) (assert (== g (+ x 0))) (call l x (+ x 1)) (return x)",
     clauses="(requires (in_i64 (+ x 1))) (ensures (== (twice r) (* 2 x)))",
     extra=["(ghost-fn twice ((n int)) int (body (* 2 n)))", "(lemma l (params (a int) (b int)) (body))"]))
ok(f("(a (vec i64))", "(r bool)", "(return true)",
     clauses="(ensures (sorted (concat a (seq-lit 1))) (== (take a 0) (seq-lit)) (contains a (len a)))"))
# A def local may reuse its result's name, and sibling quantifiers a binder's name (§2).
ok(f("(a (ref (slice i64)))", "(out (vec i64))", "(let-mut out (vec i64) (vec-new)) (push out 1) (return out)",
     clauses="(ensures (forall ((i int)) (=> (and (<= 0 i) (< i (len out))) (== (idx out i) 1))) "
             "(forall ((i int)) (=> (and (<= 0 i) (< i (len a))) (contains a (idx a i)))))", effects="alloc"))
# A lemma call with runtime arguments; an early return inside a loop; several results (D40, D43).
ok(f("(a (ref (slice i64))) (key i64)", "(r i64)",
     "(let-mut i i64 0) (while (< i (len a)) (invariant (and (<= 0 i) (<= i (len a)))) (decreases (- (len a) i)) "
     "(call l i key) (if (== (idx a i) key) (return i) (block)) (set i (+ i 1))) (return -1)",
     extra=["(lemma l (params (i int) (k int)) (requires (>= i 0)) (body))"]))
ok(f("(a (vec i64))", "(n i64) (v (vec i64))", "(let ((w (vec i64)) (k i64)) (call g a)) (return k w)",
     extra=["(spec g (params (a (vec i64))) (returns (b (vec i64)) (k i64)) (effects))",
            "(def g (body (let k i64 (len a)) (return a k)))"]))
# Reported once, not again at every later use or step (no cascades).
assert [d.code for d in diagnose(f("(x i64)", "(r i64)", "(let y i64 (+ x true)) (let z i64 y) (return (+ z w))"))] \
    == ["E-TYPE-001", "E-TYPE-002"]
assert [d.code for d in diagnose(f("(a (vec i64))", "(r i64)",
                                   "(let b (vec i64) a) (let c i64 (len a)) (return (idx a 0))"))] == ["E-OWN-001"]
assert diagnose(module("(def orphan (body (return (+ x y))))")) == diagnose(module("(def orphan (body (return)))"))

# Found in review: an element of an open-typed literal is never a collection, a local's move
# record ends with its scope, and a borrow for a non-slice parameter is misplaced (D69).
bad(module("(spec f (params) (returns (r (vec i64))) (effects))", "(def f (body (return (idx (vec-new) 0))))"),
    "E-TYPE-001", "(idx (vec-new) 0)")
bad(module("(ghost-fn g () bool (body (contains (seq-lit) (seq-lit 1))))"), "E-TYPE-001", "(seq-lit 1)")
bad(module("(ghost-fn g () int (body (occurrences (seq-lit) (seq-lit 1))))"), "E-TYPE-001", "(seq-lit 1)")
ok(f("", "(r (vec i64))", "(block (let a (vec i64) (vec-new)) (let b (vec i64) a)) (return (seq-build 1 (fn (a) a)))",
     effects="alloc"))
ok(f("(x i64)", "(r i64)", "(let y i64 (idx (vec-new) 0)) (return y)"))  # an absurd but well-typed read
ok(module("(ghost-fn g () bool (body (=> false (== (last (seq-lit)) 5))))"))
# A malformed type is a type error even in a runtime place; only a well-formed one is a ghost type (D68).
bad(f("(x (seq (seq int)))", "(r i64)", "(return 0)"), "E-TYPE-001", "(seq int)")

# types() agrees with check(): the core library is typed in its own scope, so an item may
# share a name with one of its binders, as with sorted's i and j (found in WP7's review).
for name in ("i", "j", "s", "x"):
    m = parse(module(f"(spec {name} (params (n i64)) (returns (r i64)) (effects))", f"(def {name} (body (return n)))"))
    assert c.check(m) == [] and isinstance(c.types(m), dict), name
try:
    c.types(parse(f("(x i64)", "(r i64)", "(return true)")))
except ValueError as e:
    assert "E-TYPE-001" in str(e), e
else:
    failures.append("types() typed a module that fails tier 0")

# The command line.
for name, want in [("accept/abs.b17", (0, "")),
                   ("reject/E-OWN-001-use-after-move.b17",
                    (1, "E-OWN-001-use-after-move.b17:14:20: E-OWN-001: 'a' is used after it moved at 13:24 (§5)\n")),
                   ("reject/E-PARSE-001-while-without-decreases.b17", (1, "E-PARSE-001"))]:
    out = io.StringIO()
    with redirect_stdout(out):
        code = c.main([str(SUITE / name)])
    assert code == want[0] and want[1] in out.getvalue(), (name, code, out.getvalue())

# B17-1 (subset 1, D101): the suite's labels, exactly, as for B17-0 (D44).
seen = Counter()
for path in sorted((SUITE / "b17-1").rglob("*.b17")):
    ds = diagnose(path.read_bytes(), 1)
    if path.parent.name == "accept" or path.name.startswith("E-PROOF-"):
        assert ds == [], (path.name, [str(d) for d in ds])
        seen["accept" if path.parent.name == "accept" else "proof"] += 1
    else:
        code = re.match(r"E-[A-Z]+-\d+", path.name).group()
        assert ds and all(d.code == code for d in ds), (path.name, [str(d) for d in ds])
        seen["parse" if code == "E-PARSE-001" else "tier 0"] += 1
assert seen == {"accept": 10, "proof": 5, "tier 0": 40, "parse": 2}, seen


def codes1(*items):
    return sorted({d.code for d in diagnose(module(*items), 1)})


def ok1(*items):
    if ds := diagnose(module(*items), 1):
        failures.append("expected no diagnostics:\n" + "\n".join(items) + "\n" + "\n".join(map(str, ds)))


def bad1(code, *items):
    if (got := codes1(*items)) != [code]:
        failures.append(f"expected only {code}, got {got}:\n" + "\n".join(items))


TREE = "(data tree () (leaf) (node (val i64) (left tree) (right tree)))"
BOX = "(data box (a) (box (v a)))"
SETBOX = "(data bag (a) (bag (s (iset a))))"
spec = lambda name, params, results, effects="": f"(spec {name} (params {params}) (returns {results}) (effects {effects}))"
# Types (docs/b17-1.md §3): what's runtime, well-formed and copied, and the subtyping it allows.
ok1(TREE, BOX, "(ghost-fn g ((b (box i64)) (c (box (tuple int (seq tree))))) bool (body true))")
bad1("E-GHOST-002", BOX, spec("f", "(b (box int))", "(r i64)"))  # (box int) is a ghost type
bad1("E-GHOST-002", spec("f", "(s (iset i64))", "(r i64)"))
bad1("E-TYPE-002", spec("f", "(t nowhere)", "(r i64)"))
bad1("E-TYPE-001", "(data wrap (a) (wrap (xs (vec a))))", "(ghost-fn g ((w (wrap int))) bool (body true))")
ok1("(data wrap (a) (wrap (xs (vec a))))", "(ghost-fn g ((w (wrap (option i64)))) bool (body true))")
bad1("E-TYPE-002", "(data pair (a a) (pair (x a)))")  # a parameter twice
ok1(BOX, "(ghost-fn g ((b (box i64))) (box int) (body b))")  # covariant (§3)
bad1("E-TYPE-001", SETBOX, "(ghost-fn g ((b (bag i64))) (bag int) (body b))")  # invariant: a set holds it
bad1("E-TYPE-001", "(ghost-fn g ((p (tuple i64 bool))) (tuple int int) (body p))")
ok1("(ghost-fn g ((p (tuple i64 bool))) (tuple int bool) (body p))")
ok1("(data rose () (rose (kids (seq rose))))")  # a sequence may be empty: a finite value (§3)
# Names (D82): types and values apart; constructors are value names; fields per type.
ok1("(data tree () (mk (val i64)))", "(ghost-fn tree_val ((tree tree)) int (body (field tree val)))")
bad1("E-TYPE-002", TREE, spec("f", "(leaf i64)", "(r i64)"))  # a parameter takes a constructor's name
bad1("E-TYPE-002", TREE, "(data shrub () (leaf))")
bad1("E-TYPE-002", "(data cell () (cell (some i64)))", "(data opt () (some))")
bad1("E-TYPE-001", TREE, "(ghost-fn g () tree (body leaf))")  # a constructor isn't a value: (leaf) is
ok1(TREE, "(data pair () (pair (val i64) (left bool)))")  # field names may repeat across types
bad1("E-TYPE-002", TREE, "(ghost-fn g ((t tree)) int (body (match t (case (leaf) 0) (case (node v v r) 0))))")
# Expressions (§4, §7).
ok1(TREE, "(ghost-fn g ((t tree)) bool (body (and (is node t) (== (rank t) (rank t)))))")
bad1("E-TYPE-001", TREE, "(ghost-fn g ((t tree)) int (body (match t (case (leaf) 0) (case (node v l r) false))))")
bad1("E-TYPE-001", TREE, "(ghost-fn g ((t tree)) int (body (match t (case (leaf) 0) (case (node v l r) v) (case (leaf) 0))))")
bad1("E-TYPE-001", "(ghost-fn g ((x int)) int (body (field x val)))")
bad1("E-TYPE-001", "(ghost-fn g ((x int)) bool (body (is some x)))")
bad1("E-TYPE-001", "(ghost-fn g ((p (tuple int int))) int (body (match p (case (tuple a b c) a))))")
ok1("(ghost-fn g ((p (tuple int bool))) int (body (match p (case (tuple a b) (if b a 0)))))")
ok1("(ghost-fn g ((o (option int))) int (body (if (is some o) (field o value) 0)))",
    "(ghost-fn h () (option int) (body (none)))", "(ghost-fn k () (option int) (body (some 3)))")
bad1("E-TYPE-001", "(ghost-fn k () (option bool) (body (some 3)))")
ok1("(ghost-fn g ((s (iset int)) (m (map int bool))) bool (body (and (contains (union s (iset-lit 1 2)) 3) "
    "(lookup (update m 1 true) 1))))")
bad1("E-TYPE-001", "(ghost-fn g ((s (iset int)) (m (map int int))) bool (body (== (union s m) s)))")
bad1("E-TYPE-001", "(ghost-fn g ((m (map int int))) bool (body (lookup m 1)))")
ok1("(ghost-fn g () (iset int) (body (iset-of ((x int)) (> x 0))))", "(ghost-fn h () (map int int) (body (map-lit (1 2) (3 4))))")
bad1("E-TYPE-001", "(ghost-fn g () (map int int) (body (map-lit (1 2) (3 true))))")
ok1(BOX, "(ghost-fn g () bool (body (forall ((b (box (seq (tuple int bool))))) (== b b))))")  # exact (D90)
bad1("E-TYPE-001", TREE, "(ghost-fn g () bool (body (forall ((t tree)) true)))")  # an i64 field
bad1("E-GHOST-002", TREE, spec("f", "(t tree)", "(r bool)"), "(def f (body (return (== t t))))")
bad1("E-GHOST-002", spec("f", "(x i64)", "(r bool)"), "(def f (body (return (contains (iset-lit 1) x))))")
# Ownership (§5): trees move, an i64 option is copied, and places only read.
SPEC_T = spec("f", "(t tree)", "(r tree)")
bad1("E-OWN-001", TREE, SPEC_T, "(def f (body (let u tree t) (return t)))")
ok1(TREE, spec("f", "(o (option i64))", "(r (option i64))"), "(def f (body (let p (option i64) o) (return o)))")
bad1("E-OWN-001", TREE, SPEC_T, "(def f (body (match t (case (leaf) (block)) (case (node v l r) (return l))) (return t)))")
ok1(TREE, SPEC_T, "(def f (body (match t (case (leaf) (return (leaf))) (case (node v l r) (return l)))))")
bad1("E-OWN-004", TREE, spec("f", "(t tree) (n i64)", "(r tree)"),
     "(def f (body (let-mut i i64 0) (while (< i n) (invariant true) (decreases (- n i)) (let u tree t) (set i (+ i 1))) "
     "(return (leaf))))")
bad1("E-OWN-006", TREE, spec("f", "(t tree)", "(r bool)", "alloc"), "(def f (body (return (is node (node 1 t (leaf))))))")
ok1(TREE, spec("f", "(x i64)", "(r tree)", "alloc"), "(def f (body (let t tree (node x (leaf) (leaf))) (return t)))")
bad1("E-OWN-007", TREE, "(data pair () (pair (fst tree) (snd tree)))", spec("f", "(p pair)", "(r tree)"),
     "(def f (body (return (field p fst))))")
ok1(TREE, "(data pair () (pair (fst tree) (snd tree)))", spec("f", "(p pair)", "(r tree)"),
    "(def f (body (let-mut q pair p) (let a tree (replace (field q fst) (leaf))) (return a)))")
ok1(TREE, "(data pair () (pair (fst tree) (snd tree)))", spec("f", "(p pair)", "(r i64)"),
    "(def f (body (if (is node (field p fst)) (return (field (field p fst) val)) (return 0))))")
bad1("E-TYPE-001", spec("f", "(a (vec (vec i64)))", "(r (vec i64))"),
     "(def f (body (let-mut b (vec (vec i64)) a) (let c (vec bool) (replace (idx b 0) (vec-new))) (return (vec-new))))")
ok1(spec("f", "(a (vec (vec i64)))", "(r (vec (vec i64)))", "alloc"),
    "(def f (body (let-mut b (vec (vec i64)) a) (push (idx b 0) 7) (set-idx (idx b 0) 0 1) (return b)))")
bad1("E-OWN-005", TREE, spec("f", "(t tree)", "(r (tuple tree tree))"), "(def f (body (return (tuple t t))))")
bad1("E-TYPE-002", "(data opt (a) (no) (yes (x a)))")  # a copy of option (D92)
# Effects (§6): a boxed field allocates; a trie's vector of children doesn't box.
ok1("(data trie () (trie (end bool) (kids (vec (option trie)))))", spec("f", "(k (vec (option trie)))", "(r trie)"),
    "(def f (body (return (trie true k))))")
bad1("E-EFF-001", spec("f", "(n i64)", "(r (vec (option i64)))"), "(def f (body (return (seq-build n (fn (i) (none))))))")
# D99 and D100: forall statements and obtain.
ok1("(lemma l (params (k int)) (requires (> k 0)) (ensures (> (* k k) 0)) (body))",
    "(lemma m (params) (body (forall ((k int)) (call l k)) (obtain ((j int)) (> j 5)) (assert (> j 0))))")
bad1("E-TYPE-002", "(lemma m (params) (body (forall ((k int)) (call nowhere k))))")
bad1("E-TYPE-002", "(lemma m (params) (body (obtain ((k int)) (> k 0)) (obtain ((k int)) (> k 1))))")
# B17-0 keeps its rules: no data types, no nested collections, B17-1's words as names (D101).
assert [d.code for d in diagnose(module("(ghost-fn map ((field int)) int (body field))"))] == []
assert [d.code for d in diagnose(module("(ghost-fn g ((s (seq (seq int)))) int (body 0))"))] == ["E-TYPE-001"]
assert [d.code for d in diagnose(module("(ghost-fn g ((s (seq (seq int)))) int (body 0))"), 1)] == []

assert not failures, "\n\n".join(failures)
print("checker self-check passed")
