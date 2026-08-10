"""Per-company resolution of HR / Payroll policy settings.

Several HR policies used to live in a single global singleton — HR Settings or
Payroll Settings — so one company's policy silently applied to every company on
the site. That is wrong once the site hosts entities in different countries:
Ramadan working hours are a UAE concern, gratuity accrual basis is statutory in
the UAE, geolocated check-in is a per-entity rollout decision, and reminder
emails are a local HR practice.

This module is the *only* place that decides where such a setting comes from.
Resolution order:

  1. `Company.<company_fieldname>` — the per-company override, when set.
  2. The global singleton value (HR Settings / Payroll Settings) — exactly the
     value the call site read before this module existed.

Backwards compatibility is the hard requirement: with no override configured on
any company, every call site behaves byte-identically to the pre-override code.

Override fields are deliberately *optional-looking*. Booleans are stored as a
Select of ""/"Yes"/"No" rather than a Check, because a Check cannot express
"inherit the global value" — an unchecked box is indistinguishable from "off".

Public API:
    get_company_setting(company, setting, default=None)
        Resolve one setting for one company.

    is_company_setting_enabled(company, setting)
        Boolean convenience wrapper for the tri-state (Yes/No/inherit) settings.
"""

from __future__ import annotations

import logging

import frappe

logger = logging.getLogger(__name__)

# Kinds of override field.
#   VALUE   — a real value (Date, Select, Link); blank means "inherit".
#   TRIBOOL — a Select of ""/"Yes"/"No"; blank means "inherit".
VALUE = "value"
TRIBOOL = "tribool"

# setting name -> (global singleton doctype, Company custom fieldname, kind)
#
# The setting name is always the *global* fieldname, so a reader can grep the
# old `get_single_value("HR Settings", "x")` string and land here.
COMPANY_OVERRIDES = {
	# --- HR Settings ---
	"ramadan_start_date": ("HR Settings", "hr_ramadan_start_date", VALUE),
	"ramadan_end_date": ("HR Settings", "hr_ramadan_end_date", VALUE),
	"allow_geolocation_tracking": ("HR Settings", "hr_allow_geolocation_tracking", TRIBOOL),
	"send_holiday_reminders": ("HR Settings", "hr_send_holiday_reminders", TRIBOOL),
	"send_birthday_reminders": ("HR Settings", "hr_send_birthday_reminders", TRIBOOL),
	"send_work_anniversary_reminders": (
		"HR Settings",
		"hr_send_work_anniversary_reminders",
		TRIBOOL,
	),
	"frequency": ("HR Settings", "hr_holiday_reminder_frequency", VALUE),
	# --- Payroll Settings ---
	"email_salary_slip_to_employee": (
		"Payroll Settings",
		"hr_email_salary_slip_to_employee",
		TRIBOOL,
	),
	"process_payroll_accounting_entry_based_on_employee": (
		"Payroll Settings",
		"hr_process_payroll_entry_based_on_employee",
		TRIBOOL,
	),
	"payroll_based_on": ("Payroll Settings", "hr_payroll_based_on", VALUE),
}


def _read_override(company: str, fieldname: str):
	"""Read a Company override column, tolerating a schema that lacks it.

	The columns arrive with a migration. A site whose migrate failed half-way
	(nasty-sg-dev has done exactly this) would otherwise have payroll and
	check-in blow up on a missing optional column — so a read error degrades to
	"no override", which is the pre-existing global behaviour.
	"""
	try:
		return frappe.db.get_value("Company", company, fieldname)
	except Exception:
		logger.warning(
			"[company_settings] Company.%s unavailable — has the HR policy override patch run?",
			fieldname,
		)
		return None


def get_company_setting(company: str | None, setting: str, default=None):
	"""Value of `setting` for `company`: the company override when set,
	otherwise the global HR / Payroll Settings value.

	Args:
		company: Company.name. None/blank resolves straight to the global value
			(callers that genuinely have no company context, e.g. a legacy call
			path, keep today's behaviour).
		setting: the *global* fieldname, e.g. "payroll_based_on". Must be
			registered in COMPANY_OVERRIDES.
		default: returned when neither the override nor the global value is set.

	Returns:
		For TRIBOOL settings an override resolves to 1 or 0; a global value is
		returned as stored (an int Check). VALUE settings are returned as
		stored by whichever layer answered.
	"""
	try:
		singleton, fieldname, kind = COMPANY_OVERRIDES[setting]
	except KeyError:
		raise ValueError(
			f"{setting!r} is not a company-overridable setting; register it in COMPANY_OVERRIDES"
		) from None

	value = None
	if company:
		raw = _read_override(company, fieldname)
		if raw not in (None, ""):
			value = (1 if raw == "Yes" else 0) if kind == TRIBOOL else raw
			logger.debug(
				"[company_settings] %s.%s override -> %s (company=%s)",
				singleton,
				setting,
				value,
				company,
			)

	if value is None:
		value = frappe.db.get_single_value(singleton, setting)

	if value is None or value == "":
		value = default

	return value


def is_company_setting_enabled(company: str | None, setting: str) -> bool:
	"""Truthiness of a tri-state setting for a company, global value as fallback."""
	from frappe.utils import cint

	return bool(cint(get_company_setting(company, setting, default=0)))
