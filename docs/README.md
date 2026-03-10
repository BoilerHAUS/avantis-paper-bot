# docs index (canonical)

## metadata
- version: v1.0.0
- owner_role: product_docs
- review_cadence: weekly
- next_review_due: 2026-03-17

## objective
Provide one canonical entrypoint for repo documentation so contributors and operators can find the correct contract/runbook quickly.

## source-of-truth map
| doc | audience | owner | review_cadence | source_of_truth | purpose |
|---|---|---|---|---|---|
| `README.md` | contributor/operator | shared | weekly | yes | repo overview, quickstart, baseline behavior |
| `docs/architecture.md` | developer/operator | boilerclaw | biweekly | yes | trading/dataflow architecture and strategy logic |
| `docs/REPO_UPDATE_PROCESS.md` | contributor | shared | weekly | yes | issue-first / PR-gated process contract |
| `boilerclaw/LIVE_RUNBOOK.md` | operator | boilerclaw | weekly | yes | production/live runbook and deploy checks |
| `docs/operations/RUNBOOK_PAPER_V1.md` | operator | boilermolt | weekly | yes | paper-mode start/verify/recover/rollback runbook |
| `docs/strategy/STRATEGY_CONTRACT_V1.md` | developer/strategy reviewer | boilermolt | weekly | yes | conservative/aggressive profile contract + risk boundaries |
| `docs/dashboard/DASHBOARD_CONTRACT_V1.md` | developer/operator | boilermolt | weekly | yes | dashboard/API metric formulas + rendering/compat rules |
| `dashboard/README.md` | dashboard operator | shared | weekly | yes | dashboard runtime and endpoints overview |
| `docs/agent/*` | agent author | shared | monthly | yes | agent behavior contracts and prompts |

## navigation by task
### I need to operate the bot safely
- `docs/operations/RUNBOOK_PAPER_V1.md`
- `boilerclaw/LIVE_RUNBOOK.md`

### I need to change strategy behavior
- `docs/strategy/STRATEGY_CONTRACT_V1.md`
- `docs/architecture.md`
- `config.example.json`

### I need to verify dashboard metrics/API behavior
- `docs/dashboard/DASHBOARD_CONTRACT_V1.md`
- `dashboard/README.md`

### I need to contribute code/docs
- `docs/REPO_UPDATE_PROCESS.md`
- `.github/pull_request_template.md`

## known gaps (tracked)
- #12 paper operations runbook completion
- #13 strategy contract completion
- #14 dashboard contract completion
- #15 docs quality gate automation
