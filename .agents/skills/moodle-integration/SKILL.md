---
name: moodle-integration
description: Design and implement tenant-aware Moodle/MuTMS integration with secure credentials, mappings, idempotent jobs, retries, and mockable adapters.
---

# Moodle integration

Keep external communication in `padars.integrations.moodle`; DocType controllers should persist local intent, not make HTTP requests.

## Boundaries

- Store credentials in a Single DocType Password field and never expose them to browser code or logs.
- Use stable local-to-remote mappings with explicit remote context. Do not equate MuTMS tenant IDs and Moodle category IDs without verified API semantics.
- Persist sync operations and enrollment state. Use an idempotency key for every requested operation.
- Enqueue only after commit, make retries safe, preserve diagnostics without secrets, and model observed versus desired state.
- Separate SSO from provisioning.

## Testing

Define an adapter protocol and use a deterministic mock adapter for tests and local development. Contract tests should assert request shape and mapping behavior without claiming live Moodle success.

