# KB_USAGE — GOAT Pack (RAG / retrieval)

## Purpose
Use the GOAT Crypto Trading Agent Pack as the Avantis agent’s canon for:
- microstructure / execution realism
- overfitting guardrails (PBO/DSR)
- strategy baselines
- deployment/incident playbooks

## Paths
- Canon root (default): `/home/boilerrat/clawd/knowledge/GOAT_Crypto_Trading_Agent_Pack`
- Keyword KB DB (default): `/home/boilerrat/clawd/state/goat_kb.db`

## Tools
- Index: `python3 tools/goat_kb/goat_kb_index.py --root <root> --db <db>`
- Query: `python3 tools/goat_kb/goat_kb_query.py --q "..." --limit 5`

## Retrieval rule (behavioral)
Before the agent:
- changes strategy parameters
- proposes a new edge
- changes risk settings
- diagnoses slippage

…it must query the KB and include 1–3 citations:
- file path
- short quote or snippet

## Index cadence
- Re-index daily (or on pack updates).
- Re-index before major releases.
