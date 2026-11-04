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

From a working Bench with the app installed:

```bash
bench --site <isolated-site> migrate
bench --site <isolated-site> set-config allow_tests true
bench --site <isolated-site> run-tests --app padars
```

CI provisions the dependency chain in order: ERPNext, Education, then Padars, so the clean-site test matches the declared application dependencies.

The checked-out Bench currently has a stale virtualenv shebang and the host lacks `libmariadb.so.3`; the commands must be re-run once the local runtime is repaired or in CI. Static metadata and syntax checks remain valid independently.

