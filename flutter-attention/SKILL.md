---
name: flutter-attention
description: Generate a prioritized list of the GitHub PRs and issues that need the user's attention right now, ranked by who is waiting (team, then Googlers, then customers, then everyone else) and labeled with exactly what is needed (quick re-LGTM, reply, follow-up review, or a deep first review of a large PR). Use when the user asks what to review next, what needs their attention, or for their review queue.
---

# Flutter Attention Queue

This skill produces a ranked to-do list of the PRs and issues in the Flutter
GitHub org that are currently waiting on the user. Each entry says **what is
needed** and **how much effort** it takes, so the user can tell a 2-minute
re-LGTM from a PR that needs a long, careful first review.

Never post comments, approve, or otherwise act on GitHub. Only write the report.

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`).
- Python 3 (standard library only).

## Configuration

[config.json](config.json) controls who gets priority and how sizes are judged:

| Key | Meaning |
| --- | --- |
| `team` | GitHub logins on the user's team. Highest priority. |
| `googlers` / `not_googlers` | Manual overrides for Googler detection. |
| `orgs`, `repos_exclude` | Where to search. |
| `customer_label_prefix`, `customer_labels_ignored` | Items (or a PR's linked issues) with a `customer: …` label count as customer items. `customer: crowd` is ignored by default. |
| `bots` | Accounts whose comments and reviews are ignored. |
| `size_thresholds` | Weighted-line cutoffs for small/large first reviews and for "quick" re-LGTMs. |
| `test_file_weight` | How much test lines count relative to lib lines (default 0.3). |
| `ignored_path_patterns` | Files that don't count toward size (goldens, generated code). |
| `ci_ignored_checks` | Check names that don't count as CI failures (e.g. `tree-status`). |
| `mention_lookback_days` | How far back to search for mentions; also the cutoff for mentions on drafts. |
| `top_n` | How many items get the detailed table; the rest are a compact list. |

If the user asks to change priorities (e.g. add a teammate), edit
`config.json` rather than the script.

## Workflow

### 1. Run the script

Run from any directory:

```bash
python3 <skill_dir>/scripts/attention_queue.py
```

Flags: `--user <login>` (default: the authenticated `gh` user), `--limit N`
(max results per search query), `--config <path>`, `-o <path>` (`-` for
stdout). It takes about 1–3 minutes.

The script writes `outputs/attention_<YYYY-MM-DD_HHMM>.md` and a matching
`.json` in this skill's directory (the `outputs/` directory is gitignored).

### 2. How the script decides

**Candidates**: open PRs and issues in the configured orgs where the user's
review is directly requested, that the user has reviewed, that the user
authored, that are assigned to the user, or that mention the user (last 30
days).

**What's needed** (from the user's perspective, based on their last review
and on activity since then):

| Action | When |
| --- | --- |
| Re-LGTM | User approved (or their approval was dismissed), then the author pushed a small change (≤ `quick_delta_lines`) and re-requested review or commented. |
| Reply | Someone @mentioned the user after their last activity, or the author replied to the user's comments without pushing code. |
| Land it | User's own PR is approved and CI is green. |
| Respond on issue | New comments on an issue the user is assigned to, filed, or was mentioned in. |
| Address feedback | User's own PR got new reviews or comments. |
| Re-review after big change | User approved, but much changed since. |
| Follow-up review | User requested changes or commented, and the author pushed, commented, or re-requested review. |
| First review (small / medium / large) | Review requested or assigned, user hasn't reviewed yet. |
| FYI | Changed since the user's LGTM with nobody asking, or assigned with no activity. |

**Effort** is computed per item:

| Effort | Meaning | Typical items |
| --- | --- | --- |
| ⚡ Quick | < 10 min | Re-LGTM, reply, land it, respond on issue |
| 🟢 Short | 10–30 min | Small first review; follow-up where little changed |
| 🔍 Moderate | 30–60 min | Medium first review; follow-up with a moderate delta |
| 🏋️ Deep | 1 h+ | Large first review, any RFC/design doc first review, or a follow-up where ≥ `large_weighted_lines` changed |

Sizes are "weighted lines": additions + deletions, with test files at
`test_file_weight` and generated files/goldens ignored. The delta since the
user's last review only counts the PR's own files, so merges from master don't
inflate it (shown as `~N` when a force-push made it approximate). If the user
has only ever left comments (never approved or requested changes), effort
also accounts for half the PR's size, since they likely haven't reviewed all of it.

Author comments that @mention other people but not the user don't put the
ball in the user's court. Drafts only appear if someone mentioned the user in
the last `mention_lookback_days`. CI failures list check names, ignoring
`ci_ignored_checks` (e.g. `tree-status`).

Items where the ball is in someone else's court (waiting on the author, CI, or
another reviewer) are omitted and only counted.

**Ranking**: tier first (Team > Googler > Customer > Community), then the
action order above (quick unblocks first), then `P0`–`P3` labels, then longest
waiting. The top `top_n` items get a detailed table; the rest are a compact
ranked list. The user's own PRs and FYI items get separate sections.

**Tiers**: Team = login in `team`. Googler = in `googlers`, GitHub profile
company contains "Google", or a commit email is `@google.com`. Customer =
item or linked issue has a `customer: …` label. Everyone else is Community.
For issue responses, the tier is that of the person waiting for the answer.
Flutter org members ranked as Community are listed at the end of the report
as possible Googlers, because many Googlers don't list Google on their GitHub
profile.

### 3. Refine the top of the list

The script's heuristics are imperfect. For the top ~10 items in "Needs you
now", verify before presenting:

1. **Read the latest relevant comment** (linked in the Details column) and
   restate the concrete ask in a few words, e.g. "asks whether to deprecate
   `foo` or remove it".
2. **Check large first reviews** for whether the size is real: mostly
   generated files, goldens, or mechanical renames can drop it to Moderate.
   New public API or a design change should stay Deep even if small.
3. **Check re-LGTMs** where Δ is "unknown (force-pushed?)": look at the
   commits since the user's review with `gh pr view <n> --repo <repo> --json commits`
   or the PR's "Changes since your last review" view, and reclassify.
4. **Confirm tiers**: if the report lists "Possible Googlers ranked as
   Community", ask the user which of them are Googlers and add them to
   `googlers` (or `not_googlers`) in `config.json`, then re-run.

Edit the Markdown report in place with the corrections.

### 4. Present the result

Tell the user where the report is. Then give a short summary: how many quick
items they can clear right now (list them), and the one or two deep reviews
they should block out time for. Point out anything that seems urgent
regardless of tier (P0, release blockers, a teammate blocked for a long time).

## Known limitations

- `user-review-requested` only covers direct requests, not team requests.
- GitHub removes the review request once you review, so a re-review is only
  detected if the author re-requests, comments, or pushes after your review.
- Googler detection depends on public profile data and commit emails, so some
  Googlers will be ranked as Community until added to `googlers`.
- Δ since your review is unknown after a force-push or rebase.
- Inline review-thread replies are only seen when they're part of a review
  submission; single-comment replies inside threads may be missed.
