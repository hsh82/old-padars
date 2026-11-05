# Padars Phase 1 deployment plan

Updated: 2026-11-04

## Release candidate

- Repository: `/home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench/apps/padars`
- Branch: `dev`
- Last verified code commit: `71f5a4c`
- Expected deployment artifact: a clean commit/tag after the requirements documents and any final fixes are reviewed.
- No push, tag, image build, or deployment was performed during this run.

## Target identification

**Staging target: NOT IDENTIFIED.**

The inspected site `kara.loc` is a local development site; its current site config lists Padars as installed. It is not approved for staging deployment. Phase 0 uses the isolated `padars-phase0-fresh.local` site instead.

The discovered topology is mixed:

- Host Bench checkout: `/home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench`.
- Global Docker infrastructure: `/home/weinno/frappe/services/docker-compose.yml`, containing the shared MariaDB/proxy project.
- Docker Compose projects for Moodle and PlugNmeet exist separately and must not be treated as the Frappe application stack.
- No Frappe web, worker, scheduler, or socketio application container was identified in the running container list.
- No usable `bench` executable is on PATH; the cached Bench wrapper points at an unavailable `/workspace/frappe-bench` path.

Because ownership, target site, application service, public URL, backup destination, and rollback authority are not established, deployment is intentionally stopped before backup, migration, install, build, restart, or data mutation.

## Compatibility record

- Frappe: tag `v16.52.0`.
- ERPNext: tag `v16.51.1`.
- HRMS: tag `v16.51.0`.
- Education: checkout tag `v16.1.0`; the package `__version__` currently reports `16.0.1`, which must be reconciled in the pinned build.
- Padars: commit `71f5a4c`.
- Python intended by `pyproject.toml`: `>=3.14`; local executable wrapper is broken.
- Node available locally: 24.19.0; CI requests Node 24.
- MuTMS: no endpoint, credentials, sandbox tenant, or verified service contract available.

## Required staging preflight

Before deployment, the release owner must provide a named disposable/staging site and confirm:

1. Site name, URL, environment owner, and explicit non-production classification.
2. Actual Frappe deployment method and the service/container that owns the app.
3. Installed Frappe, ERPNext, Education, HRMS, and Padars versions.
4. Working Bench/Python runtime and database connectivity.
5. Queue, Redis, scheduler, web, socketio, reverse proxy, HTTPS, disk, and database health.
6. MuTMS sandbox endpoint, tenant policy, API capability list, and test credentials stored outside Git.
7. Backup destination outside the deployment filesystem and a restore owner.
8. A synthetic two-school test dataset and role accounts.

## Schema and asset change inventory

- Padars DocTypes: School, School Membership, School Course Offering, LMS Settings, LMS Entity Mapping, LMS Enrollment State, and LMS Sync Operation.
- Education fixtures: Padars Custom Fields for Program Enrollment, Student Group, Course Schedule, Assessment Plan, and Assessment Result.
- Hooks: school permissions, Education document events, frontend assets, and hourly stale-sync recovery.
- No Padars migration patch currently exists; installation/migration must be tested on a clean disposable site before any staging run.
- No generated assets or private files are committed.

## Staging deployment sequence (not executed)

After target verification and backup approval, discover the exact commands supported by that target's Bench/container:

```text
<verified execution context> bench --help
<verified execution context> bench --site <staging-site> list-apps
<verified execution context> bench --site <staging-site> backup --with-files
<verified execution context> bench --site <staging-site> install-app padars   # only if absent
<verified execution context> bench --site <staging-site> migrate
<verified execution context> bench build --app padars
<verified execution context> bench --site <staging-site> clear-cache
<verified execution context> bench doctor
```

If the verified deployment is container-managed, run equivalent commands inside the actual Frappe app service. Do not run these commands against `kara.loc` or a Moodle container by assumption.

## Downtime and rollback policy

- Use a maintenance window for migration and asset restart unless the verified deployment owner proves zero-downtime behavior.
- Take database, public-file, and private-file backups before migration.
- Record backup paths, checksums, database/site versions, and restore commands in the deployment record.
- Git revert alone is not a database rollback. If migration is not reversible, restore the database and files to a disposable verification target before any staging recovery.
- Stop rollout on migration error, permission leak, failed queue health, asset failure, or any cross-school negative-test failure.
