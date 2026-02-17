---
name: flutter-framework-triage
description:
  Use this skill to gather relevant PRs and issues for the Flutter framework
team.
---

# Flutter Framework Triage

This skill guides the agent in locating relevant PRs and issues for the Flutter
framework team.

## Workflow

### 1. Fetch the traige README

Load the triage README from the main Flutter repository, located at:
https://github.com/flutter/flutter/blob/master/docs/triage/README.md#framework-team-team-framework.

Under the "Framework team" label (#framework-team-team-framework), there should
be four bullet points:

 * P0 list
 * Framework PR list
 * Framework-owned Package PR list
 * Incoming issue list


If these are not found, alert the user.

### 2. Generate and output lists of PRs and issues

For each bullet point, load the URL linked to it and output a list of all issues
or pull requests given at the URL. This may require navigating to subsequent
pages in the GitHub UI. Place this output into a markdown file with the name
"output.md" in the current directory.

Each item in the list should be formatted like this:

```
<title, linked to the issue/PR>
<a brief summary of the contents of the issue/PR>
```

### 3. Add headings

For each bullet point's list of issues/PRs, include a heading with the name of
the bullet point linked to the URL found in the GitHub README. After this linked
name, include the total number of issues/PRs found for that section in
parenthesis.
