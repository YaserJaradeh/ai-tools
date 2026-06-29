# Fusion Advisor — a Claude Code plugin

An independent, **multi-model second opinion** on your agent's work, powered by
[OpenRouter Fusion](https://openrouter.ai/docs/guides/routing/routers/fusion-router)
(a panel of top models across labs + a judge + a synthesizer). It ships as:

- a **skill** you or Claude can invoke: `/fusion-advisor:review [focus]`
- an automatic **"check before finishing" nudge** (a `Stop` hook) in git repos.

It's the cross-lab analogue of Claude Code's built-in `/advisor`: instead of one
same-vendor model, a panel from *different* labs reviews the work — catching the
blind spots a single model (or Claude reviewing its own work) would share.

## Requirements

- Claude Code with plugin support
- Python 3.8+ on `PATH` (Windows: `python`; macOS/Linux may use `python3` — see Notes)
- git (only for the automatic nudge; the manual skill works anywhere)
- An OpenRouter API key with Fusion access

## Install

```
/plugin marketplace add <your-github-user>/<your-repo>
/plugin install fusion-advisor@fusion-tools
```

(Or from a local clone: `/plugin marketplace add /path/to/this/repo`.) Enable it
when prompted. Installing **and enabling** activates **both** the skill and the
nudge hook — nothing else to wire up.

## Set your OpenRouter key (each user, once)

The key is read from your environment or settings — it is **never bundled, never
printed, and never pasted into chat**. Pick one:

- **Environment variable (recommended)** — add to your shell profile so it persists:
  - PowerShell: `$env:OPENROUTER_API_KEY = "sk-or-..."`
  - bash/zsh: `export OPENROUTER_API_KEY=sk-or-...`
- **User settings** (reuse across projects) — add to `~/.claude/settings.json`:
  ```json
  { "env": { "OPENROUTER_API_KEY": "sk-or-..." } }
  ```

Tip: use a **dedicated key with a spend cap** — Fusion costs ~3–5× a single call.

## Use it

- **Manual:** `/fusion-advisor:review` (optionally `/fusion-advisor:review focus on the auth logic`).
  The skill decides whether it's worth it, gathers the real diff/files/plan, runs
  the panel, and triages the findings against its own pre-committed verdict.
- **Automatic:** in a git repo, when a turn ends with more than ~20 un-reviewed
  changed lines, you get a one-line nudge — and the model decides whether to run
  the review. Cheap and dumb by design: no model call in the hook itself.

## Configuration (environment variables)

| Variable | Default | Effect |
|---|---|---|
| `FUSION_ADVISOR_PRESET` | `general-high` | Panel preset (`general-high` / `general-budget` / `general-fast`) |
| `FUSION_ADVISOR_PANEL` | (unset) | Comma-separated model slugs; overrides the preset |
| `FUSION_ADVISOR_AUTO` | on | Set `0` to disable the nudge hook |
| `FUSION_ADVISOR_MIN_LINES` | `20` | Min changed lines before the hook nudges |
| `FUSION_ADVISOR_MAX_NUDGES` | `3` | Max auto-nudges per session |

## Notes

- The panel is **read-only and static** (it can't run your code) and can produce
  false positives — treat findings as advice and **verify criticals before acting**.
- **macOS/Linux:** if `python` isn't Python 3 on your system, change `python` to
  `python3` in `plugins/fusion-advisor/hooks/hooks.json` (the skill adapts on its own).

## Publish (for the maintainer)

1. Edit owner info in `.claude-plugin/marketplace.json` and author in
   `plugins/fusion-advisor/.claude-plugin/plugin.json`.
2. Push this repo to GitHub (or any git host).
3. Share: users run `/plugin marketplace add <you>/<repo>` then
   `/plugin install fusion-advisor@fusion-tools`.
4. Ship updates by pushing changes; users run `/plugin marketplace update`.

## Layout

```
.claude-plugin/marketplace.json           # marketplace catalog (lists the plugin)
plugins/fusion-advisor/
├─ .claude-plugin/plugin.json             # plugin manifest
├─ skills/review/
│  ├─ SKILL.md                            # the /fusion-advisor:review skill
│  ├─ references/openrouter-fusion.md
│  └─ scripts/
│     ├─ fuse_review.py                   # backend: context → Fusion → markdown review
│     └─ stop_review.py                   # the Stop nudge hook
└─ hooks/hooks.json                       # registers the Stop hook
```
