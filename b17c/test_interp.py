"""WP1a's conformance tests, run against the reference interpreter (§8, D56-D59):
uv run --no-project b17c/test_interp.py"""
import io
import itertools
import random
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import interp as i
import syntax
from syntax import _print


def parse(text, subset=0):  # B17-0's tests name their subset (D101)
    return syntax.parse(text, subset)


SUITE = Path(__file__).resolve().parent.parent / "suite"
MIN, MAX = i.MIN, i.MAX
HEAD = '(module t (header (purpose "p") (invariants "i") (failures "f"))'


def load(path):
    return parse((SUITE / path).read_bytes())


def items(m, kind):
    return [it for it in m.items[3:] if it.items[0].text == kind]


def module(*its):
    return parse(HEAD + "\n" + "\n".join(its) + ")")


def f(params, returns, body, clauses="", effects="", extra=()):
    """A module whose spec and def are named f, after any extra items."""
    return module(*extra, f"(spec f (params {params}) (returns {returns}) {clauses} (effects {effects}))",
                  f"(def f (body {body}))")


def go(m, *args, check=False, **kw):
    return i.run(m, "f", args, check=check, **kw, subset=0)


def is_ok(out, *results):
    assert isinstance(out, i.Ok), i.text_of(out)
    assert out.results == results, (out.results, results)
    return out


def is_err(out, reason):
    assert isinstance(out, i.Err) and out.reason == reason, i.text_of(out)
    return out


def is_contract(out, kind):
    assert isinstance(out, i.Contract) and out.kind == kind, i.text_of(out)
    return out


def at_entry(out):
    """The requires refused the input: PRE, charged to the def itself."""
    return isinstance(out, i.Contract) and out.kind == "PRE" and out.node.path == ()


def unknown(out, *kinds):
    """ok, with these clauses (by kind) left unevaluated rather than assumed (D58)."""
    assert isinstance(out, i.Ok) and [u.kind for u in out.unchecked] == list(kinds), i.text_of(out)


# Every accept program, with check=True, on inputs its requires allows, edges included: ok,
# with every contract evaluated and holding. check=False erases ghost code and agrees.
ACCEPT = {
    "abs": [((-5,), (5,)), ((0,), (0,)), ((7,), (7,)), ((MIN + 1,), (MAX,)), ((MAX,), (MAX,))],
    "all_positive": [(((),), (True,)), (((1, 2, 3),), (True,)), (((1, 0, 3),), (False,)),
                     (((MIN,),), (False,)), (((MAX,),), (True,))],
    "binary_search": [(((), 5), (-1,)), (((1, 3, 5, 7), 5), (2,)), (((1, 3, 5, 7), 4), (-1,)),
                      (((1, 3, 5, 7), 0), (-1,)), (((1, 3, 5, 7), 8), (-1,)),
                      (((MIN, 0, MAX), MAX), (2,)), (((MIN, 0, MAX), MIN), (0,))],
    "count": [(((), 1), (0,)), (((1, 2, 1, 1), 1), (3,)), (((MIN, MAX, MIN), MIN), (2,))],
    "dedup_sorted": [(((),), ((),)), (((1, 1, 2, 3, 3, 3),), ((1, 2, 3),)),
                     (((MIN, MIN, MAX),), ((MIN, MAX),)), (((5,),), ((5,),))],
    "fib": [((0,), (0,)), ((1,), (1,)), ((2,), (1,)), ((10,), (55,)), ((92,), (7540113804746346429,))],
    "find": [(((), 3), (-1,)), (((4, 3, 3), 3), (1,)), (((4,), 5), (-1,)), (((MIN,), MIN), (0,))],
    "gcd": [((0, 0), (0,)), ((12, 18), (6,)), ((18, 12), (6,)), ((0, 5), (5,)), ((5, 0), (5,)),
            ((MAX, MAX), (MAX,)), ((MAX, 1), (1,)),
            ((7540113804746346429, 4660046610375530309), (1,))],  # fib 92 and fib 91: 90 steps deep
    "insertion_sort": [(((),), ((),)), (((1,),), ((1,),)), (((3, 1, 2),), ((1, 2, 3),)),
                       (((5, 4, 3, 2, 1),), ((1, 2, 3, 4, 5),)), (((2, 2, 1, 1),), ((1, 1, 2, 2),)),
                       (((MAX, MIN, 0),), ((MIN, 0, MAX),))],
    "is_sorted": [(((),), (True,)), (((1,),), (True,)), (((1, 2, 2, 3),), (True,)), (((2, 1),), (False,)),
                  (((MIN, MAX),), (True,)), (((MAX, MIN),), (False,))],
    "isqrt": [((0,), (0,)), ((1,), (1,)), ((2,), (1,)), ((3,), (1,)), ((4,), (2,)), ((15,), (3,)),
              ((16,), (4,)), ((17,), (4,)), ((10000,), (100,))],
    "max_element": [(((5,),), (5,)), (((1, 3, 2),), (3,)), (((MIN,),), (MIN,)), (((MIN, MAX),), (MAX,)),
                    (((-3, -1, -2),), (-1,))],
    "merge_sorted": [(((), ()), ((),)), (((1, 3, 5), (2, 4, 6)), ((1, 2, 3, 4, 5, 6),)),
                     (((1, 1), (1,)), ((1, 1, 1),)), (((), (1, 2)), ((1, 2),)),
                     (((MIN,), (MAX,)), ((MIN, MAX),))],
    "min_index": [(((5,),), (0,)), (((3, 1, 2, 1),), (1,)), (((MAX, MIN),), (1,))],
    "partition": [(((), 0), ((), 0)), (((3, 1, 4, 1, 5), 3), ((1, 1, 4, 3, 5), 2)),
                  (((1, 2), MIN), ((1, 2), 0)), (((1, 2), MAX), ((1, 2), 2))],
    "power": [((2, 10), (1024,)), ((0, 0), (1,)), ((5, 0), (1,)), ((-2, 63), (MIN,)), ((2, 62), (2**62,)),
              ((3, 39), (3**39,)), ((MIN, 1), (MIN,)), ((-1, 1001), (-1,))],
    "prefix_sums": [(((),), ((0,),)), (((1, 2, 3),), ((0, 1, 3, 6),)), (((MAX, MIN),), ((0, MAX, -1),))],
    "reverse_in_place": [(((),), ((),)), (((1,),), ((1,),)), (((1, 2),), ((2, 1),)),
                         (((1, 2, 3),), ((3, 2, 1),)), (((MIN, 0, MAX),), ((MAX, 0, MIN),))],
    "reverse": [(((),), ((),)), (((1,),), ((1,),)), (((1, 2),), ((2, 1),)), (((1, 2, 3),), ((3, 2, 1),)),
                (((MIN, 0, MAX),), ((MAX, 0, MIN),))],
    "sum": [(((),), (0,)), (((1, 2, 3),), (6,)), (((MAX, MIN),), (-1,)), (((MIN,),), (MIN,))],
}
# Inputs each requires rules out: with check=True, the run stops on entry with PRE.
OUTSIDE = {
    "abs": [(MIN,)], "binary_search": [((3, 1), 1)], "dedup_sorted": [((2, 1),)], "fib": [(-1,), (93,)],
    "gcd": [(-1, 5)], "isqrt": [(-1,)], "max_element": [((),)], "merge_sorted": [((2, 1), ())],
    "min_index": [((),)], "power": [(2, -1), (2, 63), (3, 40)], "prefix_sums": [((MAX, 1),)],
    "sum": [((MAX, 1),)],
}
# dedup_sorted's "same elements" clauses quantify over every int, so they're never evaluated (D58).
DEDUP_UNCHECKED = {("INV-ENTRY", (2, 3, 4, 1)), ("INV-KEEP", (2, 3, 4, 1)), ("POST", (5, 2))}


def accepts(name, out):
    if name == "dedup_sorted":
        got = {(u.kind, u.clause.path) for u in out.unchecked}
        assert ("POST", (5, 2)) in got and got <= DEDUP_UNCHECKED, i.text_of(out)
    else:
        assert out.unchecked == (), i.text_of(out)


assert sorted(ACCEPT) == sorted(p.stem for p in (SUITE / "accept").glob("*.b17"))
for name, cases in ACCEPT.items():
    m = load(f"accept/{name}.b17")
    (d,) = [it.items[1].text for it in items(m, "def")]
    for args, want in cases:
        out = is_ok(i.run(m, d, args, check=True, subset=0), *want)
        accepts(name, out)
        assert i.run(m, d, args, subset=0) == i.Ok(want, out.trace), (name, args)
    for args in OUTSIDE.get(name, []):
        assert at_entry(i.run(m, d, args, check=True, subset=0)), (name, args)

# And on random inputs, keeping those the requires allows. Sorted half the time, so that
# the sorted-input programs get some.
rng = random.Random(17)
EDGES = (MIN, MIN + 1, -1, 0, 1, MAX - 1, MAX)


def draw(t):
    if t == "i64":
        return rng.choice(EDGES) if rng.random() < 0.25 else rng.randint(-4, 4)
    xs = [draw("i64") for _ in range(rng.randint(0, 6))]
    return tuple(sorted(xs) if rng.random() < 0.5 else xs)


ORACLE = {  # results computed another way, where the spec fixes them
    "all_positive": lambda a: (all(x > 0 for x in a),),
    "count": lambda a, x: (a.count(x),),
    "dedup_sorted": lambda a: (tuple(sorted(set(a))),),
    "find": lambda a, k: (a.index(k) if k in a else -1,),
    "insertion_sort": lambda a: (tuple(sorted(a)),),
    "is_sorted": lambda a: (list(a) == sorted(a),),
    "max_element": lambda a: (max(a),),
    "merge_sorted": lambda a, b: (tuple(sorted(a + b)),),
    "min_index": lambda a: (a.index(min(a)),),
    "prefix_sums": lambda a: (tuple(itertools.accumulate(a, initial=0)),),
    "reverse": lambda a: (a[::-1],),
    "reverse_in_place": lambda a: (a[::-1],),
    "sum": lambda a: (sum(a),),
}
for name in [*ORACLE, "binary_search", "partition"]:
    m = load(f"accept/{name}.b17")
    (spec,) = items(m, "spec")
    types = [_print(p.items[1]) for p in spec.items[2].items[1:]]
    kept = 0
    for _ in range(40):
        args = tuple(draw("i64" if t == "i64" else "seq") for t in types)
        out = i.run(m, name, args, check=True, subset=0)
        if at_entry(out):
            continue
        kept += 1
        assert isinstance(out, i.Ok), (name, args, i.text_of(out))
        accepts(name, out)
        if name in ORACLE:
            assert out.results == ORACLE[name](*args), (name, args, out.results)
    assert kept >= 8, (name, kept)

# §8, one rule at a time. Integers: i64 arithmetic, with every err case and the edges just inside.
arith = {op: f("(a i64) (b i64)", "(r i64)", f"(return ({op} a b))") for op in "+-*/%"}
for op, a, b, want in [
        ("+", MAX, 0, MAX), ("+", MAX, 1, "OVERFLOW"), ("+", MIN, -1, "OVERFLOW"),
        ("-", MIN, 0, MIN), ("-", MIN, 1, "OVERFLOW"), ("-", 0, MIN, "OVERFLOW"), ("-", -1, MIN, MAX),
        ("*", -2**62, 2, MIN), ("*", 2**62, 2, "OVERFLOW"), ("*", MIN, -1, "OVERFLOW"), ("*", MAX, -1, MIN + 1),
        ("/", 7, 2, 3), ("/", -7, 2, -3), ("/", 7, -2, -3), ("/", -7, -2, 3),  # toward zero (D37)
        ("%", 7, 2, 1), ("%", -7, 2, -1), ("%", 7, -2, 1), ("%", -7, -2, -1),  # the dividend's sign
        ("/", MIN, 1, MIN), ("%", MIN, 1, 0), ("/", MIN, 2, -2**62), ("/", MIN, -2, 2**62),
        ("/", 1, 0, "DIV"), ("%", 1, 0, "DIV"), ("/", MIN, -1, "DIV"), ("%", MIN, -1, "DIV")]:
    out = go(arith[op], a, b)
    if isinstance(want, str):
        is_err(out, want)
    else:
        is_ok(out, want)
HELPER = ["(spec g (params (y i64)) (returns (r i64)) (effects))", "(def g (body (return y)))"]
for body in ["(let y i64 (+ x 1)) (return y)", "(print (+ x 1)) (return x)",
             "(let-mut v (vec i64) (vec-new)) (push v (+ x 1)) (return x)",
             "(let v (vec i64) (seq-build 2 (fn (i) (+ x i)))) (return x)", "(let ((y i64)) (call g (+ x 1))) (return y)"]:
    is_err(go(f("(x i64)", "(r i64)", body, effects="alloc io", extra=HELPER), MAX), "OVERFLOW")
# Operands, arguments and set-idx run left to right, so the first failure is the one reported.
is_err(go(f("(a (ref (slice i64))) (b i64)", "(r i64)", "(return (+ (idx a 3) (* b 2)))"), (), MAX), "BOUNDS")
is_err(go(f("(a (ref (slice i64))) (b i64)", "(r i64)", "(let ((r i64)) (call g (idx a 3) (* b 2))) (return r)",
            extra=["(spec g (params (x i64) (y i64)) (returns (r i64)) (effects))", "(def g (body (return x)))"]),
          (), MAX), "BOUNDS")
is_err(go(f("(a (vec i64)) (b i64)", "(r (vec i64))", "(let-mut v (vec i64) a) (set-idx v 5 (* b 2)) (return v)"),
          (1,), MAX), "OVERFLOW")  # the value runs before the index is checked...
is_err(go(f("(a (vec i64)) (b i64)", "(r (vec i64))",
            "(let-mut v (vec i64) a) (set-idx v (idx a 9) (* b 2)) (return v)"), (1,), MAX), "BOUNDS")  # ...after it
neg = f("(a i64)", "(r i64)", "(return (neg a))")
is_ok(go(neg, MAX), -MAX)
is_ok(go(neg, MIN + 1), MAX)
assert "(neg -9223372036854775808) leaves i64" in is_err(go(neg, MIN), "OVERFLOW").detail
# Ghost arithmetic is unbounded and truncates the same way (D34, D37); its only goal is b != 0.
wide = f("(a i64) (b i64)", "(r i64)", "(return a)",
         clauses="(ensures (== (- (* a 2) b) (+ (+ a a) (neg b))) (== (/ (* a 4) 4) a) (== (/ -7 2) -3)"
                 " (== (% -7 2) -1) (== (/ 7 -2) -3) (== (% 7 -2) 1)"
                 " (== (/ -9223372036854775808 -1) 9223372036854775808))")
is_ok(go(wide, MAX, MIN, check=True), MAX)
ghost_div = f("(a i64) (b i64)", "(r i64)", "(return a)", clauses="(ensures (>= (/ a b) 0))")
out = is_contract(go(ghost_div, 1, 0, check=True), "DIV")
assert out.clause.item == "spec f" and out.node.item == "spec f"

# Sequences: an index out of range, a set-idx out of range, a negative seq-build length.
index = f("(s (ref (slice i64))) (k i64)", "(r i64)", "(return (idx s k))")
is_ok(go(index, (5, 6, 7), 2), 7)
for s, k in [((5, 6, 7), 3), ((5, 6, 7), -1), ((), 0)]:
    is_err(go(index, s, k), "BOUNDS")
store = f("(a (vec i64)) (k i64)", "(r (vec i64))", "(let-mut v (vec i64) a) (set-idx v k 9) (return v)")
is_ok(go(store, (1, 2, 3), 0), (9, 2, 3))
is_err(go(store, (1, 2, 3), 3), "BOUNDS")
is_err(go(store, (), 0), "BOUNDS")
# push appends, and a moved parameter still denotes its entry value in ghost code (§5).
grow = f("(a (vec i64))", "(r (vec i64))", "(let-mut v (vec i64) a) (push v 4) (push v 5) (return v)",
         clauses="(ensures (== (len r) (+ (len a) 2)) (== (take r (len a)) a) (== (last r) 5))", effects="alloc")
is_ok(go(grow, (1,), check=True), (1, 4, 5))
# seq-build evaluates its body for exactly 0 <= i < n (D38).
build = f("(n i64)", "(r (vec i64))", "(return (seq-build n (fn (i) (* i i))))", effects="alloc")
is_ok(go(build, 4), (0, 1, 4, 9))
is_ok(go(build, 0), ())
is_err(go(build, -1), "BOUNDS")
mirror = f("(a (ref (slice i64)))", "(r (vec i64))", "(return (seq-build (len a) (fn (i) (idx a (- (- (len a) 1) i)))))",
           effects="alloc")
is_ok(go(mirror, (1, 2, 3)), (3, 2, 1))
seqs = f("(a (ref (slice i64)))", "(r bool)", "(return true)",
         clauses="(ensures (== (drop a 1) (seq-lit 2 3)) (== (take a 1) (seq-lit 1)) (== (drop a 3) (seq-lit))"
                 " (== (concat a (seq-lit 9)) (seq-lit 1 2 3 9)) (== (concat (seq-lit 9) a) (seq-lit 9 1 2 3))"
                 " (== (last a) 3) (contains a 2) (not (contains a 4)) (== (occurrences a 2) 1)"
                 " (== (occurrences (msum (multiset a) (multiset a)) 2) 2) (== (multiset a) (multiset (seq-lit 3 1 2))))")
is_ok(go(seqs, (1, 2, 3), check=True), True)
for clause, a in [("(== (take a 4) a)", (1, 2, 3)), ("(== (drop a -1) a)", (1,)), ("(== (last a) 0)", ())]:
    is_contract(go(f("(a (ref (slice i64)))", "(r bool)", "(return true)", clauses=f"(ensures {clause})"), a,
                   check=True), "BOUNDS")
ghost_build = f("(n i64)", "(r i64)", "(return n)", clauses="(ensures (== (len (seq-build n (fn (i) i))) n))")
is_ok(go(ghost_build, 3, check=True), 3)
is_contract(go(ghost_build, -1, check=True), "BOUNDS")

# and, or and => decide on their left operand when they can; so does an if expression.
for expr, s, want in [("(and false (== (idx s 0) 0))", (), False), ("(or true (== (idx s 0) 0))", (), True),
                      ("(=> false (== (idx s 0) 0))", (), True), ("(and (> (len s) 0) (== (idx s 0) 0))", (), False),
                      ("(and (> (len s) 0) (== (idx s 0) 0))", (0,), True),
                      ("(if (== (len s) 0) true (== (idx s 0) 0))", (), True)]:
    is_ok(go(f("(s (ref (slice i64)))", "(r bool)", f"(return {expr})"), s), want)
is_err(go(f("(s (ref (slice i64)))", "(r bool)", "(return (and true (== (idx s 0) 0)))"), ()), "BOUNDS")

# panic ends the run with its message, keeping what was printed.
boom = f("(n i64)", "(r i64)", '(print n) (if (> n 0) (panic "too big") (block)) (return n)', effects="panic io")
assert go(boom, 1) == i.Panic("too big", (1,))
assert go(boom, 0) == i.Ok((0,), (0,))
# Every outcome keeps what was printed, and what couldn't be checked, before it stopped.
noisy = f("(x i64)", "(r i64)", "(print 1) (assert (forall ((z int)) (== z z))) (print 2) (return (+ x 1))",
          clauses="(ensures (== r x))", effects="io")
for out in [is_err(go(noisy, MAX, check=True), "OVERFLOW"), is_contract(go(noisy, 0, check=True), "POST")]:
    assert out.trace == (1, 2) and [u.kind for u in out.unchecked] == ["ASSERT"], i.text_of(out)
# print appends to the trace in execution order, across calls.
show = module("(spec show (params (n i64)) (returns) (effects io))",
              "(def show (body (print (* n 10)) (return)))",
              "(spec f (params (n i64)) (returns (r i64)) (effects io))",
              "(def f (body (let-mut i i64 0) (while (< i n) (invariant true) (decreases (- n i))"
              " (print i) (call show i) (set i (+ i 1))) (print -1) (return i)))")
assert go(show, 3, check=True) == go(show, 3) == i.Ok((3,), (0, 0, 1, 10, 2, 20, -1))
# Several results, returned together and bound one name each (D43).
pair = module("(spec split (params (a (vec i64))) (returns (v (vec i64)) (k i64)) (ensures (== v a) (== k (len a)))"
              " (effects))",
              "(def split (body (let k i64 (len a)) (return a k)))",
              "(spec f (params (a (vec i64))) (returns (k i64) (v (vec i64))) (ensures (== k (len a)) (== v a))"
              " (effects))",
              "(def f (body (let ((w (vec i64)) (n i64)) (call split a)) (return n w)))")
is_ok(go(pair, (4, 5, 6), check=True), 3, (4, 5, 6))
# An early return leaves the loop and the def at once (D40).
early = f("(a (ref (slice i64)))", "(r i64)",
          "(let-mut i i64 0) (while (< i (len a)) (invariant (and (<= 0 i) (<= i (len a))))"
          " (decreases (- (len a) i)) (if (< (idx a i) 0) (return i) (block)) (print i) (set i (+ i 1)))"
          " (print -1) (return -1)",
          clauses="(ensures (=> (>= r 0) (< (idx a r) 0)))", effects="io")
assert go(early, (5, -2, 7), check=True) == i.Ok((1,), (0,))
assert go(early, (5, 7), check=True) == i.Ok((-1,), (0, 1, -1))

# check=True evaluates what check=False erases (D57).
clauses = f("(x i64)", "(r i64)", "(ghost-let-mut g int x) (ghost-set g (* g 2)) (assert (== g (+ x x)))"
                                  " (assert (> x 0)) (return x)",
            clauses="(requires (< x 100)) (ensures (== r x))")
is_ok(go(clauses, 0), 0)
is_ok(go(clauses, 500), 500)
is_ok(go(clauses, 5, check=True), 5)
out = is_contract(go(clauses, 0, check=True), "ASSERT")
assert out.detail == "(> x 0) is false" and out.node.path == (2, 4)
out = is_contract(go(clauses, 500, check=True), "PRE")
assert out.node.item == "def f" and out.node.path == () and out.clause.item == "spec f"
wrong = f("(x i64)", "(r i64)", "(return (+ x 1))", clauses="(ensures (== r x))")
is_ok(go(wrong, 1), 2)
out = is_contract(go(wrong, 1, check=True), "POST")
assert out.node.path == (2, 1) and out.detail == "(== r x) is false"
# A ghost-fn call checks its requires; a recursive one checks its measure (§7).
half = f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (== (half_of x) (/ x 2)))",
         extra=["(ghost-fn half_of ((n int)) int (requires (>= n 0)) (body (/ n 2)))"])
is_ok(go(half, 4, check=True), 4)
out = is_contract(go(half, -4, check=True), "PRE")
assert out.clause.item == "ghost-fn half_of" and out.node.item == "spec f"
stuck = f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (== (stuck x) 0))",
          extra=["(ghost-fn stuck ((n int)) int (decreases n) (body (if (<= n 0) 0 (stuck n))))"])
is_ok(go(stuck, 0, check=True), 0)
assert "at a recursive call from measure 1" in is_contract(go(stuck, 1, check=True), "TERM").detail
down = f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (== (down x) 0))",
         extra=["(ghost-fn down ((n int)) int (decreases n) (body (if (== n -3) 0 (down (- n 1)))))"])
assert "the measure is -1" in is_contract(go(down, 0, check=True), "TERM").detail
# ...even when the call's value is already known.
known = f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (== (+ (up 5) (up x)) 0))",
          extra=["(ghost-fn up ((n int)) int (decreases n) (body (if (>= n 5) 0 (up 5))))"])
is_ok(go(known, 5, check=True), 5)
assert "the measure is 5 at a recursive call from measure 3" in is_contract(go(known, 3, check=True), "TERM").detail
# A recursive def: its measure must stay >= 0 and drop at each recursive call.
countdown = module("(spec f (params (n i64)) (returns (r i64)) (requires (>= n 0)) (ensures (== r n)) (effects))",
                   "(def f (decreases n) (body (if (== n 0) (return 0)"
                   " (block (let ((r i64)) (call f (- n 1))) (return (+ r 1))))))")
is_ok(go(countdown, 300, check=True), 300)
is_ok(go(countdown, 300), 300)
forever = module("(spec f (params (n i64)) (returns (r i64)) (effects))",
                 "(def f (decreases n) (body (let ((r i64)) (call f n)) (return r)))")
assert is_contract(go(forever, 5, check=True), "TERM").node.path == (3, 1, 2)
out = go(forever, 5, depth=50)
assert isinstance(out, i.Limit) and out.kind == "depth"
# A call checks its requires before its measure, which may only be defined under them.
ordered = module("(spec f (params (s (ref (slice i64)))) (returns (r i64)) (requires (> (len s) 0)) (effects))",
                 "(def f (decreases (idx s 5)) (body (return 0)))")
assert at_entry(go(ordered, (), check=True))
assert is_contract(go(ordered, (1,), check=True), "BOUNDS").clause.item == "def f"
# ...so a measure that is costly or undefined outside the requires is never evaluated first.
costly = module('(ghost-fn g ((n int)) int (requires false) (decreases (len (seq-build 1000000 (fn (i) i)))) (body 0))',
                "(spec f (params) (returns (r i64)) (ensures (== (g 0) 0)) (effects))", "(def f (body (return 0)))")
assert is_contract(go(costly, check=True), "PRE")
# A recursive call inside a ghost-fn's own requires is a recursive call too.
loops = f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (g x))",
          extra=["(ghost-fn g ((n int)) bool (requires (or (<= n 0) (g n))) (decreases n) (body true))"])
is_ok(go(loops, 0, check=True), 0)
assert is_contract(go(loops, 3, check=True), "TERM").detail == "the measure is 3 at a recursive call from measure 3"
sinks = f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (g x))",
          extra=["(ghost-fn g ((n int)) bool (requires (or (<= n -5) (g (- n 1)))) (decreases n) (body true))"])
assert "the measure is -5" in is_contract(go(sinks, 3, check=True), "TERM").detail
# 0 <= callee measure is checked even when the caller's measure is unknown.
murky = module("(spec f (params (n i64)) (returns (r i64)) (effects))",
               "(def f (decreases (if (> n 0) (if (forall ((z int)) (== z z)) n n) n))"
               " (body (if (> n 0) (block (let ((r i64)) (call f -5)) (return r)) (return 0))))")
out = is_contract(go(murky, 3, check=True), "TERM")
assert out.detail == "the measure is -5 at a recursive call" and [u.kind for u in out.unchecked] == ["TERM"]
# A loop's measure must be >= 0 whenever its condition holds, and drop across each pass.
sinking = f("(n i64)", "(r i64)", "(let-mut i i64 0) (while (< i 3) (invariant true) (decreases (- 1 i))"
                                  " (set i (+ i 1))) (return i)")
is_ok(go(sinking, 0), 3)
assert is_contract(go(sinking, 0, check=True), "TERM").detail == "the measure is -1 while the loop condition holds"
# ...and only then: a negative measure once the condition fails is fine.
exits = f("(n i64)", "(r i64)", "(let-mut i i64 0) (while (< i 3) (invariant true) (decreases (- 2 i))"
                                " (set i (+ i 1))) (return i)")
is_ok(go(exits, 0, check=True), 3)
# A pass that returns leaves the loop without its invariants being checked again.
leave = f("(n i64)", "(r i64)", "(let-mut i i64 0) (while (< i n) (invariant (<= i n)) (decreases (- n i))"
                                " (set i (+ i 10)) (if (> i n) (return i) (block))) (return i)")
is_ok(go(leave, 5, check=True), 10)
# An unknown measure is recorded, once per loop.
fog = f("(n i64)", "(r i64)", "(let-mut i i64 0) (while (< i n) (invariant true)"
                              " (decreases (if (forall ((z int)) (== z z)) (- n i) 0)) (set i (+ i 1))) (return i)")
unknown(go(fog, 2, check=True), "TERM")
# A run that doesn't stop runs out of fuel, an outcome outside §8 (D59).
hang = f("(n i64)", "(r i64)", "(let-mut i i64 0) (while (< i 1) (invariant true) (decreases 1) (set i (* i 1)))"
                               " (return i)")
out = go(hang, 0, fuel=5000)
assert isinstance(out, i.Limit) and out.kind == "steps" and out.trace == ()
assert is_contract(go(hang, 0, check=True), "TERM").detail == "the measure went from 1 to 1"
# Lemma calls do nothing at run time. With check=True, a lemma's requires and ensures are
# evaluated at its arguments, in ghost context, and its body never runs (D57).
lemma = f("(x i64)", "(r i64)", "(call big (+ x 1)) (return x)",
          extra=["(lemma big (params (x int)) (requires (>= x 0)) (ensures (> x 10)) (body (assert false)))"])
is_ok(go(lemma, -5), -5)
is_ok(go(lemma, 20, check=True), 20)
is_ok(go(lemma, MAX, check=True), MAX)  # (+ x 1) is ghost: no overflow
assert is_contract(go(lemma, -5, check=True), "PRE").clause.item == "lemma big"
assert is_contract(go(lemma, 5, check=True), "POST").node.item == "def f"

# Quantifiers range over the values their guard allows (D58).


def claim(q, *args, fuel=i.FUEL, extra=()):
    return go(f("(a (ref (slice i64)))", "(r bool)", f"(assert {q}) (return true)", extra=extra), *args, check=True,
              fuel=fuel)


POSITIVE = "(forall ((i int)) (=> (and (<= 0 i) (< i (len a))) (> (idx a i) 0)))"
SOME_ZERO = "(exists ((i int)) (and (and (<= 0 i) (< i (len a))) (== (idx a i) 0)))"
INCREASING = "(forall ((i int) (j int)) (=> (and (and (<= 0 i) (< i j)) (< j (len a))) (< (idx a i) (idx a j))))"
for q, a, holds in [(POSITIVE, (1, 2), True), (POSITIVE, (1, 0), False), (POSITIVE, (), True),
                    (SOME_ZERO, (1, 0), True), (SOME_ZERO, (1, 2), False), (SOME_ZERO, (), False),
                    (INCREASING, (1, 2, 3), True), (INCREASING, (1, 3, 2), False), (INCREASING, (), True),
                    ("(forall ((k int)) (=> (and (> (len a) k) (>= k 0)) (!= (idx a k) 9)))", (1, 9), False),
                    ("(forall ((k int)) (=> (== k 1) (== (idx a k) 2)))", (1, 2), True),
                    ("(forall ((p bool)) (or p (not p)))", (), True), ("(forall ((p bool)) p)", (), False),
                    ("(exists ((p bool)) (not p))", (), True),
                    ("(exists ((p bool) (q bool)) (and (and p q) (not (== p q))))", (), False),
                    ("(and false (forall ((x int)) (== x x)))", (), False),
                    ("(or true (forall ((x int)) (== x x)))", (), True)]:
    out = claim(q, a)
    if holds:
        assert out == i.Ok((True,)), (q, a, i.text_of(out))
    else:
        assert is_contract(out, "ASSERT").detail == f"{q} is false", (q, a)
# With no range to read, a quantifier is unknown: never assumed true, and never false either.
# An unknown left operand makes and, or and => unknown, whatever the right one is.
U = "(forall ((x int)) (== x x))"
for q in ["(forall ((x int)) (!= x x))", f"(not {U})", "(forall ((i int)) (=> (<= 0 i) (> i -1)))",
          f"(and {U} false)", f"(or {U} false)", f"(=> {U} true)",
          f"(exists ((i int)) (and (and (<= 0 i) (< i 2)) {U}))"]:
    unknown(claim(q, ()), "ASSERT")
# Bounds come only from the guard's leading conjuncts that can't fail, binders fixed in order.
assert claim("(forall ((p bool) (i int)) (=> (and (<= 0 i) (< i (if p 2 1))) (>= i 0)))", ()) == i.Ok((True,))
assert claim("(exists ((p bool) (i int)) (and (and (<= 0 i) (< i (if p 2 1))) (== i 1)))", ()) == i.Ok((True,))
assert claim("(forall ((i int) (j int)) (=> (and (and (<= 0 i) (< i (len a))) (and (<= 0 j) (< j (+ i 1))))"
             " (<= j i)))", (5, 6, 7)) == i.Ok((True,))
GUARDED = "(forall ((i int)) (=> (and (and (> (len a) 0) (<= 0 i)) (< i (idx a 0))) (>= i 0)))"
assert claim(GUARDED, ()) == i.Ok((True,))  # false before the undefined (idx a 0) is reached
assert claim(GUARDED, (3,)) == i.Ok((True,))
for q in ["(forall ((i int)) (=> (and (<= 0 i) (and (> (idx a i) 0) (< i (len a)))) true))",  # idx before the bound
          "(forall ((i int)) (=> (and (<= 0 i) (and (not (contains (take a i) 9)) (< i (len a)))) true))",  # take
          "(forall ((i int)) (=> (and (<= 0 i) (and (< i (idx a 5)) (< i 0))) true))"]:  # an undefined bound
    unknown(claim(q, (1, 2)), "ASSERT")
DEEP = ["(ghost-fn deep ((n int)) int (decreases n) (body (if (<= n 0) 0 (deep (- n 1)))))"]
assert claim("(forall ((i int)) (=> (and (and (<= 0 i) (< i 0)) (< i (deep 5000))) false))", (), extra=DEEP) \
    == i.Ok((True,))  # (deep 5000) is never reached, so it isn't evaluated for a bound either
# A body that's undefined where its guard holds is a failure of the clause, not an unknown,
# and every point is evaluated, so an exists can't hide one behind an early witness.
OFF_BY_ONE = "(forall ((i int)) (=> (and (<= 0 i) (<= i (len a))) (> (idx a i) 0)))"
assert is_contract(claim(OFF_BY_ONE, (1,)), "BOUNDS").detail == "(idx s 1) on a sequence of length 1"
SOME_ONE = "(exists ((i int)) (and (and (<= 0 i) (<= i (len a))) (== (idx a i) 1)))"
for a in [(1,), (2,)]:
    assert is_contract(claim(SOME_ONE, a), "BOUNDS").detail == "(idx s 1) on a sequence of length 1"
# A ghost-fn call whose requires is unknown is itself unknown, and the requires is recorded.
VAGUE = ["(ghost-fn g ((n int)) bool (requires (or (> n 0) (forall ((z int)) (=> (>= z 0) (< z 100))))) (body true))"]
unknown(claim("(exists ((i int)) (and (and (<= 0 i) (< i 2)) (or (== i 1) (g i))))", (), extra=VAGUE), "PRE")
# A range too large to search runs out of fuel instead of passing.
HUGE = "(forall ((i int)) (=> (and (<= 0 i) (< i 1000000000000)) (>= i 0)))"
assert isinstance(claim(HUGE, (), fuel=20000), i.Limit)

# Every E-PROOF reject program shows its fault on a concrete input (§12), and only there.
PROOF = {  # label: (def, an input showing the fault, an input that doesn't)
    "OVERFLOW": ("succ", (MAX,), (0,)), "DIV": ("rem", (MIN, -1), (7, -2)),
    "BOUNDS": ("first_nonneg", ((-1,),), ((-1, 5),)), "POST": ("bad_abs", (-1,), (5,)),
    "PRE": ("caller", (-1,), (4,)), "ASSERT": ("hopeful", (0,), (1,)),
    "INV-ENTRY": ("loop_entry", (0,), None),  # its invariant is false on entry for every n
    "INV-KEEP": ("loop_keep", (1,), (0,)), "TERM": ("spin", (1,), (0,)),
}
files = sorted((SUITE / "reject").glob("E-PROOF-*.b17"))
labels = [next(k for k in PROOF if p.name.startswith(f"E-PROOF-{k}-")) for p in files]
assert sorted(labels) == sorted(PROOF), labels
for path, label in zip(files, labels):
    m = parse(path.read_bytes())
    d, bad, good = PROOF[label]
    out = i.run(m, d, bad, check=True, subset=0)
    if label in ("OVERFLOW", "DIV", "BOUNDS"):  # runtime goals: §8's err, with or without check
        is_err(out, label)
        assert i.run(m, d, bad, subset=0) == out
    else:  # ghost goals: a contract outcome, and nothing at all without check
        is_contract(out, label)
        assert isinstance(i.run(m, d, bad, subset=0), i.Ok)
    if good is not None:
        assert isinstance(i.run(m, d, good, check=True, subset=0), i.Ok), (label, good)
halves = load("reject/E-PROOF-PRE-helper-call.b17")
assert i.run(halves, "caller", (-1,), subset=0) == i.Ok((0,))  # half(-1) still runs: -1 / 2 is 0
out = i.run(halves, "caller", (-1,), check=True, subset=0)
assert (out.clause.item, out.node.item) == ("spec half", "def caller")
rem = load("reject/E-PROOF-DIV-min-rem-minus-one.b17")
assert at_entry(i.run(rem, "rem", (1, 0), check=True, subset=0))  # y != 0 is the requires' job...
is_err(i.run(rem, "rem", (1, 0), subset=0), "DIV")                # ...and §8 is stuck without it

# Interface 10's text form (D56), exactly.
assert i.text_of(go(show, 2)) == "print 0\nprint 0\nprint 1\nprint 10\nprint -1\nok 2"
assert i.text_of(go(pair, (4, 5))) == "ok 2 (seq-lit 4 5)"
assert i.text_of(go(boom, 7)) == 'print 7\npanic "too big"'
assert i.text_of(i.run(load("reject/E-PROOF-OVERFLOW-unbounded-increment.b17"), "succ", (MAX,), subset=0)) == \
    "err OVERFLOW at def succ/2.1.1@13:15: (+ 9223372036854775807 1) = 9223372036854775808 leaves i64"
assert i.text_of(out) == "contract PRE spec half/4.1@9:15 at def caller/2.1.2@21:22: (>= x 0) is false"
assert i.text_of(i.run(load("accept/dedup_sorted.b17"), "dedup_sorted", ((1, 1),), check=True, subset=0)) == (
    "unchecked INV-ENTRY def dedup_sorted/2.3.4.1@21:20 at def dedup_sorted/2.3@18:7\n"
    "unchecked INV-KEEP def dedup_sorted/2.3.4.1@21:20 at def dedup_sorted/2.3@18:7\n"
    "unchecked POST spec dedup_sorted/5.2@12:34 at def dedup_sorted/2.4@28:7\n"
    "ok (seq-lit 1)")
assert i.text_of(go(hang, 0, fuel=100)).startswith("limit steps at def f/")

# run() takes values of the spec's parameter types, and lists for sequences.
is_ok(i.run(load("accept/sum.b17"), "sum", [[1, 2]], subset=0), 3)
for bad_args in [(), (1, 2), (MAX + 1,), (True,), ((1, 2),)]:
    try:
        go(neg, *bad_args)
    except ValueError:
        pass
    else:
        raise AssertionError(bad_args)
# A call to a spec with no def can be verified, since calls are modular (§7), but can't run.
try:
    go(module("(spec helper (params (x i64)) (returns (r i64)) (effects))",
              "(spec f (params (x i64)) (returns (r i64)) (effects))",
              "(def f (body (let ((y i64)) (call helper x)) (return y)))"), 1)
except ValueError as e:
    assert "'helper' at def f/2.1.2@" in str(e) and str(e).endswith("is a spec with no def to run"), e
else:
    raise AssertionError("ran a spec with no def")

# The command line.


def cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = i.main(list(argv))
    return code, out.getvalue(), err.getvalue()


assert cli("--subset", "0", "--check", str(SUITE / "accept/abs.b17"), "abs", "-5") == (0, "ok 5\n", "")
assert cli("--subset", "0", str(SUITE / "accept/merge_sorted.b17"), "merge_sorted", "(seq-lit 1 3)",
           "(seq-build 2 (fn (i) (* i 2)))") == (0, "ok (seq-lit 0 1 2 3)\n", "")
code, text, _ = cli("--subset", "0", "--fuel", "50", str(SUITE / "accept/isqrt.b17"), "isqrt", "10000")
assert code == 1 and text.startswith("limit steps")
assert cli("--subset", "0", str(SUITE / "accept/abs.b17"), "abs", "(neg 5)")[0] == 2  # not canonical (D53)
assert cli("--subset", "0", str(SUITE / "accept/abs.b17"), "abs", "(borrow a)") \
    == (2, "", f"{SUITE / 'accept/abs.b17'}: (borrow a): 'a' isn't defined\n")
assert cli("--subset", "0", str(SUITE / "accept/abs.b17"), "nope", "1")[0] == 2
assert cli("--subset", "0", str(SUITE / "accept/abs.b17"))[0] == 2

# B17-1 (docs/b17-1.md §8), with subset=1 (D101).
D, T = i.Data, i.Tup
NONE, LEAF = D("none", ()), D("leaf", ())


def some(v):
    return D("some", (v,))


def node(v, left=LEAF, right=LEAF):
    return D("node", (v, left, right))


def seg(lo, hi, vals):
    """A segment tree over vals[lo:hi], as segmenttree_query's is_segment_tree has it."""
    if hi - lo == 1:
        return D("node", (vals[lo], lo, hi, NONE, NONE))
    left, right = seg(lo, (lo + hi) // 2, vals), seg((lo + hi) // 2, hi, vals)
    return D("node", (max(left.fields[0], right.fields[0]), lo, hi, some(left), some(right)))


def trie(*keys):
    """A trie holding keys, built by hand as trie_insert's well_formed has it."""
    kids = [NONE] * 256
    for c in sorted({k[0] for k in keys if k}):
        kids[c] = some(trie(*[k[1:] for k in keys if k and k[0] == c]))
    return D("node", (() in keys, tuple(kids)))


def m1(*its):
    return parse(HEAD + "\n" + "\n".join(its) + ")", 1)


def f1(params, returns, body, clauses="", effects="", extra=()):
    return m1(*extra, f"(spec f (params {params}) (returns {returns}) {clauses} (effects {effects}))",
              f"(def f (body {body}))")


def go1(m, *args, check=False, **kw):
    return i.run(m, "f", args, check=check, subset=1, **kw)


BST = node(5, node(2), node(9, node(7)))
SEG = seg(0, 4, [3, 1, 4, 1])
NIL = D("nil", ())
TREE = D("node", (1, D("node", (2, D("node", (4, NIL, NIL)), D("node", (5, NIL, NIL)))), D("node", (3, NIL, NIL))))
GRAPH = D("graph", (((1,), (2,), (), (0,)),))
CYCLE = D("weighted_graph", (((T((2, 1)),), (T((0, 1)),), (T((1, 1)),)),))  # 0 -> 2 -> 1 -> 0
WEIGHTED = D("weighted_graph", (((T((1, 4)), T((2, 1))), (T((0, 4)), T((2, 2))), (T((0, 1)), T((1, 2)))),))
DIJKSTRA = D("weighted_graph", (((T((1, 5)), T((2, 1))), (T((3, 0)),), (T((1, 2)),), (T((0, 7)),), ()),))  # 4 unreachable
NEG_EDGE = D("weighted_graph", (((T((1, 4)), T((2, 2))), (), (T((1, -3)),)),))  # a negative edge, no cycle
NEG_CYCLE = D("weighted_graph", (((T((1, 1)),), (T((2, -3)),), (T((1, 1)),)),))  # 1 -> 2 -> 1 weighs -2
FAR_CYCLE = D("weighted_graph", (((T((1, 2)),), (), (T((3, -1)),), (T((2, -1)),)),))  # a negative cycle 0 can't reach
FLOW = D("capacity_graph", (((T((1, 3)), T((2, 2))), (T((2, 1)), T((3, 2))), (T((3, 3)),), ()),))  # 0 to 3: 5
UNDO = D("capacity_graph", (((T((1, 1)), T((6, 1))), (T((2, 1)), T((4, 1))), (T((3, 1)),), (), (T((5, 1)),), (T((3, 1)),),
                            (T((7, 1)),), (T((2, 1)),)),))  # 0 to 3: the second path undoes the first's 1 -> 2
OPPOSITE = D("capacity_graph", (((T((1, 4)), T((0, 2))), (T((0, 3)), T((2, 2))), ()),))  # edges both ways, a self-loop
# Each accept program on inputs its requires allows: ok, and the same with check=False. The
# clauses left unchecked are those whose quantifiers range over paths, sequences, every int, or
# the members a ghost-fn's predicate picks out, which no guard bounds (D58, D102), and a proof's
# asserts that read an obtain's witness, which the run can't name (§8).
ACCEPT_1 = {  # name: (def, [(args, results)], the kinds left unchecked on the first input)
    "bst_insert": ("insert", [((LEAF, 5), (node(5),)), ((BST, 8), (node(5, node(2), node(9, node(7, LEAF, node(8)))),)),
                              ((BST, 5), (BST,))], []),
    "bst_search": ("search", [((LEAF, 5), (False,)), ((BST, 7), (True,)), ((BST, 6), (False,))], []),
    "discrete_logarithm": ("discrete_log_naive", [((2, 8, 11), (some(3),)), ((2, 3, 7), (NONE,)),
                                                  ((0, 0, 5), (some(1),)), ((3, 1, 2), (some(0),))], []),
    "longest_palindrome_substring": ("longest_palindromic_substring", [(((1, 2, 1, 3),), (T((0, 3)),)),
                                                                        (((),), (T((0, 0)),)),
                                                                        (((4, 4),), (T((0, 2)),))],
                                     ["INV-KEEP", "INV-ENTRY", "INV-KEEP", "POST"]),
    "segmenttree_query": ("query", [((SEG, 1, 3), (4,)), ((SEG, 0, 4), (4,)), ((SEG, 3, 4), (1,))], ["PRE"] * 3 + ["ASSERT"] * 2 + ["PRE"] * 2 + ["ASSERT"] * 6),
    "trie_insert": ("insert", [((NONE, (1, 2)), (trie((1, 2)),)), ((some(trie((5,))), (5, 7)), (trie((5,), (5, 7)),)),
                               ((some(trie((5,))), ()), (trie((5,), ()),))], ["POST", "ASSERT", "POST", "ASSERT", "POST", "POST"]),
    "lca": ("lowest_common_ancestor", [((TREE, 4, 5), (some(2),)), ((TREE, 4, 3), (some(1),)),
                                       ((TREE, 2, 4), (some(2),))], ["POST"] * 3),
    "bfs": ("bfs_shortest_path", [((GRAPH, 0, 2), (some(2),)), ((GRAPH, 2, 0), (NONE,)), ((GRAPH, 3, 3), (some(0),))],
            ["INV-ENTRY", "INV-ENTRY", "POST", "PRE", "PRE", "POST", "INV-KEEP", "INV-KEEP", "POST"]),
    "kruskal": ("kruskal_mst", [((WEIGHTED,), ((T((0, 2, 1)), T((1, 2, 2))),)),
                                ((CYCLE,), ((T((0, 2, 1)), T((1, 0, 1))),))],  # one-way edges, each listed once
                ["PRE", "PRE", "INV-ENTRY", "INV-ENTRY", "INV-KEEP", "INV-KEEP", "ASSERT", "POST"]),
    "prim": ("prim_mst", [((WEIGHTED,), ((T((0, 2, 1)), T((1, 2, 2))),)),
                          ((CYCLE,), ((T((0, 2, 1)), T((1, 0, 1))),)),  # an entry used from its unvisited end
                          ((D("weighted_graph", (((),),)),), ((),))],
             ["PRE", "PRE", "POST", "INV-ENTRY", "INV-ENTRY", "INV-KEEP", "INV-KEEP", "POST"]),
    "dijkstra": ("dijkstra_shortest_paths", [((DIJKSTRA, 0), ((some(0), some(3), some(1), some(3), NONE),)),
                                             ((DIJKSTRA, 4), ((NONE, NONE, NONE, NONE, some(0)),)),
                                             ((WEIGHTED, 1), ((some(3), some(0), some(2)),))],
                 ["PRE", "PRE", "INV-ENTRY", "PRE", "PRE", "PRE", "POST", "POST", "INV-KEEP", "INV-KEEP", "PRE", "INV-KEEP", "INV-KEEP",
                  "INV-ENTRY", "POST"]),
    "bellman_ford": ("bellman_ford", [((NEG_EDGE, 0), (some((some(0), some(-1), some(2))),)),
                                      ((NEG_CYCLE, 0), (NONE,)),
                                      ((FAR_CYCLE, 0), (some((some(0), some(2), NONE, NONE)),)),
                                      ((D("weighted_graph", (((T((0, -1)),),),)), 0), (NONE,))],  # a negative self-loop
                     ["PRE", "INV-ENTRY", "PRE", "POST", "INV-KEEP", "PRE", "INV-KEEP", "PRE", "POST", "INV-KEEP", "INV-KEEP",
                      "INV-ENTRY", "INV-ENTRY", "PRE", "PRE", "POST"]),
    "edmond_karp": ("max_flow_value", [((FLOW, 0, 3), (5,)), ((UNDO, 0, 3), (2,)), ((OPPOSITE, 0, 2), (2,)),
                                       ((FLOW, 3, 0), (0,)),  # nothing leaves 3
                                       ((D("capacity_graph", (((T((1, 0)),), ()),)), 0, 1), (0,))],  # a capacity of 0
                    ["PRE", "PRE", "PRE", "PRE", "PRE", "POST", "POST"]),
    "coin_change": ("coin_change", [(((1, 2, 5), 11), (3,)), (((2,), 3), (-1,)), (((3,), 0), (0,))],
                    ["ASSERT", "INV-ENTRY", "INV-ENTRY", "ASSERT", "PRE", "POST", "INV-KEEP", "PRE", "POST", "PRE", "POST", "PRE",
                     "PRE", "POST", "INV-KEEP", "ASSERT", "POST"]),
}
OUTSIDE_1 = {
    "bst_insert": [(node(5, node(7)), 1), (LEAF, -1)], "bst_search": [(node(5, LEAF, node(3)), 3)],
    "discrete_logarithm": [(2, 3, 1), (MAX, 1, 3)], "segmenttree_query": [(SEG, 2, 2), (SEG, 0, 5)],
    "trie_insert": [(NONE, (256,)), (some(trie()), (1,))], "lca": [(TREE, 4, 6)],
    "bfs": [(GRAPH, 0, 4), (D("graph", (((5,),),)), 0, 0)], "kruskal": [(D("weighted_graph", ((),)),)],
    "prim": [(D("weighted_graph", ((),)),)],
    "dijkstra": [(WEIGHTED, 3), (D("weighted_graph", (((T((0, 1)), T((0, 2))),),)), 0)],
    "bellman_ford": [(WEIGHTED, 3), (D("weighted_graph", (((T((0, 1)), T((0, -2))),),)), 0)],
    "edmond_karp": [(FLOW, 0, 0), (FLOW, 0, 4), (D("capacity_graph", (((T((1, 1)), T((1, 2))), ()),)), 0, 1)],
    "coin_change": [((), 1), ((0,), 1)],
}
assert sorted(ACCEPT_1) == sorted(p.stem for p in (SUITE / "b17-1/accept").glob("*.b17"))
for name, (d, cases, left) in ACCEPT_1.items():
    m = parse((SUITE / f"b17-1/accept/{name}.b17").read_bytes(), 1)
    for k, (args, want) in enumerate(cases):
        out = is_ok(i.run(m, d, args, check=True, subset=1), *want)
        if k == 0:
            assert [u.kind for u in out.unchecked] == left, (name, i.text_of(out))
        assert i.run(m, d, args, subset=1) == i.Ok(want, out.trace), (name, args)
    for args in OUTSIDE_1.get(name, []):
        assert at_entry(i.run(m, d, args, check=True, subset=1)), (name, args)
# B17-0's suite runs the same under subset 1: every B17-0 suite program is a B17-1 program.
for name, cases in ACCEPT.items():
    m = parse((SUITE / f"accept/{name}.b17").read_bytes(), 1)
    (d,) = [it.items[1].text for it in items(m, "def")]
    for args, _ in cases:
        assert i.run(m, d, args, check=True, subset=1) == i.run(load(f"accept/{name}.b17"), d, args, check=True, subset=0)
# ...while a B17-0 program may name a ghost-fn as B17-1 reserves (D101).
is_ok(go(f("(x i64)", "(r i64)", "(return x)", clauses="(ensures (union x))",
           extra=["(ghost-fn union ((n int)) bool (body (>= n 0)))"]), 3, check=True), 3)

# The E-PROOF rejects with a def or ghost-fn show their fault on a concrete input. A lemma's body
# never runs, and a forall statement or obtain checks nothing (§8), so the other two can't.
REJECT_1 = SUITE / "b17-1/reject"
swap = parse((REJECT_1 / "E-PROOF-BOUNDS-replace-out-of-range.b17").read_bytes(), 1)
out = is_err(i.run(swap, "swap_in", ((), 5), subset=1), "BOUNDS")
assert i.text_of(out) == "err BOUNDS at def swap_in/2.2.3.1@13:27: (idx v 0) on a vector of length 0"
is_ok(i.run(swap, "swap_in", ((1,), 5), check=True, subset=1), 1, (5,))
root = parse((REJECT_1 / "E-PROOF-FIELD-wrong-constructor.b17").read_bytes(), 1)
assert i.text_of(i.run(root, "root", (LEAF,), check=True, subset=1)) == \
    "err FIELD at def root/2.1.1@12:19: a leaf value has no field val"
is_ok(i.run(root, "root", (node(4),), subset=1), 4)
at_two = parse((REJECT_1 / "E-PROOF-BOUNDS-lookup-outside-map.b17").read_bytes(), 1)
assert i.value(at_two, "(at_two (map-lit (2 7) (2 8)))", 1) == 8  # a later key wins
try:
    i.value(at_two, "(at_two (map-lit (1 7)))", 1)
except ValueError as e:
    assert "contract BOUNDS ghost-fn at_two/4.1@7:11" in str(e), e
else:
    raise AssertionError("looked up a key outside the map")

# §8, one rule at a time. Places: an update builds the new root with one part replaced.
TRI = "(data tri () (tri (xs (vec i64)) (p (tuple i64 bool))))"
deep = f1("(a (vec (vec i64))) (t tri)", "(r (vec (vec i64))) (s tri)",
          "(let-mut v (vec (vec i64)) a) (let-mut u tri t) (set-idx (idx v 1) 0 7) (push (idx v 0) 8)"
          " (set-idx (field u xs) 0 9) (let y (tuple i64 bool) (replace (field u p) (tuple 4 false))) (return v u)",
          effects="alloc", extra=[TRI])
is_ok(go1(deep, ((1,), (2, 3)), D("tri", ((5,), T((6, True))))),
      ((1, 8), (7, 3)), D("tri", ((9,), T((4, False)))))
is_err(go1(deep, ((1,),), D("tri", ((5,), T((6, True))))), "BOUNDS")  # (idx v 1) on one element
assert "(set-idx (field u xs) 0 ...) on a vector of length 0" in \
    is_err(go1(deep, ((1,), (2,)), D("tri", ((), T((6, True))))), "BOUNDS").detail
# replace gives the old value and leaves the new one; indices and value run before the check.
taken = f1("(a (vec i64)) (k i64) (b i64)", "(r i64) (s (vec i64))",
           "(let-mut v (vec i64) a) (let y i64 (replace (idx v k) (* b 2))) (return y v)")
is_ok(go1(taken, (1, 2), 1, 5), 2, (1, 10))
is_err(go1(taken, (1,), 3, MAX), "OVERFLOW")
is_err(go1(taken, (1,), 3, 1), "BOUNDS")
# match selects its scrutinee's arm and binds the fields; is and field read them; FIELD is
# err in runtime code and a contract outcome in ghost code (§8).
TREE_T = "(data tree () (leaf) (node (val i64) (left tree) (right tree)))"
total = f1("(t tree)", "(r i64)", "(match t (case (leaf) (return 0)) (case (node v l r) (return (+ v (field l val)))))",
           extra=[TREE_T])
is_ok(go1(total, node(3, node(4))), 7)
is_ok(go1(total, LEAF), 0)
is_err(go1(total, node(3)), "FIELD")
peek = f1("(t tree)", "(r bool)", "(return (is node t))", clauses="(ensures (== (field t val) 3))", extra=[TREE_T])
is_ok(go1(peek, node(3), check=True), True)
is_contract(go1(peek, LEAF, check=True), "FIELD")
is_ok(go1(peek, LEAF), False)
pair = f1("(p (tuple i64 bool))", "(r i64)", "(return (match p (case (tuple a b) (if b a (get p 0)))))")
is_ok(go1(pair, T((4, True))), 4)
# rank is height: 0 with no data value inside, else one more than the highest inside, reached
# through vectors and tuples (§8). (none) is a data value, so flat's rank is 1.
RANKS = "(data rose () (rose (kids (vec rose)) (pair (tuple i64 (option rose)))))"
ranked = f1("(t rose)", "(r bool)", "(return true)", clauses="(ensures (== (rank t) 3) (== (rank (none)) 0))", extra=[RANKS])
flat = D("rose", ((), T((0, NONE))))
is_ok(go1(ranked, D("rose", ((flat,), T((0, some(D("rose", ((), T((1, NONE))))))))), check=True), True)
is_contract(go1(ranked, flat, check=True), "POST")
# Sets and maps are values; a set built by iset-of is its predicate, so equality with it is unknown.
SETS = ["(== (union (iset-lit 1 2) (iset-lit 2 3)) (iset-lit 3 2 1))", "(== (diff (iset-lit 1 2) (iset-lit 2)) (iset-lit 1))",
        "(== (inter (iset-lit 1 2) (iset-lit 2 3)) (iset-lit 2))", "(contains (iset-of ((x int)) (> x a)) (+ a 1))",
        "(not (contains (diff (iset-of ((x int)) (> x a)) (iset-lit (+ a 1))) (+ a 1)))",
        "(contains (union (iset-lit) (iset-of ((x int)) (== x a))) a)",
        "(== (map-lit (1 2) (1 3)) (map-lit (1 3)))", "(== (lookup (update (map-lit (1 2)) 1 5) 1) 5)",
        "(contains (map-lit (1 2)) 1)", "(not (contains (map-lit (1 2)) 2))",
        "(== (union (map-lit (1 2) (3 4)) (map-lit (1 5))) (map-lit (1 5) (3 4)))",
        "(== (multiset (seq-lit (some 1) (none) (some 1))) (multiset (seq-lit (none) (some 1) (some 1))))"]
for clause in SETS:
    is_ok(go1(f1("(a i64)", "(r i64)", "(return a)", clauses=f"(ensures {clause})"), 5, check=True), 5)
# A ghost-fn takes such a set like any value, and isn't memoized on it.
holds = ["(ghost-fn has ((s (iset int)) (y int)) bool (body (contains s y)))"]
unknown(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (has (iset-of ((x int)) (> x 0)) a) "
               "(not (has (iset-of ((x int)) (> x a)) a)))", extra=holds), 5, check=True))
# ...and a recursive call with the same such set is still caught at once (D57).
RECUR = ["(ghost-fn recur ((s (iset int))) bool (requires (recur s)) (decreases 0) (body true))"]
is_contract(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (recur (iset-of ((x int)) true)))", extra=RECUR),
                5, check=True, depth=5), "TERM")
USE = ["(ghost-fn use ((m (map int (iset int)))) bool (body (contains (lookup m 0) 1)))"]
unknown(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (use (map-lit (0 (iset-of ((x int)) (> x 0))))))",
               extra=USE), 5, check=True))
RECUR_SEQ = ["(ghost-fn recur ((s (seq (iset int)))) bool (requires (> (len s) 0)) (requires (recur (seq-lit (idx s 0))))"
             " (decreases 0) (body true))"]
is_contract(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (recur (seq-lit (iset-of ((x int)) true))))",
                   extra=RECUR_SEQ), 5, check=True, depth=6), "TERM")
# Testing a member runs inside the call that built the set: a recursive call there is one, and a
# failure there is charged to that ghost-fn's body (D57).
LOOP = ["(ghost-fn loop () (iset int) (decreases 0) (body (iset-of ((x int)) (contains (loop) x))))"]
is_contract(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (contains (loop) 0))", extra=LOOP), 5,
                check=True, fuel=200), "TERM")
LOOP_U = ["(ghost-fn loop () (iset int) (decreases (if (forall ((n int)) true) 0 0))"
          " (body (iset-of ((x int)) (contains (loop) x))))"]
is_contract(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (contains (loop) 0))", extra=LOOP_U), 5,
                check=True, fuel=200), "TERM")  # the same call as the one that built the set, even with no measure
POS = ["(ghost-fn pos ((x int)) bool (body (> x 0)))"]  # a set tested where it's built adds no depth
is_ok(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (contains (iset-of ((x int)) (pos x)) 1))", extra=POS),
          5, check=True, depth=2), 5)
BAD = ["(ghost-fn badset () (iset int) (body (iset-of ((x int)) (> (/ 1 x) 0))))"]
out = is_contract(go1(f1("(a i64)", "(r i64)", "(return a)", clauses="(ensures (contains (badset) 0))", extra=BAD), 5,
                      check=True), "DIV")
assert out.clause.item == out.node.item == "ghost-fn badset", i.text_of(out)
# A set equals itself, so a value holding it does too.
unknown(go1(f1("(a i64)", "(r i64)", "(ghost-let p (iset int) (iset-of ((x int)) true)) (assert (== p p))"
               " (assert (== (seq-lit p) (seq-lit p))) (return a)"), 5, check=True))
for clause in ["(== (iset-of ((x int)) (> x a)) (iset-of ((x int)) (> x a)))",
               "(contains (iset-lit (iset-of ((x int)) true)) (iset-lit))"]:
    unknown(go1(f1("(a i64)", "(r i64)", "(return a)", clauses=f"(ensures {clause})"), 5, check=True), "POST")
# A quantifier ranges over the members of a finite collection its guard puts a binder in, of any
# type (D102), and otherwise over B17-1's types it's unknown (D58).
for clause, a, want in [("(forall ((x int)) (=> (contains a x) (> x 0)))", (3, 1), True),
                        ("(forall ((x int)) (=> (and (contains a x) (< x 3)) (> x 1)))", (3, 1), False),
                        ("(exists ((x int)) (and (contains a x) (== x 2)))", (3, 1), False),
                        ("(forall ((s (seq int))) (=> (contains (iset-lit a (seq-lit)) s) (<= (len s) 2)))", (3, 1), True),
                        ("(forall ((p (tuple int int))) (=> (contains (iset-lit (tuple 1 2)) p) (< (get p 0) (get p 1))))",
                         (), True)]:
    claimed = f1("(a (vec i64))", "(r bool)", "(return true)", clauses=f"(ensures {clause})")
    if want:
        is_ok(go1(claimed, a, check=True), True)
    else:
        is_contract(go1(claimed, a, check=True), "POST")
# Members bound an int binder, and so the binders compared with it. A sequence's members need
# no hashing, so they may be sets kept as their predicates.
is_contract(go(f("(a i64)", "(r bool)", "(return true)",
                 clauses="(ensures (forall ((x int) (y int)) (=> (and (== x y) (contains (seq-lit 1) y)) false)))"),
               0, check=True), "POST")
unknown(go1(f1("(a i64)", "(r i64)", "(ghost-let p (iset int) (iset-of ((z int)) true))"
               " (assert (forall ((q (iset int))) (=> (contains (seq-lit p p) q) (contains q 0)))) (return a)"), 5,
            check=True))
# An empty collection makes the guard hold nowhere, whichever binder it bounds.
unknown(go1(f1("(a (vec i64))", "(r bool)", "(return true)",
               clauses="(ensures (forall ((x int) (y int)) (=> (contains (seq-lit) y) false)))"), (), check=True))
for clause in ["(forall ((s (seq int))) (=> (> (len s) 0) (>= (len s) 1)))",
               "(forall ((x int)) (=> (contains (iset-of ((y int)) (> y 0)) x) (> x 0)))"]:
    unknown(go1(f1("(a (vec i64))", "(r bool)", "(return true)", clauses=f"(ensures {clause})"), (), check=True), "POST")
# ...as in B17-0, whose sequences bound a binder the same way.
is_contract(go(f("(a (ref (slice i64)))", "(r bool)", "(return true)",
                 clauses="(ensures (forall ((x int)) (=> (contains a x) (> x 0))))"), (1, 0), check=True), "POST")
# A forall statement checks nothing. obtain finds no witness, so its ∃ is unchecked, and its
# binders are unknown to the ghost code that reads them (§8).
LEMMA = "(lemma pos (params (k int)) (requires (> k 0)) (ensures (> (* k k) 0)) (body))"
named = f1("(a i64)", "(r i64)", "(forall ((k int)) (call pos k)) (obtain ((k int)) (== k a)) (assert (== k a)) (return a)",
           extra=[LEMMA])
unknown(go1(named, 5, check=True), "ASSERT", "ASSERT")
is_ok(go1(named, 5), 5)
# A loop can build a value nested far deeper than Python's stack. It prints, compares and hashes
# all the same, so a run ends in an outcome, never a RecursionError.
DEEP = m1("(data lst () (nil) (cons (head i64) (tail lst)))",
          "(ghost-fn top ((l lst)) int (body (match l (case (nil) -1) (case (cons h t) h))))",
          "(spec two (params (n i64)) (returns (a lst) (b lst)) (requires (> n 0))"
          " (ensures (== a b) (== (top a) (- n 1)) (contains (iset-lit a) b) (!= a (cons 0 b))) (effects alloc))",
          "(def two (body (let-mut a lst (nil)) (let-mut b lst (nil)) (let-mut k i64 0)"
          " (while (< k n) (invariant (<= k n)) (decreases (- n k)) (set a (cons k a)) (set b (cons k b)) (set k (+ k 1)))"
          " (return a b)))")
out = is_ok(i.run(DEEP, "two", (50_000,), check=True, subset=1, fuel=5_000_000), *i.run(DEEP, "two", (50_000,), subset=1).results)
text = i.text_of(out)
assert text.startswith("ok (cons 49999 (cons 49998 ") and text.endswith("(cons 0 (nil))" + ")" * 49_999), text[-60:]
assert i._term(i.Data("cons", (1, i.Data("nil", ())))) == "(cons 1 (nil))"
# Equality still decides left to right, so different constructors are unequal before any set kept
# as its predicate is reached; and collections still order their elements as values, not as text.
TWO_SETS = "(data d () (a (p (iset int))) (b (q (iset int))))"
is_ok(go1(f1("(x i64)", "(r i64)", "(return x)", extra=[TWO_SETS],
             clauses="(ensures (!= (a (iset-of ((z int)) true)) (b (iset-of ((z int)) true))))"), 1, check=True), 1)
unknown(go1(f1("(x i64)", "(r i64)", "(return x)", extra=[TWO_SETS],
               clauses="(ensures (!= (a (iset-of ((z int)) true)) (a (iset-of ((z int)) true))))"), 1, check=True), "POST")
assert i._term(frozenset({(2,), (10,), (2, 1)})) == "(iset-lit (seq-lit 2) (seq-lit 2 1) (seq-lit 10))"
assert i._term(i.Map({(10,): 1, (2,): 2})) == "(map-lit ((seq-lit 2) 2) ((seq-lit 10) 1))"
# Interface 10's text form gains tuples and data values (D56), and run() checks them against the
# parameter types.
assert i.text_of(go1(f1("(t (option (tuple i64 bool)))", "(r (option (tuple i64 bool)))", "(return t)"),
                     some(T((1, False))))) == "ok (some (tuple 1 false))"
for bad in [some(T((1, 2))), some(T((MAX + 1, True))), D("leaf", ()), T((1, False)), D("some", ()),
            D("some", (T((1, False)), T((1, False))))]:
    try:
        go1(f1("(t (option (tuple i64 bool)))", "(r bool)", "(return true)"), bad)
    except ValueError as e:
        assert "is not a value of type (option (tuple i64 bool))" in str(e), e
    else:
        raise AssertionError(bad)
assert cli("--subset", "1", "--check", str(SUITE / "b17-1/accept/bst_search.b17"), "search",
           "(node 5 (leaf) (node 9 (leaf) (leaf)))", "9") == (0, "ok true\n", "")
assert cli("--subset", "1", str(SUITE / "b17-1/accept/discrete_logarithm.b17"), "discrete_log_naive", "2", "8", "11") \
    == (0, "ok (some 3)\n", "")
assert cli("--subset", "0", str(SUITE / "accept/abs.b17"), "abs", "-5") == (0, "ok 5\n", "")

print("interpreter conformance tests passed")
