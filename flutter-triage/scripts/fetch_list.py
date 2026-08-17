import sys
import os
import requests
import urllib.parse as p
import json
import time

list_name = sys.argv[1]
url = sys.argv[2] # original github url

parsed_url = p.urlparse(url)
query_dict = dict(p.parse_qsl(parsed_url.query))
q = query_dict.get('q', '')

api_url = "https://api.github.com/search/issues"
params = {'q': 'repo:flutter/flutter ' + q, 'per_page': 100}

token = os.environ.get("GITHUB_TOKEN")
headers = {"Accept": "application/vnd.github.v3+json"}
if token:
    headers["Authorization"] = f"token {token}"

os.makedirs(f"tmp/{list_name}", exist_ok=True)
page = 1

while api_url:
    print(f"Fetching page {page} for {list_name}")
    resp = requests.get(api_url, params=params if page == 1 else None, headers=headers)
    if resp.status_code == 403 and 'rate limit' in resp.text.lower():
        reset_time = int(resp.headers.get('X-RateLimit-Reset', time.time() + 60))
        sleep_time = reset_time - int(time.time()) + 1
        print(f"Rate limited. Sleeping for {sleep_time} seconds.")
        time.sleep(sleep_time)
        continue
    resp.raise_for_status()
    
    with open(f"tmp/{list_name}/page_{page}.json", "w") as f:
        json.dump(resp.json(), f)
    
    # Check for next page
    if "next" in resp.links:
        api_url = resp.links["next"]["url"]
        page += 1
    else:
        api_url = None

print(f"Done fetching {list_name}")
