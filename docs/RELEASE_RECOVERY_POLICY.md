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
4. **Optional external mirror** — deferred. The current project decision is to keep recovery points inside this same repository using immutable SHAs and stable branches.

An external mirror may be reconsidered later, but it is not required for the current development roadmap.

## Rules

- feature work never starts from the stable recovery branch;
- the stable recovery branch is moved only by an explicit release decision;
- every future stable release records its exact commit SHA;
- a recovery operation restores from a recorded SHA, never from memory;
- release backup does not replace CI, PR review, or branch protection;
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
    ├── release manifest with exact SHA
    ├── release tag when tooling is available
    └── stable recovery branch in this repository
```

The next stable promotion must record its exact SHA in a release manifest before any stable pointer is changed. P11 owns this release-safety process.


## P11 clean-restore verification

P11D verified that the P10 reference-validated release can be restored from the portable Git bundle into a new repository with:

```text
HEAD = 5228e358cf0716dc963f109a15b9e1a2d309f635
working_tree = clean
remotes = none
P10G integral dossier smoke = PASS
Linux Python 3.11 = PASS
Windows Python 3.12 = PASS
```

The internal recovery chain is therefore proven. The current recovery strategy remains inside this repository. An independent external mirror is deferred by project decision and is not a blocker for engineering development.


## Current repository-only decision

As of P12 activation, MCP Eléctrico keeps its recovery strategy in the same GitHub repository:

```text
main = active development
stable/0.9-engineering-preview = frozen P9 recovery point
stable/0.9-reference-validated = validated P10 recovery point
exact commit SHAs = canonical recovery anchors
```

Creating a second backup repository is deferred. The stable branches must not be used as feature-development branches or moved implicitly with `main`.
