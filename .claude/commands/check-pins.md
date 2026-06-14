---
description: Verify the pinned agent-image / component / action version is consistent across every file (and matches the latest tag).
allowed-tools: Bash(git:*), Bash(grep:*), Bash(sort:*), Bash(uniq:*)
---

Check that the `0.1.0-alpha.<n>` version is pinned **consistently** everywhere.
This is the project's classic footgun: a release that bumps some files but not
others ships a component whose `image:` pin points at a tag that doesn't exist.

## Evidence

- Every distinct version string in the tree (excluding CHANGELOG history):
  !`git grep -hoE "0\.1\.0-alpha\.[0-9]+" -- ':!CHANGELOG.md' | sort | uniq -c`
- Where each lives:
  !`git grep -nE "0\.1\.0-alpha\.[0-9]+" -- ':!CHANGELOG.md'`
- Latest git tag: !`git describe --tags --abbrev=0 2>/dev/null || echo none`
- Top of CHANGELOG: !`grep -m1 -E "^## \[0\.1\.0-alpha" CHANGELOG.md`

## What to report

1. If the `uniq -c` above shows **more than one** version string, the pins have
   drifted — list exactly which files carry the wrong version and what they should
   be (the highest version present, or whatever the user names).
2. If the single pinned version does **not** match the latest tag / top CHANGELOG
   entry, flag it (a pending release that hasn't tagged yet is fine — say so).
3. If everything agrees, say so in one line.

If asked to fix drift, `sed -i` the stale files up to the correct version and
re-run the grep to confirm a single consistent version remains. Do not touch
`CHANGELOG.md` historical entries.
