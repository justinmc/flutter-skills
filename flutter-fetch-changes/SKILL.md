---
name: flutter-fetch-changes
description: Fetch commits and list all changes across flutter/flutter, flutter/website, and dart-lang/site-www for a given time range (defaults to the last 7 days).
---

# Flutter Fetch Changes

This skill is used to fetch commits and list changes from the main Flutter repository (`flutter/flutter`), the Flutter website repository (`flutter/website`), and the Dart website repository (`dart-lang/site-www`) over a specified time range.

## Workflow
1. **Determine Time Range**: Evaluate the user's requested time range. If no time range is specified, default to the last 7 days (compute the ISO start date `YYYY-MM-DD`).
2. **Fetch Commits**:
   - Retrieve commits from the local `flutter/flutter` checkout (`upstream/master`).
   - Query recent commits/merged PRs from `flutter/website` and `dart-lang/site-www` remotely via the `gh` CLI (no local clones required for the website repos).
3. **List Changes**: List all the changes and total commit counts across all three repositories during the specified time range.

## Reference Commands
You can use the following commands to fetch and list the changes:
```shell
# 1. Main Flutter repository (run from a flutter/flutter checkout)
git fetch upstream
git log upstream/master --since="7 days ago" --pretty=format:"%H - %s"
git log upstream/master --since="7 days ago" --oneline | wc -l

# 2. Flutter website repository (flutter/website) via gh CLI
# Replace YYYY-MM-DD with the start date (e.g., 7 days ago)
gh api "repos/flutter/website/commits?since=YYYY-MM-DDT00:00:00Z&per_page=100" --paginate \
  --jq '.[] | "\(.sha[0:10]) - \(.commit.message | split("\n")[0])"'
gh api "repos/flutter/website/commits?since=YYYY-MM-DDT00:00:00Z&per_page=100" --paginate \
  --jq '.[].sha' | wc -l

# 3. Dart website repository (dart-lang/site-www) via gh CLI
gh api "repos/dart-lang/site-www/commits?since=YYYY-MM-DDT00:00:00Z&per_page=100" --paginate \
  --jq '.[] | "\(.sha[0:10]) - \(.commit.message | split("\n")[0])"'
gh api "repos/dart-lang/site-www/commits?since=YYYY-MM-DDT00:00:00Z&per_page=100" --paginate \
  --jq '.[].sha' | wc -l
```
