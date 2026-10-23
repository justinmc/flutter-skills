#!/usr/bin/env python3
"""Builds a prioritized list of GitHub PRs and issues that need your attention.

Uses the `gh` CLI (must be authenticated). Writes a Markdown report and a JSON
dump to the skill's gitignored `outputs/` directory.

Ranking:
  1. Who it's for: your team > Googlers > customers > everyone else.
  2. What's needed: quick unblocks first, then follow-ups, then first reviews.
  3. How long it has been waiting on you.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_DIR = os.path.join(SKILL_DIR, "outputs")
DEFAULT_CONFIG = os.path.join(SKILL_DIR, "config.json")
# Small pages keep each (heavy) search request well under GitHub's timeout.
PAGE_SIZE = 10

TIER_NAMES = {1: "Team", 2: "Googler", 3: "Customer", 4: "Community"}

# Action types, in priority order within a tier. Values are what's needed.
ACTIONS = {
    "QUICK_RELGTM": "Re-LGTM: you approved, it changed only a little since, and it's waiting on you",
    "QUICK_REPLY": "Reply: someone is waiting on an answer from you",
    "OWN_LAND": "Land it: your PR is approved and green (add `autosubmit`)",
    "ISSUE_RESPOND": "Respond on issue",
    "OWN_RESPOND": "Address feedback on your PR",
    "RELGTM_BIG_DELTA": "Re-review: you approved, but it changed substantially since",
    "FOLLOWUP_REVIEW": "Follow-up review: the author responded to your review",
    "FIRST_REVIEW_SMALL": "First review (small PR)",
    "FIRST_REVIEW_MEDIUM": "First review (medium PR)",
    "FIRST_REVIEW_LARGE": "First review (large PR, set aside real time)",
    "FYI_CHANGED": "FYI: changed since your LGTM, but nobody asked you to look again",
    "ISSUE_ASSIGNED": "FYI: assigned to you, no new activity",
}
ACTION_ORDER = list(ACTIONS)
LOW_PRIORITY_ACTIONS = {"FYI_CHANGED", "ISSUE_ASSIGNED"}
OWN_ACTIONS = {"OWN_LAND", "OWN_RESPOND"}

EFFORT_QUICK = "⚡ Quick"
EFFORT_SHORT = "🟢 Short"
EFFORT_MODERATE = "🔍 Moderate"
EFFORT_DEEP = "🏋️ Deep"
EFFORT_FYI = "ℹ️ FYI"
EFFORT_LEGEND = ("⚡ Quick (< 10 min) · 🟢 Short (10–30 min) · 🔍 Moderate (30–60 min) · "
                 "🏋️ Deep (1 h+, block out time)")

PR_FIELDS = """
  __typename
  ... on PullRequest {
    number title url createdAt updatedAt isDraft reviewDecision headRefOid
    additions deletions changedFiles
    repository { nameWithOwner }
    author { login ... on User { company name } }
    labels(first: 30) { nodes { name } }
    assignees(first: 10) { nodes { login } }
    reviewRequests(first: 20) { nodes { requestedReviewer { ... on User { login } } } }
    timelineItems(last: 20, itemTypes: [REVIEW_REQUESTED_EVENT, READY_FOR_REVIEW_EVENT]) {
      nodes {
        __typename
        ... on ReviewRequestedEvent { createdAt requestedReviewer { ... on User { login } } }
        ... on ReadyForReviewEvent { createdAt }
      }
    }
    reviews(last: 60) { nodes { author { login } state submittedAt body url commit { oid } } }
    comments(last: 40) { nodes { author { login } createdAt body url } }
    files(first: 100) { nodes { path additions deletions } }
    authorAssociation
    commits(last: 1) {
      nodes {
        commit {
          committedDate
          statusCheckRollup {
            state
            contexts(first: 100) {
              nodes {
                __typename
                ... on CheckRun { name conclusion status }
                ... on StatusContext { context state }
              }
            }
          }
        }
      }
    }
    firstCommits: commits(first: 3) { nodes { commit { author { email } } } }
    closingIssuesReferences(first: 5) { nodes { labels(first: 20) { nodes { name } } } }
  }
  ... on Issue {
    number title url createdAt updatedAt authorAssociation
    repository { nameWithOwner }
    author { login ... on User { company name } }
    labels(first: 30) { nodes { name } }
    assignees(first: 10) { nodes { login } }
    comments(last: 40) { nodes { author { login ... on User { company } } createdAt body url } }
  }
"""

SEARCH_QUERY = """
query($q: String!, $after: String, $first: Int!) {
  search(query: $q, type: ISSUE, first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes { %s }
  }
}
""" % PR_FIELDS


def log(msg):
    print(msg, file=sys.stderr)


def gh_json(args, stdin=None):
    res = subprocess.run(["gh"] + args, input=stdin, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {res.stderr.strip()[:500]}")
    return json.loads(res.stdout)


def graphql(query, variables, attempts=4):
    payload = json.dumps({"query": query, "variables": variables})
    for attempt in range(attempts):
        try:
            data = gh_json(["api", "graphql", "--input", "-"], stdin=payload)
            break
        except (RuntimeError, json.JSONDecodeError) as e:
            # Heavy search pages occasionally time out (502 / truncated body).
            if attempt == attempts - 1:
                raise
            log(f"GraphQL request failed ({str(e)[:120]}); retrying...")
            time.sleep(2 * (attempt + 1))
    if data.get("errors"):
        log(f"GraphQL warnings: {json.dumps(data['errors'])[:500]}")
    return data["data"]


def search(q, limit):
    items, after = [], None
    while len(items) < limit:
        data = graphql(SEARCH_QUERY, {"q": q, "after": after, "first": PAGE_SIZE})["search"]
        items.extend(n for n in data["nodes"] if n)
        if not data["pageInfo"]["hasNextPage"]:
            break
        after = data["pageInfo"]["endCursor"]
    return items[:limit]


def parse_time(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def login_of(node):
    a = (node or {}).get("author") or {}
    return (a.get("login") or "").lower()


def nodes(obj, key):
    return ((obj or {}).get(key) or {}).get("nodes") or []


class Ranker:
    def __init__(self, me, config):
        self.me = me.lower()
        self.cfg = config
        self.team = {u.lower() for u in config["team"]}
        self.googlers = {u.lower() for u in config.get("googlers", [])}
        self.not_googlers = {u.lower() for u in config.get("not_googlers", [])}
        self.bots = {u.lower() for u in config.get("bots", [])}
        self.ignored_paths = [re.compile(p) for p in config.get("ignored_path_patterns", [])]
        self.th = config["size_thresholds"]
        self.company_cache = {}
        self.compare_cache = {}

    # ----- people -----

    def is_bot(self, login):
        return not login or login in self.bots or login.endswith("[bot]") or login.endswith("-bot")

    def company_of(self, login):
        if login not in self.company_cache:
            try:
                self.company_cache[login] = gh_json(["api", f"users/{login}"]).get("company") or ""
            except Exception:
                self.company_cache[login] = ""
        return self.company_cache[login]

    def is_googler(self, login, company=None, emails=()):
        if login in self.not_googlers:
            return False
        if login in self.googlers or login in self.team or login == self.me:
            return True
        if any((e or "").lower().endswith("@google.com") for e in emails):
            return True
        if company is None:
            company = self.company_of(login)
        return "google" in (company or "").lower()

    def tier(self, login, labels, company=None, emails=()):
        """Returns (tier, reason)."""
        if login in self.team:
            return 1, "team"
        if self.is_googler(login, company, emails):
            return 2, "Googler"
        prefix = self.cfg["customer_label_prefix"].lower()
        ignored = {l.lower() for l in self.cfg.get("customer_labels_ignored", [])}
        customers = sorted({l for l in labels if l.lower().startswith(prefix) and l.lower() not in ignored})
        if customers:
            return 3, ", ".join(customers)
        return 4, "community"

    # ----- size -----

    def weighted_lines(self, files):
        total = 0.0
        for f in files:
            path = f.get("filename") or f.get("path") or ""
            if any(p.search(path) for p in self.ignored_paths):
                continue
            lines = (f.get("additions") or 0) + (f.get("deletions") or 0)
            is_test = "/test/" in path or path.startswith("test/") or path.endswith("_test.dart") \
                or "/integration_test/" in path or "/testing/" in path
            total += lines * (self.cfg["test_file_weight"] if is_test else 1.0)
        return int(round(total))

    def delta_since(self, repo, base, head, pr_paths):
        """Weighted lines changed in the PR's own files between two commits.

        Returns (lines, approximate). Only files that the PR touches are
        counted, so merges from master don't inflate the number. `approximate`
        is True when the old commit is no longer an ancestor (force-push or
        rebase), in which case master changes to those files may be included.
        lines is None if the comparison failed.
        """
        key = (repo, base, head)
        if key not in self.compare_cache:
            try:
                data = gh_json(["api", f"repos/{repo}/compare/{base}...{head}"])
                files = [f for f in (data.get("files") or []) if f.get("filename") in pr_paths]
                self.compare_cache[key] = (self.weighted_lines(files), data.get("status") == "diverged")
            except Exception:
                self.compare_cache[key] = (None, True)
        return self.compare_cache[key]

    def failing_checks(self, last_commit):
        ignored = {c.lower() for c in self.cfg.get("ci_ignored_checks", [])}
        rollup = last_commit.get("statusCheckRollup") or {}
        failing = []
        for c in nodes(rollup, "contexts"):
            name = c.get("name") or c.get("context") or "?"
            result = c.get("conclusion") or c.get("state")
            if result in ("FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE") \
                    and name.lower() not in ignored:
                failing.append(name)
        return sorted(set(failing))

    def effort(self, action, size, delta, files, repo, verdict=None):
        if action in ("QUICK_RELGTM", "QUICK_REPLY", "OWN_LAND", "ISSUE_RESPOND"):
            return EFFORT_QUICK
        if action in LOW_PRIORITY_ACTIONS:
            return EFFORT_FYI
        th = self.th
        # Design docs need careful reading regardless of line count.
        is_doc_repo = repo.endswith("/rfc")
        if action.startswith("FIRST_REVIEW"):
            if action == "FIRST_REVIEW_LARGE" or is_doc_repo:
                return EFFORT_DEEP
            return EFFORT_SHORT if action == "FIRST_REVIEW_SMALL" else EFFORT_MODERATE
        # Follow-ups and re-reviews scale with what changed since your review.
        lines = delta if delta is not None else size
        if verdict == "COMMENTED":
            # You've only left comments, so you likely haven't reviewed the
            # whole PR yet; part of it is effectively a first review.
            lines = max(lines, size // 2)
        if lines <= th["small_weighted_lines"]:
            return EFFORT_SHORT
        if lines >= th["large_weighted_lines"]:
            return EFFORT_DEEP
        return EFFORT_MODERATE

    # ----- classification -----

    def mentions_me(self, body):
        return re.search(rf"@{re.escape(self.me)}\b", body or "", re.IGNORECASE) is not None

    def classify_pr(self, pr):
        repo = pr["repository"]["nameWithOwner"]
        author = login_of(pr)
        labels = [l["name"] for l in nodes(pr, "labels")]
        for issue in nodes(pr, "closingIssuesReferences"):
            labels += [l["name"] for l in nodes(issue, "labels")]
        emails = [((c.get("commit") or {}).get("author") or {}).get("email") for c in nodes(pr, "firstCommits")]
        files = nodes(pr, "files")
        pr_paths = {f["path"] for f in files}
        size = self.weighted_lines(files)
        requested = {((r.get("requestedReviewer") or {}).get("login") or "").lower() for r in nodes(pr, "reviewRequests")}
        assigned = {a["login"].lower() for a in nodes(pr, "assignees")}
        reviews = [r for r in nodes(pr, "reviews") if r.get("submittedAt")]
        comments = nodes(pr, "comments")
        last_commit = (nodes(pr, "commits") or [{}])[0].get("commit") or {}
        failing = self.failing_checks(last_commit)

        item = {
            "kind": "PR", "repo": repo, "number": pr["number"], "title": pr["title"], "url": pr["url"],
            "author": author, "labels": labels, "size": size, "files": pr.get("changedFiles"),
            "additions": pr.get("additions"), "deletions": pr.get("deletions"),
            "review_decision": pr.get("reviewDecision"), "failing_checks": failing, "draft": pr.get("isDraft"),
            "author_association": pr.get("authorAssociation"), "notes": [],
        }
        if failing:
            shown = ", ".join(failing[:3]) + (f" +{len(failing) - 3} more" if len(failing) > 3 else "")
            item["notes"].append(f"CI failing: {shown}")

        # --- Your own PR ---
        if author == self.me:
            item["tier"], item["tier_reason"] = 0, "you"
            if pr.get("isDraft"):
                return None
            my_times = [parse_time(c["createdAt"]) for c in comments if login_of(c) == self.me]
            my_times += [parse_time(r["submittedAt"]) for r in reviews if login_of(r) == self.me]
            my_times.append(parse_time(last_commit.get("committedDate")))
            my_last = max(t for t in my_times if t)
            feedback = [r for r in reviews if login_of(r) != self.me and not self.is_bot(login_of(r))
                        and parse_time(r["submittedAt"]) > my_last and r["state"] in ("CHANGES_REQUESTED", "COMMENTED")]
            feedback += [c for c in comments if login_of(c) != self.me and not self.is_bot(login_of(c))
                         and parse_time(c["createdAt"]) > my_last]
            if feedback:
                first = min(feedback, key=lambda x: x.get("submittedAt") or x.get("createdAt"))
                item["action"] = "OWN_RESPOND"
                item["waiting_since"] = first.get("submittedAt") or first.get("createdAt")
                item["context"] = self.snippet(first, prefix=f"{login_of(first)}: ")
                return self.finish(item)
            if pr.get("reviewDecision") == "APPROVED" and not failing \
                    and "autosubmit" not in [l.lower() for l in labels]:
                approvals = [r for r in reviews if r["state"] == "APPROVED"]
                item["action"] = "OWN_LAND"
                item["waiting_since"] = max(r["submittedAt"] for r in approvals) if approvals else pr["updatedAt"]
                return self.finish(item)
            return None

        item["tier"], item["tier_reason"] = self.tier(author, labels, (pr.get("author") or {}).get("company"), emails)

        mine = [r for r in reviews if login_of(r) == self.me]
        my_comment_times = [parse_time(c["createdAt"]) for c in comments if login_of(c) == self.me]
        my_last_activity = max([parse_time(r["submittedAt"]) for r in mine] + my_comment_times, default=None)

        def after_me(t):
            return my_last_activity is None or parse_time(t) > my_last_activity

        def addressed_to_me(node):
            """True if the comment mentions you, or mentions nobody in particular."""
            mentioned = {m.lower() for m in re.findall(r"@([A-Za-z0-9-]+)", node.get("body") or "")}
            return not mentioned or self.me in mentioned

        others_mentions = [c for c in comments + reviews
                           if login_of(c) != self.me and not self.is_bot(login_of(c))
                           and self.mentions_me(c.get("body")) and after_me(c.get("createdAt") or c.get("submittedAt"))]
        other_reviewers_after_me = any(
            login_of(r) not in (self.me, author) and not self.is_bot(login_of(r)) and after_me(r["submittedAt"])
            for r in reviews)
        author_activity = [c for c in comments if login_of(c) == author and after_me(c["createdAt"])
                           and addressed_to_me(c)]
        # Inline-thread replies show up as author "reviews". If another reviewer
        # has weighed in since you, the replies may well be to them.
        if not other_reviewers_after_me:
            author_activity += [r for r in reviews if login_of(r) == author and after_me(r["submittedAt"])
                                and addressed_to_me(r)]

        approvals_by_others = sorted({login_of(r) for r in reviews if r["state"] == "APPROVED"
                                      and login_of(r) != self.me and not self.is_bot(login_of(r))})
        if approvals_by_others:
            item["notes"].append("approved by " + ", ".join(approvals_by_others))

        # Drafts aren't ready for review; only surface direct questions.
        if pr.get("isDraft"):
            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                days=self.cfg.get("mention_lookback_days", 30))
            recent = [m for m in others_mentions if parse_time(m.get("createdAt") or m.get("submittedAt")) > cutoff]
            if recent:
                item["notes"].append("draft")
                return self.reply(item, recent)
            return None

        is_requested = self.me in requested

        if not mine:
            if is_requested or self.me in assigned:
                if size >= self.th["large_weighted_lines"] or (pr.get("changedFiles") or 0) >= self.th["large_files"]:
                    item["action"] = "FIRST_REVIEW_LARGE"
                elif size <= self.th["small_weighted_lines"]:
                    item["action"] = "FIRST_REVIEW_SMALL"
                else:
                    item["action"] = "FIRST_REVIEW_MEDIUM"
                if approvals_by_others:
                    item["notes"].append("you'd be the second reviewer")
                item["waiting_since"] = self.requested_at(pr) or pr["createdAt"]
                if others_mentions:
                    item["context"] = self.snippet(others_mentions[-1], prefix=f"{login_of(others_mentions[-1])}: ")
                return self.finish(item)
            if others_mentions:
                return self.reply(item, others_mentions)
            return None

        last_review = mine[-1]
        verdicts = [r for r in mine if r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")]
        verdict = verdicts[-1]["state"] if verdicts else "COMMENTED"
        reviewed_oid = (last_review.get("commit") or {}).get("oid")
        head_changed = bool(reviewed_oid) and reviewed_oid != pr["headRefOid"]
        delta, approx = self.delta_since(repo, reviewed_oid, pr["headRefOid"], pr_paths) if head_changed else (0, False)
        item["delta"], item["delta_approx"] = delta, approx
        item["your_last_review"] = f"{verdict.lower().replace('_', ' ')} on {last_review['submittedAt'][:10]}"
        item["verdict"] = verdict
        # New commits that touch the PR's files (not just merges from master).
        code_changed = head_changed and (delta is None or delta > 0)

        ball_in_my_court = is_requested or bool(author_activity)
        waiting_since = min([a.get("createdAt") or a.get("submittedAt") for a in author_activity],
                            default=None) or self.requested_at(pr) or pr["updatedAt"]

        if verdict in ("APPROVED", "DISMISSED"):
            if verdict == "DISMISSED":
                item["notes"].append("your review was dismissed")
            if ball_in_my_court and (code_changed or is_requested or verdict == "DISMISSED"):
                small = delta is not None and delta <= self.th["quick_delta_lines"]
                item["action"] = "QUICK_RELGTM" if small else "RELGTM_BIG_DELTA"
                item["waiting_since"] = waiting_since
                self.add_author_context(item, author_activity)
                return self.finish(item)
            if others_mentions:
                return self.reply(item, others_mentions)
            if verdict == "APPROVED" and code_changed:
                item["action"] = "FYI_CHANGED"
                item["waiting_since"] = pr["updatedAt"]
                return self.finish(item)
            return None

        # You requested changes or left comments.
        if ball_in_my_court or code_changed:
            if not code_changed and not is_requested:
                item["action"] = "QUICK_REPLY"
                item["notes"].append("author replied to your comments, no new commits")
            else:
                item["action"] = "FOLLOWUP_REVIEW"
                if not ball_in_my_court:
                    item["notes"].append("new commits since your review, no explicit ping")
            item["waiting_since"] = waiting_since
            self.add_author_context(item, author_activity)
            return self.finish(item)
        if others_mentions:
            return self.reply(item, others_mentions)
        return None

    def finish(self, item):
        item["effort"] = self.effort(item["action"], item.get("size", 0), item.get("delta"),
                                     item.get("files"), item["repo"], item.get("verdict"))
        if item["kind"] == "PR" and item.get("tier") == 4 and item.get("author_association") == "MEMBER":
            item["possible_googler"] = True
        return item

    def classify_issue(self, issue):
        author = login_of(issue)
        labels = [l["name"] for l in nodes(issue, "labels")]
        assigned = {a["login"].lower() for a in nodes(issue, "assignees")}
        comments = nodes(issue, "comments")
        my_times = [parse_time(c["createdAt"]) for c in comments if login_of(c) == self.me]
        if author == self.me:
            my_times.append(parse_time(issue["createdAt"]))
        my_last = max(my_times, default=None)
        newer = [c for c in comments if login_of(c) != self.me and not self.is_bot(login_of(c))
                 and (my_last is None or parse_time(c["createdAt"]) > my_last)]
        mentions = [c for c in newer if self.mentions_me(c.get("body"))]

        item = {
            "kind": "Issue", "repo": issue["repository"]["nameWithOwner"], "number": issue["number"],
            "title": issue["title"], "url": issue["url"], "author": author, "labels": labels, "notes": [],
        }
        if self.me in assigned:
            item["notes"].append("assigned to you")

        if mentions or (newer and (self.me in assigned or author == self.me)):
            ask = (mentions or newer)[-1]
            asker = login_of(ask)
            item["tier"], item["tier_reason"] = self.tier(asker, labels, (ask.get("author") or {}).get("company"))
            item["action"] = "ISSUE_RESPOND"
            item["waiting_since"] = (mentions or newer)[0]["createdAt"]
            item["context"] = self.snippet(ask, prefix=f"{asker}: ")
            if not mentions:
                item["notes"].append("new comments, no direct mention")
            return self.finish(item)
        if self.me in assigned:
            item["tier"], item["tier_reason"] = self.tier(author, labels, (issue.get("author") or {}).get("company"))
            item["action"] = "ISSUE_ASSIGNED"
            item["waiting_since"] = issue["updatedAt"]
            return self.finish(item)
        return None

    # ----- helpers -----

    def reply(self, item, mentions):
        ask = mentions[-1]
        item["action"] = "QUICK_REPLY"
        item["waiting_since"] = mentions[0].get("createdAt") or mentions[0].get("submittedAt")
        item["context"] = self.snippet(ask, prefix=f"{login_of(ask)}: ")
        return self.finish(item)

    def add_author_context(self, item, author_activity):
        with_body = [a for a in author_activity if (a.get("body") or "").strip()]
        if with_body:
            item["context"] = self.snippet(with_body[-1], prefix="author: ")

    def requested_at(self, pr):
        times = [n["createdAt"] for n in nodes(pr, "timelineItems")
                 if n["__typename"] == "ReviewRequestedEvent"
                 and ((n.get("requestedReviewer") or {}).get("login") or "").lower() == self.me]
        return times[-1] if times else None

    @staticmethod
    def snippet(node, prefix=""):
        body = re.sub(r"<!--.*?-->", "", node.get("body") or "", flags=re.S)
        body = re.sub(r"```.*?```", "[code]", body, flags=re.S)
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) > 180:
            body = body[:177] + "..."
        return {"text": prefix + body, "url": node.get("url")}


def sort_key(item):
    prio = 0
    for l in item.get("labels", []):
        m = re.fullmatch(r"P([0-3])", l)
        if m:
            prio = 4 - int(m.group(1))  # P0 -> 4 ... P3 -> 1
    waiting = parse_time(item.get("waiting_since")) or datetime.datetime.now(datetime.timezone.utc)
    return (item["tier"], ACTION_ORDER.index(item["action"]), -prio, waiting)


def age(ts, now):
    t = parse_time(ts)
    if not t:
        return "?"
    d = now - t
    if d.days >= 1:
        return f"{d.days}d"
    return f"{max(1, d.seconds // 3600)}h"


def md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def describe_size(item):
    if item["kind"] != "PR":
        return ""
    parts = [f"{item['size']} weighted lines / {item.get('files')} files"]
    if "delta" in item and not item["action"].startswith("FIRST_REVIEW"):
        d = item["delta"]
        if d is None:
            parts.append("Δ since your review: unknown")
        else:
            parts.append(f"Δ since your review: {'~' if item.get('delta_approx') else ''}{d} lines")
    return "; ".join(parts)


def render(items, me, now, stats, top_n):
    main = [i for i in items if i["action"] not in LOW_PRIORITY_ACTIONS | OWN_ACTIONS]
    own = [i for i in items if i["action"] in OWN_ACTIONS]
    low = [i for i in items if i["action"] in LOW_PRIORITY_ACTIONS]

    effort_order = [EFFORT_QUICK, EFFORT_SHORT, EFFORT_MODERATE, EFFORT_DEEP]
    counts = {e: sum(1 for i in main if i["effort"] == e) for e in effort_order}

    out = [f"# Attention queue for @{me}", "",
           f"Generated {now.astimezone().strftime('%Y-%m-%d %H:%M %Z')}. "
           f"**{len(main)} items need you**: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v) + ".",
           f"Also {len(own)} of your own PRs need action and {len(low)} FYI items. "
           f"{stats['waiting']} other open items are waiting on someone else and are omitted.", "",
           f"Effort: {EFFORT_LEGEND}. Tiers: Team > Googler > Customer > Community.", ""]

    def row_cells(i):
        ref = f"[{i['repo'].split('/')[-1]}#{i['number']}]({i['url']})"
        item_cell = f"{ref} {md_escape(i['title'])}<br>by @{i['author']}"
        details = [describe_size(i)] if i["kind"] == "PR" else []
        if i.get("your_last_review"):
            details.append("you: " + i["your_last_review"])
        details += i.get("notes", [])
        if i.get("context"):
            c = i["context"]
            details.append(f"[“{md_escape(c['text'])}”]({c['url']})" if c.get("url") else md_escape(c["text"]))
        tier = TIER_NAMES.get(i["tier"], "You")
        if i["tier"] == 3:
            tier += f" ({i['tier_reason']})"
        return tier, item_cell, ACTIONS[i["action"]], i["effort"], age(i.get("waiting_since"), now), \
            "<br>".join(d for d in details if d)

    def table(rows, title, start=1):
        if not rows:
            return
        out.extend([f"## {title}", "",
                    "| # | Tier | Item | Needed from you | Effort | Waiting | Details |",
                    "| --- | --- | --- | --- | --- | --- | --- |"])
        for n, i in enumerate(rows, start):
            out.append("| " + " | ".join([str(n), *row_cells(i)]) + " |")
        out.append("")

    def compact(rows, title, start=1):
        if not rows:
            return
        out.extend([f"## {title}", ""])
        for n, i in enumerate(rows, start):
            tier, _, needed, effort, waiting, _ = row_cells(i)
            out.append(f"{n}. [{i['repo'].split('/')[-1]}#{i['number']}]({i['url']}) {md_escape(i['title'])} "
                       f"(@{i['author']}, {tier}): {effort}, {needed.split(':')[0]}, waiting {waiting}")
        out.append("")

    table(main[:top_n], f"Needs you now (top {min(top_n, len(main))}, ranked)")
    table(own, "Your own PRs")
    compact(main[top_n:], "The rest of your queue (ranked)", start=top_n + 1)
    compact(low, "Low priority / FYI")

    maybe = sorted({i["author"] for i in items if i.get("possible_googler")})
    if maybe:
        out.extend(["## Possible Googlers ranked as Community", "",
                    "These authors are Flutter org members whose GitHub profile doesn't say Google. "
                    "Add Googlers to `googlers` (or others to `not_googlers`) in `config.json` to rank them correctly:",
                    "", ", ".join(f"@{a}" for a in maybe), ""])
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--user", help="GitHub login to build the queue for (default: the authenticated gh user)")
    p.add_argument("--output", "-o", help="Markdown output path (default: outputs/attention_<timestamp>.md). '-' for stdout.")
    p.add_argument("--limit", type=int, help="Max results per search query (overrides config)")
    args = p.parse_args()

    with open(args.config) as f:
        config = json.load(f)
    me = args.user or gh_json(["api", "user"])["login"]
    limit = args.limit or config.get("max_results_per_query", 150)
    since = (datetime.date.today() - datetime.timedelta(days=config.get("mention_lookback_days", 30))).isoformat()

    queries = []
    for org in config["orgs"]:
        scope = f"org:{org} is:open archived:false"
        queries += [
            f"{scope} is:pr user-review-requested:{me}",
            f"{scope} is:pr reviewed-by:{me} -author:{me}",
            f"{scope} is:pr author:{me}",
            f"{scope} assignee:{me}",
            f"{scope} mentions:{me} updated:>={since}",
        ]

    seen = {}
    for q in queries:
        log(f"Searching: {q}")
        for node in search(q, limit):
            url = node.get("url")
            if url and url not in seen and node["repository"]["nameWithOwner"] not in config.get("repos_exclude", []):
                seen[url] = node
    log(f"Classifying {len(seen)} items...")

    ranker = Ranker(me, config)
    items, stats = [], {"waiting": 0}
    for node in seen.values():
        try:
            item = ranker.classify_pr(node) if node["__typename"] == "PullRequest" else ranker.classify_issue(node)
        except Exception as e:  # Keep going; one odd item shouldn't sink the report.
            log(f"Warning: failed to classify {node.get('url')}: {e}")
            continue
        if item:
            items.append(item)
        else:
            stats["waiting"] += 1
    items.sort(key=sort_key)

    now = datetime.datetime.now(datetime.timezone.utc)
    report = render(items, me, now, stats, config.get("top_n", 25))
    if args.output == "-":
        print(report)
    else:
        path = os.path.abspath(args.output) if args.output else os.path.join(
            OUTPUTS_DIR, f"attention_{now.astimezone().strftime('%Y-%m-%d_%H%M')}.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        with open(os.path.splitext(path)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, default=str)
        log(f"Report written to: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
