# Historical Stage 1 disposable environment baseline

> This describes the earlier `stage1.local` setup. The current clean-install
> baseline is [version-baseline.md](version-baseline.md), with no requirement
> to migrate the experimental Padars schema.

Updated: 2026-11-04. No new Python or JavaScript dependency was introduced.
Padars requires the Bench-managed Education application, so compatibility is
pinned operationally to the exact checked-out revisions below rather than
adding a second package resolver.

| Component | Version / revision |
| --- | --- |
| Python | 3.14 (Bench environment) |
| Frappe | 16.52.0 / `4515014c87ece6cb20ee91d2cfb121c5cbd1ff4a` |
| ERPNext | 16.51.1 / `5af6561f5aa48104559692fb4fd82f2580e8d338` |
| Education | reports 16.0.1 / `93bc7075753369457919720690f80c6d2207b5f2` |
| Padars baseline | `bfd8d7497170e3e4272737fd15f1f1d623fa3862` |

The disposable site is `stage1.local`; it is not staging or production. This
record predates the Phase 0 clean site. `kara.loc` is a development site and
its config lists Padars as installed; Phase 0 did not operate on it. Credentials
are not recorded here.

Before a future staging deployment, pin container image digests or equivalent
source revisions, record the generated site secret in the approved secret
manager, and rotate any exposed development credential. Do not commit `.env`,
site configuration, backups, or generated test data.
