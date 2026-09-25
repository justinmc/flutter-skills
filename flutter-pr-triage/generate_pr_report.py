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

def determine_pr_status(pr_data, reviews, check_runs=None):
    labels = [l.get('name', '') for l in pr_data.get('labels', [])]
    has_cicd = 'CICD' in labels
    has_autosubmit = 'autosubmit' in labels
    author_assoc = pr_data.get('author_association', 'NONE')
    is_member = author_assoc in ['MEMBER', 'OWNER']
    required_approvals = 1 if is_member else 2
    pr_author = pr_data.get('user', {}).get('login')

    if pr_data.get('draft'):
        return "Draft (Waiting on Author)", "Wait for the author", False

    if pr_data.get('mergeable_state') == 'dirty':
        return "Waiting on Author (Merge Conflicts)", "Wait for the author", False

    # Check reviews (exclude PR author and bots)
    latest_reviews = {}
    all_reviewers = set()
    for r in reviews:
        user_obj = r.get('user') or {}
        user = user_obj.get('login')
        user_type = user_obj.get('type', '')
        if not user or user == pr_author or user_type == 'Bot' or user.endswith('[bot]') or user in ['fluttergithubbot']:
            continue
        all_reviewers.add(user)
        state = r.get('state')
        submitted_at = r.get('submitted_at') or ''
        if state == 'COMMENTED':
            continue
        if user not in latest_reviews or submitted_at > latest_reviews[user]['submitted_at']:
            latest_reviews[user] = {'state': state, 'submitted_at': submitted_at}

    if any(info['state'] == 'CHANGES_REQUESTED' for info in latest_reviews.values()):
        return "Waiting on Author (Changes Requested)", "Wait for the author", False

    needs_cicd = not has_cicd

    # Check CI failures or in-progress runs (excluding maintainer/gate checks like Google testing)
    ignored_checks = {'Google testing', 'Awaiting CICD label', 'Merge Queue Guard'}
    if check_runs:
        failed_checks = [
            r.get('name') for r in check_runs
            if r.get('name') not in ignored_checks
            and r.get('conclusion') in ('failure', 'timed_out', 'action_required', 'cancelled')
        ]
        in_prog_checks = [
            r.get('name') for r in check_runs
            if r.get('name') not in ignored_checks
            and r.get('status') != 'completed'
        ]
        if failed_checks:
            failed_str = ", ".join(sorted(set(failed_checks))[:3])
            return f"Waiting on Author (Failing CI: {failed_str})", "Wait for the author", False
        if in_prog_checks:
            prog_str = ", ".join(sorted(set(in_prog_checks))[:3])
            return f"Waiting on Author (CI Running: {prog_str})", "Wait for the author", False

    approvals = [user for user, info in latest_reviews.items() if info['state'] == 'APPROVED']
    requested_reviewers = [r['login'] for r in pr_data.get('requested_reviewers', [])]

    if len(approvals) >= required_approvals:
        if pr_data.get('mergeable_state') == 'unstable':
            return "Waiting on Author (Failing CI)", "Wait for the author", False
        if has_autosubmit:
            return "Waiting to Land (Autosubmit enabled)", "Waiting to land", needs_cicd
        return "Ready to Merge (Needs autosubmit)", "Needs autosubmit", needs_cicd

    if len(approvals) == 1 and required_approvals == 2:
        return "Waiting on Secondary Review (1/2 approvals)", "Needs secondary review", needs_cicd

    if not requested_reviewers and not all_reviewers:
        return "Needs Reviewer Assignment", "Needs reviewer assignment", needs_cicd

    return "Waiting on Primary Review", "Needs primary review", needs_cicd

def generate_report(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
        
    pr = data['pr']
    comments = data['comments']
    reviews = data['reviews']
    files = data['files']
    check_runs = data.get('check_runs', [])
    
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
        
    triage_status, next_step_category, needs_cicd = determine_pr_status(pr, reviews, check_runs)
    labels = [l.get('name', '') for l in pr.get('labels', [])]
    has_cicd = 'CICD' in labels
    if needs_cicd:
        cicd_str = "⚠️ **NEEDS `CICD` LABEL**"
    elif has_cicd:
        cicd_str = "✅ Has `CICD` label"
    else:
        cicd_str = "Not needed yet (waiting on author)"
    
    markdown = f"# PR Triage Report: {title} (#{pr['number']})\n\n"
    markdown += f"- **URL**: {url}\n"
    markdown += f"- **Author**: [{author}]({author_url}) ({pr.get('author_association', 'NONE')})\n"
    markdown += f"- **State**: {state.upper()}\n"
    markdown += f"- **Created At**: {created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    markdown += f"- **Last Activity**: {last_activity_str}\n"
    markdown += f"- **Triage Status**: {get_status_emoji(triage_status)}\n"
    markdown += f"- **Next Step Category**: {next_step_category}\n"
    markdown += f"- **CICD Label**: {cicd_str}\n\n"
    
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
    cicd_note = " **Also apply the `CICD` label.**" if needs_cicd else ""
    if next_step_category == "Wait for the author":
        markdown += f"👉 **Action ({next_step_category})**: Waiting for the author to address review comments, resolve merge conflicts, or fix failing CI.{cicd_note}\n"
    elif next_step_category == "Needs reviewer assignment":
        is_member = pr.get('author_association', 'NONE') in ['MEMBER', 'OWNER']
        num_rev = "1 reviewer (author is Flutter org member)" if is_member else "2 reviewers"
        markdown += f"👉 **Action ({next_step_category})**: Assign {num_rev}.{cicd_note}\n"
    elif next_step_category == "Needs primary review":
        markdown += f"👉 **Action ({next_step_category})**: Complete primary review or nudge assigned reviewers ({', '.join(requested_reviewers) if requested_reviewers else 'previous reviewers'}).{cicd_note}\n"
    elif next_step_category == "Needs secondary review":
        markdown += f"👉 **Action ({next_step_category})**: Complete secondary review to provide a second approval.{cicd_note}\n"
    elif next_step_category == "Needs autosubmit":
        markdown += f"👉 **Action ({next_step_category})**: Verify CI has passed and apply the `autosubmit` label.{cicd_note}\n"
    elif next_step_category == "Waiting to land":
        markdown += f"👉 **Action ({next_step_category})**: Waiting for merge queue / bot to land the PR.{cicd_note}\n"
    else:
        markdown += f"👉 **Action**: Manual intervention needed to determine status.{cicd_note}\n"
        
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(markdown)
        
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_pr_report.py <input_json> <output_md>")
        sys.exit(1)
    generate_report(sys.argv[1], sys.argv[2])
