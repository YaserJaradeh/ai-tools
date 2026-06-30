#!/usr/bin/env python3
"""fusion-advisor Stop hook -- a cheap, dumb nudge.

When Claude finishes a turn, if there is a non-trivial, un-consulted change in a
git working tree (and a key is configured), inject a one-line note suggesting the
agent consult the fusion-advisor panel. The MODEL decides whether to act. No
network, no model call.

Fails silent (exit 0, no output) on anything unexpected, so it never blocks or
nags during normal work. Loop safety comes from hash de-duplication plus a
per-session cap -- this is the only place a nudge is ever emitted.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

MIN_LINES = int(os.environ.get("FUSION_ADVISOR_MIN_LINES", "20"))
MAX_NUDGES = int(os.environ.get("FUSION_ADVISOR_MAX_NUDGES", "3"))


def silent_exit():
    sys.exit(0)


def auto_enabled():
    v = os.environ.get("FUSION_ADVISOR_AUTO", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _candidate_settings_files(cwd):
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    home = os.path.expanduser("~")
    out, seen = [], set()
    for p in (
        os.path.join(proj, ".claude", "settings.local.json"),
        os.path.join(proj, ".claude", "settings.json"),
        os.path.join(home, ".claude", "settings.local.json"),
        os.path.join(home, ".claude", "settings.json"),
    ):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def has_key(cwd):
    """Presence check only -- never reads or returns the value."""
    if (os.environ.get("OPENROUTER_API_KEY") or "").strip():
        return True
    for path in _candidate_settings_files(cwd):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if (((data.get("env") or {}).get("OPENROUTER_API_KEY")) or "").strip():
                return True
        except (OSError, ValueError):
            continue
    return False


def git(cwd, *args):
    return subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True, text=True, timeout=15,
    )


def is_git_repo(cwd):
    try:
        r = git(cwd, "rev-parse", "--is-inside-work-tree")
        return r.returncode == 0 and r.stdout.strip() == "true"
    except (OSError, subprocess.SubprocessError):
        return False


def _read_text(path, cap=1_000_000):
    try:
        if os.path.isfile(path) and os.path.getsize(path) <= cap:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
    except OSError:
        pass
    return ""


def change_signature(cwd):
    """Return (changed_lines, file_count, hash) over tracked diff + untracked files."""
    try:
        tracked = git(cwd, "diff", "HEAD").stdout
    except (OSError, subprocess.SubprocessError):
        tracked = ""
    try:
        status = git(cwd, "status", "--porcelain").stdout
    except (OSError, subprocess.SubprocessError):
        status = ""

    if not tracked and not status:
        return 0, 0, ""

    files = set()
    untracked_files = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:  # rename: "old -> new"
            path = path.split(" -> ", 1)[1]
        files.add(path)
        if code == "??":
            untracked_files.append(path)

    untracked_blobs = [_read_text(os.path.join(cwd, p)) for p in untracked_files]

    diff_lines = sum(
        1 for ln in tracked.splitlines()
        if (ln.startswith("+") or ln.startswith("-"))
        and not ln.startswith("+++") and not ln.startswith("---")
    )
    untracked_lines = sum(b.count("\n") + 1 for b in untracked_blobs if b)
    changed = diff_lines + untracked_lines

    combined = tracked + "\x00" + "\x00".join(untracked_blobs)
    h = hashlib.sha256(combined.encode("utf-8", "replace")).hexdigest()
    return changed, len(files), h


def marker_path(session_id):
    d = os.path.join(tempfile.gettempdir(), "fusion-advisor")
    os.makedirs(d, exist_ok=True)
    safe = "".join(c for c in (session_id or "") if c.isalnum() or c in "-_")
    return os.path.join(d, f"{safe or 'session'}.json")


def load_marker(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"last_hash": "", "count": 0}


def save_marker(path, last_hash, count):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"last_hash": last_hash, "count": count}, f)
    except OSError:
        pass


def main():
    if not auto_enabled():
        silent_exit()

    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        silent_exit()

    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id") or ""

    if not has_key(cwd):
        silent_exit()
    if not is_git_repo(cwd):
        silent_exit()

    changed, files, h = change_signature(cwd)
    if not h or changed < MIN_LINES:
        silent_exit()

    mpath = marker_path(session_id)
    marker = load_marker(mpath)
    if h == marker.get("last_hash"):
        silent_exit()
    if marker.get("count", 0) >= MAX_NUDGES:
        silent_exit()

    save_marker(mpath, h, marker.get("count", 0) + 1)

    note = (
        f"You've made a non-trivial change (~{changed} lines across {files} "
        f"file(s)) without a second opinion. If it reflects a real decision, "
        f"plan, approach, or update worth pressure-testing -- not just a "
        f"mechanical edit -- consult the fusion-advisor panel before finishing."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": note,
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
