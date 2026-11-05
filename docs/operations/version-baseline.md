# Development version baseline

Verified: 2026-11-05. This is the pinned development baseline for the Padars
pre-release application. Source commits are the compatibility contract; release
or migration compatibility with prior Padars schemas is not required.

| Component | Version / source | Use |
| --- | --- | --- |
| Frappe | 16.52.0, `4515014c87ece6cb20ee91d2cfb121c5cbd1ff4a` | Framework |
| ERPNext | 16.51.1, `5af6561f5aa48104559692fb4fd82f2580e8d338` | Education dependency |
| Education | tag `v16.1.0-dirty`, commit `93bc7075753369457919720690f80c6d2207b5f2`; package reports `16.0.1` | Academic source of truth |
| Padars | `0.0.1`, commit `e254e187357fcf5636a6de3208f1606676c8fcfa`, branch `codex/stage1-tenancy-security` | Safe development branch |
| HRMS | 16.51.0, `2478afc7a8f4959d500f6d17522853f0d244e38f` | Present in the host Bench; not required by the clean Padars test site |
| Bench CLI | 5.31.0 in the running Frappe container | Site and test commands |
| Python | 3.14.2 in the runtime; CI pinned to 3.14.2 | Backend |
| Node.js | 24.19.0 on the development host; CI pinned to 24.19.0 | Frontend tooling |
| MariaDB | 10.6 host image; CI aligned to `mariadb:10.6` | Database |
| Redis | 8 host image; CI aligned to `redis:8-alpine` | Queue/cache |
| Moodle | 5.2.4 (Build 20261005), branch 502 | Local LMS code tree |
| MuTMS | `tool_mutenancy` v5.2.4.01, plugin version `2026092201`, requires Moodle `2026042004` and `tool_mulib` | Local MuTMS code tree |

The Education checkout is dirty only under its generated `public/node_modules`
tree. Do not base a release on that worktree without reproducing the build from
the pinned commit. HRMS is informational; Padars does not depend on it in its
clean-install path.

## Sites

- `kara.loc` is a local development site with developer mode enabled by the
  Bench common configuration. Its site config lists Padars as installed. It was
  not changed during Phase 0.
- `stage1.local` is the earlier disposable test site. It has Frappe, ERPNext,
  Education, and Padars installed.
- `padars-phase0-fresh.local` was created during Phase 0 from the pinned branch
  and installed in the order Frappe, ERPNext, Education, Padars. It is the
  current clean-install verification site.

Site credentials, database passwords, Moodle tokens, and site configuration
values are deliberately excluded from this document. Do not commit site
configuration, local database dumps, or Moodle data.

## Runtime caveat

The host Bench `env/bin/python` symlink points to a missing `/workspace` path,
and host Python is 3.12.3. Use the running Frappe application container for
Bench operations; its Bench CLI is 5.31.0 and its runtime is Python 3.14.2.
This runtime selection is documented so future work does not mistake host
syntax checks for a database-backed Frappe test run.

## Moodle verification boundary

The Moodle and MuTMS versions above were read from the running local code tree.
The live site API documentation, enabled web-service functions, service
account capabilities, tenant IDs, category/cohort mappings, and SSO settings
were not inspected in Phase 0. Phase 8 must verify those against the actual
Moodle site before enabling remote writes.
