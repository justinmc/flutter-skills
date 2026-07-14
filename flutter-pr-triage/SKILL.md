---
name: flutter-pr-triage
description: Use this skill gather triage information about a single PR.
---

# Flutter PR Triage

This skill guides the agent in gathering information about a single GitHub pull
request that is useful to a human during triage and code review, and it outputs
that information in a nicely formatted markdown file.

## Prerequisites
Before using this skill, ensure the following:
1.  The `requests` python library is installed (`pip install requests`).
2.  The `GITHUB_TOKEN` environment variable is set with a valid GitHub Personal Access Token with `repo` scope.

## Workflow

### 1. Get the PR URL
Start by making sure that you have the URL for the PR that the user wants to
gather information about. If you don't have the URL, ask the user for it.

### 2. Fetch information about the PR
Use the GitHub API to fetch the PR. Include all comments, linked issues and PRs,
files changed, and other metadata about the PR. A GitHub access token is
available via the $GITHUB_TOKEN environment variable.

Place this information in a json file in the tmp/ directory with a filename of
the format "<org>.<repo>.<PR number>.json". For example, the PR
https://github.com/flutter/packages/pull/11888 would have the filename
flutter.packages.11888.json.

### 3. Assess next steps
Decide what the next steps are for the PR based on the information gathered in
the json file. The options are:

  1. Wait for the author. This indicates that no action is required from the
     maintainers. The author needs to complete some work before the PR can move
     forward. For example, the author is still working on the PR, or they are
     waiting for CI to finish running, or they need to fix some broken CI
     failures (other than failures that are the responsibility of maintainers,
     like Google Tests).
  2. Needs primary review. This indicates that the PR is ready for review but
     has not yet received an approval. A Flutter maintainer needs to make a
     primary review of the PR and give approval, or needs to follow up with another
     round of review if the PR has already received a review but not an approval.
  3. Needs secondary review. This indicates that the PR has already received
     primary reviewer approval and is awaiting a secondary approval from another
     reviewer. This does not apply to members of flutter-hackers, who only
     require one review approval.

### 3. Output

Output a markdown file that contains the PR review. The filename should be
`<org>_<repo>_<PR number>.md`. For example, the PR at URL
https://github.com/flutter/flutter/pull/182994 should produce the output file
flutter_flutter_182994.md.

The output file should follow this format:

# <org>/<repo> #<PR number>: <A brief title that explains the PR>
  * <Last activity - The amount of time that has passed since the last comment or
    commit on the PR.>
  * <Author>
  * <Related issue(s)>
  * Next steps: <next steps from step #3 of this skill>

<A summary of the problem, activity up until this point, and the solution given by the user>

<A longer summary
