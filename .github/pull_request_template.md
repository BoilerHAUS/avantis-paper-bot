## Summary
- What changed?
- Why now?

## Scope
- [ ] code
- [ ] config
- [ ] infra/deploy
- [ ] docs

## Docs impact checklist (required when docs touched)
- [ ] changed sections summary included
- [ ] downstream docs touched listed (or `none`)
- [ ] canonical docs index updated (or reason why not)
- [ ] ran: `bash ./scripts/docs/check_docs.sh`

## Risk impact
- [ ] no trading risk changes
- [ ] includes trading risk changes (label `risk-change` required)

If risk changed, describe exactly what and why:

## Validation
- Commands/tests run:
- Evidence (logs/screenshots):

## Rollback plan
- Exact rollback steps:

## Post-deploy checks
- [ ] candles are fresh
- [ ] cycle/journal are fresh
- [ ] dashboard reflects current state
