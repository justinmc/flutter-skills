import json
import os
import re
import sys
import requests

def fetch_pr_info(pr_url):
    # Parse URL
    match = re.match(r'https://github.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if not match:
        print(f"Invalid PR URL: {pr_url}")
        sys.exit(1)
    
    org, repo, pr_number = match.groups()
    
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Flutter-PR-Triage-Bot"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    api_base = f"https://api.github.com/repos/{org}/{repo}"
    
    print(f"Fetching data for {org}/{repo} #{pr_number}...")
    
    # 1. PR Details
    pr_resp = requests.get(f"{api_base}/pulls/{pr_number}", headers=headers)
    if pr_resp.status_code != 200:
        print(f"Failed to fetch PR details: {pr_resp.status_code} {pr_resp.text}")
        sys.exit(1)
    pr_data = pr_resp.json()
    
    # 2. Issue Comments (regular comments on PR)
    comments_resp = requests.get(f"{api_base}/issues/{pr_number}/comments", headers=headers)
    comments = comments_resp.json() if comments_resp.status_code == 200 else []
    
    # 3. Review Comments (inline code comments)
    review_comments_resp = requests.get(f"{api_base}/pulls/{pr_number}/comments", headers=headers)
    review_comments = review_comments_resp.json() if review_comments_resp.status_code == 200 else []
    
    # 4. Reviews
    reviews_resp = requests.get(f"{api_base}/pulls/{pr_number}/reviews", headers=headers)
    reviews = reviews_resp.json() if reviews_resp.status_code == 200 else []
    
    # 5. Files
    files_resp = requests.get(f"{api_base}/pulls/{pr_number}/files", headers=headers)
    files = files_resp.json() if files_resp.status_code == 200 else []
    
    combined_data = {
        "pr": pr_data,
        "comments": comments,
        "review_comments": review_comments,
        "reviews": reviews,
        "files": files
    }
    
    # Create tmp dir if not exists
    os.makedirs("tmp", exist_ok=True)
    
    output_filename = f"tmp/{org}.{repo}.{pr_number}.json"
    with open(output_filename, "w") as f:
        json.dump(combined_data, f, indent=2)
    
    print(f"Saved data to {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_pr_data.py <PR_URL>")
        sys.exit(1)
    fetch_pr_info(sys.argv[1])
