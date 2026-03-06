#!/usr/bin/env bash
set -euo pipefail

BRANCH_NAME="dien-zinex"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
TARGET_REL="${SCRIPT_DIR#$REPO_ROOT/}"
COMMIT_MSG="${1:-chore(${TARGET_REL}): update $(date '+%Y-%m-%d %H:%M:%S')}"

cd "$REPO_ROOT"

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: Remote 'origin' not found."
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "$BRANCH_NAME" ]]; then
  if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    git switch "$BRANCH_NAME"
  else
    git switch -c "$BRANCH_NAME"
  fi
fi

# Avoid accidentally committing staged changes outside this folder.
STAGED_OUTSIDE="$(git diff --cached --name-only -- . ":(exclude)$TARGET_REL" || true)"
if [[ -n "$STAGED_OUTSIDE" ]]; then
  echo "ERROR: There are staged changes outside '$TARGET_REL'."
  echo "Please commit/reset them first, then rerun this script."
  exit 1
fi

git add -A -- "$TARGET_REL"

if ! git diff --cached --quiet -- "$TARGET_REL"; then
  git commit -m "$COMMIT_MSG"
else
  echo "No new changes to commit in '$TARGET_REL'."
fi

echo "Pushing to origin/$BRANCH_NAME ..."
if git push -u origin "$BRANCH_NAME"; then
  echo "Done: pushed '$BRANCH_NAME' to origin."
else
  echo "Push failed (likely authentication issue)."
  echo "Please authenticate git (PAT/credential helper), then rerun:"
  echo "  ./$(basename "$0")"
  exit 1
fi
