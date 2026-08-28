---
name: flutter-docs-changes
description: Find all changes in a given time period that might require updates to Flutter's external documentation (website, wiki, etc.).
---

# Flutter Documentation Changes Tracker

This skill finds all recent changes in the Flutter repository that might require updates to Flutter's external documentation (e.g., the Flutter website, wiki, and explanatory documentation). This specifically excludes updates to inline code comments or dartdocs.

## Workflow

1. **Fetch Changes**: Use the `flutter-fetch-changes` skill to retrieve all commits for a given time period. If no time frame is specified, default to the last 7 days.
2. **Filter for Documentation Impact**: Analyze the list of fetched changes to identify any that might necessitate documentation updates.
    *   **Focus On**: New features, developer-facing behavior changes, deprecations, significant DX improvements, new APIs, or breaking changes that affect how developers build with Flutter.
    *   **Exclude**: Commits that only modify inline dartdocs, internal framework refactors, dependency rolls, or typo fixes that don't impact external developers.
3. **Report Generation**: Output a human-readable list of these candidate commits. For each included change, provide a brief reasoning of *why* it might require us to update the website, wiki, or other external documentation.
