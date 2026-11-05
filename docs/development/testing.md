# Testing and verification

## Static checks

```bash
ruff check .
find padars -type f -name '*.js' -print0 | xargs -0 -n1 node --check
node --test tests/frontend/*.test.js
python3 -m compileall -q padars
find padars -type f -name '*.json' -print0 | xargs -0 -n1 jq empty
git diff --check
```

The dependency-free frontend smoke tests cover shared school-context and LMS status helpers. They do not replace browser tests against a running Desk site.

## Database-backed checks

Use a fresh disposable site on the pinned app commits. The current local
verification site is `padars-phase0-fresh.local` inside the Frappe container.
Run these commands from that Bench; never substitute `kara.loc`:

```bash
bench --site padars-phase0-fresh.local set-config allow_tests true
bench --site padars-phase0-fresh.local run-tests --app padars
```

CI provisions the dependency chain in order: ERPNext, Education, then Padars, so the clean-site test matches the declared application dependencies.

Do not run migration-upgrade checks for experimental Padars schemas; the app is
pre-release and old schema compatibility is out of scope. The host virtualenv
symlink is stale, so use the verified Frappe container or pinned CI runtime.
Static metadata and syntax checks do not substitute for the fresh-site test.

