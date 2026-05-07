import json
import datetime
import re
import sys
import os

def get_status_emoji(status):
    if "Waiting on Author" in status:
        return "🔴 " + status
    if "Draft" in status:
        return "⚪ " + status
    if status == "Waiting on Review":
        return "🟡 " + status
    if status == "Waiting for CI":
        return "⏳ " + status
    if "Blocked" in status:
        return "🔴 " + status
    if status == "Ready to Merge":
        return "🟢 " + status
    return status

def generate_summary_and_action_items(context, triage_status, is_pr):
    summary = (context.split('.')[0] + '.').split('\n')[0]

    action_items = "No immediate action items identified."
    if re.search(r'\b(fix|add|implement|investigate|discuss)\b', context, re.IGNORECASE):
        action_items = "Further investigation and discussion required."
    if re.search(r'\b(propose|proposal)\b', context, re.IGNORECASE):
        action_items = "Review proposal and discuss feasibility."
    if re.search(r'\b(example|documentation)\b', context, re.IGNORECASE):
        action_items = "Review documentation and examples."
    if re.search(r'\b(test|tests)\b', context, re.IGNORECASE):
        action_items = "Review tests and merge."

    # Refine based on triage_status if it is a PR
    if is_pr and triage_status != "N/A":
        if "Waiting on Author" in triage_status:
            if action_items == "Review tests and merge.":
                action_items = f"Waiting on author to address changes/conflicts (was: Review tests and merge)."
            else:
                action_items = f"Waiting on author ({triage_status})."
        elif triage_status == "Waiting for CI":
            if action_items == "Review tests and merge.":
                action_items = "Waiting for CI to complete, then review tests and merge."
            else:
                action_items = "Waiting for CI to complete."
        elif "Blocked" in triage_status:
            action_items = f"Blocked ({triage_status})."
        elif triage_status == "Ready to Merge":
            action_items = "Ready to merge! Review tests if needed."

    return summary, action_items

def create_markdown_section(list_name, data):
    markdown = f"## {list_name}\n\n"
    if 'items' in data:
        for item in data['items']:
            # Ensure 'context' key exists and is a string
            context = item.get('context', '')
            if not isinstance(context, str):
                context = str(context) # Convert to string if not already

            is_pr = item.get('is_pr', False)
            triage_status = item.get('triage_status', 'N/A')

            summary, action_items = generate_summary_and_action_items(context, triage_status, is_pr)
            
            date_opened = datetime.datetime.fromisoformat(item['date_opened'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            markdown += f"### [{item['title']}]({item['html_url']})\n"
            markdown += f"- **Author**: [{item['author']}]({item['author_url']})\n"
            markdown += f"- **Date Opened**: {date_opened}\n"
            markdown += f"- **Priority**: {item.get('priority', 'N/A')}\n" # Use .get for safety
            if is_pr:
                status_str = get_status_emoji(triage_status)
                markdown += f"- **Triage Status**: {status_str}\n"
            markdown += f"- **Summary**: {summary}\n"
            markdown += f"- **Action Items**: {action_items}\n\n"
    return markdown

def main():
    if len(sys.argv) != 3:
        print("Usage: python generate_report.py <input_combined_json_file> <output_markdown_file>", file=sys.stderr)
        sys.exit(1)

    input_combined_json_file = sys.argv[1]
    output_markdown_file = sys.argv[2]
    
    today = datetime.date.today().strftime("%Y-%m-%d")
    markdown = f"# Flutter Framework Triage - {today}\n\n"

    with open(input_combined_json_file, 'r') as f:
        data = json.load(f)
        for list_name, list_data in data.items():
            markdown += create_markdown_section(list_name, list_data)

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_markdown_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_markdown_file, 'w') as f:
        f.write(markdown)

if __name__ == "__main__":
    main()