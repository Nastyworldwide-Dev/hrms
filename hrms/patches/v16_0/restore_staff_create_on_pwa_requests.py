"""Staff can file the Nadi request doctypes again (v16_0).

15 September 2026: an employee filing an Attendance Request in Nadi was told
"You need the 'create' permission on Attendance Request". The doctype JSON
grants the Employee role read+write+create at level 0 and has since v15, and
the row-scope fence lets the owner-employee through for every ptype — so the
refusal cannot come from the code. It comes from the site: any Custom DocPerm
row on a doctype makes its JSON rows inert (the v15.99 lockdown lesson), and
every Nadi request doctype carries custom rows on a live site because the
Employee Self Service user type materializes its grants that way. From then
on the Employee row lives only in the site's data, where a Role Permission
Manager edit or a stripping patch can drop a flag the JSON still shows.

This patch re-asserts the JSON's staff matrix on the live rows: for each
request doctype the PWA files AS the employee, the Employee level-0 row exists
and carries the flags the JSON grants. It only ever ADDS the listed flags —
revocations (delete everywhere, Employee Advance's lock) stay where v15.99 and
v15.112 put them. Row scope (hrms.overrides.employee_owned_row_scope,
approval_row_scope, ot_row_scope) keeps an employee to their own records; this
patch touches role flags only.

STAFF_MATRIX is pinned to the doctype JSONs, and to the forms the PWA
actually ships, by hrms/tests/test_restore_staff_create_on_pwa_requests.py.
Idempotent — safe to re-run.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

ROLE = "Employee"

#: doctype -> (if_owner of the JSON row, flags the JSON grants that row).
#: Mirrors the doctype JSONs exactly — the test refuses any drift.
STAFF_MATRIX: dict[str, tuple[int, tuple[str, ...]]] = {
	"Attendance Request": (0, ("read", "write", "create")),
	"Leave Application": (0, ("read", "write", "create")),
	"Shift Request": (0, ("read", "write", "create")),
	"Compensatory Leave Request": (0, ("read", "write", "create")),
	"Expense Claim": (0, ("read", "write", "create")),
	"OT Request": (0, ("read", "write", "create")),
	"Replacement Leave Claim": (0, ("read", "write", "create")),
	"Shift Swap Request": (0, ("read", "write", "create")),
	"Remote Checkin Request": (0, ("read", "create")),
	"Employee Issue": (1, ("read", "create")),
}

#: Custom DocPerm defaults `export` to 1, so a fresh row spells every other
#: flag out as 0 — the row grants exactly the matrix, nothing by accident.
_ALL_FLAGS = (
	"read",
	"write",
	"create",
	"submit",
	"cancel",
	"amend",
	"delete",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"select",
)


def execute():
	logger.info("[staff_create] patch start")
	changed = 0
	for doctype, (if_owner, flags) in STAFF_MATRIX.items():
		changed += restore_row(doctype, if_owner, flags)
	logger.info("[staff_create] patch done — %d row(s) changed", changed)


def restore_row(doctype: str, if_owner: int, flags: tuple[str, ...]) -> int:
	"""Make the Employee level-0 row on `doctype` carry `flags`; 1 if anything was written."""
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
		logger.info("[staff_create] no Custom DocPerm rows for %s — JSON governs", doctype)
		return 0

	row = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": ROLE, "permlevel": 0, "if_owner": if_owner},
		["name", *flags],
		as_dict=True,
	)
	if row:
		missing = [flag for flag in flags if not row.get(flag)]
		if not missing:
			return 0
		frappe.db.set_value("Custom DocPerm", row.name, dict.fromkeys(missing, 1))
		logger.info("[staff_create] %s/%s L0 += %s (row %s)", doctype, ROLE, missing, row.name)
	else:
		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				"parent": doctype,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": ROLE,
				"permlevel": 0,
				"if_owner": if_owner,
				**dict.fromkeys(_ALL_FLAGS, 0),
				**dict.fromkeys(flags, 1),
			}
		).insert(ignore_permissions=True)
		logger.info("[staff_create] %s/%s L0 row added with %s", doctype, ROLE, flags)

	frappe.clear_cache(doctype=doctype)
	return 1
