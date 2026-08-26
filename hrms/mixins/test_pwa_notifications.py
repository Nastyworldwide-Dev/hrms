"""A request nobody is told about is a request nobody actions.

Mirza asked the right question: *"approver akan dapat noti dekat mana?"* — where
does the approver actually get notified? For OT Request the answer was nowhere.

Three request types raise a PWA Notification when they are filed:

    Leave Application  -> notifies leave_approver
    Expense Claim      -> notifies expense_approver
    Shift Request      -> notifies approver
    OT Request         -> nothing at all

OT Request carries no approver FIELD, so `_get_doc_approver` raised KeyError on
it and the mixin could not be used. A draft simply sat in a list until an HR
user happened to scroll past. Nothing chased it, nothing surfaced it, and the
employee had no way to tell "waiting" from "lost".

That is the same shape as everything else found this week — correct code,
absent wiring, silent.

THE FIX is not a new field. OT visibility already runs on `reports_to`
(`overrides/ot_row_scope`: own + direct reports + HR), so the approver is
resolved the same way rather than invented: the team lead, falling back to HR.
Reusing `remote_checkin_request_hooks.resolve_approver` keeps one resolution
chain in the codebase instead of two that can disagree.

Bench-free: read from the AST. Run it as a FILE:

    python3 hrms/mixins/test_pwa_notifications.py
"""

import ast
import pathlib
import unittest

MIXIN = pathlib.Path(__file__).resolve().parent / "pwa_notifications.py"
OT = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype/ot_request/ot_request.py"


def _fn(path, name):
	tree = ast.parse(path.read_text())
	fn = next(
		(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name),
		None,
	)
	assert fn is not None, f"{path.name}::{name} is missing"
	return fn


class TestTheMixinToleratesNoApproverField(unittest.TestCase):
	"""`_get_doc_approver` indexed APPROVER_FIELD directly, so any doctype
	without one raised KeyError the moment it tried to notify."""

	def test_it_does_not_index_the_map_unconditionally(self):
		src = ast.unparse(_fn(MIXIN, "_get_doc_approver"))
		self.assertNotIn(
			"APPROVER_FIELD[self.doctype]",
			src,
			"a doctype with no approver field must not KeyError",
		)

	def test_it_falls_back_to_a_resolved_approver(self):
		"""Not invented — `reports_to` then HR, the same chain remote check-in
		already uses. Two resolution chains would eventually disagree about who
		approves for the same person."""
		src = ast.unparse(_fn(MIXIN, "_get_doc_approver"))
		self.assertIn("resolve_approver", src)


class TestOTRequestNotifies(unittest.TestCase):
	def test_it_uses_the_mixin(self):
		tree = ast.parse(OT.read_text())
		cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
		bases = {b.id if isinstance(b, ast.Name) else getattr(b, "attr", "") for b in cls.bases}
		self.assertIn("PWANotificationsMixin", bases)

	def test_it_notifies_on_after_insert_not_on_validate(self):
		"""Once, when the request is filed. `validate` runs on every save, so
		notifying there would message the approver again on each edit — the
		fastest way to teach somebody to ignore notifications. Shift Request
		does it in after_insert for the same reason."""
		src = ast.unparse(_fn(OT, "after_insert"))
		self.assertIn("notify_approver", src)

		validate = ast.unparse(_fn(OT, "validate"))
		self.assertNotIn("notify_approver", validate)


if __name__ == "__main__":
	unittest.main()
