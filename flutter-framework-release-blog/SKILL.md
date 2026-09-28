---
name: flutter-framework-release-blog
description: Drafts the "Framework" section of the Flutter release blog. Use when preparing release announcements to analyze commits, verify PR inclusion (including reverts/relands), and group changes into thematic narratives like Material/Cupertino updates, Web, and Accessibility.
---

# Flutter Framework Release Blog

This skill guides the process of drafting the "What's New in the Framework" section for a Flutter release blog post. It focuses on creating a narrative of evolution rather than a simple list of changes.

## Workflow

### 1. Setup and Theme Identification
Compare the previous stable tag (`old_tag`) to the new release tag (`new_tag`).
- **Analyze**: Scope commit searches specifically to the framework packages (`packages/flutter/lib/` and `packages/flutter/test/`) while filtering out automated rolls and merges:
  ```bash
  git log --oneline --no-merges --invert-grep --grep="Roll engine from" --grep="Roll pub packages" <old_tag>..<new_tag> -- packages/flutter/lib/ packages/flutter/test/
  ```
- **Propose Themes**: Identify 4-6 high-level themes based on actual framework commits (e.g., Material & Cupertino, Web, Accessibility, Scrolling & Navigation, Foundations).

### 2. Iterative Drafting (Per Theme)
For each approved theme:
1. **Gather PRs**: Find relevant PRs in the filtered commit log for that theme.
2. **Critically Analyze**: Do not rely solely on initial PR titles and markdown descriptions (`gh pr view`), which often contain outdated plans or TODOs. Inspect the actual landed commit summary and diff to verify exact signatures and behavior:
   ```bash
   git log -1 --format=%B <commit_sha>
   git show --stat <commit_sha>
   git diff <commit_sha>^..<commit_sha> -- packages/flutter/lib/
   ```
3. **Verify Inclusion**:
   - Check release inclusion accurately across release candidate branches and cherry-picks using Flutter's official `find-release` tool:
     ```bash
     dart run engine/src/flutter/third_party/dart/tools/find_release.dart --commit=<SHA> --channel=stable
     ```
     Alternatively, verify via git logs in the release range if the tool is unavailable:
     ```bash
     git log <old_tag>..<RELEASE_TAG> --grep="cherry picked from commit <SHA>" || git merge-base --is-ancestor <SHA> <RELEASE_TAG>
     ```
   - Check for reverts bounded strictly to the release range (`<old_tag>..<RELEASE_TAG>`) to avoid false positives from post-release reverts on `master`. Search for both PR numbers and original commit SHAs:
     ```bash
     git log <old_tag>..<RELEASE_TAG> -E --grep="Revert(s)?.*#<pr_number>" --grep="<original_commit_sha>"
     ```
   - If reverted within the release range, check whether the reland PR merged before the release cutoff (`<RELEASE_TAG>`).
4. **Draft Narrative**: Group related changes into a cohesive story. Use sentence case for headers. Focus on *why* the change matters. For any featured PRs, check whether the author is not a member of the GitHub Googlers team (e.g., via commit author or `gh pr view`) and actively look for opportunities to feature and credit community contributors by name in the narrative.
5. **Deduplication Check**: Before appending any newly drafted section to the release document (`X-XX-release.md`), cross-reference all PR numbers (`#XXXXXX`) against existing sections. If a PR or widget feature is already documented, remove or consolidate the duplicate mention into the most cohesive section.

### 3. Special Sections
- **Deprecations and Breaking Changes**: 
  - Consult the official breaking changes documentation at `https://docs.flutter.dev/release/breaking-changes`.
  - Search GitHub for PRs marked with the breaking change label: `gh pr list --state merged --label "breaking-change" --search "merged:<old_tag_date>..<new_tag_date>"`
  - Search framework code specifically (`packages/flutter/lib/`) with context around new `@Deprecated` annotations:
    ```bash
    git diff -U3 <old_tag>..<new_tag> -- packages/flutter/lib/ | grep -C 3 -E '^\+.*@Deprecated'
    ```
  - Verify each candidate breaking change or deprecation is included in `<RELEASE_TAG>` before drafting.
- **Strategic & Non-Commit Announcements**: Ask the user if there are any high-level strategic announcements or non-commit-based initiatives (e.g., package unbundling or policy updates) that should be included in the release document before finalization.

### 4. Finalization
- **Tone and Style**: Ensure the draft matches the professional, engaging, and developer-focused tone of previous release blogs. See [sample-blog.md](references/sample-blog.md) for a reference implementation.
- **Introduction & Summary**: Write a compelling intro highlighting the "story" of the release, and conclude with the impact on the developer experience.
- **Review**: Perform a holistic check to ensure consistent tone, present tense, descriptive embedded links, and zero duplicate PR mentions across sections.

## Principles
- **Specific and Explicit**: List affected widgets, classes, and APIs directly instead of using vague language.
- **Inclusive Language**: Avoid "we/our"; use "developers" or passive voice ("A feature is available").
- **Embedded PR Links**: Do not link PRs as standalone PR numbers (`[#123456](...)`). Instead, embed the pull request link directly into the relevant descriptive text in the sentence (e.g., `[Popup windows are now supported on Linux](https://github.com/flutter/flutter/pull/185866)`). Always attribute changes to their pull request URL, not commit hashes.
- **Feature Community Contributors**: Actively look for opportunities to feature and credit external/community contributors by name for featured PRs when they are not members of the GitHub Googlers team.
- **Avoid Signs of AI Writing**: Strictly avoid formulaic patterns described in [Wikipedia:Signs_of_AI_writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing). Specifically:
  - Do not use promotional puffery or AI vocabulary (`robust`, `seamless`, `elevate`, `unlocks the ability`, `empower`, `foundational`, `granular`, `streamline`, `resilient`, `paramount`, `tapestry`, `state-of-the-art`, `significantly`, `revolutionary`).
  - Do not write formulaic triples ("rule of three" grouping of adjectives, nouns, or verbs like `A, B, and C`).
  - Do not write generic introductory filler/topic sentences that state general truths (`Text selection is a core component...`, `Accessibility remains a primary focus...`). Start paragraphs directly with concrete facts.
  - Do not use negative parallelisms (`not only X, but also Y`, `not X, but Y`, `X rather than Y`).
  - Do not overuse em dashes (`—...—`) or dramatic copulatives/verbs (`serves as`, `stands as`, `remains a primary focus`). Use plain verbs (`is`, `are`, `adds`, `updates`, `supports`, `fixes`).
- **Narrative over Lists**: Weave updates into a compelling story explaining *why* changes matter without relying on AI clichés.
- **Sentence Case Headers**: All headings and subheadings must use sentence case (e.g., "Material and Cupertino updates"), not title case.
