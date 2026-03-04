import express from 'express';
import fs from 'node:fs/promises';
import path from 'node:path';

const app = express();

const PORT = parseInt(process.env.PORT || '3030', 10);

// Defaults match the current VPS deploy (Dokploy paths). Override via env for portability.
const SNAPSHOT_PATH = process.env.SNAPSHOT_PATH ||
  '/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/state/snapshot.json';
const JOURNAL_DIR = process.env.JOURNAL_DIR ||
  '/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/journal';
const CANDLES_PATH = process.env.CANDLES_PATH ||
  '/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/candles/ETH-USD-15m.jsonl';

const STALE_MINUTES = parseInt(process.env.STALE_MINUTES || '20', 10);

const STRATEGY_DEFAULTS = {
  trend_fast: 20,
  trend_slow: 50,
  mr_window: 50,
  mr_entry_z: 1.5,
  notes: [
    'Trend: fast/slow SMA with slope check',
    'Mean reversion: z-score vs SMA window',
    'Resolver chooses higher-confidence signal',
    'If insufficient candles, signal stays flat'
  ]
};

app.use(express.static(path.join(process.cwd(), 'public')));

function utcDateString(d = new Date()) {
  const year = d.getUTCFullYear();
  const month = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function minutesSince(dateMs) {
  return Math.max(0, Math.round((Date.now() - dateMs) / 60000));
}

async function statSafe(p) {
  try {
    const s = await fs.stat(p);
    return { ok: true, mtimeMs: s.mtimeMs };
  } catch (e) {
    return { ok: false, error: e?.message || String(e) };
  }
}

async function readJsonSafe(p) {
  const raw = await fs.readFile(p, 'utf8');
  return JSON.parse(raw);
}

async function listJournalFile(dateStr) {
  const p = path.join(JOURNAL_DIR, `${dateStr}.jsonl`);
  return p;
}

async function tailJsonl(p, maxLines = 200) {
  // Simple (not super memory efficient) tail for v1.
  const raw = await fs.readFile(p, 'utf8');
  const lines = raw.split(/\r?\n/).filter(Boolean);
  const slice = lines.slice(-maxLines);
  const items = [];
  for (const line of slice) {
    try {
      items.push(JSON.parse(line));
    } catch {
      // ignore bad line
    }
  }
  return items;
}

async function readJsonlAll(p) {
  const raw = await fs.readFile(p, 'utf8');
  return raw
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function extractStatus(snapshot) {
  // Snapshot schema may evolve; be defensive.
  const state = snapshot?.state ?? snapshot;

  const equity = state?.equity ?? state?.account?.equity ?? null;
  const dailyPnl = state?.daily_pnl ?? state?.account?.daily_pnl ?? null;
  const candlesLoaded = state?.candles_loaded ?? state?.feed?.candles_loaded ?? null;

  const position = state?.position ?? state?.state?.position ?? null;
  // common fields if present
  const side = position?.side ?? position?.direction ?? position?.pos ?? position?.type ?? null;
  const notional = position?.notional ?? position?.size_usd ?? position?.usd_notional ?? null;
  const leverage = position?.leverage ?? position?.lev ?? null;

  const lastCycleTs = state?.timestamp ?? state?.cycle_ts ?? state?.last_cycle_ts ?? snapshot?.timestamp ?? null;
  const lastCycleNote = state?.note ?? state?.last_note ?? snapshot?.note ?? null;

  let posLabel = 'unknown';
  if (!position || side === null || side === undefined) {
    // sometimes position may be encoded as {side:'flat'} or null
    if (position === null) posLabel = 'flat';
  }

  if (typeof side === 'string') {
    const s = side.toLowerCase();
    if (['flat', 'none', '0', 'neutral'].includes(s)) posLabel = 'flat';
    else if (['long', 'buy'].includes(s)) posLabel = 'long';
    else if (['short', 'sell'].includes(s)) posLabel = 'short';
    else posLabel = s;
  } else if (typeof side === 'number') {
    if (side === 0) posLabel = 'flat';
    if (side > 0) posLabel = 'long';
    if (side < 0) posLabel = 'short';
  }

  return {
    equity,
    daily_pnl: dailyPnl,
    candles_loaded: candlesLoaded,
    position: {
      label: posLabel,
      notional,
      leverage
    },
    last_cycle: {
      timestamp: lastCycleTs,
      note: lastCycleNote
    },
    raw: snapshot
  };
}

function isoOrNull(x) {
  if (!x) return null;
  if (typeof x === 'string') return x;
  if (typeof x === 'number') {
    // assume sec if it looks like epoch seconds
    const ms = x < 10_000_000_000 ? x * 1000 : x;
    return new Date(ms).toISOString();
  }
  return null;
}

async function pathExists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

function startDataMountSelfHeal() {
  const intervalMs = parseInt(process.env.MOUNT_CHECK_INTERVAL_MS || '30000', 10);
  const graceMs = parseInt(process.env.MOUNT_CHECK_GRACE_MS || '45000', 10);
  const maxMisses = parseInt(process.env.MOUNT_CHECK_MAX_MISSES || '3', 10);

  let misses = 0;
  let checks = 0;

  setInterval(async () => {
    checks += 1;

    // give mounts a short grace period after startup/redeploy
    if (checks * intervalMs < graceMs) return;

    const snapshotDirOk = await pathExists(path.dirname(SNAPSHOT_PATH));
    const journalDirOk = await pathExists(JOURNAL_DIR);

    if (snapshotDirOk && journalDirOk) {
      misses = 0;
      return;
    }

    misses += 1;
    console.warn(
      `[mount-check] miss ${misses}/${maxMisses} snapshotDirOk=${snapshotDirOk} journalDirOk=${journalDirOk}`
    );

    if (misses >= maxMisses) {
      console.error('[mount-check] data mount appears unhealthy; exiting for container auto-restart');
      process.exit(1);
    }
  }, intervalMs);
}

app.get('/api/strategy', async (_req, res) => {
  const date = utcDateString();
  const journalPath = await listJournalFile(date);

  let latestCycle = null;
  try {
    const events = await tailJsonl(journalPath, 500);
    const cycles = events.filter((e) => e?.type === 'cycle');
    latestCycle = cycles[cycles.length - 1] || null;
  } catch {
    latestCycle = null;
  }

  res.json({
    ok: true,
    strategy: STRATEGY_DEFAULTS,
    latestSignal: latestCycle ? {
      desired: latestCycle?.signal?.desired ?? null,
      confidence: latestCycle?.signal?.confidence ?? null,
      strategy: latestCycle?.signal?.strategy ?? null,
      note: latestCycle?.signal?.note ?? null,
      candles_loaded: latestCycle?.candles_loaded ?? null
    } : null
  });
});

app.get('/api/meta', async (_req, res) => {
  res.json({
    ok: true,
    port: PORT,
    snapshotPath: SNAPSHOT_PATH,
    journalDir: JOURNAL_DIR,
    staleMinutes: STALE_MINUTES
  });
});

app.get('/api/status', async (_req, res) => {
  const snapshotStat = await statSafe(SNAPSHOT_PATH);

  let snapshot = null;
  let snapshotError = null;
  if (snapshotStat.ok) {
    try {
      snapshot = await readJsonSafe(SNAPSHOT_PATH);
    } catch (e) {
      snapshotError = e?.message || String(e);
    }
  }

  const snapshotMinsStale = snapshotStat.ok ? minutesSince(snapshotStat.mtimeMs) : null;
  const snapshotIsStale = snapshotStat.ok ? snapshotMinsStale > STALE_MINUTES : true;

  const status = snapshot ? extractStatus(snapshot) : null;

  res.json({
    ok: true,
    snapshot: {
      path: SNAPSHOT_PATH,
      stat: snapshotStat,
      minsStale: snapshotMinsStale,
      isStale: snapshotIsStale,
      parseError: snapshotError
    },
    status
  });
});

app.get('/api/timeline', async (req, res) => {
  const date = (req.query.date && String(req.query.date)) || utcDateString();
  const max = Math.min(500, Math.max(1, parseInt(req.query.max || '200', 10)));

  const journalPath = await listJournalFile(date);
  const journalStat = await statSafe(journalPath);

  let events = [];
  let parseError = null;
  if (journalStat.ok) {
    try {
      events = await tailJsonl(journalPath, max);
    } catch (e) {
      parseError = e?.message || String(e);
    }
  }

  const journalMinsStale = journalStat.ok ? minutesSince(journalStat.mtimeMs) : null;
  const journalIsStale = journalStat.ok ? journalMinsStale > STALE_MINUTES : true;

  // Identify last trade event.
  let lastTrade = null;
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i];
    const action = ev?.plan?.action;
    if (action && action !== 'hold') {
      lastTrade = ev;
      break;
    }
  }

  res.json({
    ok: true,
    date,
    journal: {
      path: journalPath,
      stat: journalStat,
      minsStale: journalMinsStale,
      isStale: journalIsStale,
      parseError
    },
    lastTrade,
    events
  });
});

const WATCHDOG_LOG_PATH = process.env.WATCHDOG_LOG_PATH || '/tmp/apb_feed_watchdog.log';

app.get('/api/chart', async (req, res) => {
  const date = (req.query.date && String(req.query.date)) || utcDateString();
  const journalPath = await listJournalFile(date);

  let candles = [];
  try {
    const candleRows = await readJsonlAll(CANDLES_PATH);
    candles = candleRows.map((c) => ({
      time: Number(c.start_ts),
      open: Number(c.o),
      high: Number(c.h),
      low: Number(c.l),
      close: Number(c.c)
    })).filter((c) => Number.isFinite(c.time) && Number.isFinite(c.open) && Number.isFinite(c.high) && Number.isFinite(c.low) && Number.isFinite(c.close));
  } catch {
    candles = [];
  }

  let events = [];
  try {
    events = await tailJsonl(journalPath, 5000);
  } catch {
    events = [];
  }
  const cycles = events.filter((e) => e?.type === 'cycle');
  const markers = [];
  const equity = [];

  for (const ev of cycles) {
    const ts = Number(ev?.ts || ev?.timestamp || 0);
    const action = String(ev?.plan?.action || 'hold');
    const eq = ev?.state?.equity ?? ev?.equity;

    if (Number.isFinite(ts) && Number.isFinite(Number(eq))) {
      equity.push({ time: ts, value: Number(eq) });
    }

    if (!Number.isFinite(ts) || action === 'hold') continue;

    let color = '#3fb950';
    let position = 'belowBar';
    let shape = 'arrowUp';
    if (action === 'close') {
      color = '#d29922';
      position = 'aboveBar';
      shape = 'circle';
    } else if (action === 'flip') {
      color = '#a371f7';
      position = 'aboveBar';
      shape = 'arrowDown';
    } else if (action === 'scale') {
      color = '#58a6ff';
      position = 'belowBar';
      shape = 'square';
    }

    markers.push({
      time: ts,
      position,
      color,
      shape,
      text: action.toUpperCase()
    });
  }

  // basic per-cycle pnl from equity deltas
  const pnl = [];
  for (let i = 1; i < equity.length; i++) {
    const curr = equity[i];
    const prev = equity[i - 1];
    pnl.push({ time: curr.time, value: curr.value - prev.value });
  }

  // watchdog incidents (best effort)
  let incidents = [];
  try {
    const raw = await fs.readFile(WATCHDOG_LOG_PATH, 'utf8');
    incidents = raw
      .split(/\r?\n/)
      .filter((l) => l.includes('restarted code-apb-feed-1'))
      .slice(-200)
      .map((line) => {
        const m = line.match(/^(\S+\s+\S+)/); // syslog-like optional prefix
        const t = m ? Date.parse(m[1] + ' UTC') : NaN;
        return {
          time: Number.isFinite(t) ? Math.floor(t / 1000) : null,
          text: line.slice(0, 120)
        };
      })
      .filter((x) => Number.isFinite(x.time));
  } catch {
    incidents = [];
  }

  res.json({
    ok: true,
    date,
    candles,
    markers,
    equity,
    pnl,
    incidents
  });
});

app.get('/api/report/daily', async (req, res) => {
  const date = (req.query.date && String(req.query.date)) || utcDateString();
  const journalPath = await listJournalFile(date);
  const journalStat = await statSafe(journalPath);
  const candlesStat = await statSafe(CANDLES_PATH);

  let events = [];
  if (journalStat.ok) {
    try {
      events = await tailJsonl(journalPath, 5000);
    } catch {
      events = [];
    }
  }

  const cycles = events.filter((e) => e?.type === 'cycle');
  const actions = {};
  const desired = {};
  let lastTrade = null;
  for (const c of cycles) {
    const a = c?.plan?.action || 'none';
    actions[a] = (actions[a] || 0) + 1;
    const d = c?.signal?.desired || 'none';
    desired[d] = (desired[d] || 0) + 1;
  }
  for (let i = cycles.length - 1; i >= 0; i--) {
    if ((cycles[i]?.plan?.action || 'hold') !== 'hold') {
      lastTrade = cycles[i];
      break;
    }
  }

  const candlesMinsStale = candlesStat.ok ? minutesSince(candlesStat.mtimeMs) : null;
  const journalMinsStale = journalStat.ok ? minutesSince(journalStat.mtimeMs) : null;

  const candlesNeeded = 50;
  const candlesLoaded = Number(cycles[cycles.length - 1]?.candles_loaded ?? 0);

  res.json({
    ok: true,
    date,
    summary: {
      cycleCount: cycles.length,
      firstCycleTs: isoOrNull(cycles[0]?.ts || cycles[0]?.timestamp || null),
      lastCycleTs: isoOrNull(cycles[cycles.length - 1]?.ts || cycles[cycles.length - 1]?.timestamp || null),
      actions,
      desired,
      lastTradeTs: isoOrNull(lastTrade?.ts || lastTrade?.timestamp || null),
      candlesMinsStale,
      journalMinsStale,
      candlesNeeded,
      candlesLoaded,
      candlesRemaining: Math.max(0, candlesNeeded - candlesLoaded),
      feedStale: candlesMinsStale === null ? true : candlesMinsStale > STALE_MINUTES,
      cycleStale: journalMinsStale === null ? true : journalMinsStale > STALE_MINUTES
    }
  });
});

app.listen(PORT, () => {
  console.log(`paper-bot-dashboard listening on :${PORT}`);
  console.log(`SNAPSHOT_PATH=${SNAPSHOT_PATH}`);
  console.log(`JOURNAL_DIR=${JOURNAL_DIR}`);
  console.log(`CANDLES_PATH=${CANDLES_PATH}`);
  startDataMountSelfHeal();
});
