# Development setup

The repository is `/home/weinno/projects/frappe/sites/kara.loc/workspace/frappe-bench/apps/padars` inside a local Bench checkout. See [version-baseline.md](../operations/version-baseline.md) for exact source commits and runtime versions. Padars is pre-release; use a fresh disposable site on the pinned Frappe/Education branch as the baseline. Historical Padars schemas and patches do not need upgrade compatibility.

`kara.loc` is a development site and its site config lists Padars as installed. Do not use it for schema experiments. Use `padars-phase0-fresh.local` or recreate a disposable site in the Frappe container. The host virtualenv wrapper is stale; run database-backed Bench work through the verified container runtime. No production or staging target is configured.

