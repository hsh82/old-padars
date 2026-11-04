# Padars frontend guide

## Locations

- Shared browser helpers: `padars/public/js/common/`.
- Education form extensions: `padars/public/js/education/`.
- Padars-owned form scripts: `padars/public/js/`.
- Custom Desk pages: `padars/padars/page/<page_name>/`.
- Shared styling: `padars/public/css/padars.css`.

## Hooks

`padars/hooks.py` registers shared assets and uses `doctype_js` to extend Education forms without modifying Education source. Keep handlers short and guard optional Custom Fields with `frm.fields_dict`/`hasField` checks.

## Backend calls

Use `frappe.call` for whitelisted Padars APIs and permission-aware `frappe.client.get_list` for list data. Browser filters improve usability only; Python permissions and validation remain authoritative. Never call Moodle directly from JavaScript or expose credentials.

## Form patterns

Use `frm.set_query` for server-side Link filtering, clear dependent fields when a new school context is selected, and use request tokens or disabled controls to prevent stale or duplicate actions. Use translated strings with `__()` and Frappe's `frappe.datetime.str_to_user` for localized date display.

## Pages and builds

Standard pages live below the Padars module and use native `frappe.ui.make_app_page`. The current app has no separate npm build; validate JavaScript with `node --check` and run the Bench asset build once a working Bench runtime is available.

The dependency-free shared-helper smoke test runs with `node --test tests/frontend/*.test.js`.
