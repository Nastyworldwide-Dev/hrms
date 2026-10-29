# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Cost Tag/Center Upload — one row of HR's Cost Tag/Center Excel.

HR uploads it through Data Import ("Insert New Records"). Owner's rules:

* 28 Oct 2026 — the rows land on each employee's Cost Tag/Center Allocation
  (Employee → Overview); the Employee ID decides whose profile.
* 29 Oct 2026 — "it has year so you can differentiate": a year+month in the
  file is the truth for that person's year+month. Its rows replace what the
  profile had for it, so a tag dropped from the file drops off. Months not
  in the file stay.
* 29 Oct 2026 — "things that can cause trip can we fix that": the cells HR
  types are read loosely — a month written any way with a year, a tag as
  "CEOF" or "CEOF - NHSB", 60 or 60% or an Excel percent cell — and anything
  still unreadable fails that row with a reason, never the whole import.
  What was understood is kept beside what was typed.

Data Import saves one Excel row at a time, but a month only adds up to 100%
once all its rows are in, so an imported row waits as Pending. When the
import ends, each employee's rows go on together with one Employee.save, so
the Employee's own checks run on the finished month. A row added by hand in
Desk is applied at once. Each row ends Done or Failed with the reason; a
failing employee is rolled back alone and does not stop the others.
"""

import calendar
import datetime
import logging
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

logger = logging.getLogger(__name__)

DOCTYPE = "Cost Tag/Center Upload"
TABLE = "interco_cost_allocation"
MONTH_EXAMPLE = "2026-10, Oct 2026 or 10/2026"

_MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})


class CostTagCenterUpload(Document):
	def before_insert(self):
		# A template downloaded with these columns must not decide them.
		self.status = "Pending"
		self.error = None

	def after_insert(self):
		if not frappe.flags.in_import:
			apply_uploads([self.name])


# ---------- reading what HR typed ----------


def read_month(value):
	"""The 1st of the month HR meant, from an Excel date or text with a year."""
	if isinstance(value, datetime.datetime):
		return value.date().replace(day=1)
	if isinstance(value, datetime.date):
		return value.replace(day=1)
	text = str(value or "").strip().lower()
	year = month = None
	if m := re.fullmatch(r"(\d{4})[-/.](\d{1,2})(?:[-/.]\d{1,2})?(?:[ t][\d:.]+)?", text):
		year, month = int(m[1]), int(m[2])
	elif m := re.fullmatch(r"(\d{1,2})[-/.](\d{4})", text):
		month, year = int(m[1]), int(m[2])
	elif m := re.fullmatch(r"\d{1,2}[-/.](\d{1,2})[-/.](\d{4})", text):
		# day/month/year, as Malaysia writes it
		month, year = int(m[1]), int(m[2])
	elif m := re.fullmatch(r"([a-z]+)[\s,./-]+(\d{4})", text):
		month, year = _MONTHS.get(m[1]), int(m[2])
	if not (year and month and 1 <= month <= 12):
		frappe.throw(
			_("Year/Month {0} is not a month with a year. Write it like {1}.").format(
				frappe.bold(value or _("(blank)")), MONTH_EXAMPLE
			)
		)
	return datetime.date(year, month, 1)


def read_percent(value):
	"""60, "60" or "60%" → 60. Excel percent cells (0.6) are scaled later,
	once the whole month is known (scale_fractions)."""
	text = str(value if value is not None else "").strip().rstrip("%").strip()
	if not re.fullmatch(r"\d+(?:\.\d+)?", text) or flt(text) <= 0:
		frappe.throw(
			_("Percentage {0} is not a number above 0. Write it like 60 or 60%.").format(
				frappe.bold(value if value not in (None, "") else _("(blank)"))
			)
		)
	return flt(text)


def scale_fractions(percents):
	"""A month whose percentages add up to 1 came from Excel percent cells
	(60% is stored as 0.6): scale it to 100. Anything else is left as typed."""
	if percents and all(p <= 1 for p in percents) and abs(sum(percents) - 1) < 0.0001:
		logger.info("[cost_tag_upload] Excel percent cells scaled to 100: %s", percents)
		return [round(p * 100, 6) for p in percents]
	return percents


def find_cost_center(value):
	"""The Cost Center HR meant: "CEOF" or "CEOF - NHSB", any case."""
	text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
	centers = frappe.get_all(
		"Cost Center", filters={"is_group": 0, "disabled": 0}, fields=["name", "cost_center_name"]
	)
	exact = [c.name for c in centers if c.name.lower() == text]
	if exact:
		return exact[0]
	short = [c.name for c in centers if (c.cost_center_name or "").strip().lower() == text]
	if len(short) == 1:
		return short[0]
	if short:
		frappe.throw(
			_("Cost Tag/Center {0} is in more than one company. Write the full name: {1}.").format(
				frappe.bold(value), ", ".join(sorted(short))
			)
		)
	frappe.throw(_("Cost Tag/Center {0} was not found.").format(frappe.bold(value)))


def find_employee(employee_id, staff_name):
	"""Whose profile: the ID decides, and the name, when given, must agree.
	With no ID, the name finds the person if exactly one has it."""
	name = re.sub(r"\s+", " ", str(staff_name or "")).strip()
	employee_id = str(employee_id or "").strip()
	if employee_id:
		found = frappe.get_all("Employee", filters={"name": employee_id}, fields=["name", "employee_name"])
		if not found:
			frappe.throw(_("Employee ID {0} was not found.").format(frappe.bold(employee_id)))
		actual = re.sub(r"\s+", " ", found[0].employee_name or "").strip()
		if name and name.lower() != actual.lower():
			frappe.throw(
				_("Employee ID {0} is {1}, not {2}. Check which one is right.").format(
					frappe.bold(employee_id), frappe.bold(actual), frappe.bold(name)
				)
			)
		return found[0].name
	if not name:
		frappe.throw(_("Employee ID is required."))
	# exact name, any case and spacing; % and _ typed in a name are not wildcards
	pattern = re.sub(r"([\\%_])", r"\\\1", name)
	found = [
		f
		for f in frappe.get_all(
			"Employee", filters={"employee_name": ("like", pattern)}, fields=["name", "employee_name"]
		)
		if re.sub(r"\s+", " ", f.employee_name or "").strip().lower() == name.lower()
	]
	if len(found) == 1:
		return found[0].name
	if found:
		frappe.throw(
			_("More than one person is called {0} ({1}). Add the Employee ID.").format(
				frappe.bold(name), ", ".join(sorted(f.name for f in found))
			)
		)
	frappe.throw(_("Nobody is called {0}. Add the Employee ID.").format(frappe.bold(name)))


# ---------- putting rows on the profile ----------


def place_row(rows, month, cost_center, territory, percentage):
	"""Replace the percentage of the row with the same month and tag, or make a
	new row. Returns (row, added): `added` rows are not yet on the employee.
	Used for a single row added by hand in Desk."""
	if not (cost_center or territory):
		frappe.throw(_("Cost Tag/Center is required."))
	month = read_month(month)
	for row in rows:
		if row.get("allocation_month") and read_month(row.get("allocation_month")) != month:
			continue
		if cost_center:
			same = row.get("cost_center") == cost_center
		else:
			same = not row.get("cost_center") and row.get("territory") == territory
		if same:
			row.percentage = flt(percentage)
			return row, False
	return frappe._dict(
		allocation_month=month,
		cost_center=cost_center,
		territory=None if cost_center else territory,
		percentage=flt(percentage),
	), True


def replace_months(existing, incoming):
	"""The employee's rows after the file: every year+month in `incoming`
	replaces that year+month; the rest of `existing` is kept as it was."""
	months = {read_month(r.allocation_month) for r in incoming}
	seen = set()
	for r in incoming:
		key = (read_month(r.allocation_month), r.cost_center or r.territory)
		if key in seen:
			frappe.throw(
				_("{0} appears more than once for {1} in the file.").format(
					frappe.bold(key[1]), key[0].strftime("%b %Y")
				)
			)
		seen.add(key)
	kept = [
		{
			"allocation_month": r.get("allocation_month"),
			"cost_center": r.get("cost_center"),
			"territory": r.get("territory"),
			"percentage": r.get("percentage"),
		}
		for r in existing
		if not r.get("allocation_month") or read_month(r.get("allocation_month")) not in months
	]
	return kept + [
		{
			"allocation_month": read_month(r.allocation_month),
			"cost_center": r.cost_center,
			"territory": None if r.cost_center else r.territory,
			"percentage": flt(r.percentage),
		}
		for r in incoming
	]


def apply_uploads(names):
	"""Put the named Pending upload rows on their employees, one save each.

	Each row is read first; an unreadable row fails alone with its reason.
	Each employee is its own savepoint: one that fails is rolled back alone,
	its rows marked Failed with the reason, and the rest carry on. The save
	runs as a Desk save would (in_import off), not with the importer's
	shortcuts, so defaults, select checks and notifications all apply."""
	records = frappe.get_all(
		DOCTYPE,
		filters={"status": "Pending", "name": ("in", list(names))},
		fields=[
			"name",
			"employee",
			"employee_name",
			"allocation_month",
			"cost_center",
			"territory",
			"percentage",
		],
		order_by="creation asc",
	)
	by_employee = {}
	for record in records:
		try:
			understood = _read(record)
		except Exception as e:
			_mark([record], "Failed", _clean(e))
			continue
		by_employee.setdefault(understood.employee_id, []).append(understood)

	in_import = frappe.flags.in_import
	frappe.flags.in_import = False
	try:
		for i, (employee_id, rows) in enumerate(by_employee.items()):
			save_point = f"cost_tag_upload_{i}"
			frappe.db.savepoint(save_point)
			try:
				_apply_employee(employee_id, rows, single=len(names) == 1)
			except Exception as e:
				frappe.db.rollback(save_point=save_point)
				_mark(rows, "Failed", _clean(e))
				logger.warning("[cost_tag_upload] employee=%s rows=%d failed: %s", employee_id, len(rows), e)
				continue
			_mark(rows, "Done", None)
			logger.info("[cost_tag_upload] employee=%s rows=%d applied", employee_id, len(rows))
	finally:
		frappe.flags.in_import = in_import


def _read(record):
	"""What HR typed → what it means, or a ValidationError saying why not."""
	if not (record.cost_center or record.territory):
		frappe.throw(_("Cost Tag/Center is required."))
	return frappe._dict(
		name=record.name,
		employee_id=find_employee(record.employee, record.employee_name),
		allocation_month=read_month(record.allocation_month),
		cost_center=find_cost_center(record.cost_center) if record.cost_center else None,
		territory=None if record.cost_center else record.territory,
		percentage=read_percent(record.percentage),
	)


def _apply_employee(employee_id, rows, single=False):
	logger.info("[cost_tag_upload] employee=%s rows=%d single=%s", employee_id, len(rows), single)
	months = {}
	for r in rows:
		months.setdefault(r.allocation_month, []).append(r)
	for month_rows in months.values():
		for r, p in zip(month_rows, scale_fractions([r.percentage for r in month_rows]), strict=True):
			r.percentage = p

	employee = frappe.get_doc("Employee", employee_id)
	existing = employee.get(TABLE) or []
	if single:
		# one row added by hand: change or add just that row
		r = rows[0]
		row, added = place_row(existing, r.allocation_month, r.cost_center, r.territory, r.percentage)
		if added:
			employee.append(TABLE, row)
	else:
		employee.set(TABLE, [])
		for row in replace_months(existing, rows):
			employee.append(TABLE, row)
	employee.save()


def after_data_import(doc, method=None):
	"""Data Import on_change: once an import of upload rows has ENDED, apply
	the rows it created.

	The status alone can't tell: the importer sets "Partial Success" after its
	first row, mid-import. It has ended when its log covers every row of the
	file (payload_count). An import that stopped (Error, Timed Out) marks its
	rows Failed instead of leaving them waiting. Never raises — an error here
	would roll back the whole import — it is logged and the rows stay Pending."""
	if doc.get("reference_doctype") != DOCTYPE:
		return
	if doc.get("status") not in ("Success", "Partial Success", "Error", "Timed Out"):
		return
	try:
		logs = frappe.get_all(
			"Data Import Log",
			filters={"data_import": doc.name},
			fields=["docname", "row_indexes", "success"],
		)
		names = [log.docname for log in logs if log.success and log.docname]
		if doc.get("status") in ("Error", "Timed Out"):
			# the import stopped: its rows would wait for ever, so say so
			if names:
				frappe.db.set_value(
					DOCTYPE,
					{"name": ("in", names), "status": "Pending"},
					{"status": "Failed", "error": _("The import did not finish. Upload the file again.")},
					update_modified=False,
				)
			return
		if len(logs) < (doc.get("payload_count") or 0):
			return
		if names:
			apply_uploads(names)
	except Exception:
		logger.exception("[cost_tag_upload] data_import=%s could not apply its rows", doc.name)


def _mark(rows, status, error):
	logger.debug("[cost_tag_upload] marking %d row(s) %s", len(rows), status)
	for record in rows:
		values = {"status": status, "error": error}
		if status == "Done":
			values.update(
				employee_id=record.employee_id,
				month=record.allocation_month,
				cost_center_id=record.cost_center,
				percent=record.percentage,
			)
		frappe.db.set_value(DOCTYPE, record.name, values, update_modified=False)


def _clean(e):
	"""The message HR reads in the Why it failed column, without HTML tags."""
	return re.sub(r"<[^>]+>", "", str(e)).strip()
