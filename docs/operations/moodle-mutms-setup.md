# Moodle and MuTMS connection setup

This setup is company-operated. School Managers do not configure Moodle
services, tokens, tenant settings, course-role IDs, or automatic roster-sync
policy.

## Moodle prerequisites

1. Use a Moodle release with the matching MuTMS Multi-tenancy core patch and
   plugin. The recorded development source is Moodle 5.2.4 with MuTMS
   `tool_mutenancy` 5.2.4.01. MuTMS requires its Moodle core patch; installing
   only the plugin package is insufficient.
2. Enable Moodle web services and the REST protocol only after the service is
   ready to be used.
3. Create a custom external service with **Authorised users only** enabled.
   Add only these functions:

   - `core_webservice_get_site_info`
   - `tool_mutenancy_get_tenants`
   - `tool_mutenancy_create_tenant`
   - `tool_mutenancy_allocate_user`
   - `core_course_get_categories`
   - `core_cohort_get_cohorts`
   - `core_user_get_users_by_field`
   - `core_user_create_users`
   - `core_user_update_users`
   - `core_course_get_courses_by_field`
   - `core_course_create_courses`
   - `core_course_update_courses`
   - `enrol_manual_enrol_users`
   - `enrol_manual_unenrol_users`
   - `core_enrol_get_users_courses`

For instructional grade discovery also add `gradereport_user_get_grade_items`
and review its capabilities in the installed site's API Documentation. It
requires course grade-report access, including other-user grade visibility for
the company service account. Never grant those service capabilities to students
or browser code. The endpoint is read-only; Padars does not update Moodle grades.

For learning discovery add `core_course_get_contents` and
`core_completion_get_activities_completion_status`. Review their exact
capabilities in the installed API Documentation. Padars fetches per-user
completion and excludes content files. The service's visibility flags are not
forwarded as proof of student access; teachers explicitly publish metadata.

4. Assign the service user only the capabilities shown by the target Moodle's
   API Documentation for those functions. MuTMS tenant lookup requires
   `tool/mutenancy:view`; tenant creation requires the system-context
   `tool/mutenancy:admin`; allocating an existing global account requires
   `tool/mutenancy:allocate`. Moodle core function capabilities are also
   listed on the target site's API Documentation page.
5. Authorize only the integration service user. Restrict the token to the
   Frappe server's source IP and an expiry where the deployment permits it.
   Do not use a School Manager's Moodle account or share a site-administrator
   credential with Padars.
6. Read the actual Moodle role IDs from this site's role administration and
   API documentation. Configure Teacher, Student, and a course-scoped School
   Manager viewing role. The School Manager role must not manage users, tenants,
   site configuration, or other tenants. No role ID is hardcoded in Padars.
   Tenant members are isolated from other tenants, but MuTMS permits access to
   standard non-tenant courses by default; restrict those categories if needed.

Moodle 5.2 documentation says the site's own API Documentation is authoritative
for which functions and capabilities its enabled service permits. It also
recommends enabling only required protocols and functions, authorizing specific
users, and applying token IP/expiry restrictions. See [Using web services](https://docs.moodle.org/502/en/Using_web_services),
[External Services](https://moodledev.io/docs/5.2/apis/subsystems/external),
and [MuTMS web services](https://docs.mutms.org/mutenancy/web-services/).

## Frappe configuration

1. Add the exact Moodle hostname to the deployment-managed
   `padars_moodle_allowed_hosts` configuration. Padars rejects HTTP, unlisted
   hosts, nonstandard ports, credentials in URLs, query strings, and fragments.
2. As a company `Padars Moodle Manager` or `Padars Platform Administrator`,
   open **LMS Settings** and set the HTTPS base URL, REST token, connection
   timeout, default tenant member limit, and the three Moodle role IDs.
3. Use **Check Moodle Connection**. This calls
   `core_webservice_get_site_info` and displays only non-secret site metadata.
4. Enable Moodle on an active School. Padars queues MuTMS tenant creation
   after the local transaction commits. Confirm the connected tenant ID,
   category ID, and cohort IDs on the School record and inspect the sync
   operation before creating courses.

The token remains in Frappe's Password field and is sent in the POST body to
`/webservice/rest/server.php`; it is not sent in the URL, browser, or sync
diagnostics. Never paste tokens into tickets, logs, or source files.

## Initial school workflow

1. Create or select the Education Course and Student Group, then create a Padars
   School Course Offering for that School, year, program, and group.
2. Assign one active Instructor linked to an enabled Frappe System User.
3. Request Moodle course provisioning. Padars creates or reconciles the course
   under the MuTMS tenant category, then queues the Teacher and School Manager
   course enrollments with the configured Moodle roles.
4. Select eligible students in **Enroll Students in Moodle**. Eligibility is
   checked again on the server: activated linked User, active group membership,
   and a submitted matching Program Enrollment.
5. Verify successful tenant, course, user, and enrollment operations and use
   **Open Moodle Course** to confirm the intended course URL.

Automatic roster synchronization is a company-controlled School setting. A
School Manager can explicitly request eligible student enrollments without
changing that policy.

This repository's contract tests use a fake client. They do not prove that a
specific Moodle service is configured correctly or that email/password
delivery works. Record live tenant/course/user/enrollment results separately
after an authorized operator configures the service on the disposable target.
