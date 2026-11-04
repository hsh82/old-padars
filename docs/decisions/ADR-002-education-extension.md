# ADR-002: Extend Education through fixtures and services

## Context

Education already owns the academic lifecycle. Editing or overriding its controllers would make upgrades unsafe.

## Alternatives

- Duplicate Education DocTypes in Padars.
- Edit/override Education controllers.
- Add Custom Fields and Padars-owned services/hooks.

## Decision

Use Custom Field fixtures for school/offering references and keep new lifecycle/integration logic in Padars controllers and services. No upstream source files are modified.

## Consequences

Padars installation must sync fixtures before school-aware validation can run. Extensions remain upgrade-friendly but need metadata verification after Education upgrades.

