# Commands for Weekly Notable Changes Report

This reference provides the exact commands for each phase of the reporting process.

## Phase 1: Data Gathering
```shell
# Fetch latest commits
git fetch

# List commits from the last 7 days
git log --since="7 days ago" --pretty=format:"%H - %s"

# Get total number of commits
git log --since="7 days ago" --oneline | wc -l
```

## Phase 2: Information Retrieval (DATA INTEGRITY MANDATE)
**DO NOT rely on bulk output. Query each PR individually.**
```shell
# Get author login, human reviewers (all states), title, url, and body
# This excludes bots and extracts ALL human participants in the review
gh pr view <PR_NUMBER> --json author,reviews,title,url,body \
  --template 'Title: {{.title}}{{"\n"}}Author: {{.author.login}} ({{.author.name}}){{"\n"}}Reviewers: {{range .reviews}}{{if not .author.is_bot}}{{.author.login}} {{end}}{{end}}{{"\n"}}'
```

```shell
# Confirm author name from git history for a specific commit SHA
git log -n 1 --format="%an <%ae>" <SHA>
```

```shell
# Get PR body for visual media attribution
gh pr view <PR_NUMBER> --json body -q ".body"
```

## Phase 3: First-Time Contributor Verification (CRITICAL)
```shell
# Automated check for author's very first commit in the repository
git log --author="<LOGIN>" --reverse --pretty=format:"%H %ci %s" | head -n 1
```

```shell
# Secondary check: Are there ANY commits from this login before the start of the week?
gh search commits --author-date "..<START_DATE_YYYY-MM-DD>" --author="<LOGIN>" --repo "flutter/flutter"
```

## Phase 4: Housekeeping
```shell
# Check if author exists in known_authors.md (case-insensitive)
grep -i "<LOGIN_OR_NAME>" packages/flutter/known_authors.md
```

## Phase 5: Verification (MANDATORY)
**Perform a final audit of your report by re-querying the data for each PR one last time.**
```shell
# Final integrity audit script
for pr in <PR_LIST>; do
  gh pr view $pr --json author,reviews,title -q '"PR #"+(.number|tostring)+": "+.author.login+" (reviewers: "+([.reviews[].author.login] | unique | join(", "))+")"'
done
```
