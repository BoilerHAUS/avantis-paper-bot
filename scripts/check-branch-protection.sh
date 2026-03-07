#!/usr/bin/env bash
set -euo pipefail

OWNER="BoilerHAUS"
REPO="avantis-paper-bot"
BRANCH="$(gh repo view ${OWNER}/${REPO} --json defaultBranchRef -q .defaultBranchRef.name)"

json=$(gh api "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection")

echo "Branch protection for ${OWNER}/${REPO}:${BRANCH}"

echo "$json" | jq '{
  required_status_checks: {
    strict: .required_status_checks.strict,
    contexts: .required_status_checks.contexts
  },
  enforce_admins: .enforce_admins.enabled,
  required_pull_request_reviews: {
    required_approving_review_count: .required_pull_request_reviews.required_approving_review_count,
    require_code_owner_reviews: .required_pull_request_reviews.require_code_owner_reviews,
    dismiss_stale_reviews: .required_pull_request_reviews.dismiss_stale_reviews
  },
  required_linear_history: .required_linear_history.enabled,
  allow_force_pushes: .allow_force_pushes.enabled,
  allow_deletions: .allow_deletions.enabled
}'

# Hard checks
has_ctx=$(echo "$json" | jq -r '.required_status_checks.contexts[]?' | grep -Fx 'lint-and-smoke' || true)
strict=$(echo "$json" | jq -r '.required_status_checks.strict')
codeowners=$(echo "$json" | jq -r '.required_pull_request_reviews.require_code_owner_reviews')
approvals=$(echo "$json" | jq -r '.required_pull_request_reviews.required_approving_review_count')
linear=$(echo "$json" | jq -r '.required_linear_history.enabled')
forcepush=$(echo "$json" | jq -r '.allow_force_pushes.enabled')
deletions=$(echo "$json" | jq -r '.allow_deletions.enabled')

fail=0
[[ "$strict" == "true" ]] || { echo "❌ strict status checks not enabled"; fail=1; }
[[ -n "$has_ctx" ]] || { echo "❌ required context lint-and-smoke missing"; fail=1; }
[[ "$codeowners" == "true" ]] || { echo "❌ code owner reviews not required"; fail=1; }
[[ "$approvals" =~ ^[1-9] ]] || { echo "❌ approvals count < 1"; fail=1; }
[[ "$linear" == "true" ]] || { echo "❌ linear history not required"; fail=1; }
[[ "$forcepush" == "false" ]] || { echo "❌ force pushes allowed"; fail=1; }
[[ "$deletions" == "false" ]] || { echo "❌ deletions allowed"; fail=1; }

if [[ "$fail" -eq 0 ]]; then
  echo "✅ branch protection baseline checks passed"
else
  exit 1
fi
