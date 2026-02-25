# CHECKLISTS — Avantis Trading Agent (GOAT Gates)

These checklists are designed to be **deterministic gates**. The agent should refuse to open a new position when required items are missing.

## 1) Pre‑trade checklist (must pass)
Source doctrine: GOAT pack `08_checklists_policies/pretrade_checklist.md`.

Minimum required artifacts:
- **Hypothesis (1 sentence):** what edge are we trading?
- **Data leakage check:** why the signal could not have leaked future information.
- **Overfitting packet attached:**
  - CSCV / PBO estimate
  - Deflated Sharpe Ratio (DSR) or other multiple-testing adjusted metric
  - Min Track Record Length (MinTRL)
  - OOS degradation scenarios + how much paper/live budget we need
- **Execution plan:**
  - venue(s), latency assumptions, fees
  - spread/impact model + slippage assumptions
  - max participation rate and child-order sizing
  - settlement frictions, funding (perps)
- **Risk controls:** leverage cap, position sizing, max deployed %, stop logic, daily kill-switch
- **Incident response (1 paragraph):** what we do if spread spikes / venue outage / liquidation cascade

Agent output requirement:
- If any item is missing: **REJECT** and list exactly what’s missing.

## 2) Strategy promotion gates
Source doctrine: GOAT pack `08_checklists_policies/deployment_playbook.md`.

Stage gates:
1) Backtest (hypothesis only)
2) Paper-trade
3) Limited live (small size)
4) Scale up

Promotion requires:
- OOS hit-rate stability
- Risk-of-ruin / drawdown profile acceptable
- Slippage delta (expected vs realized) within tolerance
- No single-venue dependency

## 3) Post-trade execution review (required for learning)
Source doctrine: GOAT pack `07_prompts_templates/execution_review.md`.

Must include:
- Data sources + latency assumptions
- Spread/impact model; expected vs realized
- Slippage attribution (model error vs regime shift vs liquidity)
- Liquidity stress notes (depth, imbalance; VPIN/Roll if available)
- Settlement/funding frictions
- Controls check: participation rate, child orders, kill-switch triggers

## 4) Overfitting & multiple-testing gate (required for new edges)
Source doctrine: GOAT pack `07_prompts_templates/overfitting_check.md` and `04_guardrails_overfitting/LINKS_AND_POLICY.md`.

Policy:
- Any new “edge” must ship with PBO, DSR, OOS degradation tests, and MinTRL.

## 5) Discretionary override gate
If the agent wants to override a rule (rare):
- run Bias Linting (Bacon + Bayes)
- require explicit human confirmation before proceeding
