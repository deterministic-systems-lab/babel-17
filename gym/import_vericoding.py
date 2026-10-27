"""Port vericoding's hardest integer-and-vector Dafny tasks into gym/tasks/vericoding/.

    git clone https://github.com/Beneficial-AI-Foundation/vericoding-benchmark <dir>
    uv run gym/import_vericoding.py <dir>

Selection uses vericoding's own results (nine 2025 models): Dafny tasks with one method,
no vericoding QA issue, and only types B17-0 can also express (int, nat and bool, sequences
and arrays of those, and ghost multisets), solved by at least one model but by at most a
quarter of them. The solving
model's code becomes the reference solution. A task is kept only if that solution passes
this harness as is: no banned construct in it or in the frozen preamble (some preambles hold
helper methods whose body is `assume false`), and verified under our Dafny with ghost preambles.
"""
import csv
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import harness
from import_algoveri import ghost, section

OUT = Path(__file__).resolve().parent / "tasks" / "vericoding"
# ponytail: a regex over the whole task, so a banned word in a comment also excludes it.
NOT_B17_0 = re.compile(r"\b(datatype|codatatype|class|trait|real|char|string|map|imap|set|iset|object"
                       r"|array2|array3|bv\d+|ORDINAL|iterator)\b|seq<\s*seq|<\s*T\b|\(\s*(int|nat|bool)\s*,")
MAX_SOLVED_SHARE = 0.25


def main(src):
    src = Path(src)
    commit = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    solved = defaultdict(dict)
    for r in csv.DictReader(open(src / "vericoding_results_v1.csv")):
        if r["Language"] == "dafny":
            solved[r["Task ID"]][r["LLM"]] = solved[r["Task ID"]].get(r["LLM"], False) or r["Success"] == "1"
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "LICENSE", OUT / "LICENSE")
    ported, dropped = 0, []
    for line in open(src / "jsonl" / "dafny_tasks.jsonl"):
        t = json.loads(line)
        by = solved.get(t["id"], {})
        k = sum(by.values())
        whole = "\n".join(t[s] for s in ("vc-preamble", "vc-helpers", "vc-spec", "vc-postamble"))
        if (t["qa-issue"] not in (0, "0") or t["vc-spec"].count("method ") != 1 or NOT_B17_0.search(whole)
                or not by or k == 0 or k / len(by) > MAX_SOLVED_SHARE):
            continue
        done = (src / "vericoded" / f"{t['id']}_vericoded.dfy").read_text()
        solution = "\n\n".join(p for p in (section(done, "vc-helpers"), section(done, "vc-spec"),
                                            section(done, "vc-code")) if p)
        preamble = ghost("\n\n".join(t[s].strip() for s in ("vc-preamble", "vc-helpers", "vc-postamble")
                                     if t[s].strip()))
        intent = " ".join(re.split(r"(?<=\.)\s", t["vc-description"].strip(), maxsplit=1)[0].split()) or "(no description in the source)"
        path = OUT / f"{t['id']}.dfy"
        path.write_text(
            f"// intent: {intent}\n// difficulty: vericoding\n"
            f"// source: vericoding {commit[:12]} {t['id']} ({t['source']} {t['source-id']}; MIT),"
            f" solved by {k} of {len(by)} models\n"
            f"//== preamble\n{preamble}\n//== signature\n{t['vc-spec'].strip()}\n//== solution\n{solution}\n")
        task = harness.load_task(path)
        stage = ("banned" if harness.violations(preamble) + harness.violations(solution)
                 else harness.verify(task, solution)[0])
        if stage != "verified":
            path.unlink()
            dropped.append(f"{t['id']} ({stage})")
            continue
        ported += 1
    print(f"ported {ported}; dropped {len(dropped)} that fail here: {', '.join(dropped)}")


if __name__ == "__main__":
    main(sys.argv[1])
