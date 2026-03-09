---
name: flutter-clone
description: This skill clones the Material or Cupertino library from the
flutter/flutter git repository into the flutter/packages repository's
material_ui or cupertino_ui packages, respectively, while preserving all
existing git history.
---

# Flutter Clone

This skill was written for Flutter's decoupling project to provide a reliable
way to copy the Material and Cupertino code from flutter/flutter into
flutter/packages while maintaining all git history.

## Prerequisites
Before using this skill, ensure the following:
1.  The `git-filter-repo` python library is installed (`pip install git-filter-repo`).

## Workflow

### 1. Ask for library name
Start by asking the user which library they would like to clone ("Material" or
"Cupertino").

### 2. Clone the source repository
Clone the repository that we'll be copying from and `cd` into it.
1. Clone the main Flutter repo located at: https://github.com/flutter/flutter
   using the following command:

   ```
   git clone git@github.com:flutter/flutter.git
   ```
2. Change directory into the newly cloned repo with `cd flutter`.

### 3. Filter for the target directory
Use git's `filter repo` command to rewrite the history of the newly cloned
repository so that it only contains the directory we're interested in. If the
library that the user chose in step 1 was "Material", then the directory is
`packages/flutter/lib/src/material`. If it was "Cupertino", then the directory
is `packages/flutter/lib/src/cupertino`.

1. Execute the following command using the correct path that corresponds to the
   library that the user chose in step 1. For example, for Material the command
   would be:

```
git filter-repo --path packages/flutter/lib/src/material
```

### 4. Prepare the destination repository
Add the source respository as a remote of the destination repository.

1. Change directory back out of the source repository.

```
cd ..
```

2. Clone the destination repository, which is flutter/packages located at
   https://github.com/flutter/packages, and `cd` into it.

```
git clone git@github.com:flutter/packages.git
cd packages
```

3. Add the source repository as a remote.

```
git remote add source-origin ../flutter
git fetch source-origin
```

### 5. Merge the history

1. Create a new branch to safely perform the merge.

```
git checkout -b merge-folder-step
```

2. Merge the source history into the new branch.

```
git merge source-origin/master --allow-unrelated-histories
```

### 6. Cleanup
Move the files into their final sub-directory (if they aren't already where you want them) and remove the temporary remote.

1. Determine the destination directory for the files. If the user chose the
   Material library in step 1, this is `packages/material_ui`. For Cupertino,
   it's `packages/cupertino_ui`.
2. Move the files into the destination directory. For Material the command is:

```
git mv -k * packages/material_ui
```

3. Commit the changes. For the Material library, the command looks like:

```
git commit -m "Relocated the Material code to its new home in packages/material_ui."
```

4. Clean up the temporary remote.

```
git remote remove source-origin
```
