---
name: flutter-notable-changes
description: Compile the weekly Flutter notable changes report across flutter/flutter, flutter/website, and dart-lang/site-www. This skill guides the agent through identifying notable commits, verifying first-time contributors, retrieving PR details (authors, reviewers, media), and drafting the final Markdown report.
---

# Flutter Weekly Notable Changes Report

This skill implements the comprehensive process for generating the weekly notable changes report across the main Flutter repository (`flutter/flutter`), the Flutter website repository (`flutter/website`), and the Dart website repository (`dart-lang/site-www`).

## Prerequisites
- Run from a `flutter/flutter` checkout that has a remote tracking the upstream repo (the script defaults to `upstream/master`). Website repositories (`flutter/website` and `dart-lang/site-www`) are queried remotely via the `gh` CLI without requiring local clones.
- Fetch first (`git fetch upstream`) so the `flutter/flutter` commit count and contributor history are current. A local branch that is behind or ahead of upstream will produce a wrong commit count.
- `gh` must be authenticated.

## Workflow

### 1. Data Gathering & Curation
- Use the `flutter-fetch-changes` skill to fetch commits and list all changes across `flutter/flutter`, `flutter/website`, and `dart-lang/site-www` for the relevant time range.
- **Selection Rubric**: Select ~15–20 notable changes total across the three repositories. Prioritize developer-facing features, DX improvements, significant bug fixes, platform/accessibility updates, and substantive documentation/guide additions on `docs.flutter.dev` and `dart.dev`. De-prioritize rolls, typos, broken link fixes, and internal refactors. See [references/rubric.md](references/rubric.md).
- Extract PR numbers from the selected commit messages. Qualify website PRs with their repository (`flutter/website#<PR>` or `website#<PR>`, and `dart-lang/site-www#<PR>` or `site-www#<PR>`). Bare PR numbers default to `flutter/flutter`.

### 2. Selection & Automated Information Retrieval
- **Semantic Selection**: From the candidate commits across all three repositories, select ~15–20 notable PRs based on the Selection Rubric.
- **Automated Script Processing**: Run the automated Python generator script, passing the selected PR specs as arguments. The script automatically fetches commit counts for `flutter/flutter`, `flutter/website`, and `dart-lang/site-www`, retrieves PR details from the appropriate repo, deduplicates human reviewers, extracts co-authors and visual media, assigns categories (placing website PRs into `Documentation and Website`), and runs first-time contributor dual-checks across the repositories:
  ```bash
  python3 <skill_dir>/scripts/generate_notable_report.py <PR_1> <PR_2> flutter/website#<PR_3> dart-lang/site-www#<PR_4> ...
  ```
  Useful flags:
  - `--start-date YYYY-MM-DD` / `--end-date YYYY-MM-DD`: the reporting period (also used for website commit counts and new-contributor checks).
  - `--since "7 days ago"`: the range used for the local `flutter/flutter` commit count.
  - `--ref upstream/master`: the git ref used for the `flutter/flutter` commit count and author history. Defaults to `upstream/master`; the script warns and falls back to `HEAD` if the ref does not exist.
  - `--repo flutter/flutter`: default GitHub repo for bare PR numbers.
  - `--category <PR_SPEC>='<Category>'`: override the computed category for a PR (e.g. `--category 192649='Tooling & Developer Experience'` or `--category flutter/website#13925='Documentation and Website'`). Repeatable.
  - `--output <PATH>` / `-o <PATH>`: where to write the report. Defaults to `<skill_dir>/outputs/notable_changes_<END_DATE>.md`. Pass `-` to print to stdout instead.

### 3. Drafting & Refining the Report
- The script writes a fully structured Markdown report to `<skill_dir>/outputs/notable_changes_<END_DATE>.md` (the `outputs/` directory is created automatically and is gitignored) and prints the path on stderr:
  ```bash
  python3 <skill_dir>/scripts/generate_notable_report.py <PR_SPECS>
  ```
- Always keep the final report in `<skill_dir>/outputs/`. Do not write it elsewhere in the repository.
- **Fine-Tuning Descriptions**: Open the created draft and write highly engaging, 1-2 sentence description bullets explaining the benefit/impact of each change, ending with 1-2 relevant emojis.
- **Image Size Limit**: Every image in the report must be no more than 300px tall. The script emits images as `<img src="URL" alt="..." style="max-height: 300px; max-width: 100%;">`. Any image you add or edit by hand must use the same form; never use plain `![alt](url)` syntax, which cannot constrain size.
- **Verify Attributions**: Double-check that the generated author and reviewer attributions (including any co-authors) look correct in the file.

### 4. Review Categorization
- Review the `⚠️  REVIEW CATEGORIZATION` block on stderr. Category assignment is label-based and only a heuristic (PRs from `flutter/website` and `dart-lang/site-www` are automatically categorized under `Documentation and Website`), so the script flags PRs whose labels are ambiguous (multiple competing areas) or repo-wide (e.g. a mass reformat touching every label).
- For each flagged PR, decide the right section and either re-run with `--category <PR_SPEC>='<Category>'` or move the entry by hand in the draft.

### 5. Validation & Commit
- Re-audit the attributions for every PR one last time (see [references/commands.md](references/commands.md), Phase 5).
- **Commit**: Ask for explicit user permission before committing changes.

## Resources
- **Commands Reference**: [references/commands.md](references/commands.md)
- **Selection Rubric**: [references/rubric.md](references/rubric.md)
- **Report Template**: [references/report_template.md](references/report_template.md)

