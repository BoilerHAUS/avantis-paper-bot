# Deploy (VPS) — paper-bot-dashboard

This is a **read-only v1** dashboard/control-plane layout for Avantis Paper Bot.

- **One service**: Node/Express reads local files and serves a web UI.
- **No secrets in the frontend bundle.**
- **No live trading actions in v1.**

## Port
Default: **3030** (override with `-e PORT=...`).

## Data sources (read-only)
By default the server reads the Dokploy paths directly:

- Snapshot: `/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/state/snapshot.json`
- Journal dir: `/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/journal/`

You can override paths with env:
- `SNAPSHOT_PATH`
- `JOURNAL_DIR`

## Option chosen for deployment: Docker container

### 1) Build
```bash
cd /opt/boilerclaw/paper-bot-dashboard

docker build -t paper-bot-dashboard:latest .
```

### 2) Run (read-only mounts)
```bash
DATA_DIR=/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data

docker run -d --name paper-bot-dashboard \
  --restart unless-stopped \
  -p 3030:3030 \
  -e PORT=3030 \
  -e SNAPSHOT_PATH=/data/state/snapshot.json \
  -e JOURNAL_DIR=/data/journal \
  -v ${DATA_DIR}:/data:ro \
  paper-bot-dashboard:latest
```

### 3) Test
Health via curl:
```bash
curl -s http://127.0.0.1:3030/api/meta | jq
curl -s http://127.0.0.1:3030/api/status | jq '.status | {position:.position, equity:.equity, daily_pnl:.daily_pnl, candles_loaded:.candles_loaded, last_cycle:.last_cycle}'
curl -s http://127.0.0.1:3030/api/timeline | jq '.events | length'
```

Browser:
- `http://<VPS-IP>:3030/`

### 4) Logs
```bash
docker logs -f paper-bot-dashboard
```

### 5) Stop / remove
```bash
docker stop paper-bot-dashboard
docker rm paper-bot-dashboard
```

## Notes
- v1 uses polling in the browser (`/api/status` + `/api/timeline`) every 15 seconds.
- “Not wired yet” controls are intentionally disabled and include TODOs in code.
