# Padars rollback and recovery runbook

Updated: 2026-11-04

## Current recovery evidence

No staging deployment or backup was performed in this run. There is therefore no Padars staging backup path or restore checksum to report. The development site `kara.loc` was not changed.

## Before any staging migration

Record, outside Git and outside the threatened deployment filesystem:

- database backup path and SHA-256 checksum;
- public-files backup path and checksum;
- private-files backup path and checksum;
- site/app versions and Git commit;
- database schema migration output;
- restore owner and tested restore target.

Use the verified deployment context's supported backup command, discovered from `bench --help` or the real app service. Do not guess container names or backup paths.

## Rollback decision

Rollback is required for failed migration, schema corruption, cross-school leakage, broken login/session behavior, missing assets, queue failure, or incorrect grade/report data. Reverting Git alone is not a rollback because migrations and data changes may be irreversible.

## Restore procedure template

1. Stop the verified staging rollout and preserve logs; do not delete evidence.
2. Put the verified staging URL into maintenance mode using the actual deployment mechanism.
3. Restore the database backup to a disposable verification target first when feasible.
4. Restore public/private files from the recorded backups.
5. Restore the compatible application commit/image and run only the verified migration/restore commands.
6. Clear cache, restart the verified web/worker/scheduler services, and run health checks.
7. Re-run the two-school authorization tests and smoke tests.
8. Record the restore result, timing, data-loss window, and follow-up defect.

No restore command is authorized against `kara.loc` or any production target by this document.
