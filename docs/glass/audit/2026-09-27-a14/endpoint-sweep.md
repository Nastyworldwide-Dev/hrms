# Endpoint sweep, 27 Sep 2026 (alpha.14 S4)

Method: AST over every `@frappe.whitelist` in `hrms/` (296 functions), each
tagged for "writes to the database" and "has a permission gate". Then read by
hand where the tags were not conclusive. Tests and patches excluded.

## Writes reachable by GET (CSRF skipped): 16 found, 15 closed
Fixed in 3b127a650 — all POST-only; `hrms/tests/test_desk_writes_are_post_only.py`
walks every whitelisted writer outside `hrms/api` so the next is caught.
Bench proof (`frappe.handler.is_valid_http_method`): GET refused, POST allowed.

Named exception: `employee_checkin.add_log_based_on_employee_field` — biometric
device ingestion, token-authenticated (no CSRF risk), gated by create permission
on Employee Checkin, and device bridges may send GET.

Also closed this release: push subscribe/unsubscribe (1c802b294).

## PWA API (`hrms/api`) with no gate the scan could see: 69
Read by hand where the caller passes an employee, a document name or a date:

| Endpoint | Verdict | Why |
|---|---|---|
| attendance_fix_day.add_tap / rebuild_day / save_day / get_day / plan_day / fix_days | safe | `_require_hr()` first, then `_require_employee` |
| attendance_master_edit.get_days / hand_back | safe | `_require_hr()` |
| approval.get_decision_actions / can_decide | safe | `_decision_access` (can_decide goes through it) |
| kpi.get_employee_kpi | safe | `_require_kpi_read` |
| roster.get_events | safe | `_validate_employee_filters` (company fence) |
| __init__._download_pdf | safe | Frappe `download_pdf` runs `validate_print_permission` |
| __init__.mark_notifications_as_read | safe | names AND to_user = session user (alpha.13) |
| helpdesk.get_ticket | UNVERIFIED | uses Helpdesk's own `get_one(is_customer_portal=True)`; Helpdesk is not installed on the test bench, so its fence could not be run |
| the rest (no caller-chosen record) | safe | read only the session user's own data, or site config |

## Open
- helpdesk.get_ticket: verify on a site with Helpdesk installed (a staff user
  must not read another's ticket by name).
