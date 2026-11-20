"""Self-check for WP11's baseline scoring (D123): uv run --no-project gym/test_baseline.py

Needs z3 on PATH, but not the secret. Scores a reply whose output the interpreter can't judge, under a
made-up secret, and checks its record holds only counts of what triage found; then summarizes a
made-up run, with a retried sample, one never done and a reply left unscored.
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
FIELDS = {"attempt", "iter", "cli", "sample", "stage", "final", "task", "reply_sha256", "spec_sha256", "b17c_commit",
          "inputs_sha256", "reward"}

with tempfile.TemporaryDirectory() as d:
    split = Path(d, "split.json")
    split.write_text(json.dumps(S.load() | {"secret_sha256": hashlib.sha256(KEY).hexdigest()}))
    rec = {"attempt": "a1", "iter": 1, "cli": "codex", "sample": 1, "stage": "verified", "final": True,
           "code": "(def same (body (return x)))"}
    out = B.score_reply(TASK, rec, KEY, split)
    assert set(out) == FIELDS | {"triage"} and out["reward"] == 0.80 and out["triage"] == {"undecided": 25}, out
    out = B.score_reply(TASK, rec | {"code": None, "stage": "no_code"}, KEY, split)
    assert set(out) == FIELDS and out["reward"] == 0.0 and out["reply_sha256"] is None and out["spec_sha256"], out


def rec(attempt, it, stage, final, sample=1, cli="claude", task="b17/abs", code=""):
    return dict(attempt=attempt, iter=it, stage=stage, final=final, sample=sample, cli=cli, task=task, code=code)


records = [rec("a", 1, "proof_failed", False), rec("a", 2, "verified", True),
           rec("x", 1, "infra_error", True, sample=2), rec("b", 1, "verified", True, sample=2),  # a checker_error, retried
           rec("c", 1, "rejected", False, cli="codex", task="b17-1/lca"), rec("c", 2, "proof_failed", True, cli="codex", task="b17-1/lca"),
           rec("d", 1, "infra_error", True, sample=3, code=None)]  # a failed call, never retried
scores = {"a": [0.2, 0.9], "x": [0.8], "b": [0.0], "c": [0.05, 0.8]}
triage = {("a", 2): {}, ("x", 1): {}, ("b", 1): {"discrepancy": 1, "limit": 2}, ("c", 2): {"limit": 1}}
rows = [{k: r[k] for k in ("attempt", "iter", "cli", "sample", "stage", "final", "task")} | {"reward": scores[r["attempt"]][r["iter"] - 1]}
        | ({"triage": triage[r["attempt"], r["iter"]]} if (r["attempt"], r["iter"]) in triage else {})
        for r in records if r["attempt"] in scores]
assert [r["attempt"] for r in B.replies(records)] == ["a", "a", "x", "b", "c", "c"]  # all but d's failed call
assert [B.tier({"reward": r}) for r in (0.2, 0.35, 0.8)] == ["checks", "some goals", "verified"]
groups, undone, disagree = B.summarize(rows, records)
assert groups["claude/b17"] == {"samples": 2, "first": 0.1, "last": 0.45, "tiers": {"right": 1, "discrepancy": 1},
                                "triage": {"discrepancy": 1, "limit": 2}}, groups
assert groups["codex/b17-1"]["tiers"] == {"verified": 1} and groups["codex/b17-1"]["triage"] == {"limit": 1}
assert undone == [("b17/abs", "claude", 3)]
assert disagree == ["b17/abs claude x iter 1: infra_error, 0.8", "b17-1/lca codex c iter 2: proof_failed, 0.8"], disagree
try:
    B.summarize(rows[1:], records)
    raise AssertionError("a reply left unscored passed")
except ValueError as e:
    assert "1 replies aren't scored" in str(e), e
print("baseline self-check passed")
