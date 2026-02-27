import json
import os
import sys

def parse_github_json(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing {file_path}: {e}", file=sys.stderr)
        return [], 0

    entries = []
    total_count = data.get('total_count', 0)

    for item in data.get('items', []):
        priority = "No Priority"
        for label in item.get('labels', []):
            if label.get('name', '').startswith('P'):
                priority = label['name']
                break
        
        entries.append({
            "title": item.get('title'),
            "html_url": item.get('html_url'),
            "author": item.get('user', {}).get('login'),
            "author_url": item.get('user', {}).get('html_url'),
            "date_opened": item.get('created_at'),
            "status": item.get('state'),
            "priority": priority,
            "summary": item.get('title'),
        })

    return entries, total_count

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python parse_api_response.py <input_json_file> <output_section_title> <output_file_path>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    section_title = sys.argv[2]
    output_file = sys.argv[3]
    
    entries, total_count = parse_github_json(input_file)

    output_content = ""
    output_content += f"## {section_title} ({total_count})\n"
    for entry in entries:
        output_content += f" * [{entry['title']}]({entry['html_url']})\n"
        output_content += f"   * [{entry['author']}]({entry['author_url']})\n"
        output_content += f"   * {entry['date_opened']}\n"
        output_content += f"   * Status: {entry['status']}\n"
        output_content += f"   * Priority: {entry['priority']}\n"
        output_content += f"   * {entry['summary']}\n"
    output_content += f"\n"

    # Append to the specified output file
    with open(output_file, 'a') as f:
        f.write(output_content)

    print(f"Successfully processed {len(entries)} entries from {input_file} and appended to {output_file}")