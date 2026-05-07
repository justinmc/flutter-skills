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

def get_pr_details(pr_url):
    try:
        response = requests.get(pr_url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PR details from {pr_url}: {e}", file=sys.stderr)
        return None

def get_reviews(pr_url):
    reviews_url = f"{pr_url}/reviews"
    reviews = []
    try:
        response = requests.get(reviews_url, headers=HEADERS)
        response.raise_for_status()
        reviews = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews from {reviews_url}: {e}", file=sys.stderr)
    return reviews

def get_check_runs(head_sha):
    check_runs_url = f"https://api.github.com/repos/flutter/flutter/commits/{head_sha}/check-runs"
    try:
        response = requests.get(check_runs_url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching check runs for {head_sha}: {e}", file=sys.stderr)
        return None

def determine_pr_status(pr_data, reviews, check_runs=None):
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
        if user not in latest_reviews or submitted_at > latest_reviews[user]['submitted_at']:
            latest_reviews[user] = {'state': state, 'submitted_at': submitted_at}
            
    if any(info['state'] == 'CHANGES_REQUESTED' for info in latest_reviews.values()):
        return "Waiting on Author (Changes Requested)"
        
    # Check if waiting on review
    if pr_data.get('requested_reviewers'):
        return "Waiting on Review"
        
    # Check CI if blocked or unstable
    if pr_data.get('mergeable_state') in ['blocked', 'unstable']:
        if check_runs:
            statuses = [run.get('status') for run in check_runs.get('check_runs', [])]
            conclusions = [run.get('conclusion') for run in check_runs.get('check_runs', []) if run.get('conclusion')]
            
            if 'in_progress' in statuses or 'queued' in statuses:
                return "Waiting for CI"
            if any(c in ['failure', 'timed_out', 'action_required'] for c in conclusions):
                return "Blocked (Failing CI)"
        else:
            return "Blocked (CI or Review)"
            
    if pr_data.get('mergeable_state') == 'clean':
        return "Ready to Merge"
        
    return f"Unknown (mergeable_state: {pr_data.get('mergeable_state')})"

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

        is_pr = 'pull_request' in item
        triage_status = "N/A"
        
        if is_pr:
            pr_url = item['pull_request']['url']
            pr_data = get_pr_details(pr_url)
            if pr_data:
                reviews = get_reviews(pr_url)
                check_runs = None
                if pr_data.get('mergeable_state') in ['blocked', 'unstable']:
                    head_sha = pr_data.get('head', {}).get('sha')
                    if head_sha:
                        check_runs = get_check_runs(head_sha)
                triage_status = determine_pr_status(pr_data, reviews, check_runs)

        entries.append({
            "title": item.get('title'),
            "html_url": item.get('html_url'),
            "author": item.get('user', {}).get('login'),
            "author_url": item.get('user', {}).get('html_url'),
            "date_opened": item.get('created_at'),
            "status": item.get('state'),
            "priority": priority,
            "context": full_context,
            "is_pr": is_pr,
            "triage_status": triage_status,
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