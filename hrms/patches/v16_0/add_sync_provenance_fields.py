"""Create the cross-instance provenance custom fields on already-installed sites.

`synced_from_instance` is defined once, in `hrms.sync.runner.get_provenance_custom_fields()`,
and merged into `hrms.setup.get_custom_fields()`. That covers **fresh installs only**:
`get_custom_fields()` runs from `after_install`, and `bench migrate` on an
already-installed site never calls it. So on every existing site the field simply
does not exist — verified on the live hub, where `Employee.synced_from_instance`
was absent. Without it the mirror cannot stamp provenance and `hrms.sync.parity`
cannot count mirrored rows, which blocks cutover.

This patch closes that gap for existing sites. It deliberately imports the SAME
definitions the install path uses rather than restating them, so the two paths
cannot drift: add a doctype to `STAMPED_DOCTYPES` and both fresh installs and this
patch pick it up. Only the stamped doctypes appear there — Company and the
create-only masters are HR-owned on this hub and carry no stamp, so giving them
the field would advertise a provenance that is never written.

Idempotent: `create_custom_fields(..., update=True)` is a no-op on a field that is
already there and correct, so a re-run — or a run on a site where the fresh-install
path already created the fields — changes nothing.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.sync.runner import get_provenance_custom_fields


def execute():
	fields = get_provenance_custom_fields()
	frappe.logger("hrms").info("[sync] ensuring provenance custom fields on %s", ", ".join(sorted(fields)))
	create_custom_fields(fields, update=True)
	frappe.db.commit()
