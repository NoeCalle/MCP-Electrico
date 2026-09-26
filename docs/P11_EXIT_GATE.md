# P11 Exit Gate — Release Safety

## Status

```text
phase = P11_RELEASE_SAFETY
status = CLOSED_INTERNAL
P11A = DONE
P11B = DONE
P11C = DONE
P11D = DONE
external_mirror = PENDING_OPERATIONAL_ACTION
professional_emission = false
```

## What is proven

The validated P10 release is protected by exact-SHA recovery anchors, a versioned public-core contract, a portable source/bundle export with SHA-256 coverage, and a clean restore proof that does not depend on the development working tree or GitHub as the source of restored code.

The restore gate proves:

- exact release SHA recovery;
- bundle verification;
- checksum verification before restore;
- clean working tree;
- no remotes in the restored repository;
- dependency installation from the restored source;
- successful integral P10G dossier smoke;
- Linux/Python 3.11 and Windows/Python 3.12 coverage.

## Recovery anchors

```text
P9 freeze
stable/0.9-engineering-preview
6720da9183c45df299a584430fddea28f4060d7a

P10 reference validated
stable/0.9-reference-validated
5228e358cf0716dc963f109a15b9e1a2d309f635
```

## What remains external

The independent mirror repository has not yet been created by the repository automation available to this project. This does not weaken the verified internal restore chain, but it remains the recommended final redundancy layer.

When the mirror repository exists, follow `docs/RELEASE_MIRROR_RUNBOOK.md` and push only a verified stable export. Do not use the mirror for feature development.

## Engineering boundary

P11 adds no new electrical calculation and does not change the numerical engines. P6 IEEE 1584 remains deferred, and professional emission remains disabled.
