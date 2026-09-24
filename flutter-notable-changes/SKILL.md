---
name: flutter-notable-changes
description: Compile the weekly Flutter notable changes report. This skill guides the agent through identifying notable commits, verifying first-time contributors, retrieving PR details (authors, reviewers, media), and drafting the final Markdown report while maintaining the known_authors.md registry.
---

# Flutter Weekly Notable Changes Report

This skill implements the comprehensive process for generating the weekly notable changes report for the Flutter repository.

## Prerequisites
- Run from a `flutter/flutter` checkout that has a remote tracking the upstream repo (the script defaults to `upstream/master`).
- Fetch first (`git fetch upstream`) so the commit count and contributor history are current. A local branch that is behind or ahead of upstream will produce a wrong commit count.
- `gh` must be authenticated.

## Workflow

### 1. Data Gathering & Curation
- Use the `flutter-fetch-changes` skill to fetch commits and list all changes for the relevant time range.
- **Selection Rubric**: Select ~15 commits. Prioritize developer-facing features, DX improvements, significant bug fixes, and platform/accessibility updates. De-prioritize rolls, typos, and internal refactors. See [references/rubric.md](references/rubric.md).
- Extract PR numbers from the selected commit messages.

### 2. Selection & Automated Information Retrieval
- **Semantic Selection**: From the candidate commits, select ~15 notable commits based on the Selection Rubric.
- **Automated Script Processing**: Run the automated Python generator script, passing the selected PR numbers as arguments. The script automatically handles individual PR detail fetching, stateful reviewer deduplication, co-author extraction, visual media scraping, categorization, and first-time contributor dual-checks:
  ```bash
  python3 <skill_dir>/scripts/generate_notable_report.py <PR_NUMBER_1> <PR_NUMBER_2> ...
  ```
  Useful flags:
  - `--start-date YYYY-MM-DD` / `--end-date YYYY-MM-DD`: the reporting period (start date also gates new-contributor checks).
  - `--since "7 days ago"`: the range used for the total commit count.
  - `--ref upstream/master`: the git ref used for the commit count and author history. Defaults to `upstream/master`; the script warns and falls back to `HEAD` if the ref does not exist.
  - `--repo flutter/flutter`: the GitHub repo queried by `gh`. Pinning this avoids misresolution in checkouts with many fork remotes.
  - `--category <PR>='<Category>'`: override the computed category for a PR. Repeatable.

### 3. Drafting & Refining the Report
- The script prints a fully structured Markdown report to stdout.
- Redirect it to the target report file:
  ```bash
  python3 <skill_dir>/scripts/generate_notable_report.py <PR_LIST> > notable_changes_YYYY-MM-DD.md
  ```
- **Fine-Tuning Descriptions**: Open the created draft and write highly engaging, 1-2 sentence description bullets explaining the benefit/impact of each change, ending with 1-2 relevant emojis.
- **Verify Attributions**: Double-check that the generated author and reviewer attributions (including any co-authors) look correct in the file.

### 4. Review Categorization
- Review the `⚠️  REVIEW CATEGORIZATION` block on stderr. Category assignment is label-based and only a heuristic, so the script flags PRs whose labels are ambiguous (multiple competing areas) or repo-wide (e.g. a mass reformat touching every label).
- For each flagged PR, decide the right section and either re-run with `--category <PR>='<Category>'` or move the entry by hand in the draft.

### 5. Validation & Commit
- Re-audit the attributions for every PR one last time (see [references/commands.md](references/commands.md), Phase 5).
- **Commit**: Ask for explicit user permission before committing changes.

## Resources
- **Commands Reference**: [references/commands.md](references/commands.md)
- **Selection Rubric**: [references/rubric.md](references/rubric.md)
- **Report Template**: [references/report_template.md](references/report_template.md)

