# ADR-001: Shared Frappe site with school-scoped authorization

> **Superseded.** This records the original provisional decision only.
> [ADR-005](ADR-005-site-per-school.md) is the accepted target architecture.

## Context

The product must support independent schools, potentially with shared parent/teacher identities and a shared Moodle MuTMS. A site-per-school model would simplify isolation but multiply upgrade, backup, and support cost.

## Alternatives

- One shared Frappe site with School and School Membership records.
- One Frappe site per school.

## Decision

Original decision: use a shared site provisionally. That implementation is
historical and must not guide new work. The accepted target is one Frappe site
and database per independent school. Existing membership checks and fields are
to be reviewed in Phase 1.

## Consequences

The authorization surface is larger: direct reads, APIs, reports, files, and background jobs require tests. Education's global settings cannot be assumed school-specific.

