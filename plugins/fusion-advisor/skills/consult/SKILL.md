---
name: consult
description: Consult an independent multi-model panel (top models across labs, via OpenRouter Fusion) for a strategic second opinion on a decision, approach, or tricky problem — and to pressure-test the current work. Returns a recommendation, the key risks, and whether you're solving the right problem.
when_to_use: Use at decision points and when judgment matters — choosing between approaches, stuck on a recurring error, unsure you're solving the right problem, weighing a risky or irreversible change, or before declaring a task done. Also when the user asks to "get a second opinion", "advise", "consult", "sanity-check", "am I on the right track", or "what am I missing".
argument-hint: "[optional question or focus, e.g. 'is this the right approach?']"
---

# Fusion Advisor — independent multi-model second opinion

Consult a panel of top models across labs (via OpenRouter Fusion) when you want
**strategic advice**: which approach to take, whether you're solving the right
problem, what you're missing, or a gut-check before committing to something
costly. Treat it as an advisor, not an oracle — weigh its advice and verify
specifics before acting. A consult costs ~3–5× a normal model call and takes
~30–120s, so use it when judgment matters, not for trivial edits.

When this skill is invoked, follow these steps.

## 1. Decide if it's worth consulting
Your call. **Skip** (and say so in one line) for trivial or mechanical work:
formatting, renames, comments, doc tweaks, tiny one-liners. **Proceed** when a
real decision or judgment is at stake: architecture, choice of approach, security,
data or migrations, concurrency, money, external APIs, ambiguous requirements, or
a recurring failure. If genuinely unsure, lean toward consulting.

## 2. Frame what you're consulting about (scope)
- A **decision or approach** you're weighing (state the options and trade-offs).
- The current **plan**, before you implement it.
- A piece of **work**: uncommitted diff (`git diff HEAD` + untracked), named files, or a commit.
- A problem you're **stuck on** (include what you've already tried).

## 3. Commit your own view first (anti-anchoring)
Before you see the panel, privately note your own leaning and confidence
("I'd do X because…"). You'll compare afterward — this keeps you from
rubber-stamping whatever the panel says.

## 4. Assemble the context (raw, not summarized)
Collect the real artifacts and write them to a temporary JSON file (use your
scratchpad directory) with these fields:
```json
{
  "task": "what the user actually asked for / the situation",
  "approach": "your plan or what you did",
  "agent_verdict": "your step-3 view + confidence",
  "scope": "e.g. 'choosing between A and B' or 'uncommitted diff'",
  "artifacts": "the RAW diff / file contents / plan / options",
  "focus": "$ARGUMENTS"
}
```
Send the actual code/diff/plan, never a paraphrase — the panel's independence
depends on seeing the real thing.

## 5. Consult the panel
```
python "${CLAUDE_PLUGIN_ROOT}/skills/consult/scripts/advise.py" --input "<your-context-file.json>"
```
(Use `python3` if that is your Python 3 launcher.) For routine or low-stakes
consults, add `--preset general-budget` (cheaper). If the script reports the API
key is missing, guide the user to set it (env var or `~/.claude/settings.json`)
— **never ask them to paste the key into the chat.**

## 6. Weigh the advice
- Share the panel's **recommendation** and key risks.
- Compare against your step-3 view: where do you agree or disagree, and why?
- Address **P0/P1** points first.
- **Verify any critical or specific claim before acting on it.** The panel reasons
  statically, cannot run the code, and can be wrong — it advises; you decide.

See [references/openrouter-fusion.md](references/openrouter-fusion.md) for presets,
cost, panel overrides, and troubleshooting.
