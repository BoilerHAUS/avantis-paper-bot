#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail(){ echo "[docs-check][fail] $1"; exit 1; }
warn(){ echo "[docs-check][warn] $1"; }
pass(){ echo "[docs-check][pass] $1"; }

# Minimal metadata gate for contract/runbook docs (v1 set)
required_docs=(
  "docs/operations/RUNBOOK_PAPER_V1.md"
  "docs/strategy/STRATEGY_CONTRACT_V1.md"
  "docs/dashboard/DASHBOARD_CONTRACT_V1.md"
)

for f in "${required_docs[@]}"; do
  [[ -f "$f" ]] || { warn "$f missing (skip metadata check until doc exists)"; continue; }
  grep -Eq '^## metadata' "$f" || fail "$f missing metadata section"
  grep -Eq '^- version:' "$f" || fail "$f missing metadata: version"
  grep -Eq '^- owner_role:' "$f" || fail "$f missing metadata: owner_role"
  grep -Eq '^- review_cadence:' "$f" || fail "$f missing metadata: review_cadence"
  grep -Eq '^- next_review_due:' "$f" || fail "$f missing metadata: next_review_due"
  pass "$f metadata ok"
done

# Internal docs link integrity for backtick links (docs/*.md + dashboard/*.md)
while IFS= read -r f; do
  while IFS= read -r link; do
    target=$(echo "$link" | sed -E 's/.*`([^`]+)`/\1/')
    case "$target" in
      docs/*.md|dashboard/*.md|README.md|boilerclaw/*.md)
        [[ -f "$target" ]] || fail "$f references missing file: $target"
        ;;
    esac
  done < <(grep -oE '`(docs/[^`]+\.md|dashboard/[^`]+\.md|README\.md|boilerclaw/[^`]+\.md)`' "$f" || true)
done < <(find docs dashboard -type f -name '*.md' | sort)
pass "internal docs links ok"

# Canonical index cross-reference check (enabled when docs/README.md exists)
INDEX="docs/README.md"
if [[ -f "$INDEX" ]]; then
  grep -Fq 'docs/architecture.md' "$INDEX" || fail "$INDEX missing cross-reference: docs/architecture.md"
  grep -Fq 'docs/REPO_UPDATE_PROCESS.md' "$INDEX" || fail "$INDEX missing cross-reference: docs/REPO_UPDATE_PROCESS.md"
  grep -Fq 'dashboard/README.md' "$INDEX" || fail "$INDEX missing cross-reference: dashboard/README.md"
  pass "canonical index cross-references ok"
else
  warn "$INDEX missing; canonical index check skipped"
fi

pass "docs quality gate complete"