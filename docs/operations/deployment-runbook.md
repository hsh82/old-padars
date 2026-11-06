# Padars deployment runbook

Current deployment: see [Stage 1 deployment](../releases/stage1-deployment.md)
for the authorized 2026-11-06 `kara.loc` update and its backup/verification.
The discovery notes below describe the earlier environment, not today's status.

Updated: 2026-11-04

## Current environment finding

This runbook is environment-specific to the discovered host, but deployment is currently paused:

- Padars repository: `/home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench/apps/padars`.
- Bench root: `/home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench`.
- Development site: `kara.loc`; its site config currently lists Padars as installed. It is not the disposable Phase 0 test site.
- Shared infrastructure Compose file: `/home/weinno/frappe/services/docker-compose.yml`.
- Moodle Compose file: `/home/weinno/projects/lms-moodle/docker-compose.yml`; it is not the Frappe stack.
- No named staging site, Frappe app container, or deployment owner was discovered.

## Safe discovery commands

These are read-only and may be run before deployment approval:

```bash
docker compose -f /home/weinno/frappe/services/docker-compose.yml ps
docker compose ls
git -C /home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench/apps/padars status --short --branch
git -C /home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench/apps/padars log -1 --oneline
```

Do not print site configuration secrets, environment values, tokens, database passwords, or pupil data.

## Staging execution checklist

Only after a named staging site and actual app service are confirmed:

1. Enter the verified Frappe execution context (host Bench or its app container).
2. Run `bench --help` and record the supported version/flags.
3. Confirm `bench --site <staging-site> list-apps`; install Padars only if absent.
4. Run the backup procedure in the deployment plan and record checksums.
5. Run migration, build Padars assets, clear cache, and restart only the verified managed services.
6. Check `bench doctor`, worker queues, scheduler, Redis, web, socketio, reverse proxy, HTTPS, and disk/database health.
7. Execute the 10 smoke tests and the two-school negative authorization suite.
8. Record actual commands, timestamps, redacted output, screenshots, and failures in `phase1-smoke-test-results.md`.

## Stop conditions

Stop immediately for an unknown site, missing backup, failed migration, unverified service ownership, cross-school access, leaked secret, failed asset build, unhealthy queue, or any mismatch between installed and pinned app versions.

## Current development package check

From the development checkout with supported Python 3.14:

```bash
python -m pip wheel --no-deps --wheel-dir /tmp/padars-current-wheel .
python scripts/check_release_package.py /tmp/padars-current-wheel/padars-*.whl
```

This builds an isolated distribution artifact; it does not install into Bench,
change a site, build shared web assets or verify fresh-site installation.
Promoting development code to `kara.loc` remains a separate staging action.
