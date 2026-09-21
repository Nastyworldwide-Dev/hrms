"""HR User can read Holiday List and Holiday List Assignment (v16_0).

21 September 2026: HR reported the holiday calendar "not available" on
Verifica. Their accounts hold HR User; ERPNext ships HR User `select` only on
Holiday List and this fork's Holiday List Assignment had no HR User row at
all, so Frappe 16 dropped both from the sidebar and Ctrl+K.

One-shot application of the same idempotent guard that runs on every migrate
(hrms.utils.holiday_access, hooks.after_migrate), so the deploy applies the
grant once whatever the after_migrate ordering. Safe to re-run.
"""

from hrms.utils.holiday_access import ensure_holiday_access


def execute():
	ensure_holiday_access()
