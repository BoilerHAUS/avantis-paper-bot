#!/usr/bin/env bash
set -euo pipefail

# Requires: gh auth login + admin rights on repo
OWNER="boilerhaus"
REPO="avantis-paper-bot"
BRANCH="main"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" \
  -f required_status_checks.strict=true \
  -f enforce_admins=true \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f required_pull_request_reviews.require_code_owner_reviews=true \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f restrictions= \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f block_creations=false

echo "Branch protection applied: ${OWNER}/${REPO}:${BRANCH}"
