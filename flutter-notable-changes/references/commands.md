# Commands for Weekly Notable Changes Report

This reference provides the exact commands for each phase of the reporting process across `flutter/flutter`, `flutter/website`, and `dart-lang/site-www`.

## Phase 1: Data Gathering
*(See `flutter-fetch-changes` skill for fetching commits across `flutter/flutter`, `flutter/website`, and `dart-lang/site-www`)*

## Phase 2: Information Retrieval (DATA INTEGRITY MANDATE)
**DO NOT rely on bulk output. Query each PR individually.**
Always pass `--repo <REPO>` (`flutter/flutter`, `flutter/website`, or `dart-lang/site-www`): a local checkout may have many fork remotes or belong to a different repository.
```shell
# Get author login, human reviewers (all states), title, url, and body
# Replace <REPO> with flutter/flutter, flutter/website, or dart-lang/site-www
gh pr view <PR_NUMBER> --repo <REPO> --json author,reviews,title,url,body \
  --template 'Title: {{.title}}{{"\n"}}Author: {{.author.login}} ({{.author.name}}){{"\n"}}Reviewers: {{range .reviews}}{{if not .author.is_bot}}{{.author.login}} {{end}}{{end}}{{"\n"}}'
```

```shell
# Confirm author name from git history for a specific flutter/flutter commit SHA
git log -n 1 --format="%an <%ae>" <SHA>
```

```shell
# Get PR body for visual media attribution
gh pr view <PR_NUMBER> --repo <REPO> --json body -q ".body"
```

## Phase 3: First-Time Contributor Verification (CRITICAL)
Query `upstream/master` (not `HEAD`) for `flutter/flutter`, and search across all three repositories on GitHub so prior contributions in any of the repos are detected.
```shell
# Automated check for author's very first commit in local flutter/flutter repository
git log upstream/master --author="<LOGIN>" --reverse --pretty=format:"%H %ci %s" | head -n 1
```

```shell
# Secondary check: Are there ANY commits from this login before the start of the week across all three repos?
gh search commits --author-date "<YYYY-MM-DD" --author="<LOGIN>" \
  --repo "flutter/flutter" --repo "flutter/website" --repo "dart-lang/site-www"
```

## Phase 4: Review Categorization
PRs from `flutter/website` and `dart-lang/site-www` are automatically placed into the `Documentation and Website` category. For `flutter/flutter` PRs, categories are derived from GitHub labels, which is a heuristic. The script prints a `REVIEW CATEGORIZATION` block on stderr for PRs whose labels are ambiguous or repo-wide. Override any of them:
```shell
python3 <skill_dir>/scripts/generate_notable_report.py <PR_SPECS> \
  --category 192649='Tooling & Developer Experience' \
  --category flutter/website#13925='Documentation and Website'
```
Valid categories: `Material Design`, `Cupertino (iOS-style)`, `Accessibility`,
`Framework & Core Libraries`, `Engine & Performance`, `Web Platform`,
`Android Platform`, `iOS Platform`, `Desktop Platforms`,
`Tooling & Developer Experience`, `Documentation and Website`.

```shell
# Inspect a PR's labels directly when deciding a category
gh pr view <PR_NUMBER> --repo <REPO> --json labels -q '[.labels[].name]|join(" | ")'
```

## Phase 5: Verification (MANDATORY)
**Perform a final audit of your report by re-querying the data for each PR one last time.**
```shell
# Final integrity audit: supports both bare PR numbers (flutter/flutter) and <repo>#<pr> specs
for spec in <PR_SPECS>; do
  if [[ "$spec" == *"#"* ]]; then
    repo="${spec%#*}"
    pr="${spec#*#}"
  else
    repo="flutter/flutter"
    pr="$spec"
  fi
  gh pr view "$pr" --repo "$repo" --json number,author,reviews \
    -q "\"$repo#\"+(.number|tostring)+\": \"+.author.login+\" | reviewers: \"+([.reviews[]|select(.author.is_bot|not)|.author.login]|unique|join(\", \"))"
done
```
Note that this audit lists self-reviews (the author commenting on their own PR);
the generator filters those out, so a reviewer matching the author is expected.

