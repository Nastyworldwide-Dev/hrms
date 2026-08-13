"""Every staff-role grant on an employee-keyed doctype must carry a row fence.

Doctype permissions are not a fence. A row granting the Employee or Employee
Self Service role read at permlevel 0 lets that user list EVERY row of the
doctype — Desk list view, `/api/resource/<DocType>`, `frappe.client.get_list`,
report view, CSV export — unless something narrows the rows. Only three things
do: a `permission_query_conditions` / `has_permission` hook, `if_owner` on the
permission row, or an `allow=Employee` User Permission on the reading user.

The third is the one that keeps failing on this fork. It is per-Employee state,
not code: it disappears when `create_user_permission` is unticked (ERPNext
deletes the rows — see the Employee.on_update comment in hooks.py), and when
`restrict_user_permission_to_hrms` is ticked the broad row is replaced by
per-doctype rows whose `applicable_for` covers only the HRMS scope list, leaving
every doctype outside that list unfenced. `hrms/hr/utils.py` says it plainly:
"that binding has broken before on this fork".

So this test refuses to let a doctype depend on it. If staff can read rows keyed
to an employee, the fence lives in code.

Pure static check over the repo's JSON and hooks.py — no bench, no site. Run in
file mode (`python3 hrms/tests/test_employee_role_fence_integrity.py`);
importing the package would drag in frappe.
"""

import ast
import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

STAFF_ROLES = {"Employee", "Employee Self Service"}

#: Doctypes that deliberately expose employee-keyed rows to every member of
#: staff. Each entry is a product decision, not an oversight.
FENCE_EXEMPT = {
	# The staff directory. Org-wide by design — the PWA profile/reporting views
	# need it — and hrms.api.get_all_employees already trims the field set for
	# non-HR callers (STAFF_DIRECTORY_FIELDS).
	"Employee",
	# Curated HR contact cards: being reachable by every employee IS the
	# feature. hrms/api/hr_contacts.py filters the rows to HR-role holders.
	"HR Contact",
}


def doctype_files():
	"""Every non-child DocType JSON shipped by this app."""
	for path in sorted(HRMS_ROOT.rglob("*/doctype/*/*.json")):
		if path.stem != path.parent.name:
			continue
		try:
			doc = json.loads(path.read_text(encoding="utf-8"))
		except (json.JSONDecodeError, UnicodeDecodeError):
			continue
		if not isinstance(doc, dict) or doc.get("doctype") != "DocType":
			continue
		if doc.get("istable"):
			continue
		yield path, doc


def hooked_doctypes(hook_name: str | None = None) -> set:
	"""Doctypes carrying a row-scope hook, read from hooks.py via AST.

	Parsed rather than imported: hooks.py is plain data, but importing the
	package pulls in frappe. `hook_name` restricts to one hook dict; None
	returns the union.
	"""
	wanted = {hook_name} if hook_name else {"permission_query_conditions", "has_permission"}
	tree = ast.parse((HRMS_ROOT / "hooks.py").read_text(encoding="utf-8"))
	hooked = set()
	for node in ast.walk(tree):
		if not isinstance(node, ast.Assign):
			continue
		names = {t.id for t in node.targets if isinstance(t, ast.Name)}
		if not names & wanted:
			continue
		if not isinstance(node.value, ast.Dict):
			continue
		for key in node.value.keys:
			if isinstance(key, ast.Constant) and isinstance(key.value, str):
				hooked.add(key.value)
	return hooked


def employee_link_fields(doc) -> list:
	return [
		f.get("fieldname")
		for f in doc.get("fields") or []
		if f.get("fieldtype") == "Link" and f.get("options") == "Employee"
	]


def staff_rows(doc) -> list:
	return [
		p
		for p in doc.get("permissions") or []
		if p.get("role") in STAFF_ROLES and not (p.get("permlevel") or 0)
	]


def unfenced():
	"""(name, rights) for doctypes where staff hold level-0 rights on employee-keyed rows."""
	hooked = hooked_doctypes()
	for path, doc in doctype_files():
		name = doc.get("name") or path.stem
		if name in FENCE_EXEMPT or name in hooked:
			continue
		rows = staff_rows(doc)
		if not rows:
			continue
		# if_owner already narrows to the creating user
		if all(p.get("if_owner") for p in rows):
			continue
		# no employee key => configuration/master data, not personal records
		if not employee_link_fields(doc):
			continue
		rights = sorted(
			{
				flag
				for p in rows
				for flag in ("read", "write", "create", "delete", "submit", "export", "report")
				if p.get(flag)
			}
		)
		yield name, rights


class TestEmployeeRoleFenceIntegrity(unittest.TestCase):
	def test_every_staff_readable_employee_doctype_has_a_row_fence(self):
		found = sorted(unfenced())
		self.assertEqual(
			found,
			[],
			"These doctypes grant the Employee/ESS role level-0 rights on employee-keyed "
			"rows with no row fence, so any member of staff can read (and in some cases "
			"write) every employee's records via Desk, /api/resource, report view or CSV "
			"export. Add a row-scope hook in hooks.py, set if_owner, or justify an entry "
			"in FENCE_EXEMPT:\n  " + "\n  ".join(f"{n}: {', '.join(r)}" for n, r in found),
		)

	def test_query_and_document_paths_are_both_fenced(self):
		"""A query condition alone does not protect direct document access.

		`permission_query_conditions` filters list views and get_list. It does
		nothing for `frappe.client.get`, a form load, print/PDF or an
		attachment fetch — those go through has_permission. A doctype wired to
		only one of the two is half-fenced.
		"""
		query_only = hooked_doctypes("permission_query_conditions") - hooked_doctypes("has_permission")
		self.assertEqual(
			query_only,
			set(),
			"Wired for list scope but not document scope — direct REST/form/print/attachment "
			f"access is unfenced: {sorted(query_only)}",
		)

	def test_owned_row_scope_wiring_matches_its_doctype_map(self):
		"""hooks.py and employee_owned_row_scope.OWNED_DOCTYPES must agree.

		The query wrappers are generated from OWNED_DOCTYPES at import time, so a
		doctype listed in hooks.py but missing from the map resolves to nothing
		and the fence silently does not load; the reverse leaves a doctype
		fenced in intent but not in wiring. Compared statically because
		importing the module pulls in frappe.
		"""
		scope_src = (HRMS_ROOT / "overrides" / "employee_owned_row_scope.py").read_text(encoding="utf-8")
		tree = ast.parse(scope_src)
		mapped = set()
		for node in ast.walk(tree):
			target = None
			if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
				target = node.target.id
			elif isinstance(node, ast.Assign):
				target = next((t.id for t in node.targets if isinstance(t, ast.Name)), None)
			if target != "OWNED_DOCTYPES" or not isinstance(node.value, ast.Dict):
				continue
			mapped = {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
			break
		self.assertTrue(mapped, "OWNED_DOCTYPES not found in employee_owned_row_scope.py")

		hooks_src = (HRMS_ROOT / "hooks.py").read_text(encoding="utf-8")
		wired_query = {
			line.split('"')[1] for line in hooks_src.splitlines() if "employee_owned_row_scope.query_" in line
		}
		wired_doc = {
			line.split('"')[1]
			for line in hooks_src.splitlines()
			if "employee_owned_row_scope.has_permission" in line
		}
		self.assertEqual(wired_query, mapped, "permission_query_conditions wiring != OWNED_DOCTYPES")
		self.assertEqual(wired_doc, mapped, "has_permission wiring != OWNED_DOCTYPES")

		# every wired dotted path must resolve to a generated wrapper name
		expected = {"query_" + d.lower().replace(" ", "_") for d in mapped}
		referenced = {
			line.split("employee_owned_row_scope.")[1].split('"')[0]
			for line in hooks_src.splitlines()
			if "employee_owned_row_scope.query_" in line
		}
		self.assertEqual(referenced, expected, "hooks.py references wrapper names that are not generated")

	def test_exempt_doctypes_still_exist(self):
		"""A stale exemption is a silent hole — fail if the doctype was renamed away."""
		known = {doc.get("name") for _, doc in doctype_files()}
		# Employee itself is owned by erpnext, so it is not in this repo's JSON set.
		missing = {n for n in FENCE_EXEMPT if n not in known} - {"Employee"}
		self.assertEqual(missing, set(), f"FENCE_EXEMPT names no longer present: {missing}")


if __name__ == "__main__":
	unittest.main(verbosity=2)
