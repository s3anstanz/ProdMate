#!/usr/bin/env python3
"""Remember prodmate decisions and past runs in <repo>/.prodmate/state.json.

Usage:
    python3 scripts/state.py show <repo>
    python3 scripts/state.py decide <repo> <item_id> <skip|accept> <reason>
    python3 scripts/state.py record <repo> <statuses.json>
"""
import datetime
import json
import sys
from pathlib import Path

STATUSES = {"Done", "Partial", "Missing", "Can't verify", "Not applicable"}
DECISIONS = {"skip", "accept"}
MAX_RUNS = 10


def state_path(repo):
    return Path(repo) / ".prodmate" / "state.json"


def today():
    return datetime.date.today().isoformat()


def load(repo):
    path = state_path(repo)
    if not path.is_file():
        return {"version": 1, "decisions": {}, "runs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(repo, state):
    path = state_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def record_decision(state, item_id, decision, reason):
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {sorted(DECISIONS)}, not {decision!r}")
    state["decisions"][item_id] = {"decision": decision, "reason": reason, "date": today()}
    return state


def record_run(state, statuses):
    bad = {item: status for item, status in statuses.items() if status not in STATUSES}
    if bad:
        raise ValueError(f"unknown status for {', '.join(f'{k}={v!r}' for k, v in bad.items())}; allowed: {sorted(STATUSES)}")
    state["runs"].append({"date": today(), "statuses": dict(statuses)})
    state["runs"] = state["runs"][-MAX_RUNS:]
    return state


def main(argv):
    if len(argv) < 3 or argv[1] not in ("show", "decide", "record"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    command, repo = argv[1], argv[2]
    data = load(repo)
    try:
        if command == "show":
            print(json.dumps(data, indent=2))
            return 0
        if command == "decide":
            if len(argv) != 6:
                print("usage: state.py decide <repo> <item_id> <skip|accept> <reason>", file=sys.stderr)
                return 2
            record_decision(data, argv[3], argv[4], argv[5])
        else:
            if len(argv) != 4:
                print("usage: state.py record <repo> <statuses.json>", file=sys.stderr)
                return 2
            record_run(data, json.loads(Path(argv[3]).read_text(encoding="utf-8")))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(save(repo, data))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
