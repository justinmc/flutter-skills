import json
import datetime
import re

def generate_summary_and_action_items(context):
    summary = (context.split('.')[0] + '.').split('\\n')[0]

    action_items = "No immediate action items identified."
    if re.search(r'\b(fix|add|implement|investigate|discuss)\b', context, re.IGNORECASE):
        action_items = "Further investigation and discussion required."
    if re.search(r'\b(propose|proposal)\b', context, re.IGNORECASE):
        action_items = "Review proposal and discuss feasibility."
    if re.search(r'\b(example|documentation)\b', context, re.IGNORECASE):
        action_items = "Review documentation and examples."
    if re.search(r'\b(test|tests)\b', context, re.IGNORECASE):
        action_items = "Review tests and merge."


    return summary, action_items

def create_markdown_section(list_name, data):
    markdown = f"## {list_name}\\n\\n"
    if 'items' in data:
        for item in data['items']:
            summary, action_items = generate_summary_and_action_items(item['context'])
            date_opened = datetime.datetime.fromisoformat(item['date_opened'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            markdown += f"### [{item['title']}]({item['html_url']})\\n"
            markdown += f"- **Author**: [{item['author']}]({item['author_url']})\\n"
            markdown += f"- **Date Opened**: {date_opened}\\n"
            markdown += f"- **Priority**: {item['priority']}\\n"
            markdown += f"- **Summary**: {summary}\\n"
            markdown += f"- **Action Items**: {action_items}\\n\\n"
    return markdown

def main():
    today = datetime.date.today().strftime("%Y%m%d")
    output_filename = f"flutter-triage/output/framework-{today}.md"
    
    markdown = f"# Flutter Framework Triage - {datetime.date.today().strftime('%Y-%m-%d')}\\n\\n"

    with open('/Users/jmccandless/.gemini/tmp/flutter-skills/combined_triage.json') as f:
        data = json.load(f)
        for list_name, list_data in data.items():
            markdown += create_markdown_section(list_name, list_data)

    with open(output_filename, 'w') as f:
        f.write(markdown)

if __name__ == "__main__":
    main()
