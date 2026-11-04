# Testing and verification

## Static checks

```bash
ruff check .
git diff --check
```

## Database-backed checks

From a working Bench with the app installed:

```bash
bench --site <isolated-site> migrate
bench --site <isolated-site> set-config allow_tests true
bench --site <isolated-site> run-tests --app padars
```

CI provisions the dependency chain in order: ERPNext, Education, then Padars, so the clean-site test matches the declared application dependencies.

The checked-out Bench currently has a stale virtualenv shebang and the host lacks `libmariadb.so.3`; the commands must be re-run once the local runtime is repaired or in CI. Static metadata and syntax checks remain valid independently.

