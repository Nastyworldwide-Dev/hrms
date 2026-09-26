"""Real-life attendance scenarios, end to end, on a real site (alpha.11).

The owner's rule for this release (26 Sep 2026): prove every day shape the
system meets, from tap to overtime to the screen, instead of one pretend day.
Each scenario writes synthetic taps for the W0 test employee inside a
savepoint, runs the real engines (the OT pricer, the call-back stamp, the
Calendar's day), checks the result and ROLLS BACK. Nothing is kept.

Run on a bench site (never live):
    bench --site <site> execute hrms.scenarios.attendance_pack.pack
Every line must read PASS.
"""

import frappe

SCENARIOS = [
	# name, taps [(time, type)], remote-approve these indexes, expected work day -> (min OT h, max OT h)
	(
		"normal 9-6 with 1h OT",
		[("2026-09-21 08:55", "IN"), ("2026-09-21 19:00", "OUT")],
		[],
		{"2026-09-21": (1.0, 1.0)},
	),
	(
		"past midnight one session",
		[("2026-09-21 09:00", "IN"), ("2026-09-22 01:30", "OUT")],
		[],
		{"2026-09-21": (7.5, 7.5)},
	),
	(
		"owner 25 Sep two sessions, 2nd approved call-back",
		[
			("2026-09-21 10:10", "IN"),
			("2026-09-21 20:11", "OUT"),
			("2026-09-21 22:45", "IN"),
			("2026-09-22 01:41", "OUT"),
		],
		[2],
		{"2026-09-21": (3.9, 4.0)},
	),  # 70 min late is owed back: OT from 19:10 -> 1.02 + call-back 2.93
	(
		"late arrival owes back before OT",
		[("2026-09-21 09:30", "IN"), ("2026-09-21 18:30", "OUT")],
		[],
		{"2026-09-21": (0.0, 0.0)},
	),
	(
		"forgotten check-out: lone IN counts nothing",
		[("2026-09-21 09:00", "IN")],
		[],
		{"2026-09-21": (0.0, 0.0)},
	),
	(
		"approved call-back, no OT earlier that day",
		[
			("2026-09-21 09:00", "IN"),
			("2026-09-21 18:00", "OUT"),
			("2026-09-21 21:00", "IN"),
			("2026-09-22 00:30", "OUT"),
		],
		[2],
		{"2026-09-21": (3.5, 3.5)},
	),
	(
		"unapproved evening punch never counts",
		[
			("2026-09-21 09:00", "IN"),
			("2026-09-21 18:00", "OUT"),
			("2026-09-21 21:00", "IN"),
			("2026-09-22 00:30", "OUT"),
		],
		[],
		{"2026-09-21": (0.0, 0.0)},
	),
	(
		"rest day (Saturday): the whole session is OT",
		[("2026-09-26 10:00", "IN"), ("2026-09-26 14:00", "OUT")],
		[],
		{"2026-09-26": (4.0, 4.0)},
	),
	(
		"lunch out/in same day",
		[
			("2026-09-21 09:00", "IN"),
			("2026-09-21 12:00", "OUT"),
			("2026-09-21 13:00", "IN"),
			("2026-09-21 19:00", "OUT"),
		],
		[],
		{"2026-09-21": (0.9, 1.1)},
	),
]


def pack():
	"""Run every scenario; print PASS/FAIL per line and return the failures."""
	from hrms.api.calendar import _my_punches
	from hrms.utils.callback_session import stamp_approved_callback
	from hrms.utils.ot_calculation import _per_day_contributions

	emp = frappe.db.get_value("Employee", {"employee_name": "W0 employee"}, "name")
	results = []
	for name, taps, approve, expect in SCENARIOS:
		frappe.db.savepoint("pk")
		try:
			frappe.db.delete(
				"Employee Checkin",
				{"employee": emp, "time": ["between", ["2026-09-20 00:00:00", "2026-09-27 23:59:59"]]},
			)
			docs = []
			if "rest day" in name:
				# the test site's list has no weekly offs; HR's list on live does
				frappe.get_doc(
					{
						"doctype": "Holiday",
						"parent": "Nadi W0 2026",
						"parenttype": "Holiday List",
						"parentfield": "holidays",
						"holiday_date": "2026-09-26",
						"description": "ZZPROBE Saturday",
						"weekly_off": 1,
					}
				).db_insert()
				frappe.clear_cache()
			for i, (t, lt) in enumerate(taps):
				d = frappe.new_doc("Employee Checkin")
				d.update({"employee": emp, "log_type": lt, "time": t})
				d.flags.ignore_permissions = True
				d.insert()
				docs.append(d)
				if i in approve:
					frappe.db.set_value(
						"Employee Checkin",
						d.name,
						{"requires_remote_approval": 0, "remote_approval_status": "Approved"},
					)
					stamp_approved_callback(d.name)
			ok = True
			got = {}
			for day, (lo, hi) in expect.items():
				d0 = frappe.utils.getdate(day)
				hours = sum(e["hours"] for e in _per_day_contributions(emp, d0, d0).get(d0, []))
				got[day] = round(hours, 2)
				cal_taps, _ = _my_punches(emp, d0)
				got[day + " taps"] = len(cal_taps)
				if not (lo <= hours <= hi) or len(cal_taps) != len(taps):
					ok = False
			results.append((("PASS" if ok else "FAIL"), name, got))
		finally:
			frappe.db.rollback(save_point="pk")
	for r in results:
		print("PACK", *r)

	return [r for r in results if r[0] != "PASS"]
