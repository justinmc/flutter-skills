import subprocess
import json
import concurrent.futures
import os
import sys

def main():
    if not os.path.exists('tmp/combined_triage.json'):
        print("Error: tmp/combined_triage.json not found.", file=sys.stderr)
        sys.exit(1)
        
    with open('tmp/combined_triage.json') as f:
        triage_data = json.load(f)

    # We want to process PRs from across any list. 
    # Usually they are grouped in the "Pull Requests" list, but let's gather all IS_PR == True items
    urls = []
    for list_name, list_data in triage_data.items():
        if 'items' in list_data:
            for item in list_data['items']:
                if item.get('is_pr', False):
                    urls.append(item['html_url'])
                    
    urls = list(set(urls)) # dedup

    print(f"Found {len(urls)} PRs to evaluate.")

    # Need to run PR triage in the flutter-pr-triage skill directory
    triage_dir = os.path.abspath('../flutter-pr-triage')
    if not os.path.exists(triage_dir):
        print(f"Error: {triage_dir} not found.", file=sys.stderr)
        sys.exit(1)

    def process_pr(url):
        print(f"Processing {url}")
        # Fetch data
        subprocess.run([sys.executable, 'fetch_pr_data.py', url], cwd=triage_dir, check=True, stdout=subprocess.DEVNULL)
        pr_num = url.split('/')[-1]
        in_json = f'tmp/flutter.flutter.{pr_num}.json'
        out_md = f'output/flutter_flutter_{pr_num}.md'
        subprocess.run([sys.executable, 'generate_pr_report.py', in_json, out_md], cwd=triage_dir, check=True, stdout=subprocess.DEVNULL)
        return pr_num

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(process_pr, urls))

    print("Finished evaluating all PRs.")

if __name__ == "__main__":
    main()
