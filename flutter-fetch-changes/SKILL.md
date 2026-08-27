---
name: flutter-fetch-changes
description: Fetch commits and list all changes for a given time range (defaults to the last 7 days).
---

# Flutter Fetch Changes

This skill is used to fetch commits and list changes from the Flutter repository over a specified time range.

## Workflow
1. **Determine Time Range**: Evaluate the user's requested time range. If no time range is specified, default to the last 7 days.
2. **Fetch Commits**: Retrieve the commits for the specified time range.
3. **List Changes**: List all the changes that occurred during the specified time range.

## Reference Commands
You can use the following commands to fetch and list the changes:
```shell
# Fetch latest commits
git fetch

# List commits from a certain time frame (replace "7 days ago" as needed)
git log --since="7 days ago" --pretty=format:"%H - %s"

# Get total number of commits
git log --since="7 days ago" --oneline | wc -l
```
