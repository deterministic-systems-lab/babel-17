"""Self-check for the verifier's cache and report (D22-D25, D63): uv run --no-project b17c/test_verify.py

Needs z3 on PATH, so it runs locally rather than in CI.
"""
import re
import tempfile
from pathlib import Path

import verify as v
from syntax import parse

SUITE = Path(__file__).resolve().parent.parent / "suite"
CACHE = Path(tempfile.mkdtemp())


def run(text, seeds=1):
    return v.verify(parse(text), seeds, CACHE)[0]


def src(name):
    return (SUITE / "accept" / f"{name}.b17").read_text()


# canonical() renames generated names in order of first occurrence, and only those.
q = "(declare-const x!12 Int) (declare-const n!p SI) (assert (= (g!fib x!12) (len.I n!p))) (assert (forall ((i!b3 Int)) (p!fib i!b3)))"
assert v.canonical(q) == "(declare-const k!0 Int) (declare-const k!1 SI) (assert (= (k!2 k!0) (len.I k!1))) (assert (forall ((k!3 Int)) (k!4 k!3)))"
assert v.canonical(v.canonical(q)) == v.canonical(q)

# The worked example verifies; run again, every verdict comes from the cache (WP5's done-when).
first = run(src("merge_sorted"))
assert all(r["verdict"] == "proved" for r in first) and not any(r["cached"] for r in first)
assert all(r["cached"] for r in run(src("merge_sorted")))

# A renamed definition sends the same canonical queries, so its proofs are reused (D45, D63).
renamed = src("merge_sorted")
for old, new in [("out", "res"), ("merge_sorted", "merge"), ("i", "k")]:
    renamed = re.sub(rf"\b{old}\b", new, renamed)
assert all(r["cached"] for r in run(renamed))

# A body edit re-verifies only that definition; its callers see only its spec (D22).
CALLS = """(module calls (header (purpose "p") (invariants "i") (failures "f"))
  (spec one (params) (returns (r i64)) (ensures (== r 1)) (effects))
  (def one (body (return 1)))
  (spec two (params) (returns (r i64)) (ensures (== r 2)) (effects))
  (def two (body (let ((x i64)) (call one)) (return (+ x 1)))))"""
run(CALLS)
edited = run(CALLS.replace("(return 1)", "(let y i64 1) (return y)"))
assert {r["node"].split("/")[0] for r in edited if not r["cached"]} == {"def one"}, edited
# A spec edit re-verifies its callers too.
respec = run(CALLS.replace("(ensures (== r 1))", "(ensures (>= r 1) (<= r 1))"))
assert {"def two"} <= {r["node"].split("/")[0] for r in respec if not r["cached"]}, respec

# The key's own parts: changing only the dependency hashes changes it (D22, D63).
cfg = {"seeds": 1}
assert v.cache_key("d", ["a", "b"], "q", cfg) == v.cache_key("d", ["b", "a"], "q", cfg)
assert v.cache_key("d", ["a", "b"], "q", cfg) != v.cache_key("d", ["a", "c"], "q", cfg)
assert v.cache_key("d", [], "q", cfg) != v.cache_key("d", [], "q", {"seeds": 2})

# A failing goal is reported by node ID, contract clause and family; the report gives the
# level, input hash and goals D24 and D25 ask for.
bad = (SUITE / "reject/E-PROOF-POST-wrong-result.b17").read_text()
rows, cfg = v.verify(parse(bad), 1, CACHE)
failed = [r for r in rows if r["verdict"] != "proved"]
assert [r["family"] for r in failed] == ["POST"] and failed[0]["node"].startswith("def bad_abs/2.1@14:7 spec bad_abs/"), rows
rep = v.report(parse(bad), rows, cfg)
assert rep["level"] == "L2-S" and rep["lockfile_sha256"] is None and rep["admitted"] == []
assert rep["input_sha256"] == v.sha256(v.canonical_bytes(parse(bad))) and len(rep["solver_sha256"]) == 64
assert rep["failed"] == [{"node": failed[0]["node"], "family": "POST", "verdict": failed[0]["verdict"]}]
assert rep["solver_trusted"] == [r["node"] for r in rows if r["verdict"] == "proved"]
assert "law_take_step" in rep["axioms"]["core"]
assert v.report(parse(src("abs")), run(src("abs")), cfg)["level"] == "L3-S"

# Every goal has its own node ID: one per ensures clause at a return, and a number for a
# node checked twice, as a loop condition is on entry and at each iteration.
TWO = """(module two (header (purpose "p") (invariants "i") (failures "f"))
  (spec f (params (a (ref (slice i64)))) (returns (r i64)) (requires (> (len a) 0)) (ensures (== r 0) (== r 1)) (effects))
  (def f (body (let-mut i i64 0) (while (< (idx a 0) i) (decreases i) (set i (- i 1))) (return 0))))"""
ids = [r["node"] + " " + r["family"] for r in run(TWO)]
assert len(ids) == len(set(ids)), ids
assert any(n.endswith("#2 BOUNDS") for n in ids), ids

# Sorts come from WP3's types: multisets of booleans, and empty literals whose element type
# only their context fixes: a comparison, concat, take, a ghost-fn's parameter or result.
SORTS = """(module sorts (header (purpose "p") (invariants "i") (failures "f"))
  (ghost-fn none ((s (seq bool))) bool (body (== s (seq-lit))))
  (ghost-fn empty () (seq bool) (body (take (seq-lit) 0)))
  (ghost-fn chosen () bool (body (if false (last (seq-lit)) (if false (idx (seq-lit) 0) true))))
  (spec same (params (a (vec bool))) (returns (r (vec bool)))
    (ensures (== (multiset r) (multiset a)) (== (occurrences r true) (occurrences a true))
             (== (concat (seq-lit) r) r) (== (seq-lit) (take r 0)) (== (take (seq-lit) 0) (take r 0))
             (none (take (seq-lit) 0)) (== (empty) (drop r (len r))) (== (if (none r) r a) r) (== (seq-lit (not false)) (seq-lit true))
             (chosen) (== (occurrences (seq-lit) true) 0) (not (contains (seq-lit) false))) (effects))
  (def same (body (return a)))
  (spec count (params (a (ref (slice bool)))) (returns (n i64)) (ensures (== n (len a))) (effects))
  (def count (body (return (len a))))
  (spec wrap (params) (returns (v (vec bool))) (ensures (== v (seq-lit))) (effects))
  (def wrap (body (let w (vec bool) (vec-new)) (let ((n i64)) (call count (borrow w))) (return w))))"""
assert all(r["verdict"] == "proved" for r in run(SORTS))
# A (multiset i64) compares with a (multiset int) (D107), and the comparison means what it says.
WIDE = """(module w (header (purpose "p") (invariants "i") (failures "f"))
  (spec f (params (x i64)) (returns (r (vec i64))) (ensures (== (multiset r) (multiset (seq-lit (+ x 0))))) (effects alloc))
  (def f (body (let-mut v (vec i64) (vec-new)) (push v x) (return v))))"""
assert all(r["verdict"] == "proved" for r in run(WIDE))
assert [r["family"] for r in run(WIDE.replace("(+ x 0)", "(+ x 1)")) if r["verdict"] != "proved"] == ["POST"]
# A module that fails tier 0 has no goals; the error lists its diagnostics.
try:
    run(SORTS.replace("(return a)", "(return b)"))
    raise AssertionError("an undefined name was verified")
except ValueError as e:
    assert "E-TYPE-002: 'b' is undefined" in str(e), e

# Only verdicts reached within the budget are cached: a timeout is solved again (D23).
real = v.G.solve_stats
v.G.solve_stats = lambda q, seed=0: ("unknown: timeout", 0)
try:
    fresh = "(module t (header (purpose \"p\") (invariants \"i\") (failures \"f\")) (spec g (params) (returns (r i64)) (ensures (== r 7)) (effects)) (def g (body (return 7))))"
    assert not any(r["cached"] for r in run(fresh)) and not any(r["cached"] for r in run(fresh))
finally:
    v.G.solve_stats = real
# A partial entry from a crashed run is a miss, not an error.
entry = next(CACHE.rglob("*.json"))
entry.write_text('{"verdict": "pro')
assert v._read(entry) is None

# B17-1 (subset 1, D101): D89's encoding as D103 refines it.
def run1(text, seeds=1):
    return v.verify(parse(text, 1), seeds, CACHE, 1)[0]


def open_(rows):
    """The families of the goals that aren't proved."""
    return sorted({r["family"] for r in rows if r["verdict"] != "proved"})


# The suite: every written proof verifies, and each proof reject fails only its label's family.
for name in ("bst_insert", "bst_search", "discrete_logarithm", "longest_palindrome_substring", "lca", "segmenttree_query",
             "trie_insert", "bfs", "coin_change", "kruskal"):
    assert open_(run1((SUITE / "b17-1/accept" / f"{name}.b17").read_text())) == [], name
for path in sorted((SUITE / "b17-1/reject").glob("E-PROOF-*.b17")):
    assert open_(run1(path.read_text())) == [path.name.split("-")[2]], path.name
# ...and breaking a written proof leaves its goal unproved, so the encoding isn't vacuous.
insert = (SUITE / "b17-1/accept/bst_insert.b17").read_text()
for old, new in [("(call insert l x)) (return (node v l2 r))", "(call insert r x)) (return (node v l l2))"),
                 ("(requires (>= x 0) (is_bst t))", "(requires (>= x 0))")]:
    assert open_(run1(insert.replace(old, new))) == ["POST"], old

H1 = '(module t (header (purpose "p") (invariants "i") (failures "f"))\n  (data tree () (leaf) (node (val i64) (left tree) (right tree)))\n'
# rank: a structural recursion terminates, and one on its own argument doesn't (D87, D89).
assert open_(run1(H1 + "(ghost-fn size ((t tree)) int (decreases (rank t)) (body (match t (case (leaf) 0)"
                       " (case (node v l r) (+ 1 (+ (size l) (size r))))))))")) == []
assert open_(run1(H1 + "(ghost-fn size ((t tree)) int (decreases (rank t)) (body (match t (case (leaf) 0)"
                       " (case (node v l r) (size t))))))")) == ["TERM"]
# field carries FIELD unless every constructor has the field; is and match supply it.
assert open_(run1(H1 + "(ghost-fn top ((t tree)) int (body (field t val))))")) == ["FIELD"]
assert open_(run1(H1 + "(ghost-fn top ((t tree)) int (body (if (is node t) (field t val) 0))))")) == []
# Tuples, sets (extensional, with iset-of as a predicate) and maps (D85, D89).
assert open_(run1(H1 + """(spec f (params (a i64) (b bool)) (returns (r (tuple i64 bool)))
    (ensures (== (get r 0) a) (== (match r (case (tuple x y) y)) b)
             (forall ((q int)) (== (union (iset-lit q) (iset-lit 1)) (union (iset-lit 1) (iset-lit q))))
             (contains (diff (iset-of ((z int)) (> z a)) (iset-lit (+ a 2))) (+ a 1))
             (not (contains (inter (iset-lit a) (iset-of ((z int)) (> z a))) a))
             (== (lookup (update (map-lit (1 2)) a 7) a) 7) (contains (union (map-lit (1 2)) (map-lit (a 3))) 1)
             (== (lookup (union (map-lit (a 2)) (map-lit (a 3))) a) 3))
    (effects))
  (def f (body (return (tuple a b)))))""")) == []
# Places: an update through field, idx and get changes that part only; replace takes the old one.
assert open_(run1(H1 + """(data box () (box (xs (vec (tuple i64 i64))) (n i64)))
  (spec f (params (b box)) (returns (r box) (old (tuple i64 i64)))
    (requires (> (len (field b xs)) 0))
    (ensures (== (len (field r xs)) (len (field b xs))) (== (idx (field r xs) 0) (tuple 1 5)) (== (field r n) (field b n))
             (== old (tuple 1 2)))
    (effects))
  (spec g (params (p (tuple (vec i64) i64))) (returns (r (tuple (vec i64) i64)))
    (requires (< (len (get p 0)) 100))
    (ensures (== (len (get r 0)) (+ (len (get p 0)) 1)) (== (get r 1) (get p 1)) (== (last (get r 0)) 7))
    (effects alloc))
  (def f (body (let-mut c box b) (set-idx (field c xs) 0 (tuple 1 2))
               (let y (tuple i64 i64) (replace (idx (field c xs) 0) (tuple 1 5))) (return c y)))
  (def g (body (let-mut q (tuple (vec i64) i64) p) (push (get q 0) 7) (return q))))""")) == []
# A match statement's arms join as an if's branches do.
assert open_(run1(H1 + """(spec f (params (t tree)) (returns (r i64)) (ensures (=> (is node t) (== r (field t val))) (=> (is leaf t) (== r 0)))
    (effects))
  (def f (body (let-mut x i64 0) (match t (case (leaf) (block)) (case (node v l r) (set x v))) (return x))))""")) == []
# D99: a forall statement gives a lemma's fact at every value, which induction alone needs;
# and a lemma applying itself through one must still decrease.
SUM = """(ghost-fn sum ((n int)) int (requires (>= n 0)) (decreases n) (body (if (== n 0) 0 (+ n (sum (- n 1))))))
  (lemma sum_ge (params (n int)) (requires (>= n 0)) (ensures (>= (sum n) n)) (decreases n)
    (body (if (> n 0) (call sum_ge (- n 1)) (block))))"""
USE = "\n(lemma all_ge (params) (ensures (forall ((m int)) (=> (>= m 0) (>= (sum m) m)))) (body {}))"
assert open_(run1(H1 + SUM + USE.format("(forall ((m int)) (call sum_ge m))") + ")")) == []
assert open_(run1(H1 + SUM + USE.format("") + ")")) == ["POST"]
assert open_(run1(H1 + "(lemma l (params (n int)) (requires (> n 0)) (decreases n) (body (forall ((k int)) (call l k)))))")) == ["TERM"]
# D100: obtain proves its ∃, then names a witness the rest of the path may use.
assert open_(run1(H1 + """(lemma w (params (s (seq int))) (requires (> (len s) 0)) (ensures (exists ((i int)) (and (<= 0 i) (== i (- (len s) 1)))))
    (body (obtain ((k int)) (and (<= 0 k) (< k (len s)))) (assert (< k (len s))))))""")) == []
# Renaming a data type, a constructor and a field changes no canonical query (D63, D92).
first = run1(insert)
renamed = insert
for old, new in [("tree", "bst"), ("leaf", "empty"), ("val", "key")]:
    renamed = re.sub(rf"\b{old}\b", new, renamed)
assert all(r["cached"] for r in run1(renamed)), [r for r in run1(renamed) if not r["cached"]]

# Codex's review of B17-1's verifier found two ways to prove false, both in B17-0 too.
H0 = '(module t (header (purpose "p") (invariants "i") (failures "f"))\n'
# A recursive ghost-fn's equation holds only on values of its parameter types, where its measure
# was proved; an SMT integer or field outside i64 isn't one.
LIE = "(lemma lie (params) (ensures false) (body (assert (bad {}))))"
assert "POST" in open_(run(H0 + "(ghost-fn bad ((x i64)) bool (decreases 0) (body (if (> x 9223372036854775807) "
                             "(not (bad x)) true)))\n" + LIE.format(0) + ")"))
assert "POST" in open_(run1(H0 + "(data cell () (cell (n i64)))\n(ghost-fn bad ((x cell)) bool (decreases 0) (body (match x "
                              "(case (cell n) (if (> n 9223372036854775807) (not (bad x)) true)))))\n" + LIE.format("(cell 0)") + ")"))
# A seq-build under binders, or in a ghost-fn's body, is a function of them, so it has their length...
assert open_(run(H0 + "(spec lie (params) (returns (r i64)) (ensures (exists ((k int)) (and (and (<= 0 k) (< k 3)) "
                      "(!= (len (seq-build k (fn (i) 0))) k)))) (effects)) (def lie (body (return 0))))")) == ["POST"]
assert open_(run(H0 + "(ghost-fn n ((k int)) int (requires (>= k 0)) (body (len (seq-build k (fn (i) 0)))))\n"
                      "(spec lie (params) (returns (r i64)) (ensures (== (n 1) (n 2))) (effects)) (def lie (body (return 0))))")) == ["POST"]
assert open_(run1(H0 + "(lemma bad (params) (ensures false) (body (obtain ((k int)) (!= (len (seq-build (* k k) (fn (i) 0))) (* k k))))))"))[0] == "ASSERT"
# ...which also proves what's true of it.
assert open_(run(H0 + "(ghost-fn n ((k int)) int (requires (>= k 0)) (body (len (seq-build k (fn (i) 0)))))\n"
                      "(spec ok (params) (returns (r i64)) (ensures (== (n 2) 2) (forall ((k int)) (=> (and (<= 0 k) (< k 4)) "
                      "(== (len (seq-build k (fn (i) (* i i)))) k)))) (effects)) (def ok (body (return 0))))")) == []
# The second pass: a recursive call in a ghost-fn's requires gets its TERM goal (D57), and a lifted
# seq-build may call the recursive ghost-fn whose body it's in.
assert open_(run(H0 + "(ghost-fn f ((n int)) bool (requires (or (f n) true)) (decreases n) (body true)))")) == ["TERM"]
assert open_(run(H0 + "(ghost-fn f ((n int)) int (requires (>= n 0)) (decreases n) (body (if (== n 0) 0 "
                      "(len (seq-build 1 (fn (i) (f (- n 1))))))))\n(lemma good (params) (ensures (== (f 1) 1)) (body)))")) == []
# The rest of that review: a data value's i64s fit (a validity predicate per data type), nested
# sequences compare by elements, a multiset of an empty sequence of data, and the multiset fact of
# an update through a place.
assert open_(run1(H0 + "(data cell () (cell (value i64)))\n(spec f (params (c cell)) (returns (r i64)) (ensures (== r (field c value))) "
                       "(effects)) (def f (body (return (+ (field c value) 0)))))")) == []
assert open_(run1(H0 + "(lemma eq (params (s (seq int))) (ensures (== (seq-lit (drop s 0)) (seq-lit s))) (body)))")) == []
assert open_(run1(H0 + "(data cell () (cell (n i64)))\n(lemma l (params) (ensures true) (body (ghost-let m (multiset cell) "
                       "(multiset (seq-lit))) (assert true))))")) == []
assert open_(run1(H0 + """(data box () (box (xs (vec i64))))
  (spec f (params (b box)) (returns (r box)) (requires (> (len (field b xs)) 0) (== (idx (field b xs) 0) 1))
    (ensures (== (occurrences (field r xs) 2) (+ (occurrences (field b xs) 2) 1))) (effects))
  (def f (body (let-mut c box b) (set-idx (field c xs) 0 2) (return c))))""")) == []

# D105: a set or map literal of sequences holds its members by their elements, as == compares
# them; and a seq-build whose body doesn't use its index counts that body n times.
assert open_(run1(H0 + """(lemma l (params (s (seq int)) (t (seq int)))
    (requires (> (len s) 0) (== t (drop s 0)))
    (ensures (== (iset-lit (drop s 0)) (iset-lit s)) (contains (iset-lit t) s)
             (== (lookup (update (map-lit (t 1)) s 2) t) 2) (not (contains (iset-lit (drop s 1)) s)))
    (body)))""")) == []
assert open_(run1(H0 + """(spec f (params (n i64)) (returns (r (vec i64))) (requires (>= n 0))
    (ensures (== (occurrences r -1) n) (== (occurrences r 0) 0)) (effects alloc))
  (def f (body (return (seq-build n (fn (j) -1))))))""")) == []

# Validity says only that a data value's i64s fit, not its vectors' lengths (D105).
assert open_(run1(H0 + """(data box () (end (tag i64) (xs (vec bool))) (more (next box)))
  (ghost-fn all_ok ((b box)) bool (decreases (rank b)) (body (match b (case (end tag xs) true) (case (more next) (all_ok next)))))
  (lemma l (params (m (map int (vec bool)))) (requires (contains m 0)) (ensures (all_ok (end 0 (lookup m 0)))) (body)))""")) == []

# D106: in B17-1 a non-recursive ghost-fn is a function whose definition its applications trigger,
# so it unfolds only where a proof applies it; B17-0 keeps its macros, byte for byte.
FOLD = H0 + """(ghost-fn pos ((s (seq int))) bool (body (forall ((i int)) (=> (and (<= 0 i) (< i (len s))) (> (idx s i) 0)))))
  (lemma l (params (s (seq int))) (requires (pos s) (> (len s) 0)) (ensures (> (idx s 0) 0)) (body)))"""
for subset, form in ((0, "(define-fun g!pos "), (1, "(declare-fun g!pos ")):
    m = parse(FOLD, subset)
    gen = v.G.Gen(m, subset)
    g = gen.check(m)[-1]
    assert form in v.G.query(gen, g[3], g[4], g[0]), subset
assert open_(run1(FOLD)) == [] and open_(run(FOLD)) == []

# D108: equal sequences are the same sequence, so every function agrees on them, in both subsets.
# A value holding sequences is equal once they're compared, and only when they're equal.
SAME = H0 + """(lemma l (params (x (vec i64)) (y (seq int))) (requires (== x y)) (ensures (== (multiset x) (multiset y))) (body)))"""
assert open_(run(SAME)) == [] and open_(run1(SAME)) == []
TUP = H0 + """(lemma l (params (s (seq int))) (requires (>= (len s) 2))
    (ensures (== (tuple (concat (take s 1) (drop s 1)) 1) (tuple s 1))) (body (assert (== (concat (take s 1) (drop s 1)) s)))))"""
assert open_(run1(TUP)) == [] and open_(run1(TUP.replace("(drop s 1)) s)", "(drop s 2)) s)"))) == ["ASSERT"]

print("verifier self-check passed")
