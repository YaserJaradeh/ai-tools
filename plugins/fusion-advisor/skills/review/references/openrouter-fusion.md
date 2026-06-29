# OpenRouter Fusion — reference for fusion-advisor

## What it is
`openrouter/fusion` runs a panel of top models (across labs) in parallel, a judge
compares their answers, and a synthesizer writes one final answer. We force the
panel with `tool_choice: "required"` so it always deliberates.

## Presets (`--preset` or `FUSION_ADVISOR_PRESET`)
- `general-high` (default) — strongest all-round panel.
- `general-budget` — cheaper panel with a frontier judge; good for routine checks.
- `general-fast` — latency-optimized panel.

## Override the panel (max independence from Claude)
Set `FUSION_ADVISOR_PANEL` to a comma-separated list of OpenRouter model slugs to
replace the preset — e.g. non-Anthropic models, so it isn't "Claude grading Claude":
```
FUSION_ADVISOR_PANEL=openai/gpt-5.5,google/gemini-3-pro
```

## Cost & latency
Roughly **3–5× the cost** of a single completion (each panel member plus the judge
is billed) and **2–3× the latency**. Use a dedicated OpenRouter key with a spend
cap.

## Key resolution
Resolved in this order, and **never printed** by the scripts:
1. `OPENROUTER_API_KEY` environment variable
2. `<project>/.claude/settings.local.json` → `env.OPENROUTER_API_KEY`
3. `<project>/.claude/settings.json` → `env.OPENROUTER_API_KEY`
4. `~/.claude/settings.local.json` → `env.OPENROUTER_API_KEY`
5. `~/.claude/settings.json` → `env.OPENROUTER_API_KEY`

## Config knobs (environment variables)
| Variable | Default | Effect |
|---|---|---|
| `FUSION_ADVISOR_PRESET` | `general-high` | Panel preset |
| `FUSION_ADVISOR_PANEL` | (unset) | Comma-separated model slugs; overrides the preset |
| `FUSION_ADVISOR_AUTO` | on | Set `0` to disable the Stop-hook nudge |
| `FUSION_ADVISOR_MIN_LINES` | `20` | Min changed lines before the hook nudges |
| `FUSION_ADVISOR_MAX_NUDGES` | `3` | Max auto-nudges per session |

## Troubleshooting
- **"OPENROUTER_API_KEY is not set"** → set the env var or add it to `~/.claude/settings.json`.
- **HTTP 400 mentioning `tool_choice`** → remove the `"tool_choice": "required"`
  line in `fuse_review.py`; a review prompt still triggers the panel almost always.
- **`insufficient_credits` / `rate_limited` / `all_panels_failed`** → Fusion
  failure reasons; check OpenRouter credits/limits, then retry.
- **Too slow or too expensive** → use `--preset general-budget`.
- **Hook never nudges** → it requires a git repo with ≥ `FUSION_ADVISOR_MIN_LINES`
  changed lines, a configured key, and `FUSION_ADVISOR_AUTO` on.
