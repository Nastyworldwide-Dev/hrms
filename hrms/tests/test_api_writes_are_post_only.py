"""Every write endpoint under hrms/api is POST-only.

Frappe validates the CSRF token only for POST / PUT / DELETE / PATCH
(`frappe.auth.UNSAFE_HTTP_METHODS`). A whitelisted function with no
`methods=` accepts GET too, so a write reachable by GET is a write reachable
by a link — no CSRF token asked. The 15 Sep 2026 persona matrix
(hrms/tests/probes/nadi_api_matrix.py) listed the accepted verbs for every
PWA call: `decide`, `finalize` and `cancel_for_correction` were pinned to
POST, the other eighteen writes accepted every verb.

Every caller already POSTs: the Nadi PWA and the roster app both configure
frappe-ui's `frappeRequest` (default method POST), Desk's `frappe.call`
POSTs, and `_download_pdf` is fetched with an explicit POST. So pinning is
free for them and closes the door for everyone else.

AST only — no bench required.

    PYTHONPATH=. python3 hrms/tests/test_api_writes_are_post_only.py
"""

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parent.parent / "api"

#: file -> the whitelisted functions in it that change state.
WRITES = {
	"__init__.py": {
		"withdraw_request",
		"mark_notification_as_read",
		"mark_all_notifications_as_read",
		"upload_base64_file",
		"delete_attachment",
	},
	"approval.py": {"decide", "finalize"},
	"correction_cancel.py": {"cancel_for_correction"},
	"remote_checkin.py": {"submit_remarks", "approve", "reject", "punch", "submit_late_checkout"},
	"helpdesk.py": {"new_ticket", "reply"},
	"sop.py": {"remove_attachment"},
	"roster.py": {
		"create_shift_schedule_assignment",
		"delete_shift_schedule_assignment",
		"swap_shift",
		"break_shift",
		"insert_shift",
	},
	"attendance_master_edit.py": {"save_rows", "hand_back"},
}


def _whitelist_methods(func: ast.FunctionDef):
	"""The `methods=[...]` list on the function's @frappe.whitelist, or None."""
	for deco in func.decorator_list:
		if not isinstance(deco, ast.Call):
			continue
		target = deco.func
		name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
		if name != "whitelist":
			continue
		for kw in deco.keywords:
			if kw.arg == "methods":
				return sorted(ast.literal_eval(kw.value))
		return None
	return None


class TestWritesArePostOnly(unittest.TestCase):
	def test_every_write_endpoint_declares_post_only(self):
		wrong = []
		for file_name, names in WRITES.items():
			tree = ast.parse((API / file_name).read_text())
			found = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
			for name in sorted(names):
				self.assertIn(name, found, f"{file_name}:{name} is no longer a function — update WRITES")
				methods = _whitelist_methods(found[name])
				if methods != ["POST"]:
					wrong.append(f"{file_name}:{name} methods={methods}")
		self.assertEqual(wrong, [], "writes reachable by GET (no CSRF check):\n" + "\n".join(wrong))


if __name__ == "__main__":
	unittest.main()
