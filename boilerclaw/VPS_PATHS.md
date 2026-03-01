# VPS paths (example layout)

These paths are environment-dependent. Keep this file updated to match the deployed stack.

## Compose
- Dokploy compose dir: `/etc/dokploy/compose/<app>/code/`
- Compose file: `docker-compose.yml`
- Bootstrap config: `bootstrap.json` (must be a FILE)

## Data
- Host data dir: `./data` (relative to compose dir)
- Container data dir: `/var/lib/avantis-paper-bot/data`

## Outputs
- Candles: `data/candles/ETH-USD-15m.jsonl`
- Journal: `data/journal/YYYY-MM-DD.jsonl`
- Snapshot: `data/state/snapshot.json`
