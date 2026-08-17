"""Widen `Employee.performance_band` to accept E3.

SYNC-00053 on verifica-live rejected 173 of 289 employees on one value:

    Employee: HR-EMP-00104:  Performance Band cannot be "E3".
        It should be one of "", "B", "C", "D", "E1", "E2", "F"

The source ERP's own employee data uses E3, and the hub's field definition did
not allow it, so those people simply did not exist on the hub — and with them
went their attendance, their check-ins and their leave, because every one of
those rows is skipped when its employee is absent. Losing a person's record over
a missing dropdown option is not a trade worth making; the source is
authoritative for employee data.

`hrms.setup.create_performance_band_field` is not reachable from the install
path — it is a standalone `bench execute` helper — so a site that already has
the field will never see the new option without this patch.

Idempotent: `create_custom_fields(update=True)` rewrites the options of a field
that is already there and creates it if it is not, so a re-run and a fresh
install both end in the same place.

If E3 turns out to be bad data on the source rather than a real band, correct it
there and narrow the option again — the direction of authority is what decides
it, not this file.
"""

import frappe

from hrms.setup import create_performance_band_field


def execute():
	frappe.logger("hrms").info("[patch] widening Employee.performance_band to include E3")
	create_performance_band_field()
