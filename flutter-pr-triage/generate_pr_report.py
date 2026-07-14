import json
import datetime
import os
import sys
import re

def calculate_last_activity(data):
    timestamps = []
    
    # PR updated_at
    if 'updated_at' in data['pr']:
        timestamps.append(data['pr']['updated_at'])
    if 'created_at' in data['pr']:
        timestamps.append(data['pr']['created_at'])
        
    # Comments
    for c in data['comments']:
        if 'updated_at' in c:
            timestamps.append(c['updated_at'])
        elif 'created_at' in c:
            timestamps.append(c['created_at'])
            
    # Review comments
    for c in data['review_comments']:
        if 'updated_at' in c:
            timestamps.append(c['updated_at'])
        elif 'created_at' in c:
            timestamps.append(c['created_at'])
            
    # Reviews
    for r in data['reviews']:
        if 'submitted_at' in r:
            timestamps.append(r['submitted_at'])
            
    if not timestamps:
        return "Unknown"
        
    # Parse timestamps and find max
    parsed_times = []
    for ts in timestamps:
        try:
            # GitHub timestamps are usually ISO 8601 in UTC: YYYY-MM-DDTHH:MM:SSZ
            parsed_times.append(datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')))
        except ValueError:
            pass
            
    if not parsed_times:
        return "Unknown"
        
    last_act = max(parsed_times)
    return last_act

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

def determine_pr_status(pr_data, reviews):
    if pr_data.get('draft'):
        return "Draft (Waiting on Author)"
        
    if pr_data.get('mergeable_state') == 'dirty':
        return "Waiting on Author (Merge Conflicts)"
        
    # Check reviews
    latest_reviews = {}
    for r in reviews:
        user = r.get('user', {}).get('login')
        state = r.get('state')
        submitted_at = r.get('submitted_at')
        if state == 'COMMENTED':
            continue
        if user not in latest_reviews or submitted_at > latest_reviews[user]['submitted_at']:
            latest_reviews[user] = {'state': state, 'submitted_at': submitted_at}
            
    if any(info['state'] == 'CHANGES_REQUESTED' for info in latest_reviews.values()):
        return "Waiting on Author (Changes Requested)"
        
    # Check if waiting on review
    if pr_data.get('requested_reviewers'):
        return "Waiting on Review"
        
    if pr_data.get('mergeable_state') in ['blocked', 'unstable']:
        approvals = [user for user, info in latest_reviews.items() if info['state'] == 'APPROVED']
        if not approvals:
            return "Waiting on Review (No approvals yet)"
        else:
            return "Blocked (CI or other checks)"
            
    if pr_data.get('mergeable_state') == 'clean':
        return "Ready to Merge"
        
    return f"Unknown (mergeable_state: {pr_data.get('mergeable_state')})"

def generate_report(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
        
    pr = data['pr']
    comments = data['comments']
    reviews = data['reviews']
    files = data['files']
    
    title = pr['title']
    url = pr['html_url']
    author = pr['user']['login']
    author_url = pr['user']['html_url']
    state = pr['state']
    created_at = datetime.datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
    
    last_act = calculate_last_activity(data)
    if isinstance(last_act, datetime.datetime):
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - last_act
        last_activity_str = f"{last_act.strftime('%Y-%m-%d %H:%M:%S')} UTC ({diff.days} days, {diff.seconds // 3600} hours ago)"
    else:
        last_activity_str = "Unknown"
        
    triage_status = determine_pr_status(pr, reviews)
    
    markdown = f"# PR Triage Report: {title} (#{pr['number']})\n\n"
    markdown += f"- **URL**: {url}\n"
    markdown += f"- **Author**: [{author}]({author_url})\n"
    markdown += f"- **State**: {state.upper()}\n"
    markdown += f"- **Created At**: {created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    markdown += f"- **Last Activity**: {last_activity_str}\n"
    markdown += f"- **Triage Status**: {get_status_emoji(triage_status)}\n\n"
    
    markdown += "## Description\n\n"
    body = pr.get('body') or "No description provided."
    if len(body) > 1000:
        body = body[:1000] + "\n\n... (truncated)"
    markdown += f"{body}\n\n"
    
    markdown += "## Files Changed\n\n"
    if not files:
        markdown += "No files listed (or failed to fetch).\n\n"
    else:
        markdown += f"Total files changed: {len(files)}\n\n"
        for f_info in files[:10]:
            markdown += f"- `{f_info['filename']}` (+{f_info['additions']}/-{f_info['deletions']})\n"
        if len(files) > 10:
            markdown += f"- ... and {len(files) - 10} more files.\n"
        markdown += "\n"
        
    markdown += "## Reviews & Comments\n\n"
    requested_reviewers = [r['login'] for r in pr.get('requested_reviewers', [])]
    if requested_reviewers:
        markdown += f"**Requested Reviewers**: {', '.join(requested_reviewers)}\n\n"
        
    latest_reviews = {}
    for r in reviews:
        user = r.get('user', {}).get('login')
        state = r.get('state')
        submitted_at = r.get('submitted_at')
        if state != 'COMMENTED':
            if user not in latest_reviews or submitted_at > latest_reviews[user]['submitted_at']:
                latest_reviews[user] = {'state': state, 'submitted_at': submitted_at}
                
    if latest_reviews:
        markdown += "**Reviewer Decisions**:\n"
        for user, info in latest_reviews.items():
            markdown += f"- {user}: {info['state']}\n"
        markdown += "\n"
    else:
        markdown += "No reviews submitted yet.\n\n"
        
    if comments:
        markdown += "**Recent Comments**:\n"
        for c in comments[-3:]:
            c_author = c['user']['login']
            c_body = c['body']
            if len(c_body) > 200:
                c_body = c_body[:200] + "..."
            markdown += f"- **{c_author}**: {c_body}\n"
        markdown += "\n"
    else:
        markdown += "No comments.\n\n"
        
    markdown += "## Next Steps\n\n"
    if "Waiting on Author" in triage_status:
        markdown += "👉 **Action**: Waiting for the author to address comments, fix merge conflicts, or move from draft.\n"
    elif "Waiting on Review" in triage_status:
        markdown += "👉 **Action**: Assign reviewers or nudge existing reviewers.\n"
    elif "Ready to Merge" in triage_status:
        markdown += "👉 **Action**: Merge the PR.\n"
    elif "Blocked" in triage_status:
        markdown += "👉 **Action**: Investigate blocking issues (CI failures, etc.).\n"
    else:
        markdown += "👉 **Action**: Manual intervention needed to determine status.\n"
        
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(markdown)
        
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_pr_report.py <input_json> <output_md>")
        sys.exit(1)
    generate_report(sys.argv[1], sys.argv[2])
