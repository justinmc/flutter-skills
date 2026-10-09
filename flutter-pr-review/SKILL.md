---
name: flutter-pr-review
description: Use this skill to aid in reviewing a Flutter PR.
---

# Flutter Pull Request Review

This skill guides the agent in producing a code review report for a given
Flutter pull request. The purpose of the report is to help the user perform
their own thorough and thoughtful code review of the PR. It point out any bugs,
deviations from typical Flutter code style and API design, performance
optimizations, grammatical or documentation problems, and any other information
useful to the user's own review. In addition, it should gather and condense any
context related to the PR, such as links to all related artifacts (docs, GitHub
issues, etc.), summaries of discussions that have happened related to the PR and
its subject area, summaries of previous changes related to the modified code in
the PR, and anything else that may be useful for the user as they perform their
own code review.

The report is an aid, not a substitute, for the user's review. Never post
comments, approve, request changes, or otherwise act on the PR on GitHub. Only
write the report.

## Prerequisites

1.  Python 3 with the `requests` library (`pip install requests`).
2.  The `GITHUB_TOKEN` environment variable set to a GitHub token that can read
    public repositories. The `gh` CLI is helpful but optional.

All paths below are relative to this skill's directory (the directory
containing this file). Run scripts from this directory so that `tmp/` and
`output/` end up here (both are git-ignored).

## Files in this skill

| File | Purpose |
| --- | --- |
| [scripts/fetch_pr_context.py](scripts/fetch_pr_context.py) | Fetches the PR, its full diff, all discussion, linked issues/PRs, cross-references, CI status, and recent history of every changed file. |
| [scripts/check_best_practices.py](scripts/check_best_practices.py) | Heuristic scan of a diff's added lines for likely deviations from the best practices and style guide. |
| [resources/flutter_best_practices.md](resources/flutter_best_practices.md) | The Flutter framework team's best practices. The PR should generally follow these. |
| [resources/report_template.md](resources/report_template.md) | The structure of the output report. |

## Workflow

### 1. Get the PR URL

Make sure you have the URL of the PR to review, e.g.
`https://github.com/flutter/flutter/pull/12345`. If you don't have it, ask the
user. Also ask (or infer from the conversation) whether the user wants the
review focused on any particular area; otherwise review everything.

### 2. Fetch the PR context

```shell
python3 scripts/fetch_pr_context.py <PR_URL>
```

This prints the output directory, `tmp/<org>.<repo>.<number>/`, which contains:

* `digest.md`: a condensed summary of everything below. **Read this in full
  first.**
* `pr.diff`: the full unified diff.
* `context.json`: the raw API data, for details the digest truncates (full
  comment bodies, bot comments, check run details, commit list, etc.).

Useful flags: `--history N` (commits of history per file, default 8),
`--max-files N`, `--max-refs N`. If the script fails because of a missing or
invalid token, tell the user rather than working around it.

### 3. Understand the problem before reading the code

Using `digest.md`, establish:

* What problem the PR claims to solve, and the linked issue(s). Read the issue
  discussion: reproduction steps, proposed solutions, and any maintainer
  opinions on the right fix. Note duplicates, reactions, and priority labels.
* Who the author is: Flutter org member, returning contributor, or first-time
  contributor (`author_association` in the digest; check their other PRs with
  `gh search prs --author=<login> --repo=<org>/<repo>` if unclear).
* What reviewers have said already, which threads are still open, and whether
  the author has addressed earlier feedback. Don't repeat feedback that's
  already been given unless it was not addressed.
* Whether there were earlier attempts at this fix (closed or reverted PRs in
  the linked issue, cross-references, or file history). If so, find out why
  they failed and whether this PR avoids the same problem.
* Any design docs linked from the PR or issues. Summarize the relevant parts.
  If you cannot access a doc, list it in the report as unread.

### 4. Read the code in context

Read the entire `pr.diff`. A diff alone is often not enough to judge
correctness, so read the surrounding code too:

* If the user has a local checkout of the repository, prefer it. Fetch the PR
  without disturbing their work, e.g.
  `git fetch upstream pull/<number>/head:pr-<number>` and read files with
  `git show pr-<number>:<path>`. Do not check out branches, stash, or modify the
  user's working tree without asking.
* Otherwise, read files at the PR's head SHA (listed in the digest) from
  `https://raw.githubusercontent.com/<head repo>/<head sha>/<path>`, or with
  `gh api`.

For each changed area, also look at callers, overrides, and similar existing
widgets/APIs, so that you can judge consistency with the rest of the framework.
Use the "Recent history of changed files" section of the digest to find PRs
that recently touched the same code; open the most relevant ones to understand
why the code is the way it is.

### 5. Run the best-practices heuristics

```shell
python3 scripts/check_best_practices.py tmp/<org>.<repo>.<number>/pr.diff
```

(Add `--json` for machine-readable output. It also accepts `-` to read a diff
from stdin, e.g. `git diff upstream/master...pr-<number> | python3
scripts/check_best_practices.py -`.)

The script is a set of regex heuristics. It produces false positives and misses
most real problems. For every finding, look at the code and decide whether it
is a real issue. Only include verified findings in the report, and never cite
the script as the reason for a finding; cite the best practice or style guide
section instead.

### 6. Review against the best practices and style guide

Read [resources/flutter_best_practices.md](resources/flutter_best_practices.md)
and check the PR against every section that is relevant to the change, not
just the ones the script flagged. Also apply the
[Flutter style guide](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md)
and [Tree Hygiene](https://github.com/flutter/flutter/blob/master/docs/contributing/Tree-hygiene.md)
(tests, breaking changes). Pay particular attention to:

* **API design**: generic composable widgets and `WidgetBuilder`s rather than
  type checks or specialized config; declarative over imperative (avoid new
  controllers when state can be a parameter); narrowly scoped APIs; class
  modifiers (`final`, `base`, `interface`) and data-class arguments to avoid
  future breaking changes; positional parameters to avoid repetition (`Text(x)`
  not `Text(text: x)`); `Raw*`/`*`/`Cupertino*` naming for shared widgets;
  mirroring native APIs before cross-platform abstractions; `maybeOf` over
  `of`; `InheritedModel` only with a clear performance benefit; consistent
  passed-through defaults referenced from a single constant.
* **Placement**: system UI in the widgets library where possible; widgets code
  must not import Material or Cupertino; features outside the Material spec
  need strong justification; soft release (default off, unexported,
  `@visibleForTesting`) or feature flags for unfinished features.
* **Platform behavior**: `defaultTargetPlatform` for behavior vs.
  `ThemeData.platform` for visuals; decide mouse/touch behavior by input type,
  not platform; match the latest OS version's behavior; docs describe behavior
  platform-independently where possible; prefer Flutter-drawn UI over platform
  views.
* **Implementation**: separate widgets instead of `_buildX()` helper methods;
  `SizedBox.shrink()` as the no-op widget; don't mutate `Paint` instances
  between draw calls; report recoverable errors via `FlutterError.reportError`;
  no unreachable assertions; assert widget invariants in the constructor, not
  in `initState`/`didUpdateWidget`; `Diagnosticable` instead of `toString`;
  sentinel values where omitted vs. explicitly passed matters. Don't demand
  `const` at the expense of clean code.
* **Breaking changes**: any change to public API signatures, defaults, or
  behavior that could break users or customer tests. If breaking, check that
  the PR follows the breaking change policy (migration guide, data-driven
  fixes, deprecation instead of removal where possible).
* **Documentation**: every new public member has dartdocs that explain why and
  when to use it, with "See also" links and samples where helpful. Check
  grammar and spelling in docs, comments, error messages, and the PR
  description. TODOs include a username and an issue link.

### 7. Review the tests

* Is there a test for every behavior change, and a regression test that fails
  without the fix? If not, does the PR qualify for a test exemption?
* Do the tests actually test the change, or would they pass without it? If you
  have a local checkout and the user agrees, you can verify this by running the
  test with and without the lib changes.
* Testing best practices: prefer `pump(duration)` to `pumpAndSettle`, using
  `TransitionDurationObserver` for page transitions; prefer headless checks
  over goldens and never capture goldens mid-animation; omit `variant` unless
  the logic is platform-specific, and only use `TargetPlatformVariant.all()`
  when behavior differs per platform; no `try`/`catch` + `expect(error,
  isNull)`; no `Key`s added to lib code just for tests; prefer generic matchers
  (`findsOne`); tests live in the library they test without cross-importing
  Material/Cupertino; use `tester.semantics.find` + `isSemantics` rather than
  `TestSemantics` trees.
* Missing edge cases: RTL, text scaling, disposal/lifecycle, rebuilding with
  new parameters (`didUpdateWidget`), web, accessibility/semantics, keyboard
  and mouse input.

### 8. Look for bugs and performance issues

Think through the change adversarially: null and empty inputs, disposal and
listener leaks, `setState` after dispose, `didUpdateWidget` not handling a
changed parameter, state lost on rebuild, focus and keyboard handling, RTL,
hit testing, layout constraint violations, and interaction with existing
features. For performance, look for work added to `build`, `layout`, or `paint`
hot paths, unnecessary rebuilds or `InheritedWidget` dependencies, and new
allocations per frame.

### 9. Check CI

Summarize the check runs from the digest. For failures, determine whether they
appear to be caused by the PR or are infrastructure/flaky/maintainer-owned
(e.g. Google testing). Don't speculate beyond what the data shows.

### 10. Write the report

Write the report to `output/<org>_<repo>_<number>_review.md` (e.g.
`output/flutter_flutter_12345_review.md`), following
[resources/report_template.md](resources/report_template.md). Requirements:

* Every finding links to the exact location in the code at the PR's head SHA,
  e.g. `https://github.com/<head repo>/blob/<head sha>/<path>#L10-L20`, and
  states its severity (**Blocking**, **Should fix**, **Nit**, or
  **Question**).
* Distinguish facts from your opinions and uncertainty. If you're not sure
  something is a bug, phrase it as a question and explain what would need to
  be true for it to be a problem.
* Be concise. Prefer a few well-supported findings over many speculative ones.
  Omit template sections that don't apply rather than padding them, except
  that each Findings subsection should say "None found." when empty.
* Include every relevant link in the Resources section: issues, related and
  previous PRs, design docs, API docs, and the best practice sections cited.

Finally, tell the user where the report is and give a 2-3 sentence summary of
the most important findings.
