# Phase 11 verification progress

Phase 11 is partial and not a release approval. Stage 1 remains pinned to
`81792d9`; the development worktree is `codex/full-product`. No shared asset
build, staging restart, staging migration or real-school test was performed.

## Distribution package gate

The current app built successfully as a Python 3.14 wheel using pip's isolated
Flit build environment. `scripts/check_release_package.py` checks the actual
wheel for required schema/controller files, every packaged DocType controller,
portal HTML/context pairs, required workspace/pages/fixtures/print format,
Python/JSON syntax, declared Education dependency, referenced hook assets,
metadata/runtime requirements and prohibited environment/cache paths. The CI
workflow now runs this gate before setting up Bench.

The wheel passed. A deliberately incomplete temporary wheel was rejected for a
missing grade-review controller and school-portal template. This artifact check
does not install or migrate a database and does not verify JavaScript behavior.

The app-owned Padars Guardian role is created before installation; install and
migration helpers also enforce its portal-only setting if Frappe created it
first. The native Education Guardian role is untouched. A focused database test
passed for correcting the app-owned role and creating a guardian Website User.

The latest full scheduling/assessment module passed 16 integration tests before
that narrow installation-role adjustment; the affected guardian test passed
after it. Fourteen offline Moodle adapter contracts passed. Full Padars tests,
fresh current-build site installation, live integrations, browsers, concurrency,
backup restore and product scenarios A–J remain open.

Native form validation defect: Frappe's client mandatory checker runs before the
server populates readonly version/binding/range fields. New Scheme, Moodle Grade
Mapping and Session Attendance Policy forms now use conditional client mandatory
rules for generated fields, retaining server reqd validation. The installed
Frappe checker was executed against all three schemas in a small Node Desk-data
harness: new forms pass, missing user inputs fail, and removing the fix reproduces
the original failure. CI includes this check after Bench installation. This is
not a DOM/browser test. Narrow academic-reference role access was also tested:
manager configuration works while User/customization administration stays denied.
