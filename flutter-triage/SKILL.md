---
name: flutter-triage
description: Use this skill to gather relevant PRs and issues for a specified team in Flutter.
---

# Flutter Triage

This skill guides the agent in locating relevant PRs and issues for a specified
team in Flutter and outputting them in a nicely formatted markdown file.

## Workflow

### 1. Ask for Team Name
Start by asking the user which team they would like to triage for (e.g., "Framework", "Engine", "Design Languages").

### 2. Fetch and Parse the Triage README
Once the user provides a team name:
1.  Load the triage README from the main Flutter repository, located at:
    `https://raw.githubusercontent.com/flutter/flutter/master/docs/triage/README.md`.
2.  Use the `scripts/parse_triage_readme.py` script with the provided team name to find the team's section and extract the URLs for their triage lists.
3.  If no lists are found, inform the user. Otherwise, proceed to the next step.

### 3. Generate and output lists of PRs and issues via GitHub API

For each list name and URL extracted in the previous step:
1.  **Convert to API URL:** Transform the web URL into a GitHub API URL.
    - **`https://github.com/`** becomes **`https://api.github.com/repos/`**.
    - The query parameters (`?q=...`) from the web URL should be used with the `search/issues` endpoint of the GitHub API.
    - **Example:** `https://github.com/flutter/flutter/issues?q=...` becomes `https://api.github.com/search/issues?q=repo:flutter/flutter...`
2.  **Fetch Data:** Use `curl` with the `Accept: application/vnd.github.v3+json` header to fetch the JSON data. Handle pagination by following the `Link` header with `rel="next"` until all pages are fetched.
3.  **Combine and Parse:**
    - Use the `scripts/combine_json.py` script to combine the `items` from all pages into a single JSON file.
    - Use the `scripts/parse_api_response.py` script to parse the combined JSON file. This script will also format the output and append it to a specified output file. The script usage is `python parse_api_response.py <input_json_file> <output_section_title> <output_file_path>`. The output file path should be `flutter-triage/output/<team_name>.md`, where `<team_name>` is the lowercase version of the team name provided by the user.
4.  **Section Heading:** The `parse_api_response.py` script takes the section title as an argument. Use the name of the list from the README as the title for each section.

**Generating Urgency and Summary:**

- **Urgency:** Assign "High" if the issue/PR has a "P0" label. Otherwise, assign "Medium".
- **Summary:** Use the title of the issue/PR as the summary.

The final output should be a single markdown file in the `flutter-triage/output/` directory, named after the team (e.g., `framework.md`). This file will contain a section for each triage list found in the README.
