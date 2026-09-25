# Release and recovery policy

## Purpose

MCP Eléctrico must always preserve a known-good version that can be recovered if a later change damages the core, data contracts, study orchestration, or reproducibility guarantees.

This policy is independent from the P10 engineering reference case.

## Current recovery points

The frozen Engineering Preview 0.9 baseline is anchored at:

```text
checkpoint = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
commit_sha = 6720da9183c45df299a584430fddea28f4060d7a
recovery_branch = stable/0.9-engineering-preview
```

The completed P10 independent reference-validation baseline is anchored separately at:

```text
checkpoint = P10_REFERENCE_VALIDATED
commit_sha = 5228e358cf0716dc963f109a15b9e1a2d309f635
recovery_branch = stable/p10-reference-validated
```

Both branches point to exact known-good commits and must not be used for normal development. The P10 checkpoint is a recovery baseline, not a claim of professional release or professional emission.

## Recovery hierarchy

1. **Main development history** — ordinary Git history and merged PRs.
2. **Stable recovery branch** — points to a known-good frozen release candidate/baseline.
3. **Immutable release tag** — should be created for every stable product release when release tooling is available.
4. **Independent mirror repository** — future external backup of stable releases, separate from the active development repository.

A mirror repository is intentionally not a development remote. It exists so an accidental destructive change in the active repository does not remove the last known-good product state.

## Rules

- feature work never starts from the stable recovery branch;
- stable recovery branches are immutable checkpoints; create a new checkpoint rather than force-moving an old one;
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

Every new stable checkpoint or product release must be added here with its exact SHA before it is mirrored externally.
