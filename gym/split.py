"""WP11's held-out split (D123), frozen in gym/split.json, and the secret it rests on.

The secret is 32 random bytes, written in hex to ~/.config/babel-17/gym-secret, readable only by its
owner and never in the repository. split.json records its SHA-256, and nothing scores a reply or
draws held-out inputs under another. Losing it means freezing a new split, with new inputs.

A task's problem is its entry in split.json's table of problems, or else its name. The table maps
names across sources that pose the same problem, and is reviewed as tasks arrive. Held out are the
gate's test set, M3's 34 tasks; any task posing one of their problems; and 1 problem in 10 of the
rest, chosen by the secret's HMAC of its name. So a problem is held out or trained on, never both.
"""
import hashlib
import hmac
import json
from pathlib import Path

import harness as h

SPLIT = h.GYM / "split.json"
SECRET = Path.home() / ".config" / "babel-17" / "gym-secret"


def load(split=SPLIT):
    return json.loads(Path(split).read_text())


def secret(path=SECRET):
    return bytes.fromhex(Path(path).read_text().strip())


def check_secret(key, split):
    """Refuse to go on without the secret whose hash the split records."""
    if hashlib.sha256(key).hexdigest() != split["secret_sha256"]:
        raise ValueError("the secret doesn't match the one the split records")


def mac(key, domain, *parts):
    """The secret's HMAC of parts in a domain, inputs or slice, as a 64-bit number."""
    return int.from_bytes(hmac.new(key, b"\0".join(s.encode() for s in (domain, *parts)), hashlib.sha256).digest()[:8], "big")


def problem(split, task_id):
    return split["problems"].get(task_id, task_id.rsplit("/", 1)[-1])


def held_out(split, key, task_id):
    p = problem(split, task_id)
    return p in {problem(split, t) for t in split["test"]} or mac(key, "slice", p) % 10 == 0
