"""Self-check for the frozen split (D123): uv run --no-project gym/test_split.py

Needs the secret, at ~/.config/babel-17/gym-secret. Checks that split.json records it, that the
test set is M3's 34 tasks, and that no task left to train on shares a problem with a held-out one,
across every task the harness loads.
"""
import harness as h
import split as S

split, key = S.load(), S.secret()
S.check_secret(key, split)
try:
    S.check_secret(key + b"\0", split)
    raise AssertionError("a different secret passed")
except ValueError:
    pass

tasks = [t["id"] for t in h.load_tasks()]
assert split["test"] == sorted(t for t in tasks if t.startswith(("b17/", "b17-1/"))) and len(split["test"]) == 34
assert set(split["problems"]) <= set(tasks), set(split["problems"]) - set(tasks)  # the table names real tasks
# The same problem under another name is held out, as D123's three are and the test set's Dafny versions.
for t in ["algoveri/binary_search", "algoveri/gcd", "algoveri/insertion_sort", "algoveri/linear_search",
          "algoveri/quick_sort", "algoveri/fast_exponential", "vericoding/DV0015", "algoveri/kruskal", "abs"]:
    assert S.held_out(split, key, t), t
assert not S.held_out(split, key, "algoveri/bfs")  # the supplement's worked proof, in every prompt (D117)

held = {S.problem(split, t) for t in tasks if S.held_out(split, key, t)}
train = {S.problem(split, t) for t in tasks if not S.held_out(split, key, t)}
assert train and not held & train, held & train
# The slice holds out 1 problem in 10, by the secret.
names = [f"problem {k}" for k in range(10_000)]
share = sum(S.held_out(split, key, n) for n in names) / len(names)
assert 0.09 < share < 0.11, share
assert [S.held_out(split, key, n) for n in names] != [S.held_out(split, b"another", n) for n in names]
print(f"split self-check passed: {len(held)} problems held out, {len(train)} to train on")
