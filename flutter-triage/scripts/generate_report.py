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
        next_step_cat = None
        cicd_label = "Unknown"
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                content = f.read()
            
            # Extract triage status
            status_match = re.search(r'- \*\*Triage Status\*\*: (.*)', content)
            if status_match:
                actual_triage = status_match.group(1)

            # Extract Next Step Category
            cat_match = re.search(r'- \*\*Next Step Category\*\*: (.*)', content)
            if cat_match:
                next_step_cat = cat_match.group(1).strip()

            # Extract CICD Label status
            cicd_match = re.search(r'- \*\*CICD Label\*\*: (.*)', content)
            if cicd_match:
                cicd_label = cicd_match.group(1).strip()
            
            # Extract summary (from ## Description)
            desc_match = re.search(r'## Description\n\n(.*?)(?=\n##|$)', content, re.DOTALL)
            if desc_match:
                summary = desc_match.group(1).strip()
                summary = re.sub(r'<!--.*?-->', '', summary, flags=re.DOTALL).strip()
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                # inline newlines
                summary = summary.replace('\n', ' ')
            
            # Extract action items (from ## Next Steps)
            action_match = re.search(r'## Next Steps\n\n(.*)', content, re.DOTALL)
            if action_match:
                action_items = action_match.group(1).strip()
                action_items = action_items.replace('\n', ' ')
            
            return summary, action_items, actual_triage, next_step_cat, cicd_label

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

    return summary, action_items, get_status_emoji(triage_status), None, "N/A"

def determine_category(is_pr, triage_status, action_items, next_step_cat=None):
    """Maps PRs to one of the 6 categories from flutter-pr-triage."""
    if not is_pr:
        return "Issues"
    if next_step_cat in [
        "Wait for the author",
        "Needs reviewer assignment",
        "Needs primary review",
        "Needs secondary review",
        "Needs autosubmit",
        "Waiting to land"
    ]:
        return next_step_cat
    
    status_lower = triage_status.lower()
    action_lower = action_items.lower()
    if "waiting on author" in status_lower or "blocked" in status_lower or "conflict" in status_lower:
        return "Wait for the author"
    if "reviewer assignment" in status_lower or "reviewer assignment" in action_lower:
        return "Needs reviewer assignment"
    if "secondary review" in action_lower or "secondary review" in status_lower:
        return "Needs secondary review"
    if "waiting on review" in status_lower or "primary review" in action_lower:
        return "Needs primary review"
    if "autosubmit" in action_lower or "ready to merge" in status_lower:
        return "Needs autosubmit"
    if "waiting to land" in action_lower or "land" in action_lower:
        return "Waiting to land"
        
    # Default fallback for unknown PR states to adhere to categories:
    return "Needs primary review"

def main():
    if len(sys.argv) != 4:
        print("Usage: python generate_report.py <input_combined_json_file> <output_markdown_file> <team_name>", file=sys.stderr)
        sys.exit(1)

    input_combined_json_file = sys.argv[1]
    output_markdown_file = sys.argv[2]
    team_name = sys.argv[3]
    
    today = datetime.date.today().strftime("%Y-%m-%d")
    markdown = f"# Flutter {team_name} Triage - {today}\n\n"

    categories = [
        "Wait for the author",
        "Needs reviewer assignment",
        "Needs primary review",
        "Needs secondary review",
        "Needs autosubmit",
        "Waiting to land",
        "Issues"
    ]
    
    categorized_items = {cat: [] for cat in categories}
    categorized_pr_numbers = {cat: [] for cat in categories}
    seen_urls = set()

    with open(input_combined_json_file, 'r') as f:
        data = json.load(f)
        for list_name, list_data in data.items():
            if 'items' in list_data:
                for item in list_data['items']:
                    html_url = item.get('html_url', '')
                    if html_url in seen_urls:
                        continue
                    seen_urls.add(html_url)

                    context = item.get('context', '')
                    if not isinstance(context, str):
                        context = str(context)

                    is_pr = item.get('is_pr', False)
                    triage_status = item.get('triage_status', 'N/A')
                    
                    pr_number = None
                    if is_pr and html_url:
                        pr_number = html_url.split('/')[-1]

                    summary, action_items, actual_triage, next_step_cat, cicd_label = generate_summary_and_action_items(context, triage_status, is_pr, pr_number)
                    
                    cat = determine_category(is_pr, actual_triage, action_items, next_step_cat)
                    
                    needs_cicd_prominent = is_pr and ("NEEDS" in cicd_label.upper())
                    cicd_badge = " 🚨 **[NEEDS CICD LABEL]**" if needs_cicd_prominent else ""

                    item_md = ""
                    date_opened = datetime.datetime.fromisoformat(item['date_opened'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    item_md += f"### [{item['title']}]({item['html_url']}){cicd_badge}\n"
                    item_md += f"- **Author**: [{item['author']}]({item['author_url']})\n"
                    item_md += f"- **Date Opened**: {date_opened}\n"
                    item_md += f"- **Priority**: {item.get('priority', 'N/A')}\n"
                    if is_pr:
                        item_md += f"- **Triage Status**: {actual_triage}\n"
                        item_md += f"- **CICD Label**: {cicd_label}\n"
                        workspace = "/usr/local/google/home/jmccandless/Projects/flutter-skills"
                        item_md += f"- **Full PR Report**: [flutter_flutter_{pr_number}.md](file://{workspace}/flutter-pr-triage/output/flutter_flutter_{pr_number}.md)\n"
                    item_md += f"- **Summary**: {summary}\n"
                    item_md += f"- **Action Items**: {action_items}\n\n"
                    
                    target_cat = cat if cat in categorized_items else "Issues"
                    categorized_items[target_cat].append(item_md)
                    if is_pr and pr_number:
                        categorized_pr_numbers[target_cat].append(pr_number)

    for cat in categories:
        if categorized_items[cat]:
            count = len(categorized_items[cat])
            pr_nums = categorized_pr_numbers[cat]
            if pr_nums:
                gh_query_url = f"https://github.com/flutter/flutter/pulls?q={'+'.join(pr_nums)}"
                markdown += f"## [{cat} ({count})]({gh_query_url})\n\n"
            else:
                markdown += f"## {cat} ({count})\n\n"
            for md in categorized_items[cat]:
                markdown += md

    output_dir = os.path.dirname(output_markdown_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_markdown_file, 'w') as f:
        f.write(markdown)

if __name__ == "__main__":
    main()
