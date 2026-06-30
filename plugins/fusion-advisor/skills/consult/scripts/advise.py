#!/usr/bin/env python3
"""fusion-advisor backend.

Consult an OpenRouter Fusion multi-model panel for a second opinion and print
its advice as markdown. Standard library only (no pip install).

Reads a context JSON describing the situation and the RAW artifacts, wraps it in
an advisory prompt, forces Fusion deliberation, and prints
choices[0].message.content.

The OpenRouter API key is resolved from the environment or from project/user
.claude settings files and is NEVER printed.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_PRESET = "general-high"
HTTP_TIMEOUT = 180
MAX_ARTIFACT_CHARS = 200_000  # cap payload to avoid runaway cost


def _candidate_settings_files():
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
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


def get_key():
    """Resolve the OpenRouter API key. Env first, then project/user settings.

    Returns the key string or None. Never prints the value.
    """
    key = os.environ.get("OPENROUTER_API_KEY")
    if key and key.strip():
        return key.strip()
    for path in _candidate_settings_files():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            k = (data.get("env") or {}).get("OPENROUTER_API_KEY")
            if k and k.strip():
                return k.strip()
        except (OSError, ValueError):
            continue
    return None


SETUP_MESSAGE = """\
ERROR: OPENROUTER_API_KEY is not set.

Create a key at https://openrouter.ai/keys (a dedicated key with a spend limit is
recommended), then set it WITHOUT pasting it into the chat, using one of:

  - Environment variable (recommended; set it in your shell profile to persist):
      $env:OPENROUTER_API_KEY = "sk-or-..."   (PowerShell)
      export OPENROUTER_API_KEY=sk-or-...      (bash/zsh)

  - User settings (reuse across projects):
      add to ~/.claude/settings.json      -> {"env": {"OPENROUTER_API_KEY": "sk-or-..."}}

  - Project settings (git-ignored):
      add to .claude/settings.local.json  -> same "env" block

Then re-run the consult."""


ADVISORY_PROMPT_TEMPLATE = """\
You are an independent panel of senior technical advisors to an AI coding agent.
The agent has come to you for a second opinion on a decision, an approach, or a
piece of work. ADVISE it: give a clear recommendation, tell it what it is
missing, and judge whether it is even solving the right problem. Be candid and
specific -- do not rubber-stamp, and flag uncertainty rather than inventing
problems. Prioritize the few things that most change the outcome.

## TASK / SITUATION (what the user asked for)
{task}

## THE AGENT'S APPROACH / PLAN
{approach}

## THE AGENT'S OWN VIEW (committed before consulting you -- judge it independently)
{agent_verdict}

## WHAT'S UNDER CONSIDERATION
{scope}

## SPECIFIC QUESTION / FOCUS (optional)
{focus}

## THE WORK / ARTIFACTS (raw: diff / files / plan)
{artifacts}

---
Weigh: (1) is this the right approach, and is there a materially simpler or safer
one? (2) is it solving the right problem? (3) correctness and logic risks;
(4) security and destructive-operation safety; (5) edge cases and failure modes;
(6) what is missing (tests, docs, migration, backward-compatibility); (7) blind spots.

Respond in this markdown format:

**Recommendation:** <what you would do> -- one or two concrete sentences.

**On track?** ON TRACK | NEEDS CHANGES | WRONG DIRECTION -- one sentence on whether this solves the right problem the right way.

**Key risks / what you may be missing (ranked):**
- [P0|P1|P2|P3] <point> -- why it matters -- what to do -- `file:line` if relevant -- confidence: high|med|low

**What I'd do next:** ...
"""


def build_messages(ctx):
    def field(key, default="(none provided)"):
        v = ctx.get(key)
        if v is None or (isinstance(v, str) and not v.strip()):
            return default
        return str(v)

    artifacts = field("artifacts")
    if len(artifacts) > MAX_ARTIFACT_CHARS:
        artifacts = artifacts[:MAX_ARTIFACT_CHARS] + "\n\n[...truncated for length...]"

    content = ADVISORY_PROMPT_TEMPLATE.format(
        task=field("task"),
        approach=field("approach"),
        agent_verdict=field("agent_verdict"),
        scope=field("scope"),
        focus=field("focus"),
        artifacts=artifacts,
    )
    return [{"role": "user", "content": content}]


def build_payload(messages, preset, panel):
    plugin = {"id": "fusion"}
    if panel:
        plugin["analysis_models"] = panel
    else:
        plugin["preset"] = preset
    return {
        "model": "openrouter/fusion",
        "plugins": [plugin],
        # Force the panel to run -- we explicitly asked for a second opinion.
        "tool_choice": "required",
        "messages": messages,
    }


def main():
    # Emit clean UTF-8 regardless of the Windows console code page.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="fusion-advisor backend")
    ap.add_argument("--input", required=True,
                    help="path to context JSON, or '-' for stdin")
    ap.add_argument("--preset",
                    default=os.environ.get("FUSION_ADVISOR_PRESET", DEFAULT_PRESET))
    args = ap.parse_args()

    key = get_key()
    if not key:
        sys.stderr.write(SETUP_MESSAGE + "\n")
        return 2

    try:
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            with open(args.input, "r", encoding="utf-8") as f:
                raw = f.read()
        ctx = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError) as e:
        sys.stderr.write(f"ERROR: could not read context JSON: {e}\n")
        return 1

    panel_env = os.environ.get("FUSION_ADVISOR_PANEL", "").strip()
    panel = [m.strip() for m in panel_env.split(",") if m.strip()] if panel_env else None

    payload = build_payload(build_messages(ctx), args.preset, panel)

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/fusion-advisor",
            "X-Title": "fusion-advisor",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            pass
        sys.stderr.write(f"ERROR: OpenRouter HTTP {e.code}: {detail[:500]}\n")
        return 1
    except (urllib.error.URLError, TimeoutError) as e:
        sys.stderr.write(f"ERROR: network/timeout calling OpenRouter: {e}\n")
        return 1

    if isinstance(body, dict) and body.get("error"):
        err = body["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        sys.stderr.write(f"ERROR: OpenRouter returned an error: {msg}\n")
        return 1

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        reason = ""
        if isinstance(body, dict):
            reason = body.get("failure_reason") or json.dumps(body)[:500]
        sys.stderr.write(f"ERROR: no advice returned. Detail: {reason}\n")
        return 1

    if not content or not content.strip():
        sys.stderr.write("ERROR: empty response returned by the panel.\n")
        return 1

    sys.stdout.write(content.rstrip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
