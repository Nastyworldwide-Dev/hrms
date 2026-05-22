"""Geofence Reject Log — append-only record of strict-mode check-in blocks.

Written by `nsty.overrides.employee_checkin.CustomEmployeeCheckin
._throw_strict_geofence` before the throw, wrapped in try/except so a log
failure never blocks the user's check-in attempt.

Read by the `out_of_radius_activity` Script Report.
"""

from frappe.model.document import Document


class GeofenceRejectLog(Document):
	pass
