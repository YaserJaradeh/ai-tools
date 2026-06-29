---
name: review
description: Get an independent second opinion on the current work from a multi-model panel (top models across labs) via OpenRouter Fusion. Reviews a diff, files, or a plan for correctness, security, edge cases, and whether it solves the right problem.
when_to_use: Use before committing to an approach, when an error keeps recurring, before declaring a task done, at ambiguous or high-stakes decisions, or when the user asks for a "second opinion", "sanity check", "independent review", "panel review", or "am I on the right track".
argument-hint: "[optional focus, e.g. 'the locking logic']"
---

# Fusion Advisor — independent multi-model second opinion

Get a skeptical review of the current work from an OpenRouter Fusion panel (top
models from multiple labs + a judge). Treat it as an advisor, not an oracle:
triage and verify before acting. A review costs ~3–5× a normal model call and
takes ~30–120s, so use it for decisions that matter, not trivial edits.

When this skill is invoked, follow these steps.

## 1. Decide if a review is worth it
This is your judgment call. **Skip** (and say so in one line) for trivial or
mechanical changes: formatting, renames, comments, docs, config bumps, tiny
one-liners. **Proceed** when the change involves logic, architecture, security,
data or migrations, concurrency, money, external APIs, ambiguous requirements,
or when an error has recurred. If genuinely unsure, lean toward reviewing.

## 2. Choose what to review (scope)
- **Default (git repo):** uncommitted work — `git diff HEAD` plus untracked files.
- A specific commit, branch range, or named files, if the user asked.
- The current **plan** itself, when reviewing an approach before implementing.
- **Not a git repo:** the files you changed this session, or the plan text.

## 3. Commit your own verdict first (anti-anchoring)
Before you see the panel, privately note your own conclusion and confidence
("I believe X is correct because…"). You will compare the two afterward — this
keeps you from rubber-stamping whatever the panel says.

## 4. Assemble the context (raw, not summarized)
Collect the real artifacts and write them to a temporary JSON file (use your
scratchpad directory) with these fields:
```json
{
  "task": "what the user actually asked for",
  "approach": "your plan / what you did",
  "agent_verdict": "your step-3 verdict + confidence",
  "scope": "e.g. 'uncommitted diff' or 'files: src/auth.py'",
  "artifacts": "the RAW diff / file contents / plan text",
  "focus": "$ARGUMENTS"
}
```
Send the actual code/diff, never a paraphrase — the panel's independence depends
on seeing the real thing, not your description of it.

## 5. Run the panel
```
python "${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/fuse_review.py" --input "<your-context-file.json>"
```
(Use `python3` if that is your Python 3 launcher.) For routine or low-stakes
checks, add `--preset general-budget` (cheaper). If the script reports the API
key is missing, guide the user to set it (env var or `~/.claude/settings.json`)
— **never ask them to paste the key into the chat.**

## 6. Present, compare, triage
- Show the panel's verdict and findings.
- Compare them against your step-3 verdict: where do you agree or disagree, and why?
- Address **P0/P1** findings first.
- **Verify any critical finding before acting on it.** The panel reads statically,
  cannot run the code, and can be wrong — confirm before you change anything.

See [references/openrouter-fusion.md](references/openrouter-fusion.md) for presets,
cost, panel overrides, and troubleshooting.
