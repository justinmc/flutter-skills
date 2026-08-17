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

def generate_summary_and_action_items(context, triage_status, is_pr, pr_number=None):
    if is_pr and pr_number:
        # Load the flutter-pr-triage output file
        report_path = f"../flutter-pr-triage/output/flutter_flutter_{pr_number}.md"
        summary = "No summary available."
        action_items = "No action items available."
        actual_triage = triage_status
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                content = f.read()
            
            # Extract triage status
            status_match = re.search(r'- \*\*Triage Status\*\*: (.*)', content)
            if status_match:
                actual_triage = status_match.group(1)
            
            # Extract summary (from ## Description)
            desc_match = re.search(r'## Description\n\n(.*?)(?=\n##|$)', content, re.DOTALL)
            if desc_match:
                summary = desc_match.group(1).strip()
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                # inline newlines
                summary = summary.replace('\n', ' ')
            
            # Extract action items (from ## Next Steps)
            action_match = re.search(r'## Next Steps\n\n(.*)', content, re.DOTALL)
            if action_match:
                action_items = action_match.group(1).strip()
                action_items = action_items.replace('\n', ' ')
            
            return summary, action_items, actual_triage

    # Stripping for basic summary
    clean_context = re.sub(r'<!--.*?-->', '', context, flags=re.DOTALL).strip()
    summary = (clean_context.split('.')[0] + '.').split('\n')[0]

    action_items = "No immediate action items identified."
    if re.search(r'\b(fix|add|implement|investigate|discuss)\b', clean_context, re.IGNORECASE):
        action_items = "Further investigation and discussion required."
    if re.search(r'\b(propose|proposal)\b', clean_context, re.IGNORECASE):
        action_items = "Review proposal and discuss feasibility."
    if re.search(r'\b(example|documentation)\b', clean_context, re.IGNORECASE):
        action_items = "Review documentation and examples."
    if re.search(r'\b(test|tests)\b', clean_context, re.IGNORECASE):
        action_items = "Review tests and merge."

    # Refine based on triage_status if it is a PR without the file
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

    return summary, action_items, get_status_emoji(triage_status)

def create_markdown_section(list_name, data):
    markdown = f"## {list_name}\n\n"
    if 'items' in data:
        for item in data['items']:
            context = item.get('context', '')
            if not isinstance(context, str):
                context = str(context)

            is_pr = item.get('is_pr', False)
            triage_status = item.get('triage_status', 'N/A')
            html_url = item.get('html_url', '')
            
            pr_number = None
            if is_pr and html_url:
                pr_number = html_url.split('/')[-1]

            summary, action_items, actual_triage = generate_summary_and_action_items(context, triage_status, is_pr, pr_number)
            
            date_opened = datetime.datetime.fromisoformat(item['date_opened'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            markdown += f"### [{item['title']}]({item['html_url']})\n"
            markdown += f"- **Author**: [{item['author']}]({item['author_url']})\n"
            markdown += f"- **Date Opened**: {date_opened}\n"
            markdown += f"- **Priority**: {item.get('priority', 'N/A')}\n"
            if is_pr:
                markdown += f"- **Triage Status**: {actual_triage}\n"
                workspace = "/usr/local/google/home/jmccandless/Projects/flutter-skills"
                markdown += f"- **Full PR Report**: [flutter_flutter_{pr_number}.md](file://{workspace}/flutter-pr-triage/output/flutter_flutter_{pr_number}.md)\n"
            markdown += f"- **Summary**: {summary}\n"
            markdown += f"- **Action Items**: {action_items}\n\n"
    return markdown

def main():
    if len(sys.argv) != 4:
        print("Usage: python generate_report.py <input_combined_json_file> <output_markdown_file> <team_name>", file=sys.stderr)
        sys.exit(1)

    input_combined_json_file = sys.argv[1]
    output_markdown_file = sys.argv[2]
    team_name = sys.argv[3]
    
    today = datetime.date.today().strftime("%Y%m%d")
    markdown = f"# Flutter {team_name} Triage - {today}\n\n"

    with open(input_combined_json_file, 'r') as f:
        data = json.load(f)
        # Order keys so issues are first, PRs are last, etc.
        for list_name, list_data in data.items():
            markdown += create_markdown_section(list_name, list_data)

    output_dir = os.path.dirname(output_markdown_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_markdown_file, 'w') as f:
        f.write(markdown)

if __name__ == "__main__":
    main()
