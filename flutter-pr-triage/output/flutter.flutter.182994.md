# PR Triage Report: Fix modal barrier tap passthrough during iOS back swipe (#182994)

- **URL**: https://github.com/flutter/flutter/pull/182994
- **Author**: [AlexanderLek](https://github.com/AlexanderLek)
- **State**: OPEN
- **Created At**: 2026-02-27 08:31:38 UTC
- **Last Activity**: 2026-06-30 22:13:43 UTC (13 days, 23 hours ago)
- **Triage Status**: 🟡 Waiting on Review

## Description

### Description

When a page is dismissed via iOS swipe-back gesture, the `ModalBarrier` of that page was ignoring pointer events (via `IgnorePointer`) because the animation status becomes `reverse`.
This caused touch events to fall through to barriers of routes beneath (e.g. `ModalBottomSheet`), unexpectedly dismissing them.

### Root cause

`_buildModalBarrier()` in `ModalRoute` wraps the barrier with:
```
// Before (buggy)
IgnorePointer(
  ignoring: !animation!.isForwardOrCompleted, // true when reverse OR dismissed
  child: barrier,
)
```
During an iOS swipe-back, animation.status == reverse, so the barrier ignores all touches — allowing them to reach barriers below.

### Fix

Replace the static IgnorePointer with a ValueListenableBuilder that reacts to NavigatorState.userGestureInProgressNotifier:
```
// After (fixed)
ignoring: animation!.isDismissed || (!animation!.isForwardOrCompleted && !gestureInProgress),
```
The barrier now stays active when reverse +

... (truncated)

## Files Changed

Total files changed: 2

- `packages/flutter/lib/src/widgets/routes.dart` (+24/-4)
- `packages/flutter/test/widgets/modal_barrier_test.dart` (+94/-0)

## Reviews & Comments

**Requested Reviewers**: justinmc

No reviews submitted yet.

**Recent Comments**:
- **AlexanderLek**: > Hey @AlexanderLek would you like to continue working on this?

Yes, I'll keep working on it. Will follow up once I've made progress. Thanks!
- **AlexanderLek**: Pushed the dart format fix — analyze shard is now green. PTAL @justinmc, thanks!
- **justinmc**: Sorry I've been busy with decoupling, but this PR is in my queue.

## Next Steps

👉 **Action**: Assign reviewers or nudge existing reviewers.
