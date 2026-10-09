#!/usr/bin/env python3
"""Flags lines in a unified diff that may violate Flutter best practices.

Usage:
  python3 check_best_practices.py <DIFF_FILE | -> [--json]

  # From a PR fetched by fetch_pr_context.py:
  python3 check_best_practices.py tmp/flutter.flutter.12345/pr.diff
  # From a local branch:
  git diff upstream/master...HEAD | python3 check_best_practices.py -

Only added lines (and file-level properties of the diff) are checked. Each
finding names the section of resources/flutter_best_practices.md (or the Flutter
style guide) that it relates to.

These checks are regex heuristics. They produce false positives and miss many
problems. Treat every finding as a prompt to look at the code, never as a
verdict, and do not copy findings into a review without verifying them.
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass

STYLE_GUIDE = "https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md"
TREE_HYGIENE = "https://github.com/flutter/flutter/blob/master/docs/contributing/Tree-hygiene.md"
BP = "flutter_best_practices.md"


@dataclass
class Finding:
    rule: str
    severity: str  # "warning" (likely issue) or "hint" (worth a look)
    path: str
    line: int  # Line number in the new file; 0 for file-level findings.
    code: str
    message: str
    reference: str


@dataclass
class Rule:
    id: str
    pattern: re.Pattern
    scope: str  # "lib", "test", or "any"
    severity: str
    message: str
    reference: str
    exclude: re.Pattern = None


def r(pattern):
    return re.compile(pattern)


LINE_RULES = [
    Rule(
        "pump-and-settle", r(r"\bpumpAndSettle\s*\("), "test", "hint",
        "Prefer pump() with an exact Duration over pumpAndSettle() where practical. "
        "For page transitions, use TransitionDurationObserver.",
        f"{BP}#expose-animation-durations-as-@visiblefortesting,-or-duplicate-them? ; {STYLE_GUIDE}#avoid-using-pumpandsettle",
    ),
    Rule(
        "widget-specific-matcher",
        r(r"\b(findsOneWidget|findsWidgets|findsNWidgets|findsAtLeastNWidgets)\b"), "test", "hint",
        "Prefer generic matchers (findsOne, findsAny, findsExactly, findsAtLeast). Minor.",
        f"{BP}#prefer-generic-matchers-in-tests",
    ),
    Rule(
        "test-semantics", r(r"\bTestSemantics(Root)?\s*\("), "test", "warning",
        "Avoid comparing whole semantics trees with TestSemantics; use "
        "tester.semantics.find + isSemantics for only the relevant nodes.",
        f"{BP}#prefer-tester.semantics.find-when-testing-semantics",
    ),
    Rule(
        "golden-test", r(r"\bmatchesGoldenFile\s*\("), "test", "hint",
        "Golden test added. Could headless checks (paints, getSize, getTopLeft) "
        "cover this instead? Make sure it is not captured mid-animation.",
        f"{BP}#avoid-fragile-golden-tests",
    ),
    Rule(
        "target-platform-variant-all", r(r"TargetPlatformVariant\.all\s*\("), "test", "hint",
        "Only use TargetPlatformVariant.all() when the code under test has "
        "platform-specific behavior; CI already runs tests on all platforms.",
        f"{BP}#which-platforms-to-use-for-targetplatformvariant",
    ),
    Rule(
        "expect-no-error", r(r"expect\(\s*\w*(error|exception|Error|Exception)\w*\s*,\s*isNull\s*\)"),
        "test", "hint",
        "Possible try/catch + expect(error, isNull) pattern. Just call the code and "
        "add a comment; use expect(tester.takeException(), isNull) if needed.",
        f"{BP}#testing-the-absence-of-an-error",
    ),
    Rule(
        "key-in-lib", r(r"\bkey:\s*(const\s+)?(Value|Object|Global)?Key\s*[<(]"), "lib", "hint",
        "Key added in library code. If it exists only so a test can find the "
        "widget, use CommonFinders (descendant, byWidgetPredicate) instead.",
        f"{BP}#avoid-adding-keys-to-the-codebase-solely-for-tests",
    ),
    Rule(
        "to-string-override", r(r"\bString\s+toString\s*\("), "lib", "warning",
        "Prefer mixing in Diagnosticable and overriding debugFillProperties over toString.",
        f"{BP}#prefer-diagnosticable-to-tostring ; {STYLE_GUIDE}#override-tostring",
    ),
    Rule(
        "builder-method", r(r"^\s*Widget\s+_?build[A-Z]\w*\s*\("), "lib", "warning",
        "Helper method returning a Widget. Prefer extracting a separate widget class.",
        f"{BP}#internally,-prefer-a-separate-widget-to-a-builder-method",
    ),
    Rule(
        "widget-type-check",
        r(r"(\bis!?\s+[A-Z]\w*(Widget|Button|Text|Icon|Field|Tile|Bar|Menu)\b|\.runtimeType\s*==)"),
        "lib", "hint",
        "Type check on a widget/object. Special-casing widget types breaks "
        "composability; prefer generic parameters or builders.",
        f"{BP}#everything-is-a-widget",
    ),
    Rule(
        "noop-widget", r(r"return\s+(const\s+)?(Container|SizedBox|Placeholder)\(\s*\)\s*;"), "lib", "hint",
        "To render nothing, return SizedBox.shrink().",
        f"{BP}#noop-widget",
    ),
    Rule(
        "paint-mutation",
        r(r"^\s*\w*[pP]aint\.(color|style|strokeWidth|shader|blendMode|strokeCap|maskFilter)\s*="),
        "lib", "hint",
        "Possible mutation of an existing Paint between draw calls. Create a new "
        "Paint for each differently styled draw call.",
        f"{BP}#don’t-mutate-paint-instances",
    ),
    Rule(
        "theme-platform", r(r"Theme\.of\([^)]*\)\.platform\b"), "lib", "hint",
        "ThemeData.platform is for visuals/styling. Use defaultTargetPlatform for "
        "behavior (gestures, a11y, text editing, system UI, platform channels).",
        f"{BP}#themedata.platform-vs.-defaulttargetplatform",
    ),
    Rule(
        "desktop-platform-gate",
        r(r"TargetPlatform\.(macOS|windows|linux)\b"), "lib", "hint",
        "Platform check involving desktop platforms. If this gates a mouse/keyboard/"
        "touch feature, decide based on input type instead of platform.",
        f"{BP}#mouse-on-mobile-and-touch-on-desktop",
    ),
    Rule(
        "inherited-model", r(r"\bextends\s+InheritedModel\b"), "lib", "hint",
        "InheritedModel adds overhead; use it only when there's a clear performance benefit.",
        f"{BP}#inheritedwidgets",
    ),
    Rule(
        "visible-for-testing", r(r"@visibleForTesting\b"), "lib", "hint",
        "Avoid @visibleForTesting except as a temporary soft-release mechanism.",
        f"{BP}#soft-release ; {STYLE_GUIDE}#avoid-using-visiblefortesting",
    ),
    Rule(
        "print-in-lib", r(r"^\s*(print|debugPrint)\s*\("), "lib", "warning",
        "Only log actionable messages to the console.",
        f"{STYLE_GUIDE}#only-log-actionable-messages-to-the-console",
    ),
    Rule(
        "todo-without-issue", r(r"//\s*TODO"), "any", "hint",
        "Flutter TODOs should be of the form `// TODO(username): ... <issue URL>`.",
        f"{STYLE_GUIDE}#comments",
        exclude=r(r"//\s*TODO\(\w[\w-]*\):.*https?://github\.com/\S+/issues/\d+"),
    ),
    Rule(
        "ignore-lint", r(r"//\s*ignore(_for_file)?\s*:"), "any", "hint",
        "Lint suppression added; confirm it's justified and has an explanation.",
        STYLE_GUIDE,
    ),
    Rule(
        "multi-param-builder-typedef",
        r(r"^\s*typedef\s+\w+(<[^>]*>)?\s*=\s*[\w<>?]+\s+Function\s*\([^,)]*,[^,)]*,"), "lib", "hint",
        "Callback typedef with 3+ positional parameters. Adding a parameter later is "
        "breaking; consider passing a single final data class instead.",
        f"{BP}#write-apis-that-discourage-breaking-changes",
    ),
]

LIFECYCLE_RE = r(r"\bvoid\s+(initState|didUpdateWidget|didChangeDependencies)\s*\(")
METHOD_RE = r(r"^\s*(@override\s*)?[\w<>?, ]+\s+\w+\s*\([^;]*\)\s*(async\s*)?\{?\s*$")
OF_RE = r(r"\bstatic\s+[\w<>?]+\s+of\s*\(\s*BuildContext\b")
MAYBE_OF_RE = r(r"\bstatic\s+[\w<>?]+\s+maybeOf\s*\(\s*BuildContext\b")
PUBLIC_DECL_RE = r(
    r"^(abstract\s+|base\s+|final\s+|interface\s+|sealed\s+|mixin\s+)*"
    r"(class|enum|mixin|typedef|extension(\s+type)?)\s+[A-Z]\w*"
)
CLASS_DECL_RE = r(r"^(?P<mods>(abstract\s+|base\s+|final\s+|interface\s+|sealed\s+|mixin\s+)*)class\s+(?P<name>[A-Z]\w*)(?P<rest>.*)")
WIDGET_SUPER_RE = r(r"\bextends\s+(State<|\w*Widget\b|\w*RenderObject\w*\b|ChangeNotifier\b|\w*Delegate\b|\w*Painter\b|ThemeExtension\b)")
IMPORT_RE = r(r"^\s*import\s+['\"]package:flutter/(material|cupertino|widgets)\.dart['\"]")


def classify(path):
    """Returns (scope, library) for a path, e.g. ("test", "widgets")."""
    if not path.endswith(".dart"):
        return None, None
    scope = "test" if re.search(r"(^|/)(test|integration_test|test_driver)/", path) or path.endswith("_test.dart") else "lib"
    if re.search(r"(^|/)(example|dev|tool|bin)/", path) and scope == "lib":
        scope = "other"
    lib = None
    m = re.search(r"/(?:lib/src|test)/(material|cupertino|widgets|rendering|painting|services|foundation|gestures|semantics|animation|scheduler|physics)/", path)
    if m:
        lib = m.group(1)
    return scope, lib


def parse_diff(text):
    """Yields dicts: {path, added: [(line_no, text)], hunks: [[(kind, line_no, text)]], status}."""
    files = []
    current = None
    new_line = 0
    hunk = None
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            current = {"path": None, "added": [], "hunks": [], "status": "modified"}
            files.append(current)
            hunk = None
            continue
        if current is None:
            continue
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            if target == "/dev/null":
                current["status"] = "removed"
            else:
                current["path"] = target[2:] if target.startswith("b/") else target
            continue
        if raw.startswith("--- "):
            if raw[4:].strip() == "/dev/null":
                current["status"] = "added"
            continue
        if raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            new_line = int(m.group(1)) if m else 0
            hunk = []
            current["hunks"].append(hunk)
            continue
        if hunk is None:
            continue
        if raw.startswith("+"):
            current["added"].append((new_line, raw[1:]))
            hunk.append(("+", new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            hunk.append(("-", None, raw[1:]))
        elif raw.startswith("\\"):
            continue
        else:
            hunk.append((" ", new_line, raw[1:] if raw else ""))
            new_line += 1
    return [f for f in files if f["path"]]


def check_lines(f, scope, findings):
    for line_no, code in f["added"]:
        stripped = code.strip()
        is_comment = stripped.startswith("//")
        for rule in LINE_RULES:
            if rule.scope != "any" and rule.scope != scope:
                continue
            if is_comment and rule.id not in ("todo-without-issue", "ignore-lint"):
                continue
            if rule.pattern.search(code) and not (rule.exclude and rule.exclude.search(code)):
                findings.append(Finding(rule.id, rule.severity, f["path"], line_no, stripped, rule.message, rule.reference))


def check_lifecycle_asserts(f, findings):
    for hunk in f["hunks"]:
        in_lifecycle = False
        for kind, line_no, code in hunk:
            if kind == "-":
                continue
            if LIFECYCLE_RE.search(code):
                in_lifecycle = True
            elif METHOD_RE.match(code) and "assert" not in code:
                in_lifecycle = False
            if kind == "+" and in_lifecycle and re.search(r"\bassert\s*\(", code):
                findings.append(Finding(
                    "assert-in-lifecycle", "warning", f["path"], line_no, code.strip(),
                    "Assertion in initState/didUpdateWidget/didChangeDependencies can cause "
                    "leaks (flutter#157470). Prefer asserting invariants in the constructor.",
                    f"{BP}#prefer-asserting-widget-invariants-in-their-constructor",
                ))


def check_declarations(f, findings):
    added = f["added"]
    added_map = dict(added)
    added_text = "\n".join(code for _, code in added)
    # .of without .maybeOf.
    if OF_RE.search(added_text) and not MAYBE_OF_RE.search(added_text):
        line_no = next(n for n, c in added if OF_RE.search(c))
        findings.append(Finding(
            "of-without-maybe-of", "hint", f["path"], line_no, added_map[line_no].strip(),
            "New static `of` without a `maybeOf`. Prefer adding `maybeOf` (and `of` only if "
            "needed), and make both register a dependency on the BuildContext.",
            f"{BP}#inheritedwidgets",
        ))
    # Public top-level declarations: docs and class modifiers.
    context_lines = {}
    for hunk in f["hunks"]:
        prev = []
        for kind, line_no, code in hunk:
            if kind == "-":
                continue
            if kind == "+" and PUBLIC_DECL_RE.match(code):
                context_lines[line_no] = list(prev)
            prev.append(code.strip())
    for line_no, prev in context_lines.items():
        code = added_map[line_no]
        # Walk back over annotations to find a doc comment.
        documented = False
        for p in reversed(prev):
            if p.startswith("@"):
                continue
            documented = p.startswith("///") or p.startswith("*/")
            break
        if not documented:
            findings.append(Finding(
                "undocumented-public-api", "warning", f["path"], line_no, code.strip(),
                "Public declaration without a /// doc comment. All public APIs need dartdocs.",
                f"{STYLE_GUIDE}#documentation-dartdocs-javadocs-etc",
            ))
        m = CLASS_DECL_RE.match(code)
        if m and not m.group("mods").strip() and not WIDGET_SUPER_RE.search(m.group("rest")):
            findings.append(Finding(
                "class-modifiers", "hint", f["path"], line_no, code.strip(),
                "New public class without a class modifier. Consider final/base/interface "
                "to prevent `implements`/`extends` uses that would make future changes breaking.",
                f"{BP}#write-apis-that-discourage-breaking-changes",
            ))


def check_imports(f, scope, lib, findings):
    if lib is None or lib == "material":
        return
    for line_no, code in f["added"]:
        m = IMPORT_RE.match(code)
        if not m:
            continue
        imported = m.group(1)
        # material may import cupertino; nothing else may import a design library
        # that isn't its own.
        if imported in ("material", "cupertino") and imported != lib:
            findings.append(Finding(
                "cross-library-import", "warning", f["path"], line_no, code.strip(),
                f"{scope} code in the {lib} library imports {imported}. Keep code and tests in "
                "their own library; tests spanning design libraries belong in material.",
                f"{BP}#organize-tests-by-library ; {BP}#sharing-code-between-material-and-cupertino",
            ))


def check_file_level(files, findings):
    lib_changed = [f["path"] for f in files if classify(f["path"])[0] == "lib" and f["added"]]
    test_changed = [f["path"] for f in files if classify(f["path"])[0] == "test"]
    if lib_changed and not test_changed:
        findings.append(Finding(
            "no-tests", "warning", lib_changed[0], 0, "",
            f"{len(lib_changed)} library file(s) changed but no test files changed. Check whether "
            "the PR qualifies for a test exemption (e.g. export-only changes) per Tree Hygiene.",
            f"{BP}#test-exemptions ; {TREE_HYGIENE}#tests",
        ))


def run(diff_text):
    files = parse_diff(diff_text)
    findings = []
    for f in files:
        if f["status"] == "removed":
            continue
        scope, lib = classify(f["path"])
        if scope is None:
            continue
        if scope in ("lib", "test"):
            check_lines(f, scope, findings)
            check_imports(f, scope, lib, findings)
        if scope == "lib":
            check_lifecycle_asserts(f, findings)
            check_declarations(f, findings)
    check_file_level(files, findings)
    return files, findings


def format_markdown(files, findings):
    out = [f"# Best-practice heuristic findings", ""]
    out.append(
        f"Scanned {len(files)} file(s); {len(findings)} finding(s). These are regex heuristics: "
        "verify each one against the code before mentioning it in a review."
    )
    out.append("")
    if not findings:
        out.append("_No findings._")
    by_path = {}
    for fd in findings:
        by_path.setdefault(fd.path, []).append(fd)
    for path, items in by_path.items():
        out.append(f"## `{path}`")
        out.append("")
        for fd in sorted(items, key=lambda x: x.line):
            loc = f"L{fd.line}" if fd.line else "file"
            out.append(f"- **{fd.severity}** `{fd.rule}` ({loc}): {fd.message}")
            if fd.code:
                out.append(f"  - Code: `{fd.code[:160]}`")
            out.append(f"  - Ref: {fd.reference}")
        out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("diff", help="Path to a unified diff, or - for stdin.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    args = parser.parse_args()
    text = sys.stdin.read() if args.diff == "-" else open(args.diff).read()
    files, findings = run(text)
    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print(format_markdown(files, findings))


if __name__ == "__main__":
    main()
