import re
import os
import sys

def parse_readme(file_path):
    content = ''
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.", file=sys.stderr)
        return {}

    framework_team_section_start_re = r'### Framework team \(`team-framework`\)'
    framework_team_section_end_re = r'### \w+ team' # Find the next team section

    p0_list_re = r'- \[P0 list]\((.*?)\)'
    framework_pr_list_re = r'- \[Framework PR list]\((.*?)\)'
    framework_owned_package_pr_list_re = r'- \[Framework-owned Package PR list]\((.*?)\)'
    incoming_issue_list_re = r'- \[Incoming issue list]\((.*?)\)'

    start_match = re.search(framework_team_section_start_re, content)

    urls = {}

    if start_match:
        start_index = start_match.start()
        end_match = re.search(framework_team_section_end_re, content[start_index + 1:])
        if end_match:
            end_index = start_index + 1 + end_match.start()
            framework_team_section = content[start_index:end_index]
        else:
            framework_team_section = content[start_index:]

        p0_match = re.search(p0_list_re, framework_team_section)
        if p0_match:
            urls['P0 list'] = p0_match.group(1)

        framework_pr_match = re.search(framework_pr_list_re, framework_team_section)
        if framework_pr_match:
            urls['Framework PR list'] = framework_pr_match.group(1)

        framework_owned_package_pr_match = re.search(framework_owned_package_pr_list_re, framework_team_section)
        if framework_owned_package_pr_match:
            urls['Framework-owned Package PR list'] = framework_owned_package_pr_match.group(1)

        incoming_issue_match = re.search(incoming_issue_list_re, framework_team_section)
        if incoming_issue_match:
            urls['Incoming issue list'] = incoming_issue_match.group(1)
    
    return urls

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_triage_readme.py <readme_file>", file=sys.stderr)
        sys.exit(1)

    readme_file = sys.argv[1]
    urls = parse_readme(readme_file)

    for name, url in urls.items():
        print(f'{name} URL: {url}')