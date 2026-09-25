# Release and recovery policy

## Purpose

MCP Eléctrico must always preserve a known-good version that can be recovered if a later change damages the core, data contracts, study orchestration, or reproducibility guarantees.

This policy is independent from the P10 engineering reference case.

## Current recovery point

The frozen Engineering Preview 0.9 baseline is anchored at:

```text
release_name = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
commit_sha = 6720da9183c45df299a584430fddea28f4060d7a
recovery_branch = stable/0.9-engineering-preview
```

The branch was created from the exact P9D freeze commit and must not be used for normal development.

## Recovery hierarchy

1. **Main development history** — ordinary Git history and merged PRs.
2. **Stable recovery branch** — points to a known-good frozen release candidate/baseline.
3. **Immutable release tag** — should be created for every stable product release when release tooling is available.
4. **Independent mirror repository** — future external backup of stable releases, separate from the active development repository.

A mirror repository is intentionally not a development remote. It exists so an accidental destructive change in the active repository does not remove the last known-good product state.

## Rules

- feature work never starts from the stable recovery branch;
- the stable recovery branch is moved only by an explicit release decision;
- every future stable release records its exact commit SHA;
- a recovery operation restores from a recorded SHA, never from memory;
- release backup does not replace CI, PR review, or branch protection;
- the external mirror should contain source, tests, workflows, examples, and release documentation;
- secrets, local credentials, generated private dossiers, and environment files must never be copied into the backup repository.

## Future release workflow

```text
development
    ↓
main
    ↓
all release gates green
    ↓
stable release commit
    ├── release tag
    ├── stable recovery branch
    └── independent mirror repository
```

The next time MCP Eléctrico is promoted beyond Engineering Preview 0.9, this document must be updated with the new release SHA before the stable pointer or mirror is changed.
