# experimentation roadmap status

## metadata
- source roadmap: `docs/roadmap/EXPERIMENTATION_ROADMAP_V1.json`
- status type: generated
- generation rule: issue-linked roadmap items derive state from GitHub issue metadata where possible
- ambiguity policy: prefer manual follow-up over silent inference

## gate summary
- **foundation_complete**: `blocked` — Evidence substrate is trustworthy enough to support disciplined experimentation. (blockers: #46)
- **experimentation_ready**: `blocked` — The repo can run and review meaningful candidate-vs-baseline experiments with trustable evidence. (blockers: #38, #39, #40, #46)
- **research_surface_ready**: `blocked` — Humans can navigate evidence without artifact spelunking. (blockers: #47, #48, #49, #50)

## current phase
- current phase: **trustable foundations** (`phase-0`)

## experimentation-ready definition
- fixed-window replay is trustworthy
- decision/regime/setup attribution is inspectable
- candidate and baseline can be compared on fixed windows
- governance/evidence rules are explicit enough to review a candidate without vibes
- at least one real strategy lane can be tested against a baseline under those rules

## trustable foundations
- gate: `foundation_complete` → `blocked`
- blockers: #46
- progress: 4/5 items complete

| item | issue | status | priority |
|---|---:|---|---|
| Deterministic replay evidence | #35 | `complete` | `priority:now` |
| Decision artifact contract | #36 | `complete` | `priority:now` |
| Explicit market regime classifier | #37 | `complete` | `priority:now` |
| Experiment governance policy | #42 | `complete` | `priority:now` |
| Replay input-window integrity validation | #46 | `in_progress` | `priority:now` |

## first experimentation-ready loop
- gate: `experimentation_ready` → `blocked`
- blockers: #38, #39, #40, #46
- progress: 0/3 items complete

| item | issue | status | priority |
|---|---:|---|---|
| Directional trend lane | #38 | `in_progress` | `priority:now` |
| Range / mean reversion lane | #39 | `in_progress` | `priority:next` |
| Experiment registry | #40 | `planned` | `-` |

## research operating surface
- gate: `research_surface_ready` → `blocked`
- blockers: #47, #48, #49, #50
- progress: 0/4 items complete

| item | issue | status | priority |
|---|---:|---|---|
| Experiment run index | #47 | `in_progress` | `priority:later` |
| Run detail / decision trace | #48 | `in_progress` | `priority:later` |
| Baseline vs candidate comparison | #49 | `in_progress` | `priority:later` |
| Promotion/rejection evidence surface | #50 | `planned` | `-` |

## refinement and scaling
- progress: 0/3 items complete

| item | issue | status | priority |
|---|---:|---|---|
| README remake | #44 | `in_progress` | `priority:next` |
| Experimentation-console umbrella framing | #41 | `planned` | `-` |
| Roadmap + progress automation | #54 | `planned` | `-` |

## authored-vs-generated split
- This file is the authored roadmap truth: phases, gate definitions, milestone semantics, and issue linkage.
- Generated roadmap state must be derived from linked issue/PR metadata plus explicit PR linkage declarations where possible.
- Automation should prefer under-automation to wrong automation.

## manual override rule
- If a PR only partially advances a roadmap item, reviewers must record that explicitly in the PR and/or issue thread; the generated roadmap should prefer `planned`/`in_progress` over incorrect completion.

