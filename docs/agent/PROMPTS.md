# PROMPTS — Avantis Trading Agent (GOAT)

These prompts are designed to be used as internal “review forms.” They should be short, repeatable, and produce auditable outputs.

## 1) Bias‑linting (Bacon + Bayes)
Source: GOAT pack `07_prompts_templates/bias_linting.md`.

**Prompt:**
You are the agent’s internal auditor. Given a proposed trade or strategy change:
1) Identify potential Idols (Bacon): Tribe, Den, Marketplace, Theatre. One sentence each.
2) Bayesian update: prior (with justification), likelihood model, posterior; show sensitivity to priors.
3) List unknowns that most change the posterior.
4) Conclude: trade allowed? yes/no, and what additional evidence would flip the decision.

## 2) Overfitting & multiple-testing check (PBO + DSR)
Source: GOAT pack `07_prompts_templates/overfitting_check.md`.

**Prompt:**
For any backtest result supplied:
- Compute CSCV/PBO estimate and describe the sampling scheme.
- Compute Deflated Sharpe Ratio and report adjusted p-value.
- Report Min Track Record Length for target Sharpe.
- Summarize OOS degradation scenarios and required live-test budget.
- Decision: promote to paper / sandbox / reject.

## 3) Execution & microstructure review
Source: GOAT pack `07_prompts_templates/execution_review.md`.

**Prompt:**
Given a strategy and trade list:
- Quote/Trade data source and latency; venues; fee tiers.
- Spread/impact model; expected vs realized; slippage attribution.
- Liquidity stress: depth, imbalance; VPIN/Roll if available.
- Settlement frictions (withdrawals/limits) and funding (if perps).
- Controls: max participation rate, child-order sizing, kill-switches.

## 4) Narrative risk (crowd + classics)
Source: GOAT pack `07_prompts_templates/narrative_risk.md`.

**Prompt:**
Before or during regime shifts:
- Map price action to a historical mania/conflict archetype (Mackay/Le Bon/Shakespeare/Tolstoy).
- Identify leader/whale behaviors and incentive vectors (Machiavelli).
- Formulate deception/terrain heuristics (Sun Tzu) → execution stance.
- Add stoic pre-trade checks (Marcus Aurelius) → emotional risk controls.

## Output formatting standard
Every prompt output should end with:
- **Decision:** ALLOW / REJECT / NEEDS_HUMAN
- **Assumptions:** 3–5 bullets
- **Next evidence to collect:** 1–3 bullets
