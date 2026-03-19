# experiment governance policy v1

## metadata
- version: v1.0.0
- owner_role: strategy_governance
- review_cadence: weekly
- next_review_due: 2026-03-26

## objective
Define the review and decision policy for strategy experiments so candidate variants are promoted, retained, rejected, archived, or rolled back through explicit evidence and auditable judgment rather than intuition.

## role of this document
`docs/strategy/EXPERIMENTATION_FRAMEWORK_V1.md` defines the repo's scientific operating model.

This document defines the governance layer that sits on top of that framework:
- what evidence is required before review
- who is allowed to approve which outcomes
- how decisions are recorded
- when exceptions are allowed
- how rollback is triggered after a prior promotion

## governance principles
- every meaningful strategy change is reviewable against one standard evidence bundle
- evidence quality outranks narrative confidence
- promotion is rare; rejection and retention are healthy outcomes
- `insufficient_evidence` is a valid decision outcome
- exceptions are allowed only when explicitly named, justified, and logged
- materially changed variants do not inherit prior approval automatically

## lifecycle states vs review outcomes
Lifecycle state and review outcome are related but not identical.

### lifecycle states
These describe where an experiment is in the operating process:
- `proposed`
- `running`
- `reviewed`
- `promoted`
- `retained_experimental`
- `rejected`
- `archived`

### review outcomes
Every formal review MUST end with exactly one governance outcome:
- `promote`
- `retain_experimental`
- `reject`
- `archive`
- `insufficient_evidence`
- `rollback`

Operational mapping:
- `promote` => lifecycle state becomes `promoted`
- `retain_experimental` => lifecycle state becomes `retained_experimental`
- `reject` => lifecycle state becomes `rejected`
- `archive` => lifecycle state becomes `archived`
- `insufficient_evidence` => lifecycle state remains `running` or becomes `reviewed` with explicit next evidence requirements
- `rollback` => previously promoted variant moves out of promoted status and reverts to the named fallback/baseline state

## required evidence bundle
No formal review may occur without one linked evidence bundle containing, at minimum:
- experiment id / strategy variant id
- hypothesis summary
- baseline comparator
- exact replay windows
- symbol and timeframe
- strategy/config fingerprint
- artifact contract version(s)
- replay evidence summary
- paper evidence summary, if paper observation exists
- risk / execution assumptions
- known weaknesses or unresolved questions

If any required section is missing, the experiment is not decision-grade and the proper outcome is `insufficient_evidence`, not an improvised judgment.

## minimum promotion gate
A reviewer may choose `promote` only if all of the following are true:
- evidence bundle is complete
- baseline and candidate were compared on fixed, pre-declared windows
- sample sufficiency is acceptable for the claim being made
- regime coverage is adequate for the target use case
- drawdown / instability remain inside tolerated bounds
- behavior is explainable through replay and attribution artifacts
- no known execution or risk caveat invalidates the conclusion

A variant MUST NOT be promoted solely because it shows higher pnl on a narrow or flattering slice.

## retain_experimental gate
A reviewer should choose `retain_experimental` when:
- the hypothesis still looks plausible
- evidence is mixed, partial, or boundary-sensitive
- more replay windows, more paper observation, or sharper attribution is required
- the variant is worth continuing, but not safe to endorse

A retain decision MUST name:
- what is still missing
- what exact next evidence is required
- what would falsify continued work

## insufficient_evidence gate
A reviewer should choose `insufficient_evidence` when:
- the evidence packet is incomplete
- required comparison windows are missing
- attribution or replay artifacts are not trustworthy enough to support judgment
- sample size / regime coverage is too weak to support the claim
- the review question is answerable in principle, but not from the current packet

`insufficient_evidence` is not a soft promote and not a soft reject. It means the repo deliberately refuses to overstate what the evidence supports.

## reject gate
A reviewer should choose `reject` when:
- the candidate fails to beat or meaningfully complement the baseline
- the apparent edge disappears outside a narrow slice
- the result depends on unstable behavior, loose risk posture, or fragile assumptions
- replay and paper evidence materially disagree without a credible explanation
- the variant adds operational complexity without proportional value

Rejected experiments remain part of the repo's negative evidence history and must remain auditable.

## archive gate
A reviewer should choose `archive` when:
- the experiment is complete and no further work is justified
- a rejected or superseded line of inquiry should be preserved but not kept active
- the variant is historically useful but no longer part of the active decision set

Archive is a recordkeeping outcome, not a statement that the result was good.

## rollback gate
A reviewer MUST consider `rollback` for any previously promoted variant when:
- paper or live behavior materially diverges from the evidence that justified promotion
- drawdown, instability, or kill-switch behavior exceed the promoted tolerance assumptions
- classifier or execution changes alter the effective operating conditions of the variant
- a safer baseline clearly dominates the promoted candidate under current evidence

Rollback decisions MUST name:
- the trigger event or evidence change
- the variant being rolled back
- the fallback baseline or operating state
- whether new follow-on investigation is required

## reviewer authority
Default reviewer authority for this repo:
- strategy/governance reviewer: required for `promote`, `rollback`, and exception approval
- implementation/technical reviewer: required when evidence depends on new artifact contracts, replay correctness, or runtime behavior changes

For now, human approval remains the final merge gate for all governance-sensitive changes.

## benchmark and comparison rules
All decision-grade comparison packets MUST obey these rules:
- same symbol, timeframe, and fixed replay windows for baseline and candidate
- same slippage / fee / funding assumptions
- same artifact contract version or an explicitly documented compatibility note
- same review question across both variants

If a candidate is evaluated on different windows, different assumptions, or incompatible artifact contracts, the result is exploratory only and cannot support promotion.

## decision record contract
Every governance review MUST leave one auditable decision record containing:
- experiment id
- issue link
- PR link, if applicable
- reviewer name/role
- decision timestamp
- governance outcome
- baseline and candidate ids
- evidence bundle links
- exact replay window identity
- strategy/config fingerprint(s)
- artifact contract version(s)
- rationale summary
- unresolved risks / missing evidence
- next action

## exceptions and overrides
Exceptions are allowed only when all of the following are present:
- explicit label: `exception`
- named approver
- written rationale
- bounded duration or scope
- statement of what normal rule is being overridden
- follow-up review trigger

An exception without an expiry condition or follow-up trigger is invalid.

## naming and versioning discipline
- materially changed strategy logic requires a new strategy version or experiment id
- materially changed evidence contracts require a versioned artifact/schema reference
- previously promoted evidence must not be reused silently for a changed candidate
- if the claim changes, the experiment identity should change too

## related docs
- `docs/strategy/EXPERIMENTATION_FRAMEWORK_V1.md`
- `docs/strategy/STRATEGY_CONTRACT_V1.md`
- `../ARTIFACT_CONTRACT_V1.md`
- `../architecture.md`
