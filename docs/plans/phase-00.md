# Phase 0 — Safe development baseline

## Goal

Start implementation from a clean Padars install on a pinned Frappe and
Education source set, on an isolated development branch and disposable site.
Padars is pre-release, so experimental schemas and patches may be redesigned
without preserving old Padars databases.

## Scope

1. Pin the framework/app revisions and CI runtime to the verified local stack.
2. Create a fresh disposable Frappe site and install ERPNext, Education, then
   Padars from the current safe branch.
3. Record current and target architecture, version facts, skills, tools, and
   known verification limits.
4. Keep `kara.loc` untouched.

Out of scope: data migration from experimental Padars schemas, migration
compatibility guarantees, patch cleanup, Moodle live writes, production
deployment, Superpowers installation, and CodeGraph installation.

## Source baseline

See [version-baseline.md](../operations/version-baseline.md). CI must use the
same Frappe, ERPNext, Education, Python, Node, Bench, MariaDB, and Redis
versions recorded there.

## Clean-install procedure

On the isolated test Bench only:

```bash
bench new-site padars-phase0-fresh.local
bench --site padars-phase0-fresh.local install-app erpnext
bench --site padars-phase0-fresh.local install-app education
bench --site padars-phase0-fresh.local install-app padars
bench --site padars-phase0-fresh.local list-apps
```

Never substitute `kara.loc` for the disposable site. Installation is the
initial-schema check; no upgrade from experimental Padars tables is required.

## Skills and tooling decision

- Keep the existing repo skills: `frappe-architecture`, `frappe-testing`, and
  `moodle-integration`.
- Do not add duplicate Padars skills in this phase. Add targeted guidance only
  when a later implementation phase demonstrates a recurring gap.
- Do not install Superpowers or CodeGraph. Existing Codex and repository
  instructions cover the immediate workflow, and CodeGraph is optional for
  this compact app.
- Use the current CI workflow and disposable Frappe container as the test
  infrastructure. Do not install local dependencies to repair the broken host
  virtualenv.

## Acceptance and current result

- [x] Clean disposable site created.
- [x] Frappe, ERPNext, Education, and Padars installed in dependency order.
- [x] Versions and safe branch recorded.
- [x] CI source/runtime pins aligned with the local baseline.
- [x] Shared-site ADR marked superseded and target architecture documented.
- [x] `kara.loc` not changed.
- [x] Attempt the Padars test suite on the fresh site; record the upstream test-preloader blocker below.

The app install succeeded. Both the full app test run and a focused Moodle
service test stopped before Padars tests while ERPNext's
`BootStrapTestData.make_item_group()` attempted to create a child group without
the expected `All Item Groups` parent. Do not spend Phase 0 repairing the
upstream fixture; keep this visible in the quality log and proceed with the
Phase 1 implementation plan.

## Recovery

The site is disposable and may be dropped and recreated if a later phase
changes the chosen schema. No old Padars site needs to be upgraded to recover
the development baseline. Keep site configs, backups, generated fixtures, and
credentials out of Git.
