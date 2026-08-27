---
name: personal-flutter-notable-changes
description: Compile the weekly Flutter notable changes report. This skill guides the agent through identifying notable commits, verifying first-time contributors, retrieving PR details (authors, reviewers, media), and drafting the final Markdown report while maintaining the known_authors.md registry.
---

# Flutter Weekly Notable Changes Report

This skill implements the comprehensive process for generating the weekly notable changes report for the Flutter repository.

## Workflow

### 1. Data Gathering & Curation
- Fetch latest commits and list all changes from the last 7 days.
- **Selection Rubric**: Select ~15 commits. Prioritize developer-facing features, DX improvements, significant bug fixes, and platform/accessibility updates. De-prioritize rolls, typos, and internal refactors.
- Extract PR numbers from the selected commit messages.

### 2. Selection & Automated Information Retrieval
- **Semantic Selection**: From the candidate commits, select ~15 notable commits based on the Selection Rubric.
- **Automated Script Processing**: Run the automated Python generator script, passing the selected PR numbers as arguments. The script automatically handles individual PR detail fetching, stateful reviewer deduplication, co-author extraction, visual media scraping, and first-time contributor dual-checks:
  ```bash
  python3 .agents/skills/personal-flutter-notable-changes/scripts/generate_notable_report.py <PR_NUMBER_1> <PR_NUMBER_2> <PR_NUMBER_3> ...
  ```
  *(Optional: Add `--start-date YYYY-MM-DD` to specify when the weekly period began for new contributor checks).*

### 3. Drafting & Refining the Report
- The script prints a fully structured Markdown report to stdout.
- Redirect it to the target report file:
  ```bash
  python3 .agents/skills/personal-flutter-notable-changes/scripts/generate_notable_report.py <PR_LIST> > notable_changes_YYYY-MM-DD.md
  ```
- **Fine-Tuning Descriptions**: Open the created draft and write highly engaging, 1-2 sentence description bullets explaining the benefit/impact of each change, ending with 1-2 relevant emojis.
- **Verify Attributions**: Double-check that the generated author and reviewer attributions (including any co-authors) look correct in the file.

### 4. Housekeeping & Validation
- **Verify Missing Known Authors**: Review the stderr output block from the script. It will explicitly alert you if any of the active authors or co-authors are missing from the `known_authors.md` registry.
- **Update `known_authors.md`**: Surgical-append all flagged missing names and logins to `packages/flutter/known_authors.md` and ensure it remains alphabetized.
- **Commit**: Ask for explicit user permission before committing changes.

## Resources
- **Commands Reference**: [references/commands.md](references/commands.md)
- **Known Authors Registry**: `packages/flutter/known_authors.md`
