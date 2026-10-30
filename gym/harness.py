"""WP17 baseline harness: agents write verified Dafny for frozen tasks.

    uv run gym/harness.py check-tasks
    uv run gym/harness.py run --clis claude,codex --samples 3 [--tasks abs,fib] [--resume RUN_ID]
    uv run gym/harness.py reverify RUN_ID
    uv run gym/harness.py summary RUN_ID [OTHER_RUN_ID]

B17-0 tasks (M3's track, D98) are b17/NAME, one per seed program in suite/accept/. Each
poses the program's header, its one spec and the ghost-fns that spec refers to; the agent
adds a def and any helpers, with docs/manual.md in its prompt, and is verified by b17c.

Each file in gym/tasks/ has three sections: a preamble of frozen definitions, the method
signature with its contracts, and a hidden reference solution. An agent's code is checked
as: its code, then the preamble, then a generated <Name>_Check method that calls <Name>
under the frozen contracts, so an agent can't weaken them. Agent code goes first so
Dafny's line numbers match the code the agent wrote.

An attempt is one task, one CLI and one sample: up to --max-iters rounds of
generate, check, and feed the verifier's output back. Every round is a fresh,
stateless call carrying the task, the previous code and the stock Dafny output.
Run one process per run ID; resume assumes nothing else is writing to it.
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
B17C, SUITE, MANUAL = GYM.parent / "b17c", GYM.parent / "suite" / "accept", GYM.parent / "docs" / "manual.md"

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
    # agy takes the prompt as an argument; "{prompt}" marks where it goes. "-high" is the effort.
    "gemini": ["agy", "-p", "{prompt}", "--model", "gemini-4-argon-high", "--output-format", "json",
               "--disable-slash-commands"],
    # grok reads ~/.claude (CLAUDE.md, skills, plugins with hooks, MCP servers) and ignores its own
    # opt-out env vars, so HOME is emptied; GROK_HOME keeps the login. --tools "" removes nothing,
    # so every client tool is disallowed by name. X search is server-side and can't be removed:
    # streaming-json reports each use as a tool_call event.
    "grok": ["env", "HOME=/var/empty", f"GROK_HOME={Path.home() / '.grok'}", "grok", "-p", "{prompt}",
             "--verbatim", "-m", "grok-4.7", "--reasoning-effort", "high", "--disallowed-tools",
             "run_terminal_command,read_file,search_replace,list_dir,grep,kill_command_or_subagent,"
             "todo_write,get_command_or_subagent_output,monitor,search_tool,use_tool,workflow,"
             "enter_plan_mode,exit_plan_mode,ask_user_question,send_feedback,image_gen,image_edit,"
             "image_to_video,reference_to_video,write,scheduler_create,scheduler_delete,scheduler_list",
             "--disable-web-search", "--no-subagents", "--no-plan", "--max-turns", "1",
             "--output-format", "streaming-json"],
}
CALL_TIMEOUT, RETRY_WAITS = 1800, [60, 120, 240, 480, 960, 1800]
# Dafny's resource limit bounds a verification; this only backstops a hang. At 30 minutes, a
# run near the limit timed out under 6 parallel jobs and ran out of resource alone (18 minutes).
VERIFY_TIMEOUT = 4 * CALL_TIMEOUT
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

B17_TASK_PROMPT = """Write B17-0 code that passes b17c with every proof goal discharged.

This is B17-0's reference manual:

{manual}

The task module:

```lisp
{frozen}
```

Rules:
- Write a def for the spec {name}. You may add lemmas, ghost-fns, and spec and def pairs for helpers. Every spec you add needs a def.
- Your items are added to the task module after its items, so don't restate them. Your first line is line {first_line} of the module that's checked.
- Answer directly without using tools. Reply with your items, and only your items, in one ```lisp block.
"""
B17_REPAIR_PROMPT = """
Your previous items:

```lisp
{code}
```

The check failed. These are b17c's diagnostics (D93), with lines counted in the whole module:

{feedback}

Reply with your complete corrected items in one ```lisp block.
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
# ponytail: block comments don't nest here, and an identifier like x'a' can look like a
# char literal, so some legal code is falsely flagged (never falsely passed); a real
# Dafny lexer fixes both if that ever bites.
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


def parenthesized(text, start):
    """The text inside the parentheses opening at text[start], and the index after them."""
    depth = 0
    for i in range(start, len(text)):
        depth += (text[i] == "(") - (text[i] == ")")
        if depth == 0:
            return text[start + 1:i], i + 1
    raise ValueError(f"unbalanced parentheses in: {text[start:start + 80]}")


def load_task(path):
    text = path.read_text()
    parts = re.split(r"^//== (preamble|signature|solution)\s*$", text, flags=re.M)
    sec = {k: v.strip() for k, v in zip(parts[1::2], parts[2::2])}
    meta = dict(re.findall(r"^// (\w+): (.*)$", parts[0], re.M))
    sig = sec["signature"]
    m = re.match(r"method\s+(\w+)\s*(?:<[^(]*>)?\s*", sig)
    name = m.group(1)
    params, end = parenthesized(sig, m.end())
    r = re.match(r"\s*returns\s*", sig[end:])
    rets, end = parenthesized(sig, end + r.end()) if r else ("", end)
    call = f"{', '.join(param_names(rets))} := " if rets else ""
    check = (f"method {name}_Check{sig[m.end(1):]}\n"
             f"{{\n  {call}{name}({', '.join(param_names(params))});\n}}")
    return dict(id=str(path.relative_to(TASKS).with_suffix("")), name=name, preamble=sec["preamble"], signature=sig,
                solution=sec["solution"], check=check, **meta)


def b17c():
    """b17c's agent and syntax modules, imported on first use: they import each other by bare name."""
    if str(B17C) not in sys.path:
        sys.path.insert(0, str(B17C))
    import agent
    import syntax
    return agent, syntax


def load_b17_task(path):
    """A seed task in B17-0 (D98): the suite program's header, its one spec, and the ghost-fns
    that spec refers to, transitively, cut from its source. Its def and any lemma or ghost-fn
    only a proof uses are the hidden solution."""
    _, syntax = b17c()
    text = path.read_text()
    m = syntax.parse(text.encode(), 0)  # M3's track is B17-0 (D101)
    items = [it for it in m.items[3:] if it.items[0].text != "def"]
    [spec] = [it for it in items if it.items[0].text == "spec"]
    fns = {it.items[1].text: it for it in items if it.items[0].text == "ghost-fn"}
    keep, todo = set(), [spec]
    while todo:
        it = todo.pop()
        if it.items[1].text not in keep:
            keep.add(it.items[1].text)
            stack = [it]
            while stack:  # every name it mentions that's a ghost-fn
                x = stack.pop()
                if isinstance(x, syntax.Form):
                    stack.extend(x.items)
                elif isinstance(x, syntax.Sym) and x.text in fns:
                    todo.append(fns[x.text])
    lines = text.split("\n")
    offset = lambda pos: sum(len(line) + 1 for line in lines[:pos[0] - 1]) + pos[1] - 1
    kept = [text[offset(it.pos):offset(it.end) + 1] for it in items if it.items[1].text in keep]
    frozen = text[:offset(m.items[3].pos)] + "\n  ".join(kept) + ")"
    dafny = TASKS / f"{path.stem}.dfy"
    meta = dict(re.findall(r"^// (\w+): (.*)$", dafny.read_text(), re.M)) if dafny.exists() else {}
    return dict(id=f"b17/{path.stem}", lang="b17", name=spec.items[1].text, frozen=frozen,
                solution=text, difficulty=meta.get("difficulty"))


def load_tasks(only=None):
    tasks = [load_task(p) for p in sorted(TASKS.rglob("*.dfy"))] + [load_b17_task(p) for p in sorted(SUITE.glob("*.b17"))]
    # An entry ending in "/" selects a whole task set, e.g. "algoveri/".
    return [t for t in tasks if not only
            or any(t["id"] == o or (o.endswith("/") and t["id"].startswith(o)) for o in only)]


def violations(code):
    bare = "".join(" " if t[:2] in ("//", "/*") or t[:1] == '"' or t[:2] == '@"' or (t[:1] == "'" and len(t) > 1)
                   else t for t in TOKEN.findall(code))
    found = [k for k, rx in BANNED.items() if re.search(rx, bare)]
    attrs = re.findall(r"\{:\s*(\w+)|(?<![\w@])@\s*([A-Za-z]\w*)", bare)
    return found + sorted({f"{{:{a}}}" if a else f"@{b}" for a, b in attrs if (a or b) not in SAFE_ATTRIBUTES})


def verify(task, code):
    """Check agent code against a task. Returns (stage, the checker's output)."""
    if task.get("lang") == "b17":
        return verify_b17(task, code)
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "program.dfy"
        f.write_text(f"{code}\n\n// ---- appended by the harness ----\n"
                     f"{task['preamble']}\n\n{task['check']}\n")
        try:
            p = subprocess.run(DAFNY + [str(f)], capture_output=True, text=True, timeout=VERIFY_TIMEOUT)
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


def verify_b17(task, code):
    """The agent's items added to the task module (D98). Verified when tier 0 passes, every spec
    has a def, and every goal is proved under the canonical seed and 10 shuffled ones (D23).
    Specs are modular, so a spec with no def would let a call assume anything."""
    agent, syntax = b17c()
    try:
        m = syntax.parse((task["frozen"][:-1] + "\n" + code + ")").encode(), 0)
    except syntax.ParseError as e:
        return "rejected", json.dumps([{"code": e.code, "node": f"module@{e.line}:{e.col}", "message": e.reason}], indent=1)
    try:
        if errors := agent.tier0(m):
            return "rejected", json.dumps(errors, indent=1)
        defs = {it.items[1].text for it in m.items[3:] if it.items[0].text == "def"}
        if missing := [it.items[1].text for it in m.items[3:] if it.items[0].text == "spec" and it.items[1].text not in defs]:
            return "no_def", f"Every spec needs a def, and these have none: {', '.join(missing)}."
        with tempfile.TemporaryDirectory() as cache:  # a fresh cache, so every verdict is solved anew
            diags = agent.diagnostics(m, cache=Path(cache))  # as Dafny's are, and reverify is independent
    except Exception as e:  # a b17c bug, not the agent's: an infrastructure error, retried on resume
        return "checker_error", f"{type(e).__name__}: {e}"
    if errors := [d for d in diags if " goal is error" in d["message"]]:  # Z3 itself failed
        return "checker_error", json.dumps(errors, indent=1)
    return ("verified", "") if not diags else ("proof_failed", json.dumps(diags, indent=1))


def allows_panic(task):
    """Whether a B17-0 task's spec lists panic: ensures bind only normal returns, so such a spec
    is met by a def that always panics, and the task would grade nothing."""
    _, syntax = b17c()
    spec = next(it for it in syntax.parse(task["frozen"].encode(), 0).items[3:] if it.items[0].text == "spec")
    effects = next(c for c in spec.items if isinstance(c, syntax.Form) and c.items[0].text == "effects")
    return any(e.text == "panic" for e in effects.items[1:])


def extract_code(text, lang="dafny"):
    blocks = re.findall(r"```(\w*)[^\n]*\n(.*?)```", text, re.S)
    for fence, body in reversed(blocks):
        if fence.lower() in (("lisp", "") if lang == "b17" else ("dafny", "dfy", "")):
            return body.strip()
    return None


def model_of(cli):
    cmd = CLIS[cli]
    return next(cmd[i + 1] for i, a in enumerate(cmd) if a in ("-m", "--model"))


def parse_reply(cli, stdout):
    """Normalize a CLI's output to text, token counts and raw usage."""
    if cli == "gemini":
        d = json.loads(stdout)
        if d.get("status") != "SUCCESS":
            raise RuntimeError(f"agy status {d.get('status')}: {stdout[:300]}")
        u = d["usage"]
        # output_tokens already includes thinking_tokens (total_tokens = input + output).
        return dict(text=d["response"], model=model_of(cli), tokens_in=u["input_tokens"],
                    tokens_out=u["output_tokens"], tool_items=d.get("num_turns", 1) - 1, usage=u)
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
    if cli == "grok":
        end = next((e for e in events if e.get("type") == "end"), None)
        if end is None:
            raise RuntimeError(f"grok produced no end event: {stdout[-300:]}")
        u = end["usage"]
        return dict(text="".join(e["data"] for e in events if e.get("type") == "text"),
                    model=",".join(end.get("modelUsage", {})),
                    tokens_in=u["input_tokens"] + u.get("cache_read_input_tokens", 0)
                    + u.get("cache_creation_input_tokens", 0),
                    tokens_out=u["output_tokens"],  # already includes reasoning_tokens
                    tool_items=sum(e.get("type") == "tool_call" for e in events), usage=u)
    items = [e["item"] for e in events if e.get("type") == "item.completed"]
    texts = [i["text"] for i in items if i.get("type") == "agent_message"]
    if not texts:
        raise RuntimeError("codex produced no agent message")
    usage = [e["usage"] for e in events if e.get("type") == "turn.completed"]
    u = {k: sum(x.get(k, 0) for x in usage) for k in usage[0]} if usage else {}
    return dict(text=texts[-1], model=model_of(cli),
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
                as_arg = "{prompt}" in CLIS[cli]
                p = subprocess.run([prompt if a == "{prompt}" else a for a in CLIS[cli]],
                                   input="" if as_arg else prompt, capture_output=True, text=True,
                                   cwd=d, timeout=CALL_TIMEOUT)
                if p.returncode != 0:
                    raise RuntimeError(f"exit {p.returncode}: {(p.stderr or p.stdout)[-500:]}")
                return dict(parse_reply(cli, p.stdout), errors=errors)
            except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
                errors.append(str(e)[-500:])
        # A quota that resets after the whole retry budget won't recover by waiting (agy's wording).
        reset = re.search(r"Resets in (\d+)h(?:(\d+)m)?", errors[-1])
        if wait is None or reset and int(reset[1]) * 3600 + int(reset[2] or 0) * 60 > sum(RETRY_WAITS):
            return dict(error=errors[-1], errors=errors)
        time.sleep(wait)


def render(task, dafny_version, code=None, feedback=None):
    if task.get("lang") == "b17":
        prompt = B17_TASK_PROMPT.format(manual=MANUAL.read_text(), frozen=task["frozen"], name=task["name"],
                                        first_line=task["frozen"].count("\n") + 2)
        if feedback is not None:
            prompt += B17_REPAIR_PROMPT.format(code=code or "(none)", feedback=feedback[:FEEDBACK_CHARS])
        return prompt
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
        lang = task.get("lang", "dafny")
        rec = dict(attempt=attempt_id, task=task["id"], lang=lang, difficulty=task.get("difficulty"),
                   cli=cli, sample=sample, iter=it, prompt_sha=sha(prompt))
        if "error" in reply:
            log(dict(rec, stage="infra_error", final=True, error=reply["error"],
                     errors=reply["errors"]))
            return
        new = extract_code(reply["text"], lang)
        if new is None:
            fence = "lisp" if lang == "b17" else "dafny"
            stage, feedback = "no_code", f"No ```{fence} code block was found in your reply."
        elif lang == "dafny" and (bad := violations(new)):
            stage, feedback = "banned", f"Your code uses constructs that are not allowed: {', '.join(bad)}."
        else:
            stage, feedback = verify(task, new)
        if stage == "checker_error":  # like a failed call: not a verdict on the agent, so resume retries it
            log(dict(rec, stage="infra_error", final=True, error=feedback, errors=reply["errors"], code=new))
            return
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
    s = dict(tasks=[t["id"] for t in tasks],
             task_sha={t["id"]: sha(json.dumps(t, sort_keys=True)) for t in tasks},
             z3=tool_version(["z3", "--version"]), harness_sha=sha(Path(__file__).read_text()))
    if any(t.get("lang", "dafny") == "dafny" for t in tasks) or not tasks:  # Dafny verdicts rest on Dafny
        s |= dict(prompt_sha=sha(TASK_PROMPT + PREAMBLE_BLOCK + REPAIR_PROMPT), dafny=dafny_version, dafny_args=DAFNY)
    if any(t.get("lang") == "b17" for t in tasks):  # B17-0 verdicts rest on b17c and the manual
        sources = sorted(B17C.glob("*.py")) + [B17C / "core.b17"]
        s |= dict(b17_prompt_sha=sha(B17_TASK_PROMPT + B17_REPAIR_PROMPT + MANUAL.read_text()),
                  b17c_sha=sha("".join(f.name + f.read_text() for f in sources if not f.name.startswith("test_"))))
    return s


def sample_key(r):
    return r["task"], r["cli"], r["sample"]


def read_records(run_dir):
    path = run_dir / "attempts.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def cmd_check_tasks(args):
    """No preamble or reference solution uses a banned construct; every reference solution
    verifies; an empty body is a proof failure (not vacuously
    true); an assume-false body verifies (the frozen preamble and contracts are well-formed,
    so the task is solvable in principle). Imported tasks with no solution skip the first."""
    bad = 0
    for t in load_tasks(args.tasks):
        if t.get("lang") == "b17":  # the suite program verifies; the task alone has no def
            ok, out = verify_b17(dict(t, frozen=t["solution"].rstrip()), "")
            stub, stub_out = verify_b17(t, "")
            if allows_panic(t):
                ok, out = "allows_panic", "a task spec that allows panic is met by a def that always panics"
            fine = ok == "verified" and stub == "no_def"
            bad += not fine
            print(f"{'ok ' if fine else 'BAD'} {t['id']:34} solution={ok:13} no-def={stub}")
            if not fine:
                print("    " + (out if ok != "verified" else stub_out).replace("\n", "\n    ")[:2000])
            continue
        # A frozen preamble with assume or {:axiom} hands every solution an unproved fact.
        banned = violations(t["preamble"]) + violations(t["solution"])
        ok, out = (("banned", ", ".join(banned)) if banned else
                   verify(t, t["solution"]) if t["solution"] else ("none", ""))
        stub, stub_out = verify(t, t["signature"] + "\n{\n}")
        wf, wf_out = verify(t, t["signature"] + "\n{\n  assume {:axiom} false;\n}")
        fine = ok in ("verified", "none") and stub == "proof_failed" and wf == "verified"
        bad += not fine
        print(f"{'ok ' if fine else 'BAD'} {t['id']:34} solution={ok:13} empty-body={stub:13} well-formed={wf}")
        if not fine:
            why = out if ok not in ("verified", "none") else wf_out if wf != "verified" else stub_out
            print("    " + why.replace("\n", "\n    ")[:2000])
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
                    git_commit=git, git_dirty=dirty, **setup)
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
    # Verdict changes from a harness edit show up as mismatches below, so its hash isn't required.
    changed = [k for k in now if k not in ("prompt_sha", "b17_prompt_sha", "harness_sha") and meta.get(k) != now[k]]
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
    # Real verdicts sort after infra errors, so a real verdict wins, as it does for resume.
    finals = {sample_key(r): r for r in sorted((r for r in recs if r.get("final")),
                                                key=lambda r: r["stage"] != "infra_error")}
    stats = {}
    # B17-0 attempts count apart from Dafny ones, as CLI/b17; records from before D98 are Dafny's.
    track = lambda r: r["cli"] + ("/b17" if r.get("lang") == "b17" else "")
    for cli in sorted({track(r) for r in finals.values()}):
        done = [r for r in finals.values() if track(r) == cli and r["stage"] != "infra_error"]
        used = [r for r in recs if track(r) == cli and sample_key(r) in finals]
        won = [r for r in done if r["stage"] == "verified"]
        tokens = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in used)
        stats[cli] = dict(
            attempts=len(done), verified=len(won),
            pass_rate=round(len(won) / len(done), 3) if done else None,
            mean_iters_to_verify=round(sum(r["iter"] for r in won) / len(won), 2) if won else None,
            tokens_per_verified=round(tokens / len(won)) if won else None,
            calls_using_tools=sum(r.get("tool_items", 0) > 0 for r in used),
            infra_errors=sum(r["stage"] == "infra_error" for r in finals.values() if track(r) == cli),
            final_stages={s: sum(r["stage"] == s for r in done) for s in sorted({r["stage"] for r in done})},
            by_difficulty={d: f"{sum(r['stage'] == 'verified' for r in done if r.get('difficulty') == d)}"
                              f"/{sum(r.get('difficulty') == d for r in done)}"
                           for d in sorted({r.get("difficulty") for r in done}, key=str)})
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
