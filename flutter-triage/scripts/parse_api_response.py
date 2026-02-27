import json
import os
import sys
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
}

def get_comments(comments_url):
    comments = []
    try:
        response = requests.get(comments_url, headers=HEADERS)
        response.raise_for_status()
        for comment in response.json():
            comments.append(comment.get('body', ''))
    except requests.exceptions.RequestException as e:
        print(f"Error fetching comments from {comments_url}: {e}", file=sys.stderr)
    return comments

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
        
        comments_url = item.get('comments_url')
        comments = get_comments(comments_url) if comments_url else []
        
        full_context = (item.get('body') or "") + "\n\n" + "\n\n".join(comments)

        entries.append({
            "title": item.get('title'),
            "html_url": item.get('html_url'),
            "author": item.get('user', {}).get('login'),
            "author_url": item.get('user', {}).get('html_url'),
            "date_opened": item.get('created_at'),
            "status": item.get('state'),
            "priority": priority,
            "context": full_context,
        })

    return entries, total_count

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python parse_api_response.py <input_json_file> <output_json_file>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    entries, total_count = parse_github_json(input_file)

    output_data = {
        "count": total_count,
        "items": entries
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Successfully processed {len(entries)} entries from {input_file} and wrote to {output_file}")