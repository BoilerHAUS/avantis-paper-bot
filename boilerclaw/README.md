# boilerclaw (agent pack)

This folder is intended to be copied onto the **VPS agent host** so the OpenClaw agent ("Boilerclaw") has:

- a **runbook** (what to check when things break)
- a minimal **soul/memory bootstrap** (what the bot is, what it must not do)
- a pointer to this repo as the source of truth

The goal is to make it easy for the VPS-resident agent to operate the bot without you SSH-ing in.

## Contents
- `RUNBOOK.md` — operational checklist for feed/cycle/monitoring
- `AGENT_SOUL.md` — suggested agent posture and hard rules
- `MEMORY_SEED.md` — seed facts the agent should know on day 1
- `VPS_PATHS.md` — expected paths (compose, data, journal, snapshot)

## Copy to VPS
You can rsync or scp the folder and place it somewhere like:

- `/opt/boilerclaw/boilerclaw/`

Then point the agent’s working directory / knowledge root at it.
