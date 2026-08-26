"""Re-link the notification templates HR Settings needs to be saveable at all.

THE SYMPTOM, from production: HR Settings would not save. Any change, on any
tab, was refused with

    Please fill the following mandatory fields before saving:
      Leave Approval Notification Template is required.
      Leave Status Notification Template is required.

Both fields carry `mandatory_depends_on: eval: doc.send_leave_notification == 1`.
Send Leave Notification was ticked and both were blank, so the form could not be
saved by anybody — which is why the geolocation setting on a completely
different tab could not be turned on.

TWO FAILURES, one cause. The blank templates also meant

    template = frappe.db.get_single_value("HR Settings", "leave_approval_notification_template")

returned '' every time somebody applied for leave, so no approver was ever
emailed. The setting said "send them", the template was blank, nothing sent and
nothing errored. Silent, like everything else in this class.

WHY A PATCH AND NOT A DEFAULT. `setup.update_hr_defaults` already sets both, and
every branch has that code — it just runs on `after_install` only. A site whose
install predates it, or whose values were cleared, is never repaired. Defaults
fix new sites; this fixes the one people are using.

Only fills what is EMPTY, and only when the template it would link actually
exists. Never overwrites a choice somebody made, and never invents a link to a
missing record — that would trade an empty mandatory field for a broken one.

Safe to re-run: the second pass finds both fields set and does nothing.
"""

import frappe

#: HR Settings field -> the Email Template `setup.make_fixtures` ships for it.
DEFAULTS = {
	"leave_approval_notification_template": "Leave Approval Notification",
	"leave_status_notification_template": "Leave Status Notification",
}


def execute():
	settings = frappe.get_single("HR Settings")
	filled = {}

	for field, template in DEFAULTS.items():
		if settings.get(field):
			continue  # somebody chose one; not ours to change
		if not frappe.db.exists("Email Template", template):
			frappe.log_error(
				title="HR Settings default template is missing",
				message=(
					f"{field} is empty and the Email Template '{template}' does not exist on "
					f"this site, so it could not be linked. HR Settings will stay unsaveable "
					f"while Send Leave Notification is ticked.\n\n"
					f"Create that Email Template, or untick Send Leave Notification."
				),
			)
			continue
		settings.set(field, template)
		filled[field] = template

	if not filled:
		print("[restore_hr_settings_defaults] both templates already set")
		return

	# ignore_mandatory: the very field this patch exists to fill is the one the
	# form refuses to save without, and the other one may still be blank on the
	# first pass if its template is missing. Saving what we CAN fix beats
	# refusing the whole repair.
	settings.flags.ignore_mandatory = True
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.db.commit()
	print(f"[restore_hr_settings_defaults] linked {len(filled)}: {filled}")
