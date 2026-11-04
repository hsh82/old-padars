# Padars engineering rules

- Education is the authoritative academic base; Padars owns only school tenancy, integration state, and justified extensions.
- Prefer composition, custom fields, document events, and `extend_doctype_class` over controller overrides.
- Never modify Frappe, ERPNext, Education, Moodle, or other upstream source files.
- Keep Moodle credentials server-side; never commit credentials or write tokens to logs.
- Do not run unapproved production database operations. Treat `kara.loc` as a development site only after verifying its configuration.
- Add tests for every new business rule, especially relationship validation, idempotency, and tenant isolation.
- Keep architecture documentation synchronized with model and permission changes.
- External integration jobs must be idempotent, observable, retryable, and queued only after the local transaction commits.
- Use permission-aware ORM APIs for user-visible data and preserve unrelated local changes.

