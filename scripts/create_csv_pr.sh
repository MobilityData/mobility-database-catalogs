#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

BRANCH_NAME="${1:-$(git rev-parse --abbrev-ref HEAD)}"

# Checkout or create the branch
git checkout "$BRANCH_NAME"

# Configure git
git config --get user.name
git config --get user.email

# Add changes
git add .

# Count new files
NEW_FILE_COUNT=$(git status --porcelain | grep -c "^A" || echo "0")

echo "Commit changes: $NEW_FILE_COUNT"
git commit -m "Automated commit — New/Updated feed(s)"

echo "Force push changes to the branch"
git push origin HEAD || (echo "Git push failed!" && git remote -v && git branch -vv && exit 1)

echo "Check if a PR already exists"
EXISTING_PR=$(gh pr list --head "$BRANCH_NAME" --json number -q '.[0].number')

if [ -n "$EXISTING_PR" ]; then
  echo "Pull request already exists. Updating PR #$EXISTING_PR"
  # PR_URL=$(gh pr view $EXISTING_PR --json url -q '.url')
else
  echo "Creating new pull request"
  # PR_URL=$(gh pr create --title "Automated Pull Request — New/Updated feed(s) [SOURCES]" \
  #                       --body "This pull request contains new or updated feed(s)" \
  #                       --base main \
  #                       --head "$BRANCH_NAME")
fi

# Output PR URL and new file count
echo "pr-url=$PR_URL"
echo "new-file-count=$NEW_FILE_COUNT"
