Created 2025.03.14 π by [Justin McCandless](mailto:jmccandless@google.com)

Last Modified 2026.06

[go/flutter-framework-best-practices](http://goto.google.com/flutter-framework-best-practices)

&nbsp;

This document lists a few best practices for cases that have come up commonly while developing the framework. The purpose is to remember and learn from our past decisions.

&nbsp;

Disagree with something here? Leave a comment or suggestion. Nothing here is final.

&nbsp;

Want to add something to this doc? Go for it\! All framework team members should have edit access. You do not need general team buy-in to add something here. If you can, link to at least one example of your best practice from the codebase or a PR.

&nbsp;

Most importantly, follow [Flutter’s style guide](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md).

&nbsp;

## Contents {#contents}

[Contents](#contents)

[Everything is a widget](#everything-is-a-widget)

[Internally, prefer a separate widget to a builder method](#internally,-prefer-a-separate-widget-to-a-builder-method)

[Recovering from errors](#recovering-from-errors)

[Prefer declarative APIs to imperative APIs](#prefer-declarative-apis-to-imperative-apis)

[Write APIs that discourage breaking changes](#write-apis-that-discourage-breaking-changes)

[Noop widget](#noop-widget)

[Soft release](#soft-release)

[For a feature that’s part of an existing class](#for-a-feature-that’s-part-of-an-existing-class)

[For a new top-level class/widget](#for-a-new-top-level-class/widget)

[Feature flags](#feature-flags)

[Passed-through default parameters](#passed-through-default-parameters)

[ThemeData.platform vs. defaultTargetPlatform](#themedata.platform-vs.-defaulttargetplatform)

[Don’t write assertions that can’t be triggered](#don’t-write-assertions-that-can’t-be-triggered)

[The sentinel pattern \- was the default value given or was the parameter omitted?](#the-sentinel-pattern---was-the-default-value-given-or-was-the-parameter-omitted?)

[Naming \- Use a positional parameter to avoid repetition](#naming---use-a-positional-parameter-to-avoid-repetition)

[Prefer Diagnosticable to toString](#prefer-diagnosticable-to-tostring)

[Sharing code between Material and Cupertino](#sharing-code-between-material-and-cupertino)

[Naming: RawMyWidget / MyWidget / CupertinoMyWidget](#naming:-rawmywidget-/-mywidget-/-cupertinomywidget)

[Should Flutter include features that are not in the Material spec?](#should-flutter-include-features-that-are-not-in-the-material-spec?)

[Cross-platform APIs](#cross-platform-apis)

[InheritedWidgets](#inheritedwidgets)

[Mouse on mobile and touch on desktop](#mouse-on-mobile-and-touch-on-desktop)

[Don’t mutate Paint instances](#don’t-mutate-paint-instances)

[Handling different versions of native platforms](#handling-different-versions-of-native-platforms)

[Avoid descriptions of platform level behavior if possible without surprising the user](#avoid-descriptions-of-platform-level-behavior-if-possible-without-surprising-the-user)

[Avoid platform UI where practical](#avoid-platform-ui-where-practical)

[Put system UI in the Widgets library where possible](#put-system-ui-in-the-widgets-library-where-possible)

[Prefer asserting widget invariants in their constructor](#prefer-asserting-widget-invariants-in-their-constructor)

[Testing](#testing)

[Avoid fragile golden tests](#avoid-fragile-golden-tests)

[Expose animation durations as @visibleForTesting, or duplicate them?](#expose-animation-durations-as-@visiblefortesting,-or-duplicate-them?)

[Which platforms to use for TargetPlatformVariant](#which-platforms-to-use-for-targetplatformvariant)

[Testing the absence of an error](#testing-the-absence-of-an-error)

[Avoid adding Keys to the codebase solely for tests](#avoid-adding-keys-to-the-codebase-solely-for-tests)

[Test exemptions](#test-exemptions)

[Prefer generic matchers in tests](#prefer-generic-matchers-in-tests)

[Organize tests by library](#organize-tests-by-library)

[Prefer tester.semantics.find when testing semantics](#prefer-tester.semantics.find-when-testing-semantics)

&nbsp;

## Everything is a widget {#everything-is-a-widget}

Prefer to use generic widgets without specialization wherever possible.

&nbsp;

Don’t type check widgets and have special behavior depending on the type of widget passed. This goes against Flutter’s generic composability.

&nbsp;

Write widgets that take generic WidgetBuilder parameters where possible.

&nbsp;

* Text selection context menus used to be implemented as a specialized class with specific configuration that builds the menu as a widget. This was inflexible and hard to maintain. Later it was ported to be a simple WidgetBuilder parameter, where developers can pass whatever widget they want.  
  * [https\://main-api.flutter.dev/flutter/widgets/EditableText/contextMenuBuilder.html](https://main-api.flutter.dev/flutter/widgets/EditableText/contextMenuBuilder.html)  
* RawRadio has no UI of its own and leaves that up to the user. Radio and CupertinoRadio implement their UIs using CustomPainters. Instead of forcing all users to pass in a CustomPainter to draw their UI, we decided to just take a generic WidgetBuilder that can return a CustomPaint if needed.  
  * [https\://github.com/flutter/flutter/pull/167764\#pullrequestreview-2794691751](https://github.com/flutter/flutter/pull/167764#pullrequestreview-2794691751)

## Internally, prefer a separate widget to a builder method {#internally,-prefer-a-separate-widget-to-a-builder-method}

When abstracting out part of a `build` method, create a separate widget instead of a method on the existing widget. It might be tempting to create a method that just returns a widget subtree, but a separate widget is more performant and less error prone.

&nbsp;

Resources:

* [Widgets vs helper methods | Decoding Flutter](https://www.youtube.com/watch?v=IOyq-eTRhvo)

## Recovering from errors {#recovering-from-errors}

For calls that can throw errors, if it’s not reasonable for the app to crash in that situation, consider catching and reporting the error to FlutterError.

&nbsp;

```java
try {
  await myPlatformChannelMethod();
} catch (error, stacktrace) {
  FlutterError.reportError(
    FlutterErrorDetails(
      exception: error,
      library: 'widget library',
      stack: stacktrace,
    ),
  );
}
```

&nbsp;

Don’t forget to follow the style guide and [only log actionable errors](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md#only-log-actionable-messages-to-the-console).

&nbsp;

* This came up [in the Sensitive Content project](https://github.com/flutter/flutter/pull/158473/files#r1996251362).&nbsp;

## Prefer declarative APIs to imperative APIs {#prefer-declarative-apis-to-imperative-apis}

When the developer wants to change the state of a widget, the typical pattern should be to call `setState` and change the value of some state variable. This is preferable to directly calling a method to make a change.

&nbsp;

For example, controller parameters should be avoided. Instead, take the state as a parameter and allow users to modify it and rebuild, if possible.

&nbsp;

This typically results in generic, Fluttery architecture that works well with Flutter’s composition pattern.

&nbsp;

* Example where Flutter does not follow this guideline:  
  * [TextEditingController](https://main-api.flutter.dev/flutter/widgets/TextEditingController-class.html)  
    * An issue was opened discussing this:  
      * [https\://github.com/flutter/flutter/issues/167983](https://github.com/flutter/flutter/issues/167983)  
* This came up while implementing RadioGroup:  
  * [https\://github.com/flutter/flutter/pull/167363\#pullrequestreview-2779586234](https://github.com/flutter/flutter/pull/167363#pullrequestreview-2779586234)  
* Somewhat related: naming of `value` vs. `initialValue` parameters:  
  * [https\://github.com/flutter/flutter/pull/170805](https://github.com/flutter/flutter/pull/170805)

&nbsp;

## Write APIs that discourage breaking changes {#write-apis-that-discourage-breaking-changes}

Breaking changes require significant engineering effort to deal with, and they also cause disruption in Flutter’s ecosystem. Write APIs that prevent or discourage usages that could break in the future.

&nbsp;

* Write multiple small, narrowly focused APIs instead of one that does everything. An API that does everything is more likely to need to change in the future.  
* Use Dart’s detailed [class modifiers](https://dart.dev/language/class-modifiers) to disallow unintended uses of your classes. A class that is `implement`ed can never be changed without a breakage.  
* If the argument list is subject to addition in the future \- for example, a builder callback that receives contextual information that might be useful \- then it's highly recommended to use a data class as the argument instead, because adding properties to a `final` class isn't breaking, unlike adding a parameter to a function.

&nbsp;

```js
// BAD: Adding more parameters to a function is breaking.

typedef DialogContentBuilder =
Widget Function(BuildContext context, double position, Widget child);


// Good: Adding more properties to a final class isn't breaking.

@immutable
final class DialogContentContext(
  final BuildContext context,
  final double position,
  final Widget child,
);

typedef DialogContentBuilder = Widget Function(DialogContentContext context);
```

&nbsp;

&nbsp;

Other resources:

* A design doc written after changes to TextInputClient broken super\_editor:  
  * [Minimizing Breaking Changes from Plaform APIs (PUBLICLY SHARED)](https://docs.google.com/document/d/1OxDsf_eot7TlsRn57z-1_dGbvuqnMxO7QEGIAmOCZtA/edit?tab=t.0)  
* A post-decoupling PR where an implemented class could not be changed:  
  * [https\://github.com/flutter/flutter/pull/185152\#pullrequestreview-4717651397](https://github.com/flutter/flutter/pull/185152#pullrequestreview-4717651397)  
* A PR where we decided to add `base` to new RenderObject classes in order to prevent users from using `implements` with them.  
  * [https\://github.com/flutter/flutter/pull/179003\#discussion\_r3737876992](https://github.com/flutter/flutter/pull/179003#discussion_r3737876992)

&nbsp;

## Noop widget {#noop-widget}

Most `build` methods require a widget to be returned, not null, so what should you return if you’d prefer not to render anything?

&nbsp;

```java
return SizedBox.shrink();
```

&nbsp;

* A community member proposed allowing `null` for this scenario:  
  * [https\://github.com/flutter/flutter/issues/165566](https://github.com/flutter/flutter/issues/165566)

## Soft release {#soft-release}

What if you want to merge a PR, but you don’t want the community to immediately jump in and start using the code you’re shipping until after you’ve shipped something else?

### For a feature that’s part of an existing class {#for-a-feature-that’s-part-of-an-existing-class}

Turn it off by default. If it’s controlled by a parameter, make that parameter default to the original behavior instead of the new behavior. When the feature is ready, open a new PR that changes the default of the parameter to be on by default.

&nbsp;

Secure paste followed this pattern when introducing the native iOS context menu ([PR1](https://github.com/flutter/flutter/pull/143002), [PR2](https://github.com/flutter/flutter/pull/159013), then turned on by default).

### For a new top-level class/widget {#for-a-new-top-level-class/widget}

What if it’s a top-level symbol and can’t be turned on/off by default?

&nbsp;

1. Flag the API whose use you want to discourage as `@visibleForTesting`.  
2. Do not export the relevant file(s) from the library. For example, don’t add an entry for the file in [widgets.dart](https://github.com/flutter/flutter/blob/master/packages/flutter/lib/widgets.dart).  
3. Explain the situation in the dartdocs for the relevant API.

&nbsp;

Only do this temporarily, when the permanent solution is coming soon, and then promptly undo the three steps above. See “[avoid using visibleForTesting](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md#avoid-using-visiblefortesting)” in the styleguide.

&nbsp;

Other resources:

* This came up in the Sensitive Content project [in this issue](https://github.com/flutter/flutter/issues/164820#issuecomment-2725474314).  
* Work is ongoing on possibly implementing a full feature flag system in Flutter.  
  * [https\://github.com/flutter/flutter/issues/167668](https://github.com/flutter/flutter/issues/167668)

### Feature flags {#feature-flags}

The framework supports feature flags for the development of large, experimental features. A feature flag is enabled or disabled at compile time and allows the framework’s code to reference it as a boolean.

&nbsp;

APIs that are gated behind a feature flag are expected to break at any time and are not subject to Flutter’s usual breaking change process. They may be changed or removed without warning.

&nbsp;

Consider using a feature flag if:

* Using a feature flag would considerably speed up development time, such as by avoiding landing a big change in a single PR, or avoiding working on a separate fork of flutter/flutter.  
* Your API is experimental and will undergo breaking changes.  
* Your feature is very large, needs to be implemented over multiple PRs, and it is dangerous to expose it to users in an unfinished state.

&nbsp;

Turn on a feature flag with `flutter config –enable-<your feature flag>`.

&nbsp;

Use a feature flag at runtime with `debugEnabledFeatureFlags.contains('<your feature flag>');`.

&nbsp;

Other resources:

* [Multi-window experimental APIs (PUBLICLY SHARED)](https://docs.google.com/document/d/1Muakcdx8Ktg72G5GiieRP-9swxl_5Uum1oEI89aBLSM/edit?tab=t.0)  
* [Notes - Flutter feature flags](https://docs.google.com/document/d/1TjH-oeYRhTR-4he1DKuMJ9vp1PuVXST_89SbnyqXxnA/edit?resourcekey=0-ce41SMJuppdw9x7dgVHv-w&tab=t.0#heading=h.c1twz6bxb1lx)  
* [Loïc Sharma](mailto:loicsharma@google.com)’s PR for feature flag support:  
  * [https\://github.com/flutter/flutter/pull/168437](https://github.com/flutter/flutter/pull/168437)  
* [mattkae](https://github.com/mattkae)’s PR adding the “windowing” feature flag for multiwindow:  
  * [https\://github.com/flutter/flutter/pull/172478](https://github.com/flutter/flutter/pull/172478)  
* Other possible uses of feature flags:  
  * flutter\_gpu

## Passed-through default parameters {#passed-through-default-parameters}

In Flutter’s composition pattern, we often have the case where a parent widget takes a parameter that is passed through verbatim to a child widget. Where should the default value of the parameter be set?

&nbsp;

Set the same default value everywhere. In the docs, explicitly mention the default value. Reference the actual value from one place (instead of `foo = 2,` everywhere, reference it like `foo = MyWidget.defaultFoo,` and only write the value `2` in MyWidget.

&nbsp;

Or, if possible, make the parameter required in parent widgets, and only set the default in the single child widget.

&nbsp;

* [Discussion on chat](https://chat.google.com/room/AAAAyMoi5-E/FSmSJFPQYiM/FSmSJFPQYiM?cls=10)  
* [PR discussion](https://github.com/flutter/flutter/pull/163491#discussion_r2059211501) about the selectAllOnFocus parameter’s default.  
* [EditableText.defaultStylusHandwritingEnabled](https://github.com/flutter/flutter/blob/83483976ec0c2667bb991d052a0e02c691687bf2/packages/flutter/lib/src/widgets/editable_text.dart#L2041) is used as the default value for all stylusHandwritingEnabledParameter’s, such as [TextField.stylusHandwritingEnabled](https://github.com/flutter/flutter/blob/b90818ec53ac6f774cdeebd2acd9ab8e71b5c7b5/packages/flutter/lib/src/material/text_field.dart#L313).  
* This came up [in a selection style PR](https://github.com/flutter/flutter/pull/167762/files#r2072092558).

&nbsp;

## ThemeData.platform vs. defaultTargetPlatform {#themedata.platform-vs.-defaulttargetplatform}

Use `defaultTargetPlatform` when you're going to affect a platform-specific behavior. For example, accessibility, text editing, gestures, system UI, or anything that makes a platform-channel call. Use `ThemeData.platform` for visuals and styling.

&nbsp;

What about the widgets library? In the long term, we should have a theme there too\! For now, use `defaultTargetPlatform`, though.

&nbsp;

* [Discussion on GitHub](https://github.com/flutter/flutter/pull/148523#discussion_r1605439225)

&nbsp;

## Don’t write assertions that can’t be triggered {#don’t-write-assertions-that-can’t-be-triggered}

Use a comment instead of an assertion if the only purpose is for code readability. For example, you may want to explain some limitations on a variable that are enforced elsewhere. Don’t use an assertion that will never trigger because of the other enforcement, just leave a comment explaining the situation.

&nbsp;

```java
class Foo {
  const Foo({
    required this.bar,
    required this.baz,
  }) : assert(baz > 0);

  final int bar;
  final int baz;

  double divide() {
    assert(baz != 0); // bad
    // baz can't be zero. // good
    return bar / baz;
  }
}
```

&nbsp;

* This previously caused [confusion in this PR](https://github.com/flutter/flutter/pull/159999/files#r2006281888).

## The sentinel pattern \- was the default value given or was the parameter omitted? {#the-sentinel-pattern---was-the-default-value-given-or-was-the-parameter-omitted?}

Sometimes in Dart it’s useful to disambiguate between an optional parameter being omitted versus being explicitly passed the default value. This can be accomplished by using a sentinel value. The optional parameter’s default value is set to the sentinel value, so that it only contains that value if it was omitted. Then it can be swapped for the actual desired default value as needed.

&nbsp;

Examples:

* TextStyle.copyWith:  
  * [https\://github.com/flutter/flutter/pull/149049](https://github.com/flutter/flutter/pull/149049)  
* TextPainter.textScaler:  
  * [https\://github.com/flutter/flutter/pull/159999](https://github.com/flutter/flutter/pull/159999)

## Naming \- Use a positional parameter to avoid repetition {#naming---use-a-positional-parameter-to-avoid-repetition}

The `Text` widget uses a positional parameter to avoid unnecessary repetition of the word “text”:

&nbsp;

```java
// Bad
Text(text: _myText);

// Good (current state)
Text(_myText);
```

&nbsp;

Recently, `CurvedTween` was updated to follow a similar pattern in [\#166012](https://github.com/flutter/flutter/pull/166012):

&nbsp;

```java
/// Bad (before)
CurvedTween(curve: _myCurve);

/// Good (after)
CurvedTween(_myCurve);
```

&nbsp;

[Tong Mu](mailto:tongmu@google.com) had a similar suggestion during [code review](https://github.com/flutter/flutter/pull/164810#discussion_r2029242702) in this PR to reduce repetition.

## Prefer `Diagnosticable` to `toString` {#prefer-diagnosticable-to-tostring}

Instead of overriding toString, mixin [Diagnosticable](https://main-api.flutter.dev/flutter/foundation/Diagnosticable-mixin.html) and override debugFillProperties instead. This integrates with devtools and provides structured, consistent output.

&nbsp;

See the [styleguide](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md#override-tostring) for more.

&nbsp;

* Here is an [example of a PR](https://github.com/flutter/flutter/pull/160714) that included migrating toString to Diagnosticable for a bunch of classes.  
* This came up in the IOSSystemContextMenuItem classes in [a comment in \#169150](https://github.com/flutter/flutter/pull/169150#discussion_r2114718654).  
  * [https\://github.com/flutter/flutter/issues/169696](https://github.com/flutter/flutter/issues/169696)  
  * [https\://github.com/flutter/flutter/pull/169705](https://github.com/flutter/flutter/pull/169705)  
  * [https\://github.com/flutter/flutter/pull/171028](https://github.com/flutter/flutter/pull/171028)

## Sharing code between Material and Cupertino {#sharing-code-between-material-and-cupertino}

Typically, provide a common raw widget in the widgets library that is used via composition in the Material and Cupertino libraries.

&nbsp;

The raw widget should have no or little opinion on its visual appearance. For example, [RawAutocomplete](https://main-api.flutter.dev/flutter/widgets/RawAutocomplete-class.html) requires builder methods to be passed in for building its field and its options. In the Material library, [Autocomplete](https://main-api.flutter.dev/flutter/material/Autocomplete-class.html) passes Material-style builders to RawAutocomplete by default. [This issue](https://github.com/flutter/flutter/issues/99619) provides some evidence that this pattern works well for our users.

&nbsp;

See [below](#naming:-rawmywidget-/-mywidget-/-cupertinomywidget) for naming and other examples.

### Naming: RawMyWidget / MyWidget / CupertinoMyWidget {#naming:-rawmywidget-/-mywidget-/-cupertinomywidget}

When you have a root widget in the widgets library that is used via composition to create a Material and Cupertino version, use the following naming convention: the widget in the widgets library should be prefixed with “Raw”, the widget in the Material library should have no prefix, and the widget in the Cupertino library should be prefixed with “Cupertino”. For example, RawMyWidget, MyWidget, and CupertinoMyWidget in the widgets, Material, and Cupertino libraries respectively.

&nbsp;

* This came up recently [in a PR](https://github.com/flutter/flutter/pull/167764#discussion_r2060549731) creating a Radio widget in the widgets library.  
* Other examples (not comprehensive):  
* [RawMenuAnchor](https://main-api.flutter.dev/flutter/widgets/RawMenuAnchor-class.html) / [MenuAnchor](https://main-api.flutter.dev/flutter/material/MenuAnchor-class.html)  
* [RawAutcomplete](https://main-api.flutter.dev/flutter/widgets/RawAutocomplete-class.html) / [Autocomplete](https://main-api.flutter.dev/flutter/material/Autocomplete-class.html)  
* [RawMagnifier](https://main-api.flutter.dev/flutter/widgets/RawMagnifier-class.html) / [Magnifier](https://main-api.flutter.dev/flutter/material/Magnifier-class.html) / [CupertinoMagnifier](https://main-api.flutter.dev/flutter/cupertino/CupertinoMagnifier-class.html)  
* [RawScrollbar](https://main-api.flutter.dev/flutter/widgets/RawScrollbar-class.html) / [Scrollbar](https://main-api.flutter.dev/flutter/material/Scrollbar-class.html) / [CupertinoScrollbar](https://main-api.flutter.dev/flutter/cupertino/CupertinoScrollbar-class.html)

&nbsp;

Examples that follow this pattern but don’t quite get the naming right:

* [EditableText](https://main-api.flutter.dev/flutter/widgets/EditableText-class.html) / [TextField](https://main-api.flutter.dev/flutter/material/TextField-class.html) / [CupertinoTextField](https://main-api.flutter.dev/flutter/cupertino/CupertinoTextField-class.html)  
* [Expansible](https://api.flutter.dev/flutter/widgets/Expansible-class.html) / [ExpansionTile](https://api.flutter.dev/flutter/material/ExpansionTile-class.html) / [CupertinoExpansionTile](https://main-api.flutter.dev/flutter/cupertino/CupertinoExpansionTile-class.html)

&nbsp;

## Should Flutter include features that are not in the Material spec? {#should-flutter-include-features-that-are-not-in-the-material-spec?}

Reject features that are not part of the spec by default due to the increased maintenance burden. Make exceptions when the maintenance burden is small and the trouble that it gives users is large.

&nbsp;

You can find examples of both approaches in Flutter today; there are PRs and issues that have been closed because they wanted something outside of the spec, but there are also many features in the framework that are not in the spec.

&nbsp;

Use discretion and err on the side of keeping the framework focused and manageable when in doubt.

&nbsp;

* This came up recently in [\#168005](https://github.com/flutter/flutter/pull/168005), where a contributor wanted to add a header and footer feature to NavigationDrawer.

## Cross-platform APIs {#cross-platform-apis}

Mirror native APIs as closely as possible in Dart, so that advanced users can use them directly if needed. Build the cross-platform abstraction on top of that. It’s ok to write an API that works on only one platform. Don’t write a “least common denominator” API that does only the common features across all platforms and leaves out each platform’s unique features.

&nbsp;

* From the styleguide on this topic:  
  * [https\://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md\#avoid-the-lowest-common-denominator](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md#avoid-the-lowest-common-denominator)  
* Example: SystemContextMenu  
  * [Justin McCandless](mailto:jmccandless@google.com) started writing SystemContextMenu as a cross-platform API that would only support iOS initially. Later, some API had to be written that was clearly iOS-only. In retrospect the naming issue could have been avoided by building a separate iOS API first and then making a cross-platform abstraction on top of that.  
    * [IOSSystemContextMenuItem](https://main-api.flutter.dev/flutter/widgets/IOSSystemContextMenuItem-class.html)  
* Counter-example: [hasStrings](https://main-api.flutter.dev/flutter/services/Clipboard/hasStrings.html)  
  * Here the cross-platform abstraction is made at the embedder level. There is a hasStrings platformChannel method that all platforms support in various different ways in each of their embedders, but on the framework Dart side it’s all just a hasStrings boolean.  
  * Here’s how the Android embedder implements hasStrings:  
    * [https\://github.com/flutter/flutter/blob/4b1d2644cbdb19ef79cef592d43ceb176dc28418/engine/src/flutter/shell/platform/android/io/flutter/plugin/platform/PlatformPlugin.java\#L608-L622](https://github.com/flutter/flutter/blob/4b1d2644cbdb19ef79cef592d43ceb176dc28418/engine/src/flutter/shell/platform/android/io/flutter/plugin/platform/PlatformPlugin.java#L608-L622)  
    * It’s fairly complicated and uses a couple of different platform APIs.  
  * Versus how it’s implemented on iOS:  
    * [https\://github.com/flutter/flutter/blob/4b1d2644cbdb19ef79cef592d43ceb176dc28418/engine/src/flutter/shell/platform/darwin/ios/framework/Source/FlutterPlatformPlugin.mm\#L423-L425](https://github.com/flutter/flutter/blob/4b1d2644cbdb19ef79cef592d43ceb176dc28418/engine/src/flutter/shell/platform/darwin/ios/framework/Source/FlutterPlatformPlugin.mm#L423-L425)  
    * It directly mirrors the iOS hasStrings API.  
  * This API is small enough (a single boolean) that it probably makes sense to do the abstraction at the embedder level instead of porting the underlying APIs to Dart as-is.  
    * We would have needed to port Android’s whole clipboard API to Dart. Maybe we should if we have time, but not just for hasStrings.  
* This came up when discussing how to bring [Android’s credentials API](https://developer.android.com/reference/android/credentials/package-summary) to Flutter.  
  * [Autofill Adoption 2025](https://docs.google.com/document/d/1MxdIyPbtWkyJLDwieHfKoiw8KoEUqBdZ6cEug1I00wQ/edit?tab=t.0)

## InheritedWidgets {#inheritedwidgets}

Should you use InheritedWidget or InheritedModel? Should you add `.of` methods or `.maybeOf`? Should they add dependencies on the calling BuildContext? Use the following flow to decide.

&nbsp;

* Use InheritedModel only if you expect a performance benefit, otherwise use InheritedWidget.  
  * Indicators of an InheritedModel performance benefit:  
    * If it’s expected that the framework, or users, will typically use only one of a few properties in a given widget.  
    * If it’s expected that the properties will change independently of each other and not all at the same time.  
  * Example: [MediaQuery](https://main-api.flutter.dev/flutter/widgets/MediaQuery-class.html) uses InheritedModel  
    * It contains many unrelated bits of information that users are very likely to access individually and that are very likely to change independently. So, using InheritedModel and providing `maybeOf` methods for individual properties is worth the overhead.  
* Prefer adding `maybeOf` over `of` unless it’s specifically needed.  
  * `of` methods were added before Dart’s null safety feature was brought to Flutter.  
* Always add a dependency to the BuildContext in `of` and `maybeOf` methods.  
  * The canonical way to access an InheritedWidget without adding a dependency is to instead use [getElementForInheritedWidgetOfExactType](https://main-api.flutter.dev/flutter/widgets/BuildContext/getElementForInheritedWidgetOfExactType.html).  
    * This isn’t always possible, though. For example, Theme.of. Theme is not an InheritedWidget itself, and instead Theme.of depends on a private InheritedWidget internally.  
      * See [https\://github.com/flutter/flutter/issues/106549\#issuecomment-2943732849](https://github.com/flutter/flutter/issues/106549#issuecomment-2943732849).

&nbsp;

Here are some cases where this has come up:

* A PR looking to add extra `of` methods:  
  * [https\://github.com/flutter/flutter/pull/168630\#pullrequestreview-2862170009](https://github.com/flutter/flutter/pull/168630#pullrequestreview-2862170009)  
  * Related issue that came out of it about optionally adding a dependency or not:  
    * [https\://github.com/flutter/flutter/issues/169539](https://github.com/flutter/flutter/issues/169539)  
* A large PR that sought to change how InheritedModels are used by introducing what it called the “selector model”, while migrating all Theme InheritedWidgets to InheritedModels. This sparked a lot of discussion around the relative performance of the two.  
  * [https\://github.com/flutter/flutter/pull/165289](https://github.com/flutter/flutter/pull/165289)  
* A PR that proposes to add a way to automatically unsubscribe widgets that no longer use an InheritedWidget:  
  * [https\://github.com/flutter/flutter/pull/170104](https://github.com/flutter/flutter/pull/170104)  
  * [https\://github.com/flutter/flutter/issues/106549](https://github.com/flutter/flutter/issues/106549)  
  * [https\://github.com/flutter/flutter/issues/12992](https://github.com/flutter/flutter/issues/12992)  
  * [https\://discord.com/channels/608014603317936148/1378635435328405545/1378635440487399565](https://discord.com/channels/608014603317936148/1378635435328405545/1378635440487399565)  
* A discussion about adding `.of` methods as extension methods on BuildContext.  
  * [Flutter Framework vision for Lang/Framework for 2026](https://docs.google.com/document/d/1Rjzrgrb-a7jYXdXNh8Tro1x_HUcdVGyOefMpKwWhO3A/edit?resourcekey=0-5_5FbsuGAZuwnqoD2kLu2A&tab=t.0#heading=h.g08wip5nml11)

## Mouse on mobile and touch on desktop {#mouse-on-mobile-and-touch-on-desktop}

Ultimately Flutter should behave the same way that the native platforms do. Try it on a real native device with real peripherals if at all possible.

&nbsp;

In general, however, use the type of input rather than the platform to decide behavior. For example, if you are building a mouse feature, it should probably work on all platforms when a physical mouse is plugged in. Modern Android and iOS have good support for physical keyboards and mice. Previously, Flutter often restricted mouse and keyboard features to desktop platforms with `defaultTargetPlatform`, and that was a mistake.

&nbsp;

Don’t forget about web, which can be mobile or desktop. Google has paused active work on desktop, but desktop web should still be actively supported.

## Don’t mutate [Paint](https://main-api.flutter.dev/flutter/dart-ui/Paint-class.html) instances {#don’t-mutate-paint-instances}

Don’t mutate a single instance of Paint when making subsequent draw calls. This leads to tricky bugs when testing with [paints](https://main-api.flutter.dev/flutter/flutter_test/paints.html), where recorded draw calls are retroactively mutated. Instead, declare a new Paint instance each time you need to make a new draw call with a different style.

&nbsp;

```java
  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint =
      Paint()
        ..color = Colors.red
        ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(0.0, 0.0), 10.0, paint);

    // Bad
    paint.color = Colors.blue;
    canvas.drawCircle(Offset(20.0, 0.0), 10.0, paint);

    // Good
    final Paint bluePaint =
      Paint()
        ..color = Colors.blue
        ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(20.0, 0.0), 10.0, bluePaint);
}
```

&nbsp;

* This bug came up in:  
  * [https\://github.com/flutter/flutter/pull/170321/files\#r2138619243](https://github.com/flutter/flutter/pull/170321/files#r2138619243)  
* Docs were updated to warn about this in:  
  * [https\://github.com/flutter/flutter/pull/171180](https://github.com/flutter/flutter/pull/171180)

## Handling different versions of native platforms {#handling-different-versions-of-native-platforms}

Typically, we always try to match the behavior of the latest version of each platform.  This includes when running on older versions.  So a Flutter app running on an older iOS device will still look and feel like the latest iOS version.

&nbsp;

The main reason behind this is to limit complexity due to our finite resources. It would be a lot of work to, say, allow developers to choose which version of iOS they wanted their app to look like.  That may change if we ever have enough demand and resources to create such a thing.

&nbsp;

* [The styleguide on this topic](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md#widget-libraries-follow-the-latest-oem-behavior).  
* Some possible exceptions:  
  * The [useMaterial3](https://main-api.flutter.dev/flutter/material/ThemeData/useMaterial3.html) flag was added to allow Flutter to slowly adopt Material 3 without giving users an unexpected partial change to the new visuals.  
    * Similarly, various [year2023](https://main-api.flutter.dev/flutter/material/Slider/year2023.html) flags were added.  
  * Flutter may handle Material 3 Expressive and iOS 26 visuals in a different way.

&nbsp;

## Avoid descriptions of platform level behavior if possible without surprising the user {#avoid-descriptions-of-platform-level-behavior-if-possible-without-surprising-the-user}

Focus on giving developers the information they need to rely on our apis without surprising them. Describing behavior in a platform independent way is less surprising over time because platforms tend to respond to each other.  If it’s not possible to describe the behavior in a platform independent way, use platform specific details as examples and, if relevant, link to platform specific docs.&nbsp;

&nbsp;

Examples

&nbsp;

Android deprecated the announce api for accessibility. Adding a dart api to indicate if widgets should use announce or should instead prefer a different way of updating accessibility labels should have platform independent descriptions.&nbsp;

&nbsp;

Good:&nbsp;

&nbsp;

&nbsp;

```java
// Indicates if the host platform should prefer announcements over other accessibility label apis like liveregion. 
AccessibilityDetails.shouldAnnounce() {...}
```

&nbsp;

Good:&nbsp;

&nbsp;

```java
// Indicates if the host platform should use accessibility announcements. 
// 
// Android: 
// Android has deprecated announce apis as of api 36 see LINK-TO-DOCS
// Accessibility announcements will work on lower api android devices. 
AccessibilityDetails.shouldAnnounce() {...}
```

&nbsp;

Bad:&nbsp;

&nbsp;

```java
// Signal for widgets on android devices to use liveregion instead of announcements 
// because the apis for announce are deprecated on android. 
AccessibilityDetails.shouldAnnounce() {...}
```

&nbsp;

## Avoid platform UI where practical {#avoid-platform-ui-where-practical}

Prefer using Flutter to draw UI elements as opposed to showing platform UI unless impossible or impractical (see exceptions below). Flutter UI works as expected with other Flutter widgets while platform views may have [limitations](https://docs.flutter.dev/platform-integration/ios/platform-views#composition-limitations), and Flutter UI will look exactly the same across all of our platforms.

&nbsp;

* Exceptions  
  * [SystemContextMenu](https://main-api.flutter.dev/flutter/widgets/SystemContextMenu-class.html)  
    * On iOS, shows the platform text selection context menu in text fields instead of the Flutter-drawn context menu.  
    * iOS shows a permissions dialog when an app programmatically pastes, so before this change, Flutter apps showed this dialog when users pressed the paste button in the context menu, but native apps did not. We were unable to find a way around this besides showing the platform context menu.  
    * [iOS Secure Paste & Native Edit Menu (PUBLICLY SHARED)](https://docs.google.com/document/d/16-8kn58h_oD902e7vPSh6W20aHRBJKyNOdSe5rbAe_g/edit?resourcekey=0-gVdJ3fbOybV70ZKeHU7fkQ&tab=t.0#heading=h.iamvrpjs1n1)  
  * Platform view text input (especially on web)  
    * There are several common text input features that cannot work on web without the addition of new APIs to Flutter’s supported browsers. Instead of waiting years for this support, we are exploring using native text inputs on web.  
    * This is not yet implemented, but it is under investigation this year as a part of [Text Input OKR 2025 Strategy](https://docs.google.com/document/d/188u6rXfVW4x65b2uPoPKZVV9Ddj2EwrSzHnEqBk1hhQ/edit?tab=t.0).  
    * [Native Text Fields for Flutter Web Evaluation](https://docs.google.com/document/d/1G_m71595NVPvbxB7f4ayA58O9PVQ9txH24oLTVl3lEY/edit?resourcekey=0-MnLBzjEW2rAjDv0XGjql_A&tab=t.0#heading=h.lcvm38gwdyqx)  
    * [Native text editing on web using platform views (PUBLICLY SHARED)](https://docs.google.com/document/d/1t6qAX46tsR1tdBS42yro6G_5Igtrj7WzmKKiUI_JC-k/edit?tab=t.0)

## Put system UI in the Widgets library where possible {#put-system-ui-in-the-widgets-library-where-possible}

System UI is the user interface elements and behaviors that are specific to a given platform and typically appear the same across most apps. For example, text selection handles, context menus, and page transitions. Android system UI is not the same thing as Material Design, and iOS system UI is not the same thing as Cupertino.

&nbsp;

Put system UI code in the Widgets library whenever possible. This helps developers target a platform without adding a dependency on that platform’s design language. However, if the system UI depends heavily on the design language, put it in the design language package rather than duplicating code or creating other architectural problems.

&nbsp;

* [System UI Library (PUBLICLY SHARED)](https://docs.google.com/document/d/1JwQ7gdJ1evQ-IfDu7JjouwO8JXYC6fIw3TJzAYNWPPo/edit?pli=1&tab=t.0)

## Prefer asserting widget invariants in their constructor {#prefer-asserting-widget-invariants-in-their-constructor}

For example:

&nbsp;

```js
class Foo extends StatelessWidget {
  const Foo({
    super.key,
    required this.name,
  }) : assert(name != '', 'Name must not be empty');

  final String name;
  
  @override
  Widget build(BuildContext context) {
    return Text('Hello ${widget.name}');
  }
}
```

&nbsp;

Prefer asserting widget invariants in the constructor even if it means the widget cannot be `const`.

&nbsp;

Using assertions to catch user errors in widget lifecycle methods like `initState` and `didUpdateWidget` cause leaks: [flutter\#157470](https://github.com/flutter/flutter/issues/157470). Prefer alternatives like asserting in the constructor if possible.

&nbsp;

* This also came up in [\#180029](https://github.com/flutter/flutter/pull/180029), which wanted to add `const` to `Container`.

## Prefer clean code over the ability to use `const`

Using the `const` keyword can result in performance improvements. However, requiring `const` everywhere gives annoying lint errors and sometimes less readable code. Also, the performance gain by using the `const` keyword is usually modest in practice. Therefore, we do not enforce the use of `const` as a strict requirement and we don’t recommend that our users do, either.

&nbsp;

* Some issues that investigated this:  
  * [https\://github.com/flutter/flutter/issues/149932](https://github.com/flutter/flutter/issues/149932)  
  * [https\://github.com/dart-lang/core/issues/833](https://github.com/dart-lang/core/issues/833)  
* The PR that removed the const lints from flutter\_lints:  
  * [https\://github.com/flutter/packages/pull/7688](https://github.com/flutter/packages/pull/7688)  
* This also came up more recently when a bug was discovered in a `const` lint rule:  
  * [https\://github.com/dart-lang/sdk/issues/63965](https://github.com/dart-lang/sdk/issues/63965)

&nbsp;

## Testing {#testing}

### Avoid fragile golden tests {#avoid-fragile-golden-tests}

Prefer using Flutter’s robust headless testing if possible (e.g. [paints](https://main-api.flutter.dev/flutter/flutter_test/paints.html), [getSize](https://main-api.flutter.dev/flutter/flutter_test/WidgetController/getSize.html), [getTopLeft](https://main-api.flutter.dev/flutter/flutter_test/WidgetController/getTopLeft.html), etc.) instead of visual diff testing (goldens). Goldens often end up testing much more than intended, and will break when subtle unrelated changes are made to antialiasing, layout, etc.

&nbsp;

If a golden test is needed, don’t capture a screenshot midway through an animation, as the resulting image can be non-deterministic.

&nbsp;

* Exceptions:  
  * Search the test directory for `matchesGoldenFile`.

### Expose animation durations as `@visibleForTesting`, or duplicate them? {#expose-animation-durations-as-@visiblefortesting,-or-duplicate-them?}

It probably depends on the situation. Does the test care what the animation duration is, or does it just want to wait until it’s finished? Is it reasonably likely that breaking a test because someone changed the duration would be beneficial and not an annoyance? See [this discussion](https://github.com/flutter/flutter/pull/165606#discussion_r2037935263).

&nbsp;

What *is* certain is that we should always prefer `pump` with the exact Duration instead of `pumpAndSettle` where practical, [per the styleguide](https://github.com/flutter/flutter/blob/master/docs/contributing/Style-guide-for-Flutter-repo.md#avoid-using-pumpandsettle).

&nbsp;

Page transition durations should be looked up using [TransitionDurationObserver](https://main-api.flutter.dev/flutter/flutter_test/TransitionDurationObserver-class.html). That way, the test won’t be broken if the transition changes or even if the duration of the transition changes. This came up [when changing the default page transition](https://github.com/flutter/flutter/pull/165832#issuecomment-2932867868) caused many test breakages. For an example, see [this test](https://github.com/flutter/flutter/blob/7c417dbcb1caf50d54fae28b1e9e16666035820f/packages/flutter/test/widgets/heroes_test.dart#L731) that follows this pattern.

### Which platforms to use for TargetPlatformVariant {#which-platforms-to-use-for-targetplatformvariant}

The [testWidgets](https://main-api.flutter.dev/flutter/flutter_test/testWidgets.html) method takes the parameter `variant`, which is commonly used to define which platforms a test should be run as. In most cases the parameter should be omitted entirely, unless specifically testing platform-specific code.

&nbsp;

When testing something that contains no platform-specific logic itself, omit the `variant` parameter. This means that when running on your local machine, it will by default run the test as Android. However, on CI, the test will be run through our suite of scenarios which includes running the tests on all supported platforms. This is the most common scenario for most of Flutter’s tests.

&nbsp;

When the logic being tested applies only to some subset of platforms, pass exactly those platforms and omit others.

&nbsp;

When testing something that may have different behavior on each platform, for example code containing a `switch` on `defaultTargetPlatfrom`, then use `TargetPlatformVariant.all()`.

&nbsp;

You may be tempted to always pass `TargetPlatformVariant.all()` to make sure everything is covered, but this is wasting resources unless explicitly needed. As mentioned above, CI will run the test on all of our platforms anyway.

### Testing the absence of an error {#testing-the-absence-of-an-error}

Avoid adding complexity with unnecessary `try`/`catch` blocks when instead directly allowing the code to throw an error would suffice. To communicate the intention of the test, use comments rather than redundant `expect`s.

&nbsp;

```java
// Bad:
AssertionError? error;
 try {
   myTestCode();
 } on AssertionError catch (e) {
   error = e;
 }
 expect(error, isNull);

// Good:
// Regression test for <GitHub URL>.
// Should not trigger an assertion.
myTestCode();
// Or for async code:
await expectLater(myAsyncTestCode(), completes);
```

&nbsp;

Be aware of how errors affect test control flow. Errors triggered as a result of WidgetTester calls like `pumpWidget` will be swallowed until the end of the test, at which point it will trigger a failure. If it’s desirable for the test to fail immediately, use `expect(tester.takeException(), isNull);`.

&nbsp;

* This came up in [https\://github.com/flutter/flutter/pull/170891](https://github.com/flutter/flutter/pull/170891).

### Avoid adding Keys to the codebase solely for tests {#avoid-adding-keys-to-the-codebase-solely-for-tests}

Don’t add a [Key](https://main-api.flutter.dev/flutter/foundation/Key-class.html) whose only purpose is to locate a widget in a test. Instead, use Flutter’s robust set of [CommonFinders](https://main-api.flutter.dev/flutter/flutter_test/CommonFinders-class.html). For example, [descendant](https://main-api.flutter.dev/flutter/flutter_test/CommonFinders/descendant.html) can often be used to eliminate potential ambiguity in a finder, and can even be used with private widget classes via [byWidgetPredicate](https://main-api.flutter.dev/flutter/flutter_test/CommonFinders/byWidgetPredicate.html).

&nbsp;

This eliminates unused overhead in users’ apps, and avoids the chance of collisions between a Key in a user’s codebase.

&nbsp;

* This came up in: [https\://github.com/flutter/flutter/pull/170761\#discussion\_r2159760635](https://github.com/flutter/flutter/pull/170761#discussion_r2159760635)  
* This was enforced in: [https\://github.com/flutter/flutter/pull/170952](https://github.com/flutter/flutter/pull/170952)

### Test exemptions {#test-exemptions}

The [tree hygiene docs](https://github.com/flutter/flutter/blob/master/docs/contributing/Tree-hygiene.md#tests) discuss when tests are required, but here is a list of notable exceptions:

&nbsp;

* There’s no need to test a change to what is exported from the framework. Any test would be too trivial to be valuable.  
  * In flutter/packages this may not be the case.  
  * [https\://github.com/flutter/flutter/pull/170563\#issuecomment-2981783469](https://github.com/flutter/flutter/pull/170563#issuecomment-2981783469)  
  * [https\://discord.com/channels/608014603317936148/608018585025118217/1382878586590986270](https://discord.com/channels/608014603317936148/608018585025118217/1382878586590986270)

### Prefer generic matchers in tests {#prefer-generic-matchers-in-tests}

Use generic matchers like [`findsOne`](https://main-api.flutter.dev/flutter/flutter_test/findsOne-constant.html) instead of widget-specific matchers like [`findsOneWidget`](https://main-api.flutter.dev/flutter/flutter_test/findsOneWidget-constant.html), even when matching widgets. flutter\_test currently contains several of these duplicate matcher functions with the same functionality but different names. In this case, they actually are identical under the hood:

&nbsp;

```
const Matcher findsOneWidget = _FindsCountMatcher(1, 1);

const Matcher findsOne = _FindsCountMatcher(1, 1);
```

&nbsp;

The reason for this was a move toward generic matchers that supported matching semantics nodes, which introduced `findsOne` in addition to the original `findsOneWidget`. There was a plan to deprecate `findsOneWidget`, but it has never happened.

&nbsp;

This is not a super critical rule to follow since both matchers are equivalent and flutter/flutter’s tests use `findsOneWidget` extensively. Instead it’s meant to help understand the direction and intention of this API.

&nbsp;

* Relevant discussions on the PR that added `findsOne`:  
  * [https\://github.com/flutter/flutter/pull/127137\#discussion\_r1213744575](https://github.com/flutter/flutter/pull/127137#discussion_r1213744575)  
  * [https\://github.com/flutter/flutter/pull/127137\#discussion\_r1278034663](https://github.com/flutter/flutter/pull/127137#discussion_r1278034663)  
* This came up in:  
  * [https\://github.com/flutter/flutter/pull/174787/files\#r2325402666](https://github.com/flutter/flutter/pull/174787/files#r2325402666)

### Organize tests by library {#organize-tests-by-library}

Keep test code in its respective library and don’t cross-import unnecessary code. For example, put a test for a Cupertino widget in the Cupertino library and don’t import Material. Tests that explicitly involve platform adaptivity or multiple design libraries should be located in Material.

&nbsp;

* Testing something related to Cupertino or Material? Put it in Cupertino or Material, and don’t import the other library.  
* Testing something in Widgets? Put it in Widgets and don’t import Material or Cupertino.  
* Testing something involving platform adaptivity or multiple design languages? Put it in the Material library. It’s ok to import Cupertino in the Material tests when essential to the test.

&nbsp;

When should we write tests that involve multiple libraries?

&nbsp;

* Always test platform adaptive behaviors, like `.adaptive` constructors.  
* When interoperability provides a benefit to users. E.g., users will expect to be able to put a CupertinoTextField under a MaterialApp, and we should test that that works.

&nbsp;

For more information, see:

&nbsp;

* [Decoupling Framework Tests (PUBLICLY SHARED)](https://docs.google.com/document/d/1UHxALQqCbmgjnM1RNV9xE2pK3IGyx-UktGX1D7hYCjs/edit?pli=1&tab=t.0#heading=h.e28dyzvsnela)

&nbsp;

### Prefer [`tester.semantics.find`](https://main-api.flutter.dev/flutter/flutter_test/SemanticsController/find.html) when testing semantics {#prefer-tester.semantics.find-when-testing-semantics}

Avoid using [TestSemantics](https://github.com/flutter/flutter/blob/dcc3ab2054b11df9867bdf7930a06ed301dba6e8/packages/flutter/test/widgets/semantics_tester.dart#L22) to compare a dump of the entire semantics tree, which is brittle to changes unrelated to what’s being tested. Instead, test only the specific relevant semantics using [`tester.semantics.find`](https://main-api.flutter.dev/flutter/flutter_test/SemanticsController/find.html) paired with [isSemantics](https://main-api.flutter.dev/flutter/flutter_test/isSemantics.html).

&nbsp;

```c
expect(
  tester.semantics.find(find.bySemanticsLabel('Alert'))
  isSemantics(
    label: 'Alert',
    role: SemanticsRole.dialog,
    namesRoute: true,
    scopesRoute: true,
    children: <Matcher>[
      isSemantics(
        hasImplicitScrolling: true,
        children: <Matcher>[
          isSemantics(label: 'The title'),
          isSemantics(label: 'The message'),
        ],
      ),
    ],
  ),
);
```

&nbsp;

&nbsp;

Many parts of the codebase currently use TestSemantics and need to be migrated. This work is tracked in [\#184367](https://github.com/flutter/flutter/issues/184367).

&nbsp;

* This came up in a PR:  
  * [https\://github.com/flutter/flutter/pull/183790\#issuecomment-4158558039](https://github.com/flutter/flutter/pull/183790#issuecomment-4158558039)  
* These PRs show examples of migrating to the preferred semantics testing approach:  
  * [https\://github.com/flutter/packages/pull/12055](https://github.com/flutter/packages/pull/12055)  
  * [https\://github.com/flutter/packages/pull/12057](https://github.com/flutter/packages/pull/12057)
