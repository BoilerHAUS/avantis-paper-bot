# experimentation framework v1

## metadata
- version: v1.0.0
- owner_role: strategy_governance
- review_cadence: weekly
- next_review_due: 2026-03-26

## objective
Define the scientific operating model for strategy development in `avantis-paper-bot` so new variants are proposed, evaluated, promoted, retained, or rejected through comparable evidence instead of intuition.

## doctrine
This repo is a **strategy lab**, not a parameter playground.

That means:
- every meaningful strategy change starts with a falsifiable hypothesis
- every experiment is evaluated on fixed comparison windows
- every review uses the same evidence vocabulary
- rejection is a valid outcome
- promotion requires both edge evidence and operational safety

## experiment lifecycle
Experiments move through these states:

1. `proposed`
   - hypothesis written
   - target regime defined
   - baseline selected
   - replay windows frozen
2. `running`
   - implementation exists
   - replay and/or paper observation artifacts are being collected
3. `reviewed`
   - evidence pack is complete
   - reviewer can make a deterministic decision
4. `promoted`
   - variant is explicitly approved for operational use in one of two ways:
     - it becomes the new baseline for its target regime or lane, or
     - it becomes an approved paper lane that is allowed to continue under standard review until final replacement criteria are met
5. `retained_experimental`
   - variant shows promise but evidence is incomplete or mixed
   - allowed to continue only with explicit follow-up questions
6. `rejected`
   - variant failed its test or cannot justify operational risk
7. `archived`
   - experiment is closed and preserved for future reference

## minimum experiment template
Every experiment proposal MUST define:
- hypothesis
- strategy / variant name and version
- expected edge
- intended regime(s): `trend_up`, `trend_down`, `range`, `transition`
- baseline comparator
- fixed replay windows
- paper observation plan (if applicable)
- success criteria
- failure / rollback criteria
- next review trigger

## standard evidence pack
Every strategy PR or review packet MUST include one evidence pack with the following sections.

### 1) hypothesis summary
- one-sentence edge claim
- what should improve
- what should stay unchanged or worsen only within tolerance

### 2) implementation scope
- exact files / config surfaces changed
- whether the change is logic, thresholding, sizing, filtering, or execution behavior
- statement of whether the change is small enough to test as one hypothesis

If a proposed change combines multiple independent ideas, it MUST be split before review.

### 3) frozen comparison setup
- baseline strategy/version
- candidate strategy/version
- exact replay windows
- same symbols, timeframe, and market conditions for baseline and candidate
- same fee / slippage / funding assumptions

No candidate may be compared against a hand-picked window set that differs from the baseline review packet.

### 4) replay evidence
Replay results MUST report at minimum:
- pnl / expectancy
- max drawdown
- trade count
- win rate or hit-rate
- exposure / deployed capital profile
- regime coverage
- stability across windows

Good pnl on too few trades, too little time, or too little regime coverage is **not** promotion-grade evidence. Even when exact numeric thresholds are still evolving, reviewers must treat sample sufficiency as a first-class gate.

Where possible, the report should also show why the result happened, not just that it happened.

### 5) paper evidence
If the variant has reached paper observation, the review packet MUST include:
- paper window covered
- number of decision cycles observed
- expected vs observed behavior deltas
- operational incidents, false positives, or obvious failure modes

### 6) safety and execution check
Every packet MUST state:
- leverage assumptions
- max deployed capital assumptions
- stop / invalidation behavior
- kill-switch interaction
- known liquidity / execution caveats

A variant that appears profitable but violates operational safety is not promotable.

### 7) review decision
Every review must end with exactly one outcome:
- `promoted`
- `retained_experimental`
- `rejected`
- `archived`

The decision MUST include:
- why the outcome was chosen
- what evidence carried the decision
- what the next action is

## comparison rules
To keep experiments comparable:
- baseline and candidate MUST use the same replay windows
- windows MUST be frozen before the comparison is treated as decision-grade
- comparisons MUST include more than raw pnl
- regime coverage matters; a variant that only works in one narrow market condition is not automatically promotable
- if paper results materially differ from replay expectations, paper evidence takes precedence for promotion decisions

## promotion gates
A variant may be marked `promoted` only when all of the following are true:
- evidence pack is complete
- replay results are favorable or clearly decision-useful versus baseline
- drawdown / instability stay within defined tolerance
- the variant does not rely on an obviously narrow or non-repeatable window
- target regime behavior is coherent and explainable
- operational risk is acceptable under current leverage, sizing, and kill-switch rules

## retention criteria
A variant should be marked `retained_experimental` when:
- evidence is directionally promising but insufficient
- replay and paper evidence disagree but the disagreement is diagnosable
- the edge looks regime-specific and needs more boundary testing
- the change is interesting enough to continue, but not safe enough to promote

Retention MUST include a specific follow-up plan. “Needs more testing” is not enough.

## rejection criteria
A variant should be marked `rejected` when any of the following are true:
- no clear edge versus baseline
- edge disappears outside a narrow replay slice
- drawdown, instability, or variance is too high for the observed benefit
- paper behavior contradicts replay in a material way
- the rationale is not explainable enough to trust in production
- the change creates operational fragility or unsafe risk behavior

Rejected experiments are still useful. They become negative evidence and should not be quietly retried under a new name without new reasoning.

## rollback criteria
A previously promoted variant MUST be reviewed for rollback if:
- live or paper behavior materially diverges from review evidence
- drawdown or kill-switch behavior exceeds expectations
- regime classifier behavior changes the effective conditions under which the strategy acts
- execution assumptions prove materially wrong
- a safer baseline or newer candidate clearly dominates it

## baseline and versioning rules
- every experiment must name the baseline it is trying to beat or replace
- every candidate variant must have an auditable version or label
- materially changed variants should not silently inherit prior evidence
- if the hypothesis changes, the experiment id should change too

## review artifact contract
A decision-ready review should leave behind:
- linked issue
- linked PR
- linked evidence artifacts
- explicit decision outcome
- named reviewer or review authority
- date/time of decision

Evidence artifacts should be stored in one predictable repo location or naming scheme rather than scattered ad hoc. The exact directory can evolve, but each experiment should produce a clearly named report bundle that includes the experiment id or strategy version so reviewers can find baseline/candidate evidence without guesswork.

If someone reads the repo later, they should be able to answer: what was tested, against what, on which windows, with what result, and why the repo accepted or rejected it.

## what this issue should produce
Issue `#34` is satisfied when this framework exists in-repo as the initial operating document and future strategy work can point back to it.

Follow-on issues should then:
- implement replay/evidence tooling
- implement deterministic review artifacts
- refine promotion policy and governance details
- revise this framework when real usage reveals gaps

## related docs
- `docs/strategy/STRATEGY_CONTRACT_V1.md`
- `docs/architecture.md`
- `docs/agent/CHECKLISTS.md`
- `docs/REPO_UPDATE_PROCESS.md`
