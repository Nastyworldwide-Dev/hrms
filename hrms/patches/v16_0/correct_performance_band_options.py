"""Put `Employee.performance_band` back to the real band scheme, and clear E3.

E3 was added to this field for one reason: SYNC-00053 rejected 173 employees
because the source held that value and the hub's Select would not accept it. HR
have since confirmed E3 was their own data-entry error on the source — so the
band scheme is, and always was, B / C / D / E1 / E2 / F.

Widening a destination's field to accommodate bad source data is the wrong
direction of fix. It also treats a symptom: the reason a single unexpected value
could cost 173 employee records was that the mirror wrote each row verbatim and
let Select validation reject the whole document. That is fixed properly in
`hrms.sync.runner._narrow_to_local_schema`, which drops a value this site cannot
represent, keeps the record, and names the field on the run. So the option is no
longer needed to load anyone — and any band the source invents next costs one
field instead of a person.

Two things to undo, because the earlier patch already ran on the live hub:

* the option list, rewritten through the same helper the install path uses;
* any `E3` already stored on an Employee, cleared to blank. It was never a valid
  band here, and leaving it would keep a value the field no longer offers —
  invisible in the form, but still in the database and still in reports.

Idempotent: `create_custom_fields(update=True)` rewrites an existing field, and
the UPDATE matches nothing once it has run.
"""

import frappe

from hrms.setup import create_performance_band_field


def execute():
	create_performance_band_field()

	stale = frappe.db.count("Employee", {"performance_band": "E3"})
	if not stale:
		return

	frappe.db.set_value(
		"Employee",
		{"performance_band": "E3"},
		"performance_band",
		"",
		update_modified=False,
	)
	frappe.logger("hrms").warning(
		"[patch] cleared E3 from %s employee record(s) — never a valid band here", stale
	)
