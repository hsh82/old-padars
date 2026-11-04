# Development setup

The repository is `/home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench/apps/padars` inside a local Bench checkout. Checked-out tags are Frappe 16.52.0, Education 16.1.0, ERPNext 16.51.1, and HRMS 16.51.0. The Education package has a metadata discrepancy: its checkout tag is `v16.1.0` while `education/__init__.py` reports `16.0.1`; resolve this in the pinned build before release. The intended runtime is Python 3.14, but the local wrapper points to an unavailable `/workspace/frappe-bench` interpreter path.

The configured `kara.loc` site has Frappe, ERPNext, HRMS, Airplane Mode, Draw, and Education installed. Padars is not installed there at audit time. Treat it as a development site only; use an isolated disposable site for schema tests. No staging target was identified during the deployment audit.

