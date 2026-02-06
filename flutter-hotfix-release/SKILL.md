---
name: flutter-hotfix-release
description:
  Use this skill to release a new hotfix version of Flutter.
---

# Flutter Hotfix Release

This skill guides the agent in releasing a new hotfix version of Flutter on
either the beta or stable channel. The Flutter team attempts to release a new
hotfix for both the beta channel and the stable channel each week that there is
no planned initial release if there are any changes that contributors think are
qualified as a hotfix. The process at a high level consists of merging any open
cherry pick pull requests, updating various files, getting the release built,
and then getting the release approved.

## Definitions

## Release channel
The release channel is either "beta" or "stable". The human that triggers this
skill should state which release channel they plan to release.

### Release candidate branch
The release candidate branch is the branch that we plan to release. It can be
found by visiting
https://github.com/flutter/flutter/blob/beta/bin/internal/release-candidate-branch.version
for the beta release channel, or
https://github.com/flutter/flutter/blob/stable/bin/internal/release-candidate-branch.version
for the stable release channel.

### Release version
The release version is the version that we plan to release. Find it by
navigating to https://docs.flutter.dev/install/archive, finding the most recent
release version for the beta or stable channel, and incrementing it by 1.

For example, if the most recent beta channel release version is 3.41.0-0.2.pre,
the our beta hotfix release version is 3.41.0-0.3.pre. If the most recent stable
channel release version is 3.38.9, then our stable hotfix release version is
3.38.10.

## Workflow

### 1. Updating DEPS

#### Finding the correct Dart revision SHA

##### Finding the most recent release for the release channel

Open https://sites.google.com/corp/google.com/dash/operations-hub/releases and
look for the most recent release on the given release channel that is in the
past. For example, as of February 6th, 2026, the most recent beta is Flutter
3.41 beta based on the "Est. Release Date" of "Jan 14th, 2026". The most recent
stable is Flutter 3.38.

Take the Dart version from that most recent release. In the case of my
example, that was "Dart 3.11 beta 3" for beta and "Dart 3.10" for stable.

##### Using the Dart version to get the Dart SHA

Open https://dart.googlesource.com/sdk/+refs and find the first tag with the
Dart major and minor version found in the previous step. Navigate to that tag's
page. Find the Dart SHA that we need listed after the label "commit".

#### Create a branch to work on

Create a new branch with the name "<release version>-DEPS" branched off of the
current release candidate branch.

#### Update the dart_revision

In the file DEPS, replace the SHA under `dart_revision` with the Dart SHA that
you found.

#### Update the dependencies
Run `gclient sync -D`.

Update the dependencies by running `engine/src/tools/dart/create_updated_flutter_deps.py -f DEPS`.

Run `client sync -D` again.

### 2. Update engine.version

#### Ensure that cherry pick PRs are merged
Check if there are any open cherry pick PRs that target the release candidate
branch by visiting
https://github.com/flutter/flutter/pulls?q=is%3Apr+is%3Aopen+label%3A%22cp%3A+review%22.
Ask the human running this skill if they are sure that they have merged
all of the cherry picks that they wanted to land, and list any open cherry picks
that you found. Continue only if the user confirms, otherwise exit.

#### Create a branch to work on

Create a new branch with the name "<release version>-engine-version" branched
off of the current release candidate branch. Make sure that this branch includes
an update to DEPS, such as what was created in step 1 in this file.

#### Find the engine change SHA

Find the most recent commit into the release candidate branch that included
changes to the engine/ directory. Typically this will be a cherry pick PR.

#### Update the file
Run the following command to automatically get the engine change SHA and write
it to bin/internal/engine.version:
`bin/internal/last_engine_commit.sh > bin/internal/engine.version`

Read the file and verify that the SHA matches the engine change SHA found in the
previous step. If the script failed, just write the engine change SHA found in
the previous commit to bin/internal/engine.version.

#### Submit the change

Make a commit that includes the change and has the message "engine.version now
contains the most recent commit that modified the engine."

Push the commit to the "origin" remote.

Prompt the human to open a pull request at the URL that was output by the push
command.

### 3.

## Resources

  - Typically humans follow this guide when making a new Flutter release:
    - https://g3doc.corp.google.com/company/teams/flutter/release/release_workflow.md
