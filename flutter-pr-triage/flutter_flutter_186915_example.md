# [flutter/flutter #186915](https://github.com/flutter/flutter/pull/186915): Deprecate Material and Cupertino
 - Last activity: July 9th, 2026
 - Author: [justinmc](https://github.com/justinmc) (Google, contributor)
 - Keywords: decoupling, Material, Cupertino
 - Next steps: Wait for the author to finish the PR. Wait for material_ui and
 cupertino_ui to be published at version 1.0.0.

## Summary
As part of the decoupling initiative, this PR aims to deprecate the Material and
Cupertino libraries in order to encourage users to migrate to material_ui and
cupertino_ui, respectively. It also includes the data driven dart fix that helps
users migrate to the new packages.

Currently, the PR is incomplete, and it is also awaiting the release of
material_ui and cupertino_ui at versions 1.0.0. It is still a draft.

### The problem
Flutter is separating its Material and Cupertino libraries from the core
framework in order to accelerate the development of these libraries while
stabilizing the core APIs. The new packages will soon be published, and users
will need to migrate to use them instead of the old libraries in
flutter/flutter. These users need to be made aware of this process and given a
smooth migration experience to ensure success.

### The solution
This PR proposes to deprecate Material and Cupertino with a helpful deprecation
message explaining the situation. This will communicate to users that they need
to migrate and how to do it, while still allowing them to continue using the old
libraries for now. The included data driven dart fix will help users migrate
with a single command.

## Resources
 - [flutter/flutter issue
 #172942](https://github.com/flutter/flutter/issues/172942), which tracks the
 deprecation and removal of Material and Cupertino.
 - [material_ui](https://github.com/flutter/packages/tree/main/packages/material_ui)
 and
 [cupertino_ui](https://github.com/flutter/packages/tree/main/packages/cupertino_ui),
 which will take the place of these deprecated libraries in flutter/flutter.
