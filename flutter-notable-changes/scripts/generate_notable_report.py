import argparse
import datetime
import json
import re
import subprocess
import sys
from datetime import timezone

def run_command(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def get_pr_details(pr_num, repo="flutter/flutter"):
    # Fetch comprehensive PR details in JSON format
    fields = "number,title,author,reviews,comments,body,url,commits,labels"
    cmd = f"gh pr view {pr_num} --repo {repo} --json {fields}"
    stdout = run_command(cmd)
    if not stdout:
        print(f"Error: Failed to fetch PR #{pr_num}", file=sys.stderr)
        return None
    try:
        return json.loads(stdout)
    except Exception as e:
        print(f"Error: Failed to parse JSON for PR #{pr_num}: {e}", file=sys.stderr)
        return None

def is_bot_account(author_dict=None, login=None, name=None, email=None):
    # Determines if the given account is an automated bot/roller account.
    if author_dict and isinstance(author_dict, dict):
        if author_dict.get('isBot') or author_dict.get('is_bot'):
            return True
        if not login:
            login = author_dict.get('login')
        if not name:
            name = author_dict.get('name')
            
    login_lower = login.lower() if login else ""
    name_lower = name.lower() if name else ""
    email_lower = email.lower() if email else ""
    
    # Check standard indicators
    if '[bot]' in login_lower or '[bot]' in name_lower:
        return True
    if login_lower.endswith('-bot') or name_lower.endswith('-bot'):
        return True
    if login_lower.endswith('-roller') or name_lower.endswith('-roller'):
        return True
    if login_lower.endswith('-autoroll') or name_lower.endswith('-autoroll'):
        return True
    if login_lower.endswith('-autoroller') or name_lower.endswith('-autoroller'):
        return True
    if login_lower.endswith('-helper') or name_lower.endswith('-helper'):
        return True
        
    # Suffixes/prefixes in emails
    if 'bot' in email_lower and '@' in email_lower:
        return True
    if 'roller' in email_lower and '@' in email_lower:
        return True
    if 'autoroll' in email_lower and '@' in email_lower:
        return True
    if 'gserviceaccount.com' in email_lower:
        return True
        
    # Known automated accounts
    known_bots = {
        'engine-flutter-autoroll',
        'fluttergithubbot',
        'skia-flutter-autoroll',
        'skia-autoroll',
        'dependabot',
        'github-actions',
        'gemini-code-assist',
        'google-copybara',
        'flutter-goldman',
        'google-cla',
        'fuchsia-autoroll',
        'dart-internal-client',
        'auto-submit',
        'web-platform-tests',
        'wpt-pr-bot',
        'pr-review-bot',
        'gtech-roller',
        'chrome-roller',
        'swift-roller',
        'web-roller',
        'recipe-mega-autoroller',
        'chops-service-accounts',
        'google-clear-roller',
        'reland-bot',
        'reland-helper',
        'codelabs-builder',
        'flutter-dashboard',
        'keyval-bot',
        'milestone-notifier',
        'size-bot',
        'triage-bot',
        'copybara',
        'lgtm-co',
        'sonarcloud',
        'codecov',
        'greenkeeper',
        'snyk-bot',
        'snyk',
        'renovate',
        'bors'
    }
    
    if login_lower in known_bots or name_lower in known_bots:
        return True
        
    return False

def check_first_time_contributor(author_login, author_name, pr_commits, start_date,
                                 ref="upstream/master", repo="flutter/flutter"):
    if is_bot_account(login=author_login, name=author_name):
        return False
    # Check 1: Check local Git log by author name and email
    emails = set()
    names = set()
    for commit in pr_commits:
        # PR commits have an 'authors' list
        for ca in commit.get('authors', []):
            if ca.get('login') == author_login:
                email = ca.get('email')
                name = ca.get('name')
                if email: emails.add(email)
                if name: names.add(name)
        # Fallback to single 'author' dict if present
        commit_author = commit.get('author', {})
        if commit_author and commit_author.get('login') == author_login:
            email = commit_author.get('email')
            name = commit_author.get('name')
            if email: emails.add(email)
            if name: names.add(name)
        
    # If no commit matched the login, fall back to author details
    if not emails and not names:
        if author_login: names.add(author_login)
        if author_name: names.add(author_name)
        
    is_first_git = True
    for email in emails:
        # Find first ever commit date in git local log
        first_commit = run_command(f'git log {ref} --author="{email}" --reverse --pretty=format:"%ci" | head -n 1')
        if first_commit:
            # Extract date part YYYY-MM-DD
            first_date_str = first_commit.split()[0]
            first_date = datetime.date.fromisoformat(first_date_str)
            # If first commit was before start_date, they are not new
            if first_date < start_date:
                is_first_git = False
                break
                
    if is_first_git:
        for name in names:
            first_commit = run_command(f'git log {ref} --author="{name}" --reverse --pretty=format:"%ci" | head -n 1')
            if first_commit:
                first_date_str = first_commit.split()[0]
                first_date = datetime.date.fromisoformat(first_date_str)
                if first_date < start_date:
                    is_first_git = False
                    break

    # Check 2: Check GitHub Search for commits before start_date
    is_first_gh = True
    start_date_str = start_date.strftime('%Y-%m-%d')
    gh_search_cmd = f'gh search commits --author-date="<{start_date_str}" --author="{author_login}" --repo "{repo}" --limit 1'
    gh_res = run_command(gh_search_cmd)
    if gh_res:
        is_first_gh = False
        
    return is_first_git and is_first_gh


def extract_co_authors(body, commits):
    co_authors = []
    # Check 1: Scan PR body for Co-authored-by
    pattern = r'Co-authored-by:\s*([^<]+)\s*<([^>]+)>'
    matches = re.findall(pattern, body or '')
    for name, email in matches:
        co_authors.append({
            'name': name.strip(),
            'email': email.strip(),
            'login': None
        })
        
    # Check 2: Scan commit messages
    for commit in commits:
        msg = commit.get('message', '')
        matches = re.findall(pattern, msg)
        for name, email in matches:
            entry = {'name': name.strip(), 'email': email.strip(), 'login': None}
            if entry not in co_authors:
                co_authors.append(entry)
                
    return co_authors

def extract_media(body):
    media_elements = []
    if not body: return media_elements
    
    # 1. Match Markdown images: ![alt](url)
    # Allows standard image extensions OR user-attachments/assets or assets URLs
    md_imgs = re.findall(r'!\[[^\]]*\]\(((?:https?://[^\)]+\.(?:png|jpg|jpeg|gif|webp))|(?:https?://github\.com/(?:user-attachments/assets|assets)/[a-f0-9-]+))\)', body)
    for img in md_imgs:
        media_elements.append(f"![Visual Demonstration]({img})")
        
    # 2. Match HTML images: <img ... src="url" ...>
    html_imgs = re.findall(r'<img\s+[^>]*src=["\']((?:https?://[^"\']+\.(?:png|jpg|jpeg|gif|webp))|(?:https?://github\.com/(?:user-attachments/assets|assets)/[a-f0-9-]+))["\']', body, re.IGNORECASE)
    for img in html_imgs:
        if f"![Visual Demonstration]({img})" not in media_elements:
            media_elements.append(f"![Visual Demonstration]({img})")
        
    # 3. Match HTML videos: <video ... src="url" ...>
    video_urls = re.findall(r'<video\s+[^>]*src=["\']((?:https?://[^"\']+\.(?:mp4|mov|webm))|(?:https?://github\.com/(?:user-attachments/assets|assets)/[a-f0-9-]+))["\']', body, re.IGNORECASE)
    for vid in video_urls:
        media_elements.append(f'<video src="{vid}" controls="controls" style="max-width: 100%;"></video>')
        
    # 4. Match stand-alone links to mp4/mov
    vid_links = re.findall(r'(https?://[^\s\)]+\.(?:mp4|mov|webm))', body)
    for vid in vid_links:
        if not any(vid in el for el in media_elements):
            media_elements.append(f'<video src="{vid}" controls="controls" style="max-width: 100%;"></video>')
            
    return media_elements

# Labels that carry no signal about what area a PR touches.
NOISE_LABELS = {
    'cicd',
    'emergency',
    'override code freeze',
    'will affect goldens',
    'waiting for tree to go green',
    'autosubmit',
    'revert',
    'work in progress (wip)',
}

NOISE_PREFIXES = ('team-', 'd: ', 'c: ', 'l:', 'p: first party', 'r: ')

# Ordered by precedence: the first category with a matching label wins.
# Matching is on exact label names, since Flutter labels like "a: tests" or
# "platform-fuchsia" would otherwise be caught by substring matches.
CATEGORY_LABELS = [
    ("Accessibility", {'a: accessibility'}),
    ("Material Design", {'f: material design', 'p: material_ui'}),
    ("Cupertino (iOS-style)", {'f: cupertino', 'p: cupertino_ui'}),
    ("Web Platform", {'platform-web', 'e: web_canvaskit', 'e: web_html', 'e: skwasm'}),
    ("Android Platform", {'platform-android'}),
    ("iOS Platform", {'platform-ios'}),
    ("Desktop Platforms", {'platform-linux', 'platform-macos', 'platform-windows', 'a: desktop'}),
    ("Tooling & Developer Experience", {'tool', 'a: build', 't: gradle', 't: xcode', 't: flutter driver'}),
    ("Engine & Performance", {'engine', 'e: impeller', 'flutter-gpu'}),
    ("Framework & Core Libraries", {'framework'}),
]

DEFAULT_CATEGORY = "Framework & Core Libraries"

# PRs carrying more labels than this touch the whole repo (e.g. a repo-wide
# reformat), so any label-derived category is arbitrary.
REPO_WIDE_LABEL_THRESHOLD = 8

def categorize_pr(labels):
    # Returns (category, confidence, candidates).
    # confidence is 'high' or 'low'; 'low' means the caller should review the
    # choice and override it with --category if needed.
    label_names = {l['name'].lower() for l in labels}
    meaningful = {
        name for name in label_names
        if name not in NOISE_LABELS and not name.startswith(NOISE_PREFIXES)
    }

    candidates = [cat for cat, cat_labels in CATEGORY_LABELS if meaningful & cat_labels]
    category = candidates[0] if candidates else DEFAULT_CATEGORY

    confidence = 'high'
    if len(meaningful) > REPO_WIDE_LABEL_THRESHOLD:
        # Repo-wide change: prefer Tooling if it is a tool change, else default.
        category = "Tooling & Developer Experience" if 'tool' in meaningful else DEFAULT_CATEGORY
        confidence = 'low'
    elif len(candidates) >= 3:
        confidence = 'low'
    elif not candidates:
        confidence = 'low'

    return category, confidence, candidates



def main():
    parser = argparse.ArgumentParser(description="Generate Weekly Notable Changes Report")
    parser.add_argument("pr_numbers", nargs="+", type=int, help="List of PR numbers to include in the report")
    parser.add_argument("--since", type=str, default="7 days ago", help="Git since description (for total commits calculation)")
    parser.add_argument("--start-date", type=str, help="Start date for first-time contributor checks (YYYY-MM-DD). Defaults to 7 days ago.")
    parser.add_argument("--end-date", type=str, help="End date of report (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--ref", type=str, default="upstream/master",
                        help="Git ref to count commits and check author history against. "
                             "Defaults to upstream/master so a stale or forked local HEAD does not skew results.")
    parser.add_argument("--repo", type=str, default="flutter/flutter",
                        help="GitHub repo to query. Defaults to flutter/flutter.")
    parser.add_argument("--category", action="append", default=[], metavar="PR=CATEGORY",
                        help="Override the computed category for a PR, e.g. --category 192649='Tooling & Developer Experience'. "
                             "Repeatable.")
    args = parser.parse_args()
    
    now = datetime.datetime.now(timezone.utc).date()
    
    if args.start_date:
        start_date = datetime.date.fromisoformat(args.start_date)
    else:
        start_date = now - datetime.timedelta(days=7)
        
    if args.end_date:
        end_date = datetime.date.fromisoformat(args.end_date)
    else:
        end_date = now
        
    categories = {
        "Material Design": [],
        "Cupertino (iOS-style)": [],
        "Accessibility": [],
        "Framework & Core Libraries": [],
        "Engine & Performance": [],
        "Web Platform": [],
        "Android Platform": [],
        "iOS Platform": [],
        "Desktop Platforms": [],
        "Tooling & Developer Experience": []
    }

    # Parse --category overrides.
    category_overrides = {}
    for override in args.category:
        if '=' not in override:
            print(f"Error: --category expects PR=CATEGORY, got '{override}'", file=sys.stderr)
            return 2
        pr_str, cat = override.split('=', 1)
        cat = cat.strip()
        if cat not in categories:
            print(f"Error: unknown category '{cat}'. Valid categories: {', '.join(categories)}", file=sys.stderr)
            return 2
        category_overrides[int(pr_str.strip().lstrip('#'))] = cat

    # Resolve the ref used for commit counting and author history.
    ref = args.ref
    if ref and not run_command(f'git rev-parse --verify --quiet "{ref}^{{commit}}"'):
        print(f"Warning: ref '{ref}' not found; falling back to HEAD. "
              f"Commit counts may be wrong if HEAD is not synced with upstream.", file=sys.stderr)
        ref = "HEAD"

    total_commits = run_command(f'git log {ref} --since="{args.since}" --oneline | wc -l')

    first_time_contributors = []
    low_confidence_categories = []
    
    print(f"Processing {len(args.pr_numbers)} PRs... This may take a minute...", file=sys.stderr)
    
    for pr_num in args.pr_numbers:
        pr = get_pr_details(pr_num, repo=args.repo)
        if not pr:
            continue
            
        title = pr.get('title', '')
        author_login = pr['author']['login']
        author_name = pr['author'].get('name') or author_login
        pr_url = pr.get('url', '')
        body = pr.get('body', '')
        commits = pr.get('commits', [])
        labels = pr.get('labels', [])
        
        # Deduplicate human reviewers (exclude automated/robot accounts)
        reviewers_set = set()
        
        # 1. Scan formal reviews
        for review in pr.get('reviews', []):
            if not review.get('author'):
                continue
            reviewer_login = review['author'].get('login')
            if not reviewer_login:
                continue
            # Exclude bots and the author
            if not is_bot_account(review['author'], reviewer_login) and reviewer_login != author_login:
                reviewers_set.add(reviewer_login)
                
        # Co-author processing (excluding bots)
        co_authors = extract_co_authors(body, commits)
        human_co_authors = []
        for ca in co_authors:
            if is_bot_account(login=ca.get('login'), name=ca.get('name'), email=ca.get('email')):
                continue
            if not ca['login']:
                # Try to search github by email
                ca_search = run_command(f'gh search users "{ca["email"]}" --limit 1 --json login')
                if ca_search:
                    try:
                        ca_json = json.loads(ca_search)
                        if ca_json:
                            login = ca_json[0]['login']
                            ca['login'] = login
                    except Exception:
                        pass
            # Re-verify resolved login isn't a bot
            if is_bot_account(login=ca.get('login'), name=ca.get('name'), email=ca.get('email')):
                continue
                
            human_co_authors.append(ca)
            if ca['login']:
                reviewers_set.discard(ca['login'])
                
        co_authors = human_co_authors
        reviewers_list = list(reviewers_set)
        
        # Check if the main PR author is a bot/robot
        is_author_bot = is_bot_account(pr.get('author'), author_login, author_name)
        
        # Check First-time Contributor Status
        if not is_author_bot:
            already_listed = any(c['login'] == author_login for c in first_time_contributors)
            if not already_listed:
                is_new = check_first_time_contributor(author_login, author_name, commits, start_date,
                                                      ref=ref, repo=args.repo)
                if is_new:
                    first_time_contributors.append({
                        'name': author_name,
                        'login': author_login,
                        'pr_number': pr_num,
                        'pr_url': pr_url,
                        'title': title
                    })
                
        # Extract visual media
        media = extract_media(body)
        
        # Handle case where main author is a bot, but there are human co-authors
        actual_author_name = author_name
        actual_author_login = author_login
        actual_co_authors = co_authors[:]
        has_author = True
        
        if is_author_bot:
            if actual_co_authors:
                # Promote first human co-author to main author
                first_ca = actual_co_authors.pop(0)
                actual_author_name = first_ca['name']
                actual_author_login = first_ca['login'] or first_ca['email']
                has_author = True
            else:
                has_author = False
                
        # Build entry object
        entry = {
            'number': pr_num,
            'url': pr_url,
            'title': title,
            'author_name': actual_author_name,
            'author_login': actual_author_login,
            'has_author': has_author,
            'co_authors': actual_co_authors,
            'reviewers': reviewers_list,
            'media': media
        }
        
        # Categorize
        category, confidence, candidates = categorize_pr(labels)
        if pr_num in category_overrides:
            category = category_overrides[pr_num]
        elif confidence == 'low':
            low_confidence_categories.append({
                'number': pr_num,
                'title': title,
                'category': category,
                'candidates': candidates,
                'labels': sorted(l['name'] for l in labels),
            })
        categories[category].append(entry)
        
    # Generate Report Content
    start_formatted = start_date.strftime('%B %d, %Y')
    end_formatted = end_date.strftime('%B %d, %Y')
    
    report = []
    report.append(f"### {start_formatted} to {end_formatted}\n")
    report.append(f"This week, {total_commits} commits landed in the Flutter repository. ")
    if first_time_contributors:
        new_contribs_list = [f"@{c['login']}" for c in first_time_contributors]
        new_contribs_str = ", ".join(new_contribs_list)
        report.append(f"A special welcome to our new contributors: {new_contribs_str}! ")
    report.append("Below are the notable changes that landed this week:\n")
    
    for cat, prs in categories.items():
        if not prs:
            continue
        report.append(f"#### {cat}\n")
        for pr in prs:
            # Format title (Sentence case, strip trailing dots)
            title_formatted = pr['title'].strip()
            if title_formatted and not title_formatted.endswith('.'):
                pass # keep standard
                
            report.append(f"*   **[#{pr['number']}]({pr['url']}) {title_formatted}**")
            report.append("    Detailed impact/benefit description of the change goes here. Use 1-2 relevant emojis. 🚀")
            
            # Embed Media
            for med in pr['media']:
                report.append(f"    {med}")
                
            # Format Attributions
            author_str = ""
            if pr['has_author']:
                author_str = f"[{pr['author_name']}](https://github.com/{pr['author_login']})"
                if pr['co_authors']:
                    ca_strs = []
                    for ca in pr['co_authors']:
                        ca_id = ca['login'] or ca['email']
                        ca_strs.append(f"[{ca['name']}](https://github.com/{ca_id})")
                    author_str += " (with co-authors " + ", ".join(ca_strs) + ")"
                    
            rev_str = ""
            if pr['reviewers']:
                rev_strs = [f"[{r}](https://github.com/{r})" for r in pr['reviewers']]
                if len(rev_strs) == 1:
                    rev_str = rev_strs[0]
                elif len(rev_strs) == 2:
                    rev_str = f"{rev_strs[0]} and {rev_strs[1]}"
                else:
                    rev_str = ", ".join(rev_strs[:-1]) + f", and {rev_strs[-1]}"
                    
            if author_str and rev_str:
                report.append(f"    *   Authored by {author_str} and reviewed by {rev_str}.")
            elif author_str:
                report.append(f"    *   Authored by {author_str}.")
            elif rev_str:
                report.append(f"    *   Reviewed by {rev_str}.")
        report.append("")
        
    # Welcoming First-time Contributors
    if first_time_contributors:
        report.append("#### First-time Contributors\n")
        report.append("We would like to extend a warm welcome to our new contributors this week! Thank you for your impactful contributions:\n")
        for c in first_time_contributors:
            report.append(f"- [{c['name']}](https://github.com/{c['login']}), for [#{c['pr_number']}]({c['pr_url']}), which resolved: **{c['title']}**.")
        report.append("")
        
    # Print the report to stdout
    print('\n'.join(report))

    # Flag categorizations the agent should review manually.
    if low_confidence_categories:
        print("\n===================================================", file=sys.stderr)
        print("⚠️  REVIEW CATEGORIZATION: label-based guess is unreliable for these PRs", file=sys.stderr)
        for item in low_confidence_categories:
            others = [c for c in item['candidates'] if c != item['category']]
            print(f"* #{item['number']} {item['title']}", file=sys.stderr)
            print(f"    placed in: {item['category']}", file=sys.stderr)
            print(f"    other candidates: {', '.join(others) if others else 'none'}", file=sys.stderr)
            print(f"    labels: {', '.join(item['labels'])}", file=sys.stderr)
        print("Re-run with --category <PR>='<Category>' to override any of the above.",
              file=sys.stderr)
        print("===================================================\n", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
