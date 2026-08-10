"""Create Company.hr_attendance_timezone and seed it from each company's country.

Attendance is a local wall-clock domain (see hrms/utils/timezone.py). Sites
whose System Settings timezone differs from where staff actually work filed
every punch hours off; this seeds the per-company timezone so the resolver has
something to answer with on day one.

Idempotent: never overwrites a value that is already set. Countries whose
timezone is ambiguous are left blank (the resolver falls back to the system
timezone) and logged for manual completion.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields

logger = logging.getLogger(__name__)

# Only unambiguous single-timezone countries. Deliberately not exhaustive:
# guessing for a country that spans zones (US, Russia, Australia) would file
# attendance against the wrong clock, which is the bug this fixes.
COUNTRY_TIMEZONE = {
	"Malaysia": "Asia/Kuala_Lumpur",
	"United Arab Emirates": "Asia/Dubai",
	"China": "Asia/Shanghai",
	"Singapore": "Asia/Singapore",
	"Hong Kong": "Asia/Hong_Kong",
	"Thailand": "Asia/Bangkok",
	"Vietnam": "Asia/Ho_Chi_Minh",
	"Philippines": "Asia/Manila",
	"Japan": "Asia/Tokyo",
	"South Korea": "Asia/Seoul",
	"India": "Asia/Kolkata",
	"Indonesia": None,  # spans WIB/WITA/WIT — must be set per company
	"United Kingdom": "Europe/London",
}


def execute():
	company_fields = {"Company": get_custom_fields()["Company"]}
	create_custom_fields(company_fields, ignore_validate=True)

	companies = frappe.get_all("Company", fields=["name", "country", "hr_attendance_timezone"])
	seeded, skipped = 0, []

	for company in companies:
		if company.hr_attendance_timezone:
			continue

		timezone = COUNTRY_TIMEZONE.get(company.country)
		if not timezone:
			skipped.append(f"{company.name} ({company.country or 'no country'})")
			continue

		frappe.db.set_value("Company", company.name, "hr_attendance_timezone", timezone)
		seeded += 1
		logger.info("[patch] Attendance timezone %s -> %s", company.name, timezone)

	if skipped:
		logger.warning(
			"[patch] Attendance timezone not seeded for %d company(ies) — set manually: %s",
			len(skipped),
			", ".join(skipped),
		)

	logger.info("[patch] set_attendance_timezones seeded=%d skipped=%d", seeded, len(skipped))
