---
name: frappe-architecture
description: Design and extend Frappe DocTypes safely after inspecting installed metadata, controllers, hooks, permissions, and migration conventions.
---

# Frappe architecture

Use this skill for Padars model design or changes to Education integration points.

## Workflow

1. Inspect the installed app version and actual DocType JSON/controller before proposing a model.
2. Reuse Education records when their lifecycle and uniqueness semantics cover the requirement. Add a Padars DocType only for a distinct ownership or lifecycle boundary.
3. Prefer Custom Fields, fixtures, `doc_events`, `extend_doctype_class`, and independent services. Do not edit upstream app files or use `override_doctype_class` without a documented reason.
4. Define Link, Dynamic Link, and Child Table targets explicitly. Put relationship and cross-school validation in server-side controllers or services.
5. Document naming, mandatory/unique rules, permissions, ownership, and migration behavior before adding schema.
6. Keep shared-site tenancy checks in permission hooks and server-side validation; frontend filters are not isolation.

## Safety

- Preserve existing local changes.
- Do not run destructive migrations or production database writes.
- Keep secrets in Password fields or Frappe secure settings, never source or logs.
- Update `docs/architecture/` and `docs/development/progress.md` when the model changes.

