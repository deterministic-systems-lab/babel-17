"""WP8's done-when: every example in docs/manual.md has the outcome it states, and every code in
docs/b17-0.md §9 has an example. uv run --no-project b17c/test_manual.py

An example is a ```lisp block right after a line `<!-- expect: OUTCOME -->`. OUTCOME is `ok`, a
tier 0 code such as E-OWN-001, or a proof family such as E-PROOF-POST. A block that isn't a whole
module is checked inside one. Proof outcomes need z3 on PATH, so CI checks only that those
examples pass tier 0.
"""
import re
import shutil
import tempfile
from pathlib import Path

import check as C
import verify as V
from syntax import ParseError, parse

ROOT = Path(__file__).resolve().parent.parent
MANUAL = (ROOT / "docs" / "manual.md").read_text()
DOC = (ROOT / "docs" / "b17-0.md").read_text()
EXAMPLE = re.compile(r"<!-- expect: (\S+) -->\n```lisp\n(.*?)```", re.S)
WRAP = '(module example\n  (header (purpose "An example.") (invariants "None.") (failures "None."))\n{}\n)'
z3 = shutil.which("z3")
cache = Path(tempfile.mkdtemp())

failures, seen = [], set()
for k, (want, text) in enumerate(EXAMPLE.findall(MANUAL), 1):
    seen.add(want)
    src = text if text.lstrip().startswith("(module") else WRAP.format(text.rstrip())
    where = f"example {k} ({want}): {text.strip().splitlines()[0][:60]}"
    try:
        m = parse(src.encode())
    except ParseError as e:
        if want != "E-PARSE-001":
            failures.append(f"{where}: doesn't parse: {e}")
        continue
    if want == "E-PARSE-001":
        failures.append(f"{where}: parses")
        continue
    codes = sorted({d.code for d in C.check(m)})
    if want.startswith("E-PROOF-") or want == "ok":
        if codes:
            failures.append(f"{where}: fails tier 0 with {codes}")
        elif z3:
            failed = sorted({"E-PROOF-" + r["family"] for r in V.verify(m, 1, cache)[0] if r["verdict"] != "proved"})
            if failed != ([] if want == "ok" else [want]):
                failures.append(f"{where}: proof outcome {failed or 'all proved'}")
    elif codes != [want]:
        failures.append(f"{where}: tier 0 gives {codes or 'nothing'}")

# Every code in §9's tables has an example.
codes = set()
for first, last in re.findall(r"^\| `(E-[A-Z0-9-]+)`(?: to `(E-[A-Z0-9-]+)`)? \|", DOC, re.M):
    if last:
        codes |= {f"{first[:-3]}{n:03}" for n in range(int(first[-3:]), int(last[-3:]) + 1)}
    else:
        codes.add(first)
missing = sorted(codes - seen)
if missing:
    failures.append(f"codes with no example: {', '.join(missing)}")

assert not failures, "\n".join(failures)
print(f"manual self-check passed: {len(EXAMPLE.findall(MANUAL))} examples, all {len(codes)} codes covered"
      + ("" if z3 else " (without z3: proof outcomes not checked)"))
