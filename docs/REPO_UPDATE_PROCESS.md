# REPO_UPDATE_PROCESS.md — boilerhaus/avantis-paper-bot

This is the standard process for all updates.

## Branch model

- Protected branch: `main`
- Working branches:
  - `feat/<topic>`
  - `fix/<topic>`
  - `ops/<topic>`
  - `docs/<topic>`

## Required flow

1. Open issue (bug/change/risk adjustment)
2. Create branch from latest `main`
3. Implement + test (`python -m compileall -q src scripts`, `bash ./scripts/docs/check_docs.sh`, and `pytest -q`)
4. Open PR using template
5. Required review approval(s)
6. Squash merge to `main`
7. Deploy + post-deploy checks

No direct pushes to `main`.

## PR rules

Every PR must include:
- Purpose and scope
- Risk impact (especially sizing/leverage/kill-switch)
- Rollback plan
- Validation evidence (logs/screenshots/commands)
- Roadmap linkage for substantive work:
  - roadmap phase/item
  - linked issue(s)
  - whether the PR completes, advances, or only partially satisfies the roadmap item

For roadmap-bearing work, contributors should regenerate roadmap status before or during PR prep:

```bash
./scripts/render_roadmap.py
```

Ambiguous PRs must not silently advance roadmap state. If a PR is only a partial step, the PR body and linked issue thread must say so explicitly.

### Required CI checks

The following check must pass before merge:
- `lint-and-smoke` (GitHub Actions `CI` workflow)

If this check is red, do not merge.

## Risk-change policy (trading-critical)

Any change touching these requires explicit review:
- leverage
- deployed capital limits
- kill switch
- position sizing
- stop-loss / take-profit logic
- order execution path

Label required: `risk-change`

## Deploy policy

- Deploy only from merged `Main`
- Run preflight checks from `boilerclaw/LIVE_RUNBOOK.md`
- If any check fails: rollback/revert first, then debug

## Emergency hotfix policy

Allowed only for production-impact incidents.

Flow:
1. `hotfix/<topic>` branch
2. Minimal patch only
3. Fast review (still required)
4. Deploy
5. Follow-up PR for cleanup/tests/docs within 24h

## Ownership

- CODEOWNERS defines required reviewers for sensitive paths.
- If reviewer unavailable, wait unless incident severity demands hotfix path.


### Branch protection verification

After applying protections, run:

```bash
./scripts/check-branch-protection.sh
```

Expected: `✅ branch protection baseline checks passed`
