import json

data = {}
try:
    with open('/Users/jmccandless/.gemini/tmp/flutter-skills/framework_pr_list_parsed.json') as f:
        data['Framework PR list'] = json.load(f)
except FileNotFoundError:
    pass

try:
    with open('/Users/jmccandless/.gemini/tmp/flutter-skills/framework_package_pr_list_parsed.json') as f:
        data['Framework-owned Package PR list'] = json.load(f)
except FileNotFoundError:
    pass

try:
    with open('/Users/jmccandless/.gemini/tmp/flutter-skills/incoming_issue_list_parsed.json') as f:
        data['Incoming issue list'] = json.load(f)
except FileNotFoundError:
    pass

with open('/Users/jmccandless/.gemini/tmp/flutter-skills/combined_triage.json', 'w') as f:
    json.dump(data, f, indent=2)
