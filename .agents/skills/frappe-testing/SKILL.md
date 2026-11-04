---
name: frappe-testing
description: Create and verify Frappe tests for validation, relationships, permissions, tenant isolation, migrations, and repeatable setup.
---

# Frappe testing

Use Frappe's installed test conventions, normally `FrappeTestCase`, and keep tests focused on business invariants.

## Required coverage

- Valid and invalid Link relationships across School, Academic Year, Program, Course, Student Group, and Instructor.
- Duplicate prevention for compound business keys where MariaDB cannot express the rule as one field.
- Direct document access, list/report query conditions, and API permission boundaries for shared-site school data.
- Sync operation state transitions, idempotency, retry behavior, and mapping uniqueness.
- Repeatable fixtures and clean-site installation/migration where a Frappe site is available.

Use a mock external adapter for integration tests. Never call Moodle or use real credentials in tests.

If the local test runtime is unavailable, run static validation and document the exact blocked command and missing dependency; never report an unexecuted test as passing.

