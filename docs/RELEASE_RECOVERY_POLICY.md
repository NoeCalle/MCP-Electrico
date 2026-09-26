# Release and recovery policy

## Purpose

MCP Eléctrico must always preserve a known-good version that can be recovered if a later change damages the core, data contracts, study orchestration, or reproducibility guarantees.

This policy is independent from the P10 engineering reference case.

## Current recovery points

Two known-good anchors are preserved.

### P9 frozen baseline

```text
release_name = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
commit_sha = 6720da9183c45df299a584430fddea28f4060d7a
recovery_branch = stable/0.9-engineering-preview
```

This is the exact P9D freeze before the independent P10 reference validation.

### P10 reference-validated baseline

```text
release_name = MCP_ELECTRICO_0_9_REFERENCE_VALIDATED
commit_sha = 5228e358cf0716dc963f109a15b9e1a2d309f635
recovery_branch = stable/0.9-reference-validated
release_manifest = releases/mcp_electrico_0_9_reference_validated.json
```

This is the exact P10G merge after the full reference project passed Workspace V5 and reproducible-dossier validation.

Neither stable branch is used for normal development or moved automatically with `main`.

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

The next stable promotion must record its exact SHA in a release manifest before any stable pointer or mirror is changed. P11 owns this release-safety process.
