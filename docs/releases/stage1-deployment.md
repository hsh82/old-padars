# Stage 1 staging deployment

Date: 2026-11-06. User explicitly authorized updating `kara.loc` for manual
testing. This is a partial-feature staging release, not full MVP acceptance.

## Environment and preservation

- Verified `kara.loc` has developer mode enabled and Education/Padars already
  installed. Padars was upgraded in place, not installed a second time.
- Before deployment, School, Student, Student Group, Course Schedule and
  Assessment Result counts were zero. No demo school or student records were
  inserted; initial setup is a manual test scenario.
- Preserved user changes to AGENTS.md and padars/tests/test_registration.py.
- Full database/config/public/private-files backup completed with
  `bench --site kara.loc backup --with-files --ignore-backup-conf`.
- Backup copies and SHA256SUMS are outside the Bench at
  `/home/weinno/.local/share/padars-staging-backups/20261106_132639/`.
  This directory contains secrets and is not committed. A restore was not tested.

## Deployment and checks

- `bench --site kara.loc migrate`: exit 0; log in the Frappe container at
  `/tmp/padars-kara-stage1-migrate.log`.
- `bench build --app padars`: exit 0; log at
  `/tmp/padars-kara-stage1-build.log`.
- `bench --site kara.loc clear-cache`: exit 0.
- Restarted the managed Frappe development web program and the short worker,
  long worker and scheduler containers to load the current code.
- `bench --site kara.loc doctor`: exit 0, four workers online.
- Through the host proxy with Host `kara.loc`, `/login`, `/api/method/ping` and
  `/assets/padars/js/education/assessment_result_tool.js` returned HTTP 200.
- Verified required Padars DocTypes, setup/registration/monitor pages and
  manager Assessment Result Tool permission exist in the target database.
- Fixed Teacher Workload access through the report wrapper for School Managers.
  The focused staff module passed 5 tests on `padars-phase12-fresh.local`,
  including allowed manager and denied unrelated-user report access.
- No automated application suite, authentication experiment or seed script was
  run against `kara.loc`. Authenticated browser journeys await manual testing.

## Access and limits

Use `http://kara.loc/app/padars-setup` with existing Administrator credentials.
The host shell does not resolve the hostname automatically; HTTP was verified
using a Host/DNS override to the local proxy. Client machines need appropriate
DNS/hosts mapping to the staging server. HTTPS is not configured for this name
on the current proxy, so use synthetic data for this preview.

Follow [the manual test guide](stage1-manual-test-guide.md). Academic setup,
registration, manual attendance and draft/individual assessment approval are
the test scope. Live LMS, SSO, activity evidence, PlugNmeet integration, official
report-card publication and complete student/guardian dashboards are outside
this staged feature set. Their implementation/verification remains outstanding.

The latest readiness assessment is [the MVP audit](../quality/mvp-readiness-audit.md).
Future work should be driven by the manual test findings before expanding scope.
