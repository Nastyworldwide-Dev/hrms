"""Is this site actually able to do the things people think it does?

Every serious defect this system has produced was the same shape, and not one
of them raised anything:

    the scheduler was off ............ check-ins never became Attendance
    a setting was off ................ the whole geofence never ran
    a counter never advanced ......... nobody could check in at all
    a config row was missing ......... no radius, so nobody was ever "inside"
    an approver resolved to None ..... requests nobody could see

Absence produces no error. A feature that is switched off, unconfigured or
unreachable looks exactly like one that is fine, so all of these were found by
an employee failing to clock in rather than by us. That is the gap this closes.

TWO ENTRY POINTS, and the second one is the point:

  `report_readiness`  a daily scheduler job.
  `system_readiness`  a whitelisted read, callable any time from Desk.

The on-demand path is not a convenience. The very first finding here is "the
scheduler is inactive" — and a check that only runs on the scheduler cannot
report that. A monitor that shares its subject's failure mode is not a monitor.

`evaluate` is pure. It takes facts and returns findings, so every rule is tested
without a bench. A health check that is itself wrong is worse than none, because
it actively reassures.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

FAIL = "fail"
WARN = "warn"


def _finding(id, status, detail, fix):
	return {"id": id, "status": status, "detail": detail, "fix": fix}


def evaluate(facts: dict) -> list[dict]:
	"""Facts about a site -> what is wrong with it. Pure.

	Severity is deliberate and narrow:

	  FAIL  an employee can act and the system silently does nothing with it.
	  WARN  a real choice somebody may have made on purpose.

	Geolocation being off is the case that fixes the boundary. It is a privacy
	decision, not a defect, and reporting it as a failure would train whoever
	reads this to ignore the whole thing. A report that always says something
	gets ignored within a week, so a healthy site returns exactly nothing.
	"""
	out = []

	if facts.get("scheduler_inactive"):
		out.append(
			_finding(
				"scheduler",
				FAIL,
				"The background scheduler is not running. 23 scheduled jobs are dormant, "
				"including the one that turns check-ins into Attendance records.",
				"Check the site's scheduler status (Desk shows a banner). "
				"`bench --site <site> enable-scheduler` if it is disabled.",
			)
		)

	if not facts.get("checkin_enabled"):
		out.append(
			_finding(
				"checkin_disabled",
				WARN,
				"Mobile check-in is switched off, so the app shows no Check In button.",
				"HR Settings -> Allow Employee Checkin From Mobile App.",
			)
		)

	auto = facts.get("auto_attendance_shifts", 0)
	total = facts.get("total_shifts", 0)
	if total and not auto:
		out.append(
			_finding(
				"auto_attendance",
				FAIL,
				f"None of the {total} Shift Type(s) has Enable Auto Attendance. Check-ins are "
				"stored as raw logs and never become Attendance — staff can punch in all week "
				"and the Attendance report stays empty.",
				"Shift Type -> Enable Auto Attendance, on each shift that should mark attendance.",
			)
		)
	elif total and auto < total:
		out.append(
			_finding(
				"auto_attendance",
				WARN,
				f"{total - auto} of {total} Shift Type(s) do not mark attendance automatically.",
				"Fine if those shifts are marked by hand. Otherwise tick Enable Auto Attendance.",
			)
		)

	behind = facts.get("series_behind") or {}
	if behind:
		lines = ", ".join(f"{p} at {cur}, rows reach {high}" for p, (cur, high) in sorted(behind.items()))
		out.append(
			_finding(
				"naming_series",
				FAIL,
				f"{len(behind)} naming counter(s) are behind the rows already on disk ({lines}). "
				"The next document created will be handed a name that is taken, and the save "
				"will fail with 'already exists'.",
				"Run `bench --site <site> migrate` — "
				"patches.v16_0.repair_mirrored_naming_series advances them.",
			)
		)

	if facts.get("leave_notification_on") and not facts.get("leave_templates_set"):
		out.append(
			_finding(
				"leave_templates",
				FAIL,
				"Send Leave Notification is on but a notification template is blank. No approver "
				"is emailed when leave is applied for — get_single_value returns '' and nothing "
				"sends. It also makes HR Settings refuse to save AT ALL, on every tab.",
				"Run `bench --site <site> migrate` — "
				"patches.v16_0.restore_hr_settings_defaults links the shipped templates.",
			)
		)

	# Push is wrapped in try/except at the send site, so a missing relay is
	# indistinguishable from a working one that had nothing to say.
	if not facts.get("push_relay_enabled"):
		out.append(
			_finding(
				"push_relay",
				WARN,
				"The push notification relay is off, so the PWA sends no push notifications. "
				"In-app notifications still work; nothing reaches a phone that is not open.",
				"Push Notification Settings -> enable the relay and set the API key and "
				"secret from your hosting provider.",
			)
		)
	elif not facts.get("push_credentials_set"):
		out.append(
			_finding(
				"push_credentials",
				FAIL,
				"The push notification relay is ENABLED but has no API key or secret, so every "
				"send fails. The send site swallows the error, so this looks identical to "
				"working.",
				"Push Notification Settings -> fill in API Key and API Secret.",
			)
		)

	unscoped = facts.get("ess_users_without_permission") or []
	if unscoped:
		out.append(
			_finding(
				"ess_user_permission",
				FAIL,
				f"{len(unscoped)} user(s) hold the Employee Self Service role with NO User "
				f"Permission on an Employee record: {', '.join(unscoped[:5])}. That role grants "
				"read on Salary Slip, and the ONLY thing narrowing it to their own is a User "
				"Permission. Without one they read every payslip on the site.",
				"Set each user's User Type to 'Employee Self Service' — that creates the "
				"permission automatically — or add a User Permission allowing Employee = "
				"their own record. Adding the ROLE alone does not create it.",
			)
		)

	orphans = facts.get("orphan_requests", 0)
	if orphans:
		out.append(
			_finding(
				"orphan_requests",
				FAIL,
				f"{orphans} remote check-in request(s) have no approver. The pending list filters "
				"on approver, so nobody can see or action them and the employee is waiting on "
				"something that will never arrive.",
				"Set an approver on each, and give those employees a Shift Request Approver "
				"or a Reports To so the next one resolves.",
			)
		)

	# Everything below is about the geofence, which only means anything when
	# location is being collected at all.
	if not facts.get("geo_enabled"):
		out.append(
			_finding(
				"geolocation",
				WARN,
				"Geolocation is off, so check-ins record no coordinates. Nobody can tell whether "
				"an employee was on site, and out-of-range check-ins never become approval "
				"requests — the whole geofence is inert.",
				"HR Settings -> Allow Geolocation Tracking. It can also be overridden per "
				"Company via Allow Geolocation Tracking on the Company record.",
			)
		)
		return sorted(out, key=lambda f: f["status"] != FAIL)

	if not facts.get("shift_locations"):
		out.append(
			_finding(
				"shift_locations",
				FAIL,
				"Geolocation is on but no Shift Location exists. There is nothing to measure "
				"against, so every check-in is accepted unchecked while appearing to be policed.",
				"Create a Shift Location with the site's coordinates and a check-in radius, "
				"then link it through Shift Location Rule.",
			)
		)

	missing_coords = facts.get("locations_without_coords") or []
	if missing_coords:
		out.append(
			_finding(
				"location_coords",
				FAIL,
				f"{len(missing_coords)} Shift Location(s) have no coordinates: "
				f"{', '.join(missing_coords)}. Distance cannot be computed for anyone assigned "
				"to them.",
				"Open each and set latitude and longitude (Fetch Geolocation fills them from the map).",
			)
		)

	missing_radius = facts.get("locations_without_radius") or []
	if missing_radius:
		out.append(
			_finding(
				"location_radius",
				FAIL,
				f"{len(missing_radius)} Shift Location(s) have a check-in radius of 0: "
				f"{', '.join(missing_radius)}. Nobody is ever inside — every check-in becomes a "
				"remote request, and under strict geofence it is refused outright.",
				"Set Checkin Radius in metres on each.",
			)
		)

	return sorted(out, key=lambda f: f["status"] != FAIL)


def collect_facts() -> dict:
	"""Read the site. Every value here is consumed by `evaluate` and nowhere else."""
	from frappe.utils.scheduler import is_scheduler_inactive

	from hrms.sync.runner import STAMPED_DOCTYPES, series_matchers, split_series_name

	settings = frappe.get_single("HR Settings")
	shifts = frappe.get_all("Shift Type", fields=["name", "enable_auto_attendance"])
	locations = frappe.get_all("Shift Location", fields=["name", "latitude", "longitude", "checkin_radius"])

	# The check-in blocker as a STANDING check, not a one-off patch. A restore
	# from backup or a hand-run import reopens it exactly the same way.
	behind = {}
	from frappe.model.naming import NamingSeries

	for doctype in STAMPED_DOCTYPES:
		if not frappe.db.table_exists(doctype):
			continue
		matchers = series_matchers(doctype)
		if not matchers:
			continue
		highest: dict[str, int] = {}
		for name in frappe.get_all(doctype, pluck="name"):
			split = split_series_name(name, matchers)
			if split:
				prefix, number = split
				highest[prefix] = max(highest.get(prefix, 0), number)
		for prefix, number in highest.items():
			try:
				current = NamingSeries(prefix).get_current_value()
				if number > current:
					behind[prefix] = (current, number)
			except Exception as e:
				logger.warning("[readiness] could not read series %s: %s", prefix, e)

	# Measured, not assumed: an ESS user WITH the permission sees 1 of 2 salary
	# slips; the same user WITHOUT it sees 2 of 2. The role is granted by User
	# Type (setup.get_user_types_data), which creates the permission — but adding
	# the role by hand does not, and nothing complains.
	ess_users = frappe.get_all(
		"Has Role",
		filters={"role": "Employee Self Service", "parenttype": "User"},
		pluck="parent",
	)
	unscoped_ess = [
		u for u in ess_users if not frappe.db.exists("User Permission", {"user": u, "allow": "Employee"})
	]

	push = (
		frappe.get_single("Push Notification Settings")
		if frappe.db.exists("DocType", "Push Notification Settings")
		else None
	)

	return {
		"scheduler_inactive": bool(is_scheduler_inactive()),
		"leave_notification_on": bool(settings.get("send_leave_notification")),
		"leave_templates_set": bool(
			settings.get("leave_approval_notification_template")
			and settings.get("leave_status_notification_template")
		),
		# No relay doctype at all means an older framework; treat as enabled so
		# this does not nag about a feature the site cannot have.
		"push_relay_enabled": bool(push.enable_push_notification_relay) if push else True,
		"push_credentials_set": bool(push and push.api_key and push.api_secret),
		"ess_users_without_permission": unscoped_ess,
		"checkin_enabled": bool(settings.get("allow_employee_checkin_from_mobile_app")),
		"geo_enabled": bool(settings.get("allow_geolocation_tracking")),
		"auto_attendance_shifts": sum(1 for s in shifts if s.enable_auto_attendance),
		"total_shifts": len(shifts),
		"shift_locations": len(locations),
		"locations_without_coords": [loc.name for loc in locations if not (loc.latitude and loc.longitude)],
		"locations_without_radius": [loc.name for loc in locations if not loc.checkin_radius],
		"orphan_requests": frappe.db.count(
			"Remote Checkin Request", {"status": "Pending", "approver": ("is", "not set")}
		)
		if frappe.db.table_exists("Remote Checkin Request")
		else 0,
		"series_behind": behind,
	}


@frappe.whitelist()
def system_readiness() -> dict:
	"""What is silently not working. Read-only, callable any time.

	Whitelisted for read precisely because the first finding is "the scheduler
	is inactive": a check that only runs on the scheduler cannot report that.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	findings = evaluate(collect_facts())
	logger.info("[readiness] %d finding(s): %s", len(findings), [f["id"] for f in findings])
	return {
		"findings": findings,
		"failing": sum(1 for f in findings if f["status"] == FAIL),
		"warning": sum(1 for f in findings if f["status"] == WARN),
	}


def report_readiness() -> list[dict]:
	"""Daily scheduler entry. One Error Log when something is silently broken.

	Deliberately still scheduled even though the scheduler is one of its own
	subjects. When the scheduler runs, this is the thing that surfaces the other
	four; when it does not, `system_readiness` is there to be asked.
	"""
	report = system_readiness()
	failing = [f for f in report["findings"] if f["status"] == FAIL]
	if not failing:
		logger.info("[readiness] nothing is silently broken")
		return []

	frappe.log_error(
		title=f"{len(failing)} thing(s) on this site are silently not working",
		message=(
			"Each of these lets somebody act and produces nothing. None of them raises an "
			"error on its own — that is why they are listed here.\n\n"
			+ "\n\n".join(f"{f['id']}\n  {f['detail']}\n  FIX: {f['fix']}" for f in failing)
		),
	)
	return failing
