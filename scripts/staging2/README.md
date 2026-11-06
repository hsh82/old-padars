# Isolated Staging 2 operations

This deployment is explicitly for `stage2.kara.loc`; it does not replace the
original `kara.loc` site. Use synthetic data. The files are controlled deployment
and test tooling, not application request instrumentation.

Current runtime root: `/home/weinno/frappe/sites/stage2.kara.loc`.
Its `.env` sets `STAGING_ROOT`, the existing supported `SOURCE_BENCH`, and
`COMPOSE_PROJECT_NAME=padars-stage2`. `compose.yaml` and `nginx.conf` are copies
of these versioned templates. No host ports are opened by this stack; its nginx
joins the existing reverse proxy network with only `stage2.kara.loc` registered.

The independent Bench layout contains `apps/padars` as a self-contained clone
on `staging-2`, `config/pids`, `logs`, `sites/apps.txt`, and separate sites/assets.
Python, Node and the installed upstream app directories are mounted read-only
from the supported source Bench. They are not independently packaged upstream
releases. Padars source, asset manifests, site storage, Redis, web, socket server,
worker and scheduler are separate. Do not run an upstream build/update in the
shared source Bench while staging tests are underway.

For a new staging deployment, create that layout first, set the site's default
in `common_site_config.json` to `stage2.kara.loc`, database host `global-db`, and
Redis endpoints `redis://redis-cache:6379` / `redis://redis-queue:6379` (socketio
also uses queue). Set socketio port 9000, web port 8000, developer_mode 0 and
apps.txt to frappe, erpnext, education, padars only. Copy the supported source
asset manifests, css/js/locale directories into its own assets directory, with
per-app symlinks to their standard mounted public paths. Clone Padars using
`git clone --local --no-hardlinks --branch staging-2 <source> <new apps/padars>`.
Do not bind the mutable development checkout as staging's app.

Start only the new Redis services, then run the native fresh installer from the
new Bench's `sites/` directory. Feed the database root password via protected
stdin, never argv or logs. The provided `install.py` refuses existing sites or
an incorrect default-site/queue configuration. It saves a random Administrator
password in `/workspace/private/staging2-credentials.json` mode 0600 and enables
muted email/staging-demo mode, with LMS disabled. Never reinstall over a tested
site to refresh fixtures.

With the runtime running, execute the versioned seed tools once using the
isolated service (the following commands run from the deployment root):

```sh
docker compose exec -T -w /workspace/frappe-bench/sites web /workspace/frappe-bench/env/bin/python /workspace/frappe-bench/apps/padars/scripts/staging2/seed.py --site stage2.kara.loc --credentials /workspace/private/staging2-credentials.json
docker compose exec -T -w /workspace/frappe-bench/sites web /workspace/frappe-bench/env/bin/python /workspace/frappe-bench/apps/padars/scripts/staging2/assessment_demo.py --site stage2.kara.loc --credentials /workspace/private/staging2-credentials.json
docker compose exec -T web bench --site stage2.kara.loc enable-scheduler
docker compose exec -T web /workspace/frappe-bench/env/bin/python /workspace/frappe-bench/apps/padars/scripts/verify_installation.py --site stage2.kara.loc --expected-app-root /workspace/frappe-bench/apps/padars
docker compose exec -T web /workspace/frappe-bench/env/bin/python /workspace/frappe-bench/apps/padars/scripts/staging2/smoke.py --credentials /workspace/private/staging2-credentials.json
docker compose exec -T web bench doctor
```

Both seeds preserve existing data/passwords after their committed marker.
`smoke.py` first verifies the site-routing headers before authentication. It uses
real HTTP sessions, native CSRF and actual endpoints, including a small empty
private intake CSV. Re-running that check creates an extra empty Data Import;
it does not execute an identity import or contact an external service.

The nginx template resolves Docker upstream names dynamically, avoiding stale
addresses after container restart. To validate/reload its **actual** config:

```sh
docker compose exec -T nginx nginx -c /etc/nginx/staging.conf -t
docker compose exec -T nginx nginx -c /etc/nginx/staging.conf -s reload
```

To promote a later approved snapshot, fetch/fast-forward only this clone,
perform any required migration explicitly against `stage2.kara.loc`, and restart
only this stack's web/worker/scheduler as needed for changed Python code. Keep
Stage 1 services and assets untouched. Back up the site DB, private/public files,
encryption key and credential file before intentional data changes. Do not run
`down -v`, drop a site or delete its test history as part of a normal update.

Manual acceptance: [Staging 2 test guide](../../docs/development/STAGING_2_TEST_GUIDE.md).
