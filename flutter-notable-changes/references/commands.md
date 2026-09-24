# Commands for Weekly Notable Changes Report

This reference provides the exact commands for each phase of the reporting process.

## Phase 1: Data Gathering
*(Moved to `flutter-fetch-changes` skill)*

## Phase 2: Information Retrieval (DATA INTEGRITY MANDATE)
**DO NOT rely on bulk output. Query each PR individually.**
Always pass `--repo flutter/flutter`: a Flutter checkout usually has many fork
remotes, and `gh` may otherwise resolve the wrong repository.
```shell
# Get author login, human reviewers (all states), title, url, and body
# This excludes bots and extracts ALL human participants in the review
gh pr view <PR_NUMBER> --repo flutter/flutter --json author,reviews,title,url,body \
  --template 'Title: {{.title}}{{"\n"}}Author: {{.author.login}} ({{.author.name}}){{"\n"}}Reviewers: {{range .reviews}}{{if not .author.is_bot}}{{.author.login}} {{end}}{{end}}{{"\n"}}'
```

```shell
# Confirm author name from git history for a specific commit SHA
git log -n 1 --format="%an <%ae>" <SHA>
```

```shell
# Get PR body for visual media attribution
gh pr view <PR_NUMBER> --repo flutter/flutter --json body -q ".body"
```

## Phase 3: First-Time Contributor Verification (CRITICAL)
Query `upstream/master`, not `HEAD`: a local branch is often stale or carries
unmerged work, which skews both commit counts and author history.
```shell
# Automated check for author's very first commit in the repository
git log upstream/master --author="<LOGIN>" --reverse --pretty=format:"%H %ci %s" | head -n 1
```

```shell
# Secondary check: Are there ANY commits from this login before the start of the week?
gh search commits --author-date "..<START_DATE_YYYY-MM-DD>" --author="<LOGIN>" --repo "flutter/flutter"
```

## Phase 4: Review Categorization
Categories are derived from GitHub labels, which is only a heuristic. The script
prints a `REVIEW CATEGORIZATION` block on stderr for PRs whose labels are
ambiguous or repo-wide. Override any of them:
```shell
python3 <skill_dir>/scripts/generate_notable_report.py <PR_LIST> \
  --category 192649='Tooling & Developer Experience' \
  --category 187251='Android Platform'
```
Valid categories: `Material Design`, `Cupertino (iOS-style)`, `Accessibility`,
`Framework & Core Libraries`, `Engine & Performance`, `Web Platform`,
`Android Platform`, `iOS Platform`, `Desktop Platforms`,
`Tooling & Developer Experience`.

```shell
# Inspect a PR's labels directly when deciding a category
gh pr view <PR_NUMBER> --repo flutter/flutter --json labels -q '[.labels[].name]|join(" | ")'
```

## Phase 5: Verification (MANDATORY)
**Perform a final audit of your report by re-querying the data for each PR one last time.**
```shell
# Final integrity audit: author plus deduplicated, bot-filtered reviewers
for pr in <PR_LIST>; do
  gh pr view $pr --repo flutter/flutter --json number,author,reviews \
    -q '"PR #"+(.number|tostring)+": "+.author.login+" | reviewers: "+([.reviews[]|select(.author.is_bot|not)|.author.login]|unique|join(", "))'
done
```
Note that this audit lists self-reviews (the author commenting on their own PR);
the generator filters those out, so a reviewer matching the author is expected.

