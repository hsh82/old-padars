# Phase 3 progress and verification

Date: 2026-11-05. Phase 3 is not complete.

Implemented staff-facing individual registration, returning-student draft
enrollment, and CSV preview and bounded partial processing. A private keyed
digest reservation prevents duplicate identities created through these
services. Tests exercise manager and guest authorization, retries, mismatched
contacts, batch isolation, native Education Student hooks, and prevention of
automatic account creation.

On disposable `padars-phase12-fresh.local`, the Padars-only light-mode suite
ran 43 tests successfully with six obsolete shared-site tests skipped. Other
apps' test suites were not run. The new page has not been browser-tested.

Outstanding: country-specific identifier/checksum policy, an SMS provider and
phone verification, public self-registration and its abuse controls, approval,
secure activation, minor/guardian policy, Excel upload, and durable downloadable
import results. Existing Students outside this service need a reviewed identity
reconciliation process before site-wide duplicate prevention can be claimed.
Review Frappe error and request logging settings for sensitive request data
before handling real national identifiers; verbose diagnostic tracebacks may
include function arguments. The current service is not production-ready.

Real student creation requires a configured, backed-up site encryption key,
Education's Skip User Creation setting, and a genuine email address. Contact
phone format validation does not verify phone ownership.
