# Review: [<org>/<repo> #<number>](<PR URL>): <PR title>

- Author: [<login>](https://github.com/<login>) (<employer if known>, <first-time / returning contributor / Flutter org member>)
- Status: <open | draft | merged | closed>, last activity <date>
- Size: <N> files, +<additions>/-<deletions>
- Reviews so far: <e.g. "approved by X; changes requested by Y"; or "none">
- CI: <passing | failing (list relevant failures) | pending>
- Areas: <keywords, e.g. text input, Material, semantics, iOS>
- Recommendation: <Looks good with nits | Needs changes | Needs design discussion | Not ready for review>

## TL;DR

<2-5 sentences. What the PR does, whether the approach is sound, and the most
important things the reviewer should focus on.>

## Context

### The problem
<The bug or feature request, in your own words. Link the issue(s). Note how
long it has been open, how many users are affected (reactions, duplicates),
and any prior priority/triage labels.>

### The solution
<How the PR solves it. Describe the approach at the level of classes/methods,
not line by line. Mention alternatives that were considered in the issue,
design docs, or earlier PRs, and whether this PR picked the right one.>

### History
<Relevant previous changes to the modified code (with PR links), previous
attempts at fixing this issue, related reverts, and anything the reviewer
needs to know about why the code looks the way it does today.>

### Discussion so far
<Condensed summary of review comments and issue discussion. Who said what,
which threads are resolved, which are still open, and any disagreements.
Omit bot noise.>

## Findings

Order by severity. Each finding links to the exact line(s) in the PR's "Files
changed" view or to the file at the PR's head SHA, quotes or paraphrases the
code, explains the problem, and suggests a fix. Mark each finding as one of:
**Blocking**, **Should fix**, **Nit**, or **Question**.

### Correctness and bugs
1. **<Severity>** [`path/to/file.dart:L123`](<link>): <issue and suggested fix>

### API design and breaking changes
<New/changed public APIs, naming, class modifiers, declarative vs imperative,
whether the change is breaking (and whether it follows the breaking change
process), and consistency with similar existing APIs.>

### Flutter best practices and style
<Deviations from resources/flutter_best_practices.md and the Flutter style
guide. Name the relevant section for each.>

### Tests
<Are the changes tested? Is there a regression test for the issue? Do tests
follow the testing best practices (no pumpAndSettle where avoidable, generic
matchers, tester.semantics.find, correct TargetPlatformVariant, tests in the
right library)? Missing cases?>

### Performance
<Unnecessary rebuilds, allocations in hot paths (build/layout/paint), O(n^2)
work, missing const where it matters, etc. Write "None found." if none.>

### Documentation and grammar
<Missing or inaccurate dartdocs, typos, grammar, missing sample code or
"See also" sections, PR description problems.>

## Suggested review comments

<Optional. Ready-to-paste comments for the most important findings, each with
the file and line it should be attached to. Phrase them politely and
constructively, as questions where the right answer is uncertain.>

## Resources

- <Issue links, related PRs, design docs, API docs, relevant source files,
  style guide / best practice sections referenced above.>
