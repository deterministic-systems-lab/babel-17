"""WP17 baseline harness: agents write verified Dafny for frozen tasks.

    uv run gym/harness.py check-tasks
    uv run gym/harness.py run --clis claude,codex --samples 3 [--tasks abs,fib] [--resume RUN_ID]
    uv run gym/harness.py reverify RUN_ID
    uv run gym/harness.py summary RUN_ID [OTHER_RUN_ID]

Each file in gym/tasks/ has three sections: a preamble of frozen definitions, the method
signature with its contracts, and a hidden reference solution. An agent's code is checked
as: its code, then the preamble, then a generated <Name>_Check method that calls <Name>
under the frozen contracts, so an agent can't weaken them. Agent code goes first so
Dafny's line numbers match the code the agent wrote.

An attempt is one task, one CLI and one sample: up to --max-iters rounds of
generate, check, and feed the verifier's output back. Every round is a fresh,
stateless call carrying the task, the previous code and the stock Dafny output.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

GYM = Path(__file__).resolve().parent
TASKS, RUNS = GYM / "tasks", GYM / "runs"

# Z3 rlimit units, same as Dafny's CSV ResourceCount. The heaviest reference proof
# (merge_sorted) uses 14M; the rest stay under 0.5M.
# ponytail: one fixed budget for every task; make it per-task if harder tasks need more.
RESOURCE_LIMIT = 100_000_000
DAFNY = ["dafny", "verify", "--cores", "1", "--resource-limit", str(RESOURCE_LIMIT),
         "--verification-time-limit", "0"]
CLIS = {
    "claude": ["claude", "-p", "--model", "opus", "--effort", "high", "--tools", "",
               "--setting-sources", "project", "--strict-mcp-config", "--disable-slash-commands",
               "--no-session-persistence", "--output-format", "json"],
    "codex": ["codex", "exec", "--ignore-user-config", "--ephemeral", "--ignore-rules",
              "--disable", "shell_tool", "--disable", "unified_exec", "-m", "gpt-5.6-sol",
              "-c", "model_reasoning_effort=high", "-s", "read-only", "--skip-git-repo-check",
              "--json", "-"],
}
CALL_TIMEOUT, RETRY_WAITS = 900, [60, 120, 240, 480, 960, 1800]
FEEDBACK_CHARS = 6000

TASK_PROMPT = """Write Dafny {dafny_version} code that verifies with no errors.

Implement this method. Keep its name, parameters, return values and contracts as shown:

```dafny
{signature}
```
{preamble_block}
Rules:
- You may add loop invariants, assertions, decreases clauses, and helper lemmas, predicates, functions and methods. Every helper needs a body.
- Not allowed: assume, expect, decreases *, include, and attributes other than {{:trigger}}, {{:induction}}, {{:fuel}}, {{:opaque}}, {{:isolate_assertions}}, {{:split_here}}, {{:focus}}, {{:vcs_split_on_every_assert}} and {{:tailrecursion}}.
- Your code is checked by appending the definitions above and a method {name}_Check that calls {name} under the contracts shown.
- Answer directly without using tools. Reply with your complete code in one ```dafny block.
"""
PREAMBLE_BLOCK = """
These definitions are already in scope. Use them, but do not redefine them:

```dafny
{preamble}
```
"""
REPAIR_PROMPT = """
Your previous code:

```dafny
{code}
```

The check failed:

{feedback}

Reply with the complete corrected code in one ```dafny block.
"""

# Dafny identifiers may contain ' and ?, so assume' is a legal name, not the keyword.
BANNED = {k: rf"(?<![\w'?]){rx}(?![\w'?])" for k, rx in
          {"assume": "assume", "expect": "expect", "decreases *": r"decreases\s*\*", "include": "include"}.items()}
# Attributes are allow-listed: both syntaxes ({:axiom}, @Axiom) can switch off checking,
# and Dafny keeps adding new ones.
SAFE_ATTRIBUTES = {"trigger", "induction", "fuel", "opaque", "isolate_assertions", "split_here",
                   "focus", "vcs_split_on_every_assert", "tailrecursion",
                   "IsolateAssertions", "Fuel", "Induction", "TailRecursion"}
# One pass, leftmost match first, so "//" inside a string is a string, not a comment.
# Verbatim strings (@"...", with "" as the escape) come before ordinary ones.
# ponytail: block comments don't nest here, so text inside a nested comment can be
# falsely flagged (never falsely passed); track comment depth if that ever bites.
TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|@"(?:""|[^"])*"|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])\'|.', re.S)
AXIOM_WARNING = re.compile(r"has no \{:axiom\} annotation|bodyless")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def param_names(params):
    """Names from a Dafny parameter list, splitting only on top-level commas."""
    names, depth, cur = [], 0, ""
    for ch in params + ",":
        depth += (ch in "<([") - (ch in ">)]")
        if ch == "," and depth == 0:
            if cur.strip():
                names.append(cur.split(":")[0].replace("ghost ", "").strip())
            cur = ""
        else:
            cur += ch
    return names


def load_task(path):
    text = path.read_text()
    parts = re.split(r"^//== (preamble|signature|solution)\s*$", text, flags=re.M)
    sec = {k: v.strip() for k, v in zip(parts[1::2], parts[2::2])}
    meta = dict(re.findall(r"^// (\w+): (.*)$", parts[0], re.M))
    sig = sec["signature"]
    m = re.match(r"method\s+(\w+)\s*\((.*?)\)\s*(?:returns\s*\((.*?)\))?", sig, re.S)
    name, rets = m.group(1), param_names(m.group(3) or "")
    call = f"{', '.join(rets)} := " if rets else ""
    check = (f"method {name}_Check{sig[m.end(1):m.end()]}{sig[m.end():]}\n"
             f"{{\n  {call}{name}({', '.join(param_names(m.group(2)))});\n}}")
    return dict(id=path.stem, name=name, preamble=sec["preamble"], signature=sig,
                solution=sec["solution"], check=check, **meta)


def load_tasks(only=None):
    tasks = [load_task(p) for p in sorted(TASKS.glob("*.dfy"))]
    return [t for t in tasks if not only or t["id"] in only]


def violations(code):
    bare = "".join(" " if t[:2] in ("//", "/*") or t[:1] == '"' or t[:2] == '@"' or (t[:1] == "'" and len(t) > 1)
                   else t for t in TOKEN.findall(code))
    found = [k for k, rx in BANNED.items() if re.search(rx, bare)]
    attrs = re.findall(r"\{:\s*(\w+)|(?<![\w@])@\s*([A-Za-z]\w*)", bare)
    return found + sorted({f"{{:{a}}}" if a else f"@{b}" for a, b in attrs if (a or b) not in SAFE_ATTRIBUTES})


def verify(task, code):
    """Check agent code against a task. Returns (stage, Dafny output)."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "program.dfy"
        f.write_text(f"{code}\n\n// ---- appended by the harness ----\n"
                     f"{task['preamble']}\n\n{task['check']}\n")
        try:
            p = subprocess.run(DAFNY + [str(f)], capture_output=True, text=True, timeout=CALL_TIMEOUT)
        except subprocess.TimeoutExpired:
            return "timeout", "The verifier timed out."
        out = (p.stdout + p.stderr).replace(str(f), "program.dfy").strip()
    if AXIOM_WARNING.search(out):
        return "axiom", out
    if re.search(r"parse errors detected|resolution/type errors detected", out):
        return "rejected", out
    if re.search(r"out of resource|timed out", out):
        return "out_of_resource", out
    # Exit 2 with only non-axiom warnings (e.g. missing triggers) still verifies.
    if p.returncode == 0 or re.search(r"finished with \d+ verified, 0 errors\s*$", out, re.M):
        return "verified", out
    if p.returncode == 4:
        return "proof_failed", out
    return f"dafny_exit_{p.returncode}", out


def extract_code(text):
    blocks = re.findall(r"```(\w*)[^\n]*\n(.*?)```", text, re.S)
    for lang, body in reversed(blocks):
        if lang.lower() in ("dafny", "dfy", ""):
            return body.strip()
    return None


def parse_reply(cli, stdout):
    """Normalize a CLI's output to text, token counts and raw usage."""
    if cli == "claude":
        d = json.loads(stdout)
        if d.get("is_error"):
            raise RuntimeError(d.get("result") or "claude reported an error")
        u = d["usage"]
        return dict(text=d["result"], model=",".join(d.get("modelUsage", {})),
                    tokens_in=u["input_tokens"] + u.get("cache_creation_input_tokens", 0)
                    + u.get("cache_read_input_tokens", 0),
                    tokens_out=u["output_tokens"], tool_items=0, usage=u)
    events = [json.loads(line) for line in stdout.splitlines() if line.startswith("{")]
    items = [e["item"] for e in events if e.get("type") == "item.completed"]
    texts = [i["text"] for i in items if i.get("type") == "agent_message"]
    if not texts:
        raise RuntimeError("codex produced no agent message")
    usage = [e["usage"] for e in events if e.get("type") == "turn.completed"]
    u = {k: sum(x.get(k, 0) for x in usage) for k in usage[0]} if usage else {}
    return dict(text=texts[-1], model="gpt-5.6-sol",
                tokens_in=u.get("input_tokens", 0),
                tokens_out=u.get("output_tokens", 0),  # already includes reasoning_output_tokens
                tool_items=sum(i.get("type") not in ("agent_message", "reasoning") for i in items),
                usage=u)


def call_cli(cli, prompt):
    """One stateless model call from an empty directory, retrying with backoff."""
    errors = []
    for wait in RETRY_WAITS + [None]:
        with tempfile.TemporaryDirectory() as d:
            try:
                p = subprocess.run(CLIS[cli], input=prompt, capture_output=True, text=True,
                                   cwd=d, timeout=CALL_TIMEOUT)
                if p.returncode != 0:
                    raise RuntimeError(f"exit {p.returncode}: {(p.stderr or p.stdout)[-500:]}")
                return dict(parse_reply(cli, p.stdout), errors=errors)
            except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
                errors.append(str(e)[-500:])
        if wait is None:
            return dict(error=errors[-1], errors=errors)
        time.sleep(wait)


def render(task, dafny_version, code=None, feedback=None):
    preamble = PREAMBLE_BLOCK.format(preamble=task["preamble"]) if task["preamble"] else ""
    prompt = TASK_PROMPT.format(dafny_version=dafny_version, signature=task["signature"],
                                preamble_block=preamble, name=task["name"])
    if feedback is not None:
        prompt += REPAIR_PROMPT.format(code=code or "(none)", feedback=feedback[:FEEDBACK_CHARS])
    return prompt


def run_attempt(task, cli, sample, max_iters, dafny_version, log):
    attempt_id, code, feedback = uuid.uuid4().hex[:12], None, None
    for it in range(1, max_iters + 1):
        prompt = render(task, dafny_version, code, feedback)
        start = time.time()
        reply = call_cli(cli, prompt)
        rec = dict(attempt=attempt_id, task=task["id"], difficulty=task.get("difficulty"),
                   cli=cli, sample=sample, iter=it, prompt_sha=sha(prompt))
        if "error" in reply:
            log(dict(rec, stage="infra_error", final=True, error=reply["error"],
                     errors=reply["errors"]))
            return
        new = extract_code(reply["text"])
        if new is None:
            stage, feedback = "no_code", "No ```dafny code block was found in your reply."
        elif bad := violations(new):
            stage, feedback = "banned", f"Your code uses constructs that are not allowed: {', '.join(bad)}."
        else:
            stage, feedback = verify(task, new)
        code = new if new is not None else code
        done = stage == "verified" or it == max_iters
        log(dict(rec, stage=stage, final=done, seconds=round(time.time() - start, 1),
                 model=reply["model"], tokens_in=reply["tokens_in"], tokens_out=reply["tokens_out"],
                 tool_items=reply["tool_items"], errors=reply["errors"],
                 usage=reply["usage"], code=new, feedback=None if stage == "verified" else feedback,
                 response=reply["text"]))
        if done:
            return


def tool_version(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def settings(tasks, dafny_version):
    """What a run's verdicts depend on; resume and reverify refuse if any of it changed."""
    return dict(tasks=[t["id"] for t in tasks],
                task_sha={t["id"]: sha(json.dumps(t, sort_keys=True)) for t in tasks},
                prompt_sha=sha(TASK_PROMPT + PREAMBLE_BLOCK + REPAIR_PROMPT),
                dafny=dafny_version, dafny_args=DAFNY)


def sample_key(r):
    return r["task"], r["cli"], r["sample"]


def read_records(run_dir):
    path = run_dir / "attempts.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def cmd_check_tasks(args):
    """Every reference solution verifies, and an empty body does not."""
    bad = 0
    for t in load_tasks(args.tasks):
        ok, out = verify(t, t["solution"])
        stub, _ = verify(t, t["signature"] + "\n{\n}")
        fine = ok == "verified" and stub != "verified"
        bad += not fine
        print(f"{'ok ' if fine else 'BAD'} {t['id']:18} solution={ok:13} empty-body={stub}")
        if ok != "verified":
            print("    " + out.replace("\n", "\n    ")[:2000])
    print(f"{bad} problem(s)")
    return 1 if bad else 0


def cmd_run(args):
    tasks, clis = load_tasks(args.tasks), args.clis.split(",")
    run_id = args.resume or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + "-".join(clis)
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=bool(args.resume))
    dafny_version = tool_version(["dafny", "--version"])
    setup = dict(samples=args.samples, max_iters=args.max_iters, **settings(tasks, dafny_version),
                 clis={c: dict(cmd=CLIS[c], version=tool_version([CLIS[c][0], "--version"])) for c in clis})
    if (run_dir / "meta.json").exists():
        meta = json.loads((run_dir / "meta.json").read_text())
        changed = [k for k in setup if meta.get(k) != setup[k]]
        if changed:
            sys.exit(f"can't resume {run_id}: {', '.join(changed)} changed since it started")
    else:
        git = tool_version(["git", "-C", str(GYM), "rev-parse", "HEAD"])
        dirty = bool(tool_version(["git", "-C", str(GYM), "status", "--porcelain"]))
        meta = dict(run_id=run_id, started=datetime.now(timezone.utc).isoformat(),
                    git_commit=git, git_dirty=dirty, z3=tool_version(["z3", "--version"]), **setup)
        (run_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    done = {sample_key(r) for r in read_records(run_dir) if r.get("final") and r["stage"] != "infra_error"}
    todo = [(t, c, s) for t in tasks for c in clis for s in range(1, args.samples + 1)
            if (t["id"], c, s) not in done]
    lock, out = threading.Lock(), open(run_dir / "attempts.jsonl", "a")

    def log(rec):
        with lock:
            out.write(json.dumps(rec) + "\n")
            out.flush()
            if rec["final"]:
                print(f"{rec['task']:18} {rec['cli']:7} s{rec['sample']} iter {rec['iter']}: {rec['stage']}", flush=True)

    print(f"run {run_id}: {len(todo)} attempt(s) to go, {len(done)} already done", flush=True)
    with cf.ThreadPoolExecutor(args.jobs) as pool:
        for f in [pool.submit(run_attempt, t, c, s, args.max_iters, dafny_version, log) for t, c, s in todo]:
            f.result()
    out.close()
    return cmd_summary(argparse.Namespace(run_ids=[run_id]))


def cmd_reverify(args):
    """Re-run Dafny on every recorded program; verdicts must match exactly."""
    meta = json.loads((RUNS / args.run_id / "meta.json").read_text())
    tasks = {t["id"]: t for t in load_tasks(meta["tasks"])}
    now = settings(list(tasks.values()), tool_version(["dafny", "--version"]))
    changed = [k for k in now if k != "prompt_sha" and meta.get(k) != now[k]]
    if changed:
        sys.exit(f"can't reverify {args.run_id}: {', '.join(changed)} changed since the run")
    recs = [r for r in read_records(RUNS / args.run_id)
            if r.get("code") and r["stage"] not in ("banned", "no_code", "infra_error")]
    with cf.ThreadPoolExecutor(args.jobs) as pool:
        stages = list(pool.map(lambda r: verify(tasks[r["task"]], r["code"])[0], recs))
    diffs = [(r, s) for r, s in zip(recs, stages) if s != r["stage"]]
    for r, s in diffs:
        print(f"MISMATCH {r['task']} {r['cli']} s{r['sample']} iter {r['iter']}: recorded {r['stage']}, now {s}")
    print(f"{len(recs) - len(diffs)}/{len(recs)} verdicts reproduced")
    return 1 if diffs else 0


def summarize(run_id):
    recs = read_records(RUNS / run_id)
    # The latest final record per (task, cli, sample) decides it; every call made for a
    # decided sample counts toward tokens, including attempts a crash abandoned.
    finals = {sample_key(r): r for r in recs if r.get("final")}
    stats = {}
    for cli in sorted({r["cli"] for r in finals.values()}):
        done = [r for r in finals.values() if r["cli"] == cli and r["stage"] != "infra_error"]
        used = [r for r in recs if r["cli"] == cli and sample_key(r) in finals]
        won = [r for r in done if r["stage"] == "verified"]
        tokens = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in used)
        stats[cli] = dict(
            attempts=len(done), verified=len(won),
            pass_rate=round(len(won) / len(done), 3) if done else None,
            mean_iters_to_verify=round(sum(r["iter"] for r in won) / len(won), 2) if won else None,
            tokens_per_verified=round(tokens / len(won)) if won else None,
            calls_using_tools=sum(r.get("tool_items", 0) > 0 for r in used),
            infra_errors=sum(r["stage"] == "infra_error" for r in finals.values() if r["cli"] == cli),
            final_stages={s: sum(r["stage"] == s for r in done) for s in sorted({r["stage"] for r in done})},
            by_difficulty={d: f"{sum(r['stage'] == 'verified' for r in done if r.get('difficulty') == d)}"
                              f"/{sum(r.get('difficulty') == d for r in done)}"
                           for d in ("easy", "medium", "hard")})
    return stats


def cmd_summary(args):
    runs = {rid: summarize(rid) for rid in args.run_ids}
    print(json.dumps(runs, indent=2))
    if len(runs) == 2:
        (a, sa), (b, sb) = runs.items()
        for cli in sorted(sa.keys() & sb.keys()):
            if sa[cli]["pass_rate"] is not None and sb[cli]["pass_rate"] is not None:
                diff = abs(sa[cli]["pass_rate"] - sb[cli]["pass_rate"])
                verdict = "within" if diff <= TOLERANCE else "OUTSIDE"
                print(f"{cli}: pass rates differ by {diff:.0%}, {verdict} the {TOLERANCE:.0%} tolerance")
    return 0


# ponytail: flat tolerance for rerun agreement; replace with a paired bootstrap interval for the M3 experiment.
TOLERANCE = 0.15


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check-tasks")
    p.add_argument("--tasks", type=lambda s: s.split(","))
    p = sub.add_parser("run")
    p.add_argument("--clis", default="claude,codex")
    p.add_argument("--samples", type=int, default=3)
    p.add_argument("--max-iters", type=int, default=8)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--tasks", type=lambda s: s.split(","))
    p.add_argument("--resume", metavar="RUN_ID")
    p = sub.add_parser("reverify")
    p.add_argument("run_id")
    p.add_argument("--jobs", type=int, default=4)
    p = sub.add_parser("summary")
    p.add_argument("run_ids", nargs="+")
    args = ap.parse_args()
    return {"check-tasks": cmd_check_tasks, "run": cmd_run, "reverify": cmd_reverify,
            "summary": cmd_summary}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
