import json
import os
import sys

def filter_and_parse_prs(json_data, required_labels):
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return [], 0

    filtered_prs = []
    
    for item in data.get('items', []):
        item_labels = {label['name'] for label in item.get('labels', [])}
        if not required_labels.isdisjoint(item_labels): # Check for any intersection
            urgency = "High" if 'P0' in item_labels else "Medium"
            
            filtered_prs.append({
                "title": item.get('title'),
                "html_url": item.get('html_url'),
                "author": item.get('user', {}).get('login'),
                "author_url": item.get('user', {}).get('html_url'),
                "date_opened": item.get('created_at'),
                "status": item.get('state'),
                "urgency": urgency,
                "summary": item.get('title'),
            })

    return filtered_prs, len(filtered_prs)

if __name__ == "__main__":
    json_data = sys.stdin.read()
    
    required_labels = {
        "p: two_dimensional_scrollables",
        "p: go_router",
        "p: go_router_builder",
        "p: google_fonts",
        "p: animation",
        "p: animations",
        "p: cupertino_icons",
        "p: flutter_lints",
    }
    
    prs, total_count = filter_and_parse_prs(json_data, required_labels)

    output_content = ""
    output_content += f"## Framework-owned Package PR list ({total_count})\n"
    for pr in prs:
        output_content += f" * [{pr['title']}]({pr['html_url']})\n"
        output_content += f"   * [{pr['author']}]({pr['author_url']})\n"
        output_content += f"   * {pr['date_opened']}\n"
        output_content += f"   * Status: {pr['status']}\n"
        output_content += f"   * Urgency: {pr['urgency']}\n"
        output_content += f"   * {pr['summary']}\n"
    output_content += f"\n"

    with open('output.md', 'a') as f:
        f.write(output_content)

    print(f"Successfully filtered and processed {len(prs)} PRs and appended to output.md")