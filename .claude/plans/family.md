# FAMILY — the Fix Day entry point HR could not find

CLASS: a shared bundle registering itself into a key the page's own script
owns. The later assignment wins silently, so the feature exists, tests pass on
its source, and the button is simply absent from the screen.

Changed: fix_day.bundle.js stops assigning frappe.listview_settings; each
doctype's list script registers the entry point itself.

Call sites the machine lists for `hrms.fix_day.*` and for the two list scripts:

* hrms/public/js/fix_day.bundle.js — same-root (the assignment is removed; the
  screen, `open`, `from_taps` and the new `from_attendance` stay)
* hrms/hr/doctype/employee_checkin/employee_checkin_list.js — same-root (now the
  one owner of that key, and registers the button)
* hrms/hr/doctype/attendance/attendance_list.js — same-root (same, plus
  `employee` in add_fields so a ticked row can name its own day)
* hrms/hr/report/shift_attendance/shift_attendance.js:142 — not-affected: opens
  the screen with frappe.require + hrms.fix_day.open, touches no listview_settings
* hrms/hr/report/unclaimable_days/unclaimable_days.js:26 — not-affected: same shape
* hrms/hooks.py (app_include_js) — not-affected: the bundle still loads at boot,
  which is what makes hrms.fix_day.enabled() answerable when a list opens

Rest of the app: no other file assigns frappe.listview_settings for a doctype
that a bundle also writes (checked below).

LOCK:
* regression (the instance): the two list tests load the bundle and then the
  list script in Desk's real order and ask the resulting onload what it
  registered — the failing shape, executed rather than read.
* invariant (the class): no file under hrms/public/js may assign
  frappe.listview_settings, enforced in hrms/public/js/fix_day.bundle.test.js.
