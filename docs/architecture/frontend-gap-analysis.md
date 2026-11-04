# Frontend gap analysis

## Reference audit

Junior School `develop` was inspected at commit `3567e3f11c1ac553929f9bd3b111c306fe689d60`. It is AGPL-3.0 licensed. Padars uses it only as a behavior reference and does not copy its source.

The most reusable patterns were small `doctype_js` extensions: company-aware Link filters, academic-term filters, contextual action buttons, assessment status filtering, and roster helper actions. Junior School also contains a Vue timetable interface and several controller overrides; those are deferred because Padars does not yet have the required timetable or report-publication backend contracts.

| Feature | Education | Junior School | Padars | Decision | Phase |
| --- | --- | --- | --- | --- | --- |
| Student registration | Student and Program Enrollment forms | ID/email automation and promotion tools | Education user-link behavior exists; no bulk backend | Extend form context only; defer bulk UI | 1/2 |
| School-aware selectors | Academic-year/term queries | Company filters across forms | School Membership and school fields | Implement server-backed school queries | 1 |
| Student Group management | Roster, instructors, capacity validation | Get Students helper | Education controller plus Padars school validation | Extend selectors and capacity feedback | 1 |
| Course Offering | No annual school offering | No equivalent model | `School Course Offering` exists | Implement form and dependent Link filters | 1 |
| Moodle synchronization | Missing | Missing | Sync Operation, mapping, mock adapter, APIs | Implement offering controls and monitor | 1 |
| Student account status | Student has `user`; Education creates users by setting | Custom ID/email behavior | Existing `user` link; no retry API | Display status only; do not invent credentials | 1 |
| Assessment forms | Assessment Plan/Result and tools | Term/company filters and open-plan filter | Offering fixture fields, no period/publication model | Add offering/term selectors; defer publication | 1/2 |
| Report cards | Student Report Generation Tool | Custom print action | No publication/version API | Reuse Education print flow; defer custom publication | 2 |
| Timetable | Course Schedule/calendar | Calendar and generator | No generator model | Defer | 2 |
| Persian RTL/Jalali | Frappe locale/date formatting | No Padars-compatible contract to copy | Native translated strings and `str_to_user` | Implement CSS/translation-ready UI | 1 |

## Backend contracts intentionally not invented

- Bulk student import preview/commit and downloadable error reports.
- Returning-student registration service.
- Student account provisioning status/retry service.
- Moodle course URL/SSO navigation.
- Report-card approval/publication/version snapshots.

The frontend exposes the safe existing workflows and documents these as follow-up contracts.
