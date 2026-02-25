---
name: flutter-framework-triage
description: Use this skill to gather relevant PRs and issues for the Flutter framework team.
---

# Flutter Framework Triage

This skill guides the agent in locating relevant PRs and issues for the Flutter
framework team and outputting them in a nicely formatted markdown file.

## Workflow

### 1. Fetch the triage README

Load the triage README from the main Flutter repository, located at:
https://raw.githubusercontent.com/flutter/flutter/master/docs/triage/README.md.

Under the heading "### Framework team (`team-framework`)", there should be four bullet points:

 * P0 list
 * Framework PR list
 * Framework-owned Package PR list
 * Incoming issue list


If these are not found, alert the user.

If they are found, tell the user the URL is linked for each one, which you will
use in the next step to load the issues and PRs.

### 2. Generate and output lists of PRs and issues via GitHub API

For each bullet point, **use the GitHub API** to fetch the list of issues or pull requests. Do not use `web_fetch` on the HTML URLs directly as parsing HTML is unreliable.

**Converting Web URLs to API URLs:**

To use the API, you need to convert the web URLs from the README into API URLs. Here's how:
- **`https://github.com/`** becomes **`https://api.github.com/repos/`**.
- The query parameters (`?q=...`) from the web URL should be used with the `search/issues` endpoint of the GitHub API.

**Example Conversion:**
- **Web URL:** `https://github.com/flutter/flutter/issues?q=is%3Aissue%20is%3Aopen%20label%3Ateam-framework`
- **API URL:** `https://api.github.com/search/issues?q=repo%3Aflutter%2Fflutter%20is%3Aissue%20is%3Aopen%20label%3Ateam-framework`
  - Note the addition of `repo:flutter/flutter` to the query.

**Fetching and Parsing JSON:**

Use `curl` with the appropriate `Accept: application/vnd.github.v3+json` header to fetch the JSON data from the API URL. The response will be a JSON object containing a list of items.

Parse this JSON to extract the required information for each issue/PR: `title`, `html_url`, `user.login` (author), `created_at` (date opened), and `state` (status).

**Generating Urgency and Summary:**

- **Urgency:** Assign "High" if the issue/PR has a "P0" label. Otherwise, assign "Medium".
- **Summary:** Use the title of the issue/PR as the summary.

Place this output into a markdown file with the name `output.md` in the current directory.

Each item in the list should be formatted like this:

```
 * <title, linked to the issue/PR>
   * <author, linked to the author's GitHub profile>
   * <date opened>
   * Status: <open, closed, or draft>
   * Urgency: <your assessment based on the rules above>
   * <The issue/PR title as summary>
```

### 3. Add headings

For each bullet point's list of issues/PRs, include a heading with the name of
the bullet point linked to the URL found in the GitHub README. After this linked
name, include the total number of issues/PRs found for that section in
parentheses.
