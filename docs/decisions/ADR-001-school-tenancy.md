# ADR-001: Shared Frappe site with school-scoped authorization

## Context

The product must support independent schools, potentially with shared parent/teacher identities and a shared Moodle MuTMS. A site-per-school model would simplify isolation but multiply upgrade, backup, and support cost.

## Alternatives

- One shared Frappe site with School and School Membership records.
- One Frappe site per school.

## Decision

Use a shared site provisionally. Enforce school context with membership-aware query conditions, direct permission checks, and server-side relationship validation. Keep tenancy-specific logic in Padars so a future site-per-school deployment does not require duplicating the Education academic core.

## Consequences

The authorization surface is larger: direct reads, APIs, reports, files, and background jobs require tests. Education's global settings cannot be assumed school-specific.

