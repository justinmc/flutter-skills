import re
import os
import sys

def parse_readme_for_team(file_path, team_name):
    content = ''
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.", file=sys.stderr)
        return {}

    # Construct a regex to find the section for the given team
    team_section_start_re = re.compile(f'### {team_name} team \(`team-{team_name.lower().replace(" ", "-")}`\)', re.IGNORECASE)
    
    start_match = team_section_start_re.search(content)

    if not start_match:
        # Fallback for simpler team headings
        team_section_start_re = re.compile(f'### {team_name} team', re.IGNORECASE)
        start_match = team_section_start_re.search(content)

    if not start_match:
        print(f"Error: Could not find section for '{team_name} team'.", file=sys.stderr)
        return {}

    start_index = start_match.end()
    
    # Find the next section to define the end of the current team's section
    next_section_match = re.search(r'### \w+ team', content[start_index:])
    if next_section_match:
        end_index = start_index + next_section_match.start()
        team_section = content[start_index:end_index]
    else:
        team_section = content[start_index:]

    # Regex to find all markdown list items (bullet points with links)
    list_item_re = re.compile(r'-\s+\[(.*?)\]\((.*?)\)')
    
    urls = {}
    for match in list_item_re.finditer(team_section):
        list_name = match.group(1).strip()
        url = match.group(2).strip()
        urls[list_name] = url
    
    return urls

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python parse_triage_readme.py <readme_file> \"<team_name>\"", file=sys.stderr)
        sys.exit(1)

    readme_file = sys.argv[1]
    team_name = sys.argv[2]
    
    urls = parse_readme_for_team(readme_file, team_name)

    if not urls:
        print(f"No triage lists found for '{team_name} team'.")
    else:
        for name, url in urls.items():
            print(f"{name}:{url}")
