# Rubric for Selecting Notable Commits

Use the following rubric to select approximately 15–20 notable commits/PRs from the last 7 days across `flutter/flutter`, `flutter/packages`, `flutter/website`, and `dart-lang/site-www`.

## Prioritize
- **Developer-Facing Features**: New widgets, new properties, new tool capabilities, or new features in first-party packages and plugins (`material_ui`, `cupertino_ui`, `go_router`, `pigeon`, `vector_graphics`, `camera`, `shared_preferences`, `webview_flutter`, etc.).
- **Developer Experience Improvements**: Better error messages, more consistent tooling, or improved code generation.
- **Significant Bug Fixes**: Fixes for common crashes, visual glitches, or long-standing issues in the framework, engine, or first-party packages.
- **Platform & Accessibility**: Compatibility with new OS/tool versions (e.g., Xcode) and accessibility improvements.
- **Architectural Significance**: Changes that enable future work or represent a new direction.
- **Documentation & Website Additions (`flutter/website`, `dart-lang/site-www`)**: New guides, tutorials, codelabs, architectural explanations, language/SDK feature documentation, or major improvements to installation and onboarding flows.

## De-prioritize (Generally Exclude)
- **Routine dependency rolls, batch releases, & infrastructure bumps**: Skia, Dart SDK, and `Roll Flutter ...` rolls; automated `[<pkg>] Batch release` and `Sync release-... to main` PRs in `flutter/packages`; website deploy image bumps, cache TTL tweaks, etc.
- **Duplicate cross-repo changes**: Changes cherry-picked or mirrored into both `flutter/flutter` and `flutter/packages` (e.g. during `material_ui`/`cupertino_ui` decoupling)—include at most once.
- **Minor documentation**: Typos, broken link fixes, or formatting changes.
- **CI/testing infrastructure**: Tweaks that don't affect developers (e.g. test-only mock migrations or workflow fixes).
- **Internal code refactoring**: Changes that don't change behavior or API.
- **Scope**: Tool, Web, and platform-specific changes unless they are highly significant.
