"""Script Reports must not hand staff a way around row scope.

A Script Report runs arbitrary SQL. Frappe checks the report's own roles and a
doctype-level `has_permission(ref_doctype, "report")` — and that is all. No
`permission_query_conditions` hook runs, no User Permission is applied, no
`if_owner`. So a Script Report carrying the Employee role is an org-wide read of
its ref doctype, no matter how carefully that doctype is fenced elsewhere.

That is not hypothetical here: it is why the leave-balance reports were
restricted to HR ("the report reads the ledger directly, bypassing row scope"),
and `Shift Attendance`, `Employee Analytics`, `Employee Birthday` and
`Employee Advance Summary` were the same hole until
`patches/v16_0/restrict_staff_script_reports.py`.

A staff-facing report is still allowed — it just has to scope itself in code,
the way `appraisal_overview.get_data` does (own employee + manual shares, with
an explicit comment that frappe.qb bypasses query conditions). This test asks
for exactly that: if a Script Report on employee-keyed data ships a staff role,
its module must show evidence of self-scoping.

Pure static check over the repo's JSON and report sources — no bench, no site.
Run in file mode; importing the package would drag in frappe.
"""

import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

STAFF_ROLES = {"Employee", "Employee Self Service"}

#: ref doctypes that carry per-employee data. A report over one of these is an
#: employee-data report, whatever its title says.
EMPLOYEE_REF_DOCTYPES = {
	"Appraisal",
	"Attendance",
	"Daily Work Summary",
	"Employee",
	"Employee Advance",
	"Employee Checkin",
	"Expense Claim",
	"Leave Allocation",
	"Leave Application",
	"Leave Ledger Entry",
	"Salary Slip",
	"Salary Structure Assignment",
	"Timesheet",
}

#: Markers that a report narrows its own rows. Kept deliberately loose — the
#: test proves that scoping was *considered*, and the reviewer reads the code.
SELF_SCOPE_MARKERS = (
	"apply_employee_scope",  # hrms.utils.report_scope — the shared helper
	"frappe.session.user",
	"get_allowed_appraisal_employees",
	"get_permitted_companies",
	"allowed_companies",
	"get_shared",
)


def report_files():
	for path in sorted(HRMS_ROOT.rglob("*/report/*/*.json")):
		if path.stem != path.parent.name:
			continue
		try:
			doc = json.loads(path.read_text(encoding="utf-8"))
		except (json.JSONDecodeError, UnicodeDecodeError):
			continue
		if isinstance(doc, dict) and doc.get("doctype") == "Report":
			yield path, doc


def unscoped_staff_reports():
	"""(report, ref_doctype, roles) for staff-visible employee-data reports with no self-scoping."""
	for path, doc in report_files():
		roles = {r.get("role") for r in doc.get("roles") or []}
		staff = roles & STAFF_ROLES
		if not staff:
			continue
		ref = doc.get("ref_doctype")
		if ref not in EMPLOYEE_REF_DOCTYPES:
			continue
		if doc.get("report_type") != "Script Report":
			# Report Builder / Query Report go through reportview, which does
			# apply permissions and query conditions.
			continue
		source = path.with_suffix(".py")
		body = source.read_text(encoding="utf-8") if source.exists() else ""
		if any(marker in body for marker in SELF_SCOPE_MARKERS):
			continue
		yield doc.get("name"), ref, sorted(staff)


class TestReportRoleIntegrity(unittest.TestCase):
	def test_staff_script_reports_scope_themselves(self):
		found = sorted(unscoped_staff_reports())
		self.assertEqual(
			found,
			[],
			"These Script Reports grant a staff role over employee data and do not scope "
			"their own rows, so any member of staff can read the whole organisation "
			"through /app/query-report — row scope does not apply to Script Report SQL. "
			"Either restrict the report to HR roles (and add it to "
			"patches/v16_0/restrict_staff_script_reports.py so existing sites are fixed "
			"too), or scope it in code the way appraisal_overview.get_data does:\n  "
			+ "\n  ".join(f"{name} (ref {ref}): {', '.join(roles)}" for name, ref, roles in found),
		)

	def test_patch_covers_every_report_stripped_in_json(self):
		"""The JSON edit only reaches fresh installs; existing sites need the patch.

		Any report we took a staff role away from must also be named in the
		patch, or live sites keep the `Has Role` rows and stay exposed.
		"""
		patch = (HRMS_ROOT / "patches" / "v16_0" / "restrict_staff_script_reports.py").read_text(
			encoding="utf-8"
		)
		shipped = {doc.get("name"): doc for _, doc in report_files()}
		listed = {
			line.split('"')[1]
			for line in patch.splitlines()
			if line.strip().startswith('"') and line.strip().endswith('",')
		}
		self.assertTrue(listed, "ORG_WIDE_REPORTS list not found in the patch")

		unknown = {name for name in listed if name not in shipped}
		self.assertEqual(
			unknown,
			set(),
			f"Patch names reports this app does not ship — a rename would make it a no-op: {sorted(unknown)}",
		)

		# The patch deletes staff Has Role rows; if the JSON still ships one, a
		# fresh install would re-create exactly what the patch removes.
		still_granted = {
			name for name in listed if {r.get("role") for r in shipped[name].get("roles") or []} & STAFF_ROLES
		}
		self.assertEqual(
			still_granted,
			set(),
			"Patch strips a staff role that the shipped JSON still grants — fresh installs "
			f"would re-create it: {sorted(still_granted)}",
		)


if __name__ == "__main__":
	unittest.main(verbosity=2)
