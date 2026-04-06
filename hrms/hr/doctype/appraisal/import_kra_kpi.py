# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Import KRA, KPI, and Appraisal Templates from the KRA-KPI Excel file.

Usage:
  bench --site <site> execute hrms.hr.doctype.appraisal.import_kra_kpi.import_kra_kpi_from_excel \
    --kwargs '{"file_path": "/path/to/KRA-KPI_NAsty 2026.xlsx"}'

Or from browser console:
  frappe.call({
    method: "hrms.hr.doctype.appraisal.import_kra_kpi.import_kra_kpi_from_excel",
    args: { file_path: "/path/to/file.xlsx" },
    callback: (r) => console.log(r.message)
  })
"""

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def import_kra_kpi_from_excel(file_path):
	"""Read all department sheets from the KRA-KPI Excel and create records.

	Args:
		file_path: Absolute path to the .xlsx file, or a Frappe file URL
			(e.g. /files/KRA-KPI_NAsty 2026.xlsx)

	Returns:
		dict with counts of created records
	"""
	import openpyxl

	# Resolve Frappe file URL to absolute path
	if file_path.startswith("/files/") or file_path.startswith("/private/files/"):
		file_path = frappe.get_site_path(file_path.lstrip("/"))

	wb = openpyxl.load_workbook(file_path, data_only=True)

	summary = {
		"kras_created": 0,
		"kras_skipped": 0,
		"kpis_created": 0,
		"kpis_skipped": 0,
		"templates_created": 0,
		"templates_skipped": 0,
		"errors": [],
	}

	for sheet_name in wb.sheetnames:
		if not sheet_name.startswith("KRA"):
			continue

		# Extract department name from sheet: "KRA·KPI Global Sales" → "Global Sales"
		dept_name = sheet_name.replace("KRA·KPI", "").replace("KRA.KPI", "").strip()
		if not dept_name:
			continue

		ws = wb[sheet_name]
		positions = _parse_sheet(ws)

		for pos in positions:
			_create_records_for_position(pos, dept_name, summary)

	frappe.db.commit()

	msg = (
		f"Import complete: {summary['kras_created']} KRAs, "
		f"{summary['kpis_created']} KPIs, "
		f"{summary['templates_created']} templates created. "
		f"{summary['kras_skipped']} KRAs, "
		f"{summary['kpis_skipped']} KPIs, "
		f"{summary['templates_skipped']} templates skipped (already exist)."
	)
	if summary["errors"]:
		msg += f" {len(summary['errors'])} errors."

	frappe.msgprint(msg)
	print(msg)
	if summary["errors"]:
		for err in summary["errors"]:
			print(f"  ERROR: {err}")

	return summary


def _parse_sheet(ws):
	"""Parse a single worksheet into a list of position dicts.

	Each position has:
		title: str (e.g. "COUNTRY DIRECTOR  |  Grade: E1")
		grade: str (e.g. "E1")
		kpis: list of dicts with kra, kpi, param, weight, target
	"""
	positions = []
	current_pos = None
	current_kra = None

	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
		line = str(row[0] or "").strip()

		# Detect position header: "▸ COUNTRY DIRECTOR  |  Grade: E1"
		if "▸" in line or line.startswith(">"):
			if current_pos:
				positions.append(current_pos)

			title = line.replace("▸", "").replace(">", "").strip()

			# Extract grade if present
			grade = ""
			if "Grade:" in title:
				parts = title.split("Grade:")
				grade = parts[-1].strip()
				title = parts[0].strip().rstrip("|").strip()

			current_pos = {"title": title, "grade": grade, "kpis": []}
			current_kra = None
			continue

		if not current_pos:
			continue

		# Check if it's a numbered row
		try:
			int(line)
		except (ValueError, TypeError):
			continue

		kra = str(row[1] or "").strip()
		if kra:
			current_kra = kra

		kpi_title = str(row[2] or "").strip()
		param = str(row[3] or "").strip()
		weight = flt(row[4])
		target = str(row[5] or "").strip()

		if kpi_title and current_kra:
			current_pos["kpis"].append({
				"kra": current_kra,
				"kpi": kpi_title,
				"param": param,
				"weight": weight,
				"target": target,
			})

	if current_pos:
		positions.append(current_pos)

	return positions


def _create_records_for_position(pos, dept_name, summary):
	"""Create KRA, KPI, and Appraisal Template records for one position."""

	template_title = f"{dept_name} - {pos['title']}"

	# Skip if template already exists
	if frappe.db.exists("Appraisal Template", template_title):
		summary["templates_skipped"] += 1
		return

	goals = []

	for kpi_data in pos["kpis"]:
		kra_name = kpi_data["kra"]
		kpi_title = kpi_data["kpi"]

		# Create KRA if not exists
		if not frappe.db.exists("KRA", kra_name):
			try:
				frappe.get_doc({
					"doctype": "KRA",
					"title": kra_name,
					"department": dept_name if frappe.db.exists("Department", dept_name) else None,
				}).insert(ignore_permissions=True)
				summary["kras_created"] += 1
			except Exception as e:
				summary["errors"].append(f"KRA '{kra_name}': {e}")
				continue
		else:
			summary["kras_skipped"] += 1

		# Create KPI if not exists
		kpi_name = f"{kra_name}-{kpi_title}"
		if not frappe.db.exists("KPI", kpi_name):
			try:
				frappe.get_doc({
					"doctype": "KPI",
					"title": kpi_title,
					"kra": kra_name,
					"description": kpi_data["param"],
					"default_target": _parse_target(kpi_data["target"]),
				}).insert(ignore_permissions=True)
				summary["kpis_created"] += 1
			except Exception as e:
				summary["errors"].append(f"KPI '{kpi_title}' under '{kra_name}': {e}")
				continue
		else:
			summary["kpis_skipped"] += 1

		goals.append({
			"key_result_area": kra_name,
			"kpi": kpi_name,
			"kpi_description": kpi_data["param"],
			"per_weightage": kpi_data["weight"],
			"default_target": _parse_target(kpi_data["target"]),
		})

	if not goals:
		return

	# Create Appraisal Template
	try:
		template = frappe.get_doc({
			"doctype": "Appraisal Template",
			"template_title": template_title,
			"department": dept_name if frappe.db.exists("Department", dept_name) else None,
			"goals": goals,
		})
		template.insert(ignore_permissions=True)
		summary["templates_created"] += 1
	except Exception as e:
		summary["errors"].append(f"Template '{template_title}': {e}")


def _parse_target(target_str):
	"""Try to extract a numeric target from strings like '≥100% of target', '≥15 per year', etc."""
	if not target_str:
		return 0

	import re

	# Extract first number from the string
	match = re.search(r"[\d.]+", target_str)
	if match:
		return flt(match.group())
	return 0
