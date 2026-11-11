"""Self-check for WP11's baseline scoring (D123): uv run --no-project gym/test_baseline.py

Needs z3 on PATH, but not the secret. Scores a reply whose output the interpreter can't judge, under a
made-up secret, and checks its record names no input; then summarizes made-up replies.
"""
import hashlib
import json
import tempfile
from pathlib import Path

import baseline as B
import split as S

KEY = b"not the real secret"
TASK = {"id": "test/same", "lang": "b17", "name": "same", "frozen": """(module same
  (header (purpose "Return x.") (invariants "None.") (failures "None."))
  (spec same (params (x i64)) (returns (y i64)) (requires (< -100 x) (< x 100))
    (ensures (== y x) (forall ((k int)) (=> (< k y) (< k (+ x 1))))) (effects)))"""}

with tempfile.TemporaryDirectory() as d:
    split = Path(d, "split.json")
    split.write_text(json.dumps(S.load() | {"secret_sha256": hashlib.sha256(KEY).hexdigest()}))
    rec = {"attempt": "a1", "iter": 1, "cli": "codex", "stage": "verified", "code": "(def same (body (return x)))"}
    out = B.score_reply(TASK, rec, KEY, split)
    assert out["reward"] == 0.80 and out["triage"] == [(k, "undecided") for k in range(25)], out
    assert B.score_reply(TASK, rec | {"code": None, "stage": "no_code"}, KEY, split)["reward"] == 0.0

row = lambda attempt, it, reward, stage, cli="claude", task="b17/abs", **kw: dict(
    attempt=attempt, iter=it, reward=reward, stage=stage, cli=cli, task=task, **kw)
groups, disagree = B.summarize([
    row("a", 1, 0.2, "proof_failed", parts=[False]), row("a", 2, 0.9, "verified", triage=[]),
    row("b", 1, 0.0, "verified", triage=[(3, "discrepancy")]),
    *(row("c", k, r, stage, cli="codex", task="b17-1/lca", **kw) for k, r, stage, kw in
      [(1, 0.05, "rejected", {}), (2, 0.8, "proof_failed", {"triage": [(0, "limit")]})]),
])
assert groups["claude/b17"] == {"attempts": 2, "first": 0.1, "last": 0.45, "tiers": {"right": 1, "discrepancy": 1},
                                "triage": {"discrepancy": 1}}, groups
assert groups["codex/b17-1"]["tiers"] == {"verified": 1} and groups["codex/b17-1"]["triage"] == {"limit": 1}
assert disagree == ["b17-1/lca codex c iter 2: proof_failed, 0.8"]
print("baseline self-check passed")
