#!/usr/bin/env python3
"""Fetches the context needed to review a GitHub pull request.

Usage:
  python3 fetch_pr_context.py <PR_URL> [--out-dir DIR] [--history N]
                              [--max-files N] [--max-refs N]

Writes the following files into <out-dir>/<org>.<repo>.<number>/
(default out-dir: ./tmp):

  context.json  Raw data from the GitHub API: PR metadata, commits, files,
                issue comments, review comments, reviews, check runs, linked
                issues/PRs (with their comments), timeline cross-references,
                and recent commit history for every changed file.
  pr.diff       The full unified diff of the PR.
  digest.md     A condensed, human/agent-readable summary of context.json.
                Read this first; fall back to context.json for details.

Requires the `requests` library and a GITHUB_TOKEN environment variable
(unauthenticated requests work but are heavily rate limited).
"""

import argparse
import json
import os
import re
import sys
import time

import requests

API = "https://api.github.com"
PR_URL_RE = re.compile(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)")
# Matches full GitHub issue/PR URLs, e.g. https://github.com/flutter/flutter/issues/123.
REF_URL_RE = re.compile(
    r"https?://github\.com/([\w.-]+)/([\w.-]+)/(?:issues|pull)/(\d+)"
)
# Matches short references like flutter/packages#123 or #123.
REF_SHORT_RE = re.compile(r"(?<![\w/#])(?:([\w.-]+)/([\w.-]+))?#(\d+)\b")
# Matches the "(#12345)" suffix that squash-merged commits have in flutter repos.
COMMIT_PR_RE = re.compile(r"\(#(\d+)\)")
BOT_SUFFIX = "[bot]"


class GitHub:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "flutter-pr-review-skill",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _request(self, url, params=None, accept=None):
        headers = {"Accept": accept} if accept else None
        for _ in range(5):
            resp = self.session.get(url, params=params, headers=headers, timeout=60)
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if resp.status_code in (403, 429) and remaining == "0":
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset - int(time.time()) + 1, 1)
                print(f"Rate limited; sleeping {wait}s.", file=sys.stderr)
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                time.sleep(2)
                continue
            return resp
        return resp

    def get(self, path, params=None, accept=None):
        """Returns parsed JSON, or None on a non-200 response."""
        url = path if path.startswith("http") else f"{API}{path}"
        resp = self._request(url, params=params, accept=accept)
        if resp.status_code != 200:
            print(
                f"Warning: GET {url} -> {resp.status_code}: {resp.text[:200]}",
                file=sys.stderr,
            )
            return None
        return resp.json()

    def get_text(self, path, accept):
        resp = self._request(f"{API}{path}", accept=accept)
        if resp.status_code != 200:
            print(
                f"Warning: GET {path} ({accept}) -> {resp.status_code}",
                file=sys.stderr,
            )
            return None
        return resp.text

    def get_all(self, path, params=None, key=None, limit=3000):
        """Follows pagination and returns a combined list."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url = f"{API}{path}"
        results = []
        while url and len(results) < limit:
            resp = self._request(url, params=params)
            if resp.status_code != 200:
                print(
                    f"Warning: GET {url} -> {resp.status_code}: {resp.text[:200]}",
                    file=sys.stderr,
                )
                break
            data = resp.json()
            results.extend(data[key] if key else data)
            url = resp.links.get("next", {}).get("url")
            params = None  # The "next" URL already includes the query string.
        return results


def parse_pr_url(url):
    match = PR_URL_RE.match(url.strip())
    if not match:
        sys.exit(f"Invalid PR URL: {url}")
    org, repo, number = match.groups()
    return org, repo, int(number)


def find_references(texts, default_org, default_repo, self_number):
    """Finds issue/PR references in free text, preserving first-seen order."""
    refs = []
    seen = set()
    for text in texts:
        if not text:
            continue
        # Strip fenced code blocks; "#123" inside code is rarely a reference.
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        candidates = [m.groups() for m in REF_URL_RE.finditer(text)]
        candidates += [
            (m.group(1) or default_org, m.group(2) or default_repo, m.group(3))
            for m in REF_SHORT_RE.finditer(text)
        ]
        for org, repo, num in candidates:
            key = (org.lower(), repo.lower(), int(num))
            if key == (default_org.lower(), default_repo.lower(), self_number):
                continue
            if key not in seen:
                seen.add(key)
                refs.append((org, repo, int(num)))
    return refs


def slim_user(user):
    return (user or {}).get("login")


def slim_comment(c):
    return {
        "author": slim_user(c.get("user")),
        "author_association": c.get("author_association"),
        "created_at": c.get("created_at"),
        "url": c.get("html_url"),
        "body": c.get("body"),
    }


def fetch_reference(gh, org, repo, number, max_comments):
    issue = gh.get(f"/repos/{org}/{repo}/issues/{number}")
    if issue is None:
        return None
    comments = []
    if issue.get("comments"):
        comments = gh.get_all(
            f"/repos/{org}/{repo}/issues/{number}/comments", limit=max_comments
        )[:max_comments]
    return {
        "repo": f"{org}/{repo}",
        "number": number,
        "is_pr": "pull_request" in issue,
        "merged_at": (issue.get("pull_request") or {}).get("merged_at"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "state_reason": issue.get("state_reason"),
        "url": issue.get("html_url"),
        "author": slim_user(issue.get("user")),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "labels": [l.get("name") for l in issue.get("labels", [])],
        "reactions": (issue.get("reactions") or {}).get("total_count"),
        "comment_count": issue.get("comments"),
        "body": issue.get("body"),
        "comments": [slim_comment(c) for c in comments],
    }


def fetch_file_history(gh, org, repo, base_ref, path, count):
    commits = gh.get(
        f"/repos/{org}/{repo}/commits",
        params={"path": path, "sha": base_ref, "per_page": count},
    )
    history = []
    for c in commits or []:
        message = (c.get("commit") or {}).get("message", "")
        title = message.splitlines()[0] if message else ""
        pr_match = COMMIT_PR_RE.search(title)
        history.append(
            {
                "sha": c.get("sha"),
                "date": ((c.get("commit") or {}).get("author") or {}).get("date"),
                "author": slim_user(c.get("author"))
                or ((c.get("commit") or {}).get("author") or {}).get("name"),
                "title": title,
                "pr": int(pr_match.group(1)) if pr_match else None,
                "url": c.get("html_url"),
            }
        )
    return history


def diff_from_files(files):
    """Builds an approximate unified diff from the per-file patches."""
    chunks = []
    for f in files:
        old = f.get("previous_filename") or f["filename"]
        new = f["filename"]
        chunks.append(f"diff --git a/{old} b/{new}")
        chunks.append("--- /dev/null" if f["status"] == "added" else f"--- a/{old}")
        chunks.append("+++ /dev/null" if f["status"] == "removed" else f"+++ b/{new}")
        if f.get("patch"):
            chunks.append(f["patch"])
        else:
            chunks.append("# (patch omitted by GitHub: binary or too large)")
    return "\n".join(chunks) + "\n"


def truncate(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + " …[truncated]"


def write_digest(ctx, path):
    pr = ctx["pr"]
    lines = []
    add = lines.append
    add(f"# {ctx['repo']}#{pr['number']}: {pr['title']}")
    add("")
    add(f"- URL: {pr['html_url']}")
    state = "merged" if pr.get("merged_at") else pr["state"]
    if pr.get("draft"):
        state += " (draft)"
    add(f"- State: {state}")
    add(
        f"- Author: {slim_user(pr['user'])} "
        f"(association: {pr.get('author_association')})"
    )
    add(f"- Created: {pr['created_at']}  Updated: {pr['updated_at']}")
    add(f"- Base: {pr['base']['ref']}  Head: {pr['head']['label']} @ {pr['head']['sha']}")
    add(
        f"- Size: {pr['changed_files']} files, +{pr['additions']}/-{pr['deletions']}, "
        f"{pr['commits']} commits"
    )
    add(f"- Labels: {', '.join(l['name'] for l in pr.get('labels', [])) or 'none'}")
    add(
        "- Requested reviewers: "
        + (", ".join(slim_user(u) for u in pr.get("requested_reviewers", [])) or "none")
    )
    add(f"- Mergeable state: {pr.get('mergeable_state')}")
    add("")

    add("## Description")
    add("")
    add(pr.get("body") or "_No description._")
    add("")

    add("## Reviews")
    add("")
    reviews = [r for r in ctx["reviews"] if r.get("state") != "PENDING"]
    if not reviews:
        add("_No reviews yet._")
    for r in reviews:
        add(
            f"- **{slim_user(r.get('user'))}** {r.get('state')} at "
            f"{r.get('submitted_at')}: {truncate(r.get('body'), 600) or '(no body)'}"
        )
    add("")

    add("## Conversation (issue comments)")
    add("")
    human = [c for c in ctx["comments"] if not (slim_user(c.get("user")) or "").endswith(BOT_SUFFIX)]
    bots = len(ctx["comments"]) - len(human)
    if not human:
        add("_No human comments._")
    for c in human:
        add(f"- **{slim_user(c.get('user'))}** ({c.get('created_at')}): {truncate(c.get('body'), 1500)}")
    if bots:
        add(f"- _{bots} bot comment(s) omitted; see context.json._")
    add("")

    add("## Inline review threads")
    add("")
    threads = {}
    for c in ctx["review_comments"]:
        root = c.get("in_reply_to_id") or c["id"]
        threads.setdefault(root, []).append(c)
    if not threads:
        add("_No inline review comments._")
    for root, comments in threads.items():
        first = comments[0]
        line = first.get("line") or first.get("original_line")
        outdated = " (outdated)" if first.get("line") is None else ""
        add(f"### {first.get('path')}:{line}{outdated}")
        add(f"{first.get('html_url')}")
        add("")
        for c in comments:
            add(f"- **{slim_user(c.get('user'))}**: {truncate(c.get('body'), 1200)}")
        add("")

    add("## Changed files")
    add("")
    for f in ctx["files"]:
        rename = f" (renamed from {f['previous_filename']})" if f.get("previous_filename") else ""
        add(f"- `{f['filename']}` {f['status']}{rename} +{f['additions']}/-{f['deletions']}")
    add("")

    add("## CI (check runs on head commit)")
    add("")
    runs = ctx["check_runs"]
    if not runs:
        add("_No check runs found._")
    else:
        buckets = {}
        for r in runs:
            key = r.get("conclusion") or r.get("status")
            buckets.setdefault(key, []).append(r.get("name"))
        for key, names in sorted(buckets.items(), key=lambda kv: str(kv[0])):
            shown = ", ".join(names[:15]) + (" …" if len(names) > 15 else "")
            add(f"- {key}: {len(names)} ({shown})")
    add("")

    add("## Linked issues and PRs")
    add("")
    if not ctx["references"]:
        add("_No references found in the PR description, commits, or comments._")
    for ref in ctx["references"]:
        kind = "PR" if ref["is_pr"] else "Issue"
        state = "merged" if ref.get("merged_at") else ref["state"]
        add(f"### {kind} {ref['repo']}#{ref['number']}: {ref['title']} ({state})")
        add(
            f"{ref['url']} — by {ref['author']}, created {ref['created_at']}, "
            f"{ref['comment_count']} comments, {ref['reactions']} reactions, "
            f"labels: {', '.join(ref['labels']) or 'none'}"
        )
        add("")
        add(truncate(ref.get("body"), 2000) or "_No body._")
        add("")
        for c in ref["comments"]:
            if (c["author"] or "").endswith(BOT_SUFFIX):
                continue
            add(f"- **{c['author']}** ({c['created_at']}): {truncate(c['body'], 800)}")
        add("")

    add("## Cross-references (other issues/PRs that mention this PR)")
    add("")
    if not ctx["cross_references"]:
        add("_None._")
    for x in ctx["cross_references"]:
        add(f"- {x['repo']}#{x['number']} ({x['state']}): {x['title']} — {x['url']}")
    add("")

    add("## Recent history of changed files (on base branch)")
    add("")
    for path_, history in ctx["file_history"].items():
        add(f"### `{path_}`")
        if not history:
            add("_No history (new file?)._")
        for h in history:
            pr_link = f" (#{h['pr']})" if h["pr"] else ""
            add(f"- {(h['date'] or '')[:10]} {h['author']}: {h['title']}{pr_link} {h['url']}")
        add("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pr_url")
    parser.add_argument("--out-dir", default="tmp")
    parser.add_argument("--history", type=int, default=8, help="Commits of history per changed file.")
    parser.add_argument("--max-files", type=int, default=40, help="Max changed files to fetch history for.")
    parser.add_argument("--max-refs", type=int, default=20, help="Max linked issues/PRs to fetch.")
    parser.add_argument("--max-ref-comments", type=int, default=30, help="Max comments per linked issue/PR.")
    args = parser.parse_args()

    org, repo, number = parse_pr_url(args.pr_url)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN is not set; you will likely be rate limited.", file=sys.stderr)
    gh = GitHub(token)
    base = f"/repos/{org}/{repo}"

    print(f"Fetching {org}/{repo}#{number}...", file=sys.stderr)
    pr = gh.get(f"{base}/pulls/{number}")
    if pr is None:
        sys.exit("Failed to fetch the PR.")

    files = gh.get_all(f"{base}/pulls/{number}/files")
    commits = gh.get_all(f"{base}/pulls/{number}/commits")
    comments = gh.get_all(f"{base}/issues/{number}/comments")
    review_comments = gh.get_all(f"{base}/pulls/{number}/comments")
    reviews = gh.get_all(f"{base}/pulls/{number}/reviews")
    check_runs = gh.get_all(
        f"{base}/commits/{pr['head']['sha']}/check-runs", key="check_runs", limit=500
    )

    print("Fetching diff...", file=sys.stderr)
    diff = gh.get_text(f"{base}/pulls/{number}", accept="application/vnd.github.v3.diff")
    if diff is None:
        print("Falling back to a diff assembled from per-file patches.", file=sys.stderr)
        diff = diff_from_files(files)

    print("Fetching linked issues and PRs...", file=sys.stderr)
    texts = [pr.get("body")]
    texts += [(c.get("commit") or {}).get("message") for c in commits]
    texts += [c.get("body") for c in comments]
    texts += [r.get("body") for r in reviews]
    texts += [c.get("body") for c in review_comments]
    references = []
    for ref_org, ref_repo, ref_num in find_references(texts, org, repo, number)[: args.max_refs]:
        ref = fetch_reference(gh, ref_org, ref_repo, ref_num, args.max_ref_comments)
        if ref:
            references.append(ref)

    print("Fetching cross-references...", file=sys.stderr)
    timeline = gh.get_all(f"{base}/issues/{number}/timeline", limit=1000)
    cross_references = []
    for event in timeline:
        if event.get("event") != "cross-referenced":
            continue
        issue = (event.get("source") or {}).get("issue") or {}
        if not issue:
            continue
        repo_url = issue.get("repository_url", "")
        cross_references.append(
            {
                "repo": "/".join(repo_url.rstrip("/").split("/")[-2:]),
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "is_pr": "pull_request" in issue,
                "url": issue.get("html_url"),
            }
        )

    print("Fetching history of changed files...", file=sys.stderr)
    file_history = {}
    for f in files[: args.max_files]:
        if f["status"] == "added":
            file_history[f["filename"]] = []
            continue
        path = f.get("previous_filename") or f["filename"]
        file_history[f["filename"]] = fetch_file_history(
            gh, org, repo, pr["base"]["ref"], path, args.history
        )

    ctx = {
        "repo": f"{org}/{repo}",
        "pr": pr,
        "commits": commits,
        "files": files,
        "comments": comments,
        "review_comments": review_comments,
        "reviews": reviews,
        "check_runs": check_runs,
        "references": references,
        "cross_references": cross_references,
        "file_history": file_history,
    }

    out_dir = os.path.join(args.out_dir, f"{org}.{repo}.{number}")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "context.json"), "w") as f:
        json.dump(ctx, f, indent=2)
    with open(os.path.join(out_dir, "pr.diff"), "w") as f:
        f.write(diff)
    write_digest(ctx, os.path.join(out_dir, "digest.md"))
    print(out_dir)


if __name__ == "__main__":
    main()
