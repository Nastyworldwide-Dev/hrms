"""Every Desk write endpoint that took GET is POST-only (alpha.14 S4).

Same class as test_api_writes_are_post_only (hrms/api, 15 Sep): Frappe checks
the CSRF token only on unsafe methods, so a whitelisted write with no
`methods=` can be triggered by a link or an <img> on any page the signed-in
person opens. The 27 Sep sweep (every @frappe.whitelist in hrms, AST) found
sixteen more, all in the Desk doctypes, e.g. goal.update_status,
employee_checkin.bulk_fetch_shift, exit_interview.send_exit_questionnaire
(emails a questionnaire), leave_ledger_entry.expire_allocation.

Every caller already POSTs: Desk's frappe.call and frappe.xcall default to
POST (frappe/public/js/frappe/request.js), and msgprint server_action goes
through frappe.call. Pinning is free for them.

One exception, named: employee_checkin.add_log_based_on_employee_field is the
biometric-device ingestion endpoint. Devices call it with API keys (token
auth carries no CSRF risk) and some device bridges send GET; closing GET
could silently stop real punches, and no one on this side can see the
devices. It is gated by real create permission on Employee Checkin.

The list is not hand-kept: any whitelisted function in hrms (outside
hrms/api, which has its own test) whose body writes must be POST-only.

    PYTHONPATH=. python3 hrms/tests/test_desk_writes_are_post_only.py
"""

import ast
import pathlib
import re
import unittest

HRMS = pathlib.Path(__file__).resolve().parents[1]
#: device ingestion, token-authenticated; see the module docstring
EXCEPT = {"hr/doctype/employee_checkin/employee_checkin.py:add_log_based_on_employee_field"}
WRITE = re.compile(
	r"\.(insert|save|submit|cancel)\(|set_value\(|delete_doc\(|db\.delete\(|db_set\(|sendmail\("
)


def _whitelist(func):
	for deco in func.decorator_list:
		target = deco.func if isinstance(deco, ast.Call) else deco
		name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
		if name != "whitelist":
			continue
		keywords = deco.keywords if isinstance(deco, ast.Call) else []
		for kw in keywords:
			if kw.arg == "methods":
				return sorted(ast.literal_eval(kw.value))
		return "ANY"
	return None


def writers_reachable_by_get():
	wrong = []
	for path in sorted(HRMS.rglob("*.py")):
		rel = path.relative_to(HRMS).as_posix()
		if rel.startswith(("api/", "tests/", "patches/")) or path.name.startswith("test_"):
			continue
		src = path.read_text()
		try:
			tree = ast.parse(src)
		except SyntaxError:
			continue
		for node in tree.body:
			if not isinstance(node, ast.FunctionDef):
				continue
			methods = _whitelist(node)
			if methods is None or methods == ["POST"] or f"{rel}:{node.name}" in EXCEPT:
				continue
			if WRITE.search(ast.get_source_segment(src, node) or ""):
				wrong.append(f"{rel}:{node.name} methods={methods}")
	return wrong


class TestDeskWritesArePostOnly(unittest.TestCase):
	def test_no_desk_write_is_reachable_by_get(self):
		wrong = writers_reachable_by_get()
		self.assertEqual(wrong, [], "writes reachable by GET (no CSRF check):\n" + "\n".join(wrong))


if __name__ == "__main__":
	unittest.main()
