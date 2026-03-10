export function parseStrategyIds(raw, fallback = 'conservative') {
  const vals = String(raw || fallback)
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean);
  return vals.length ? vals : [fallback];
}

export function normalizeStrategyId(raw, strategyIds, defaultId = 'conservative') {
  const v = String(raw || defaultId).trim();
  return strategyIds.includes(v) ? v : defaultId;
}

export function strategySnapshotPath(baseSnapshotPath, strategyId, defaultId = 'conservative') {
  if (strategyId === defaultId) return baseSnapshotPath;
  return baseSnapshotPath.replace(/\/state\/snapshot\.json$/, `/strategies/${strategyId}/state/snapshot.json`);
}

export function strategyJournalDir(baseJournalDir, strategyId, defaultId = 'conservative') {
  if (strategyId === defaultId) return baseJournalDir;
  return baseJournalDir.replace(/\/journal$/, `/strategies/${strategyId}/journal`);
}
