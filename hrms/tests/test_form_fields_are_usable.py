"""A form must not offer a control the person looking at it cannot use.

REPORTED, with a console log and two screenshots. A normal employee opening
New Expense Claim gets tabs called **Advances** and **Totals**, and inside them
Exchange Gain/Loss, Gain Loss Account, Bank / Cash Account, Payable Account,
Accounting Dimensions, Project and Cost Center. Every one of those pickers
throws the moment it is touched:

    frappe.exceptions.PermissionError: Insufficient Permission for <strong>Account</strong>
    frappe.exceptions.PermissionError: Insufficient Permission for <strong>Currency</strong>
    [request] failed: frappe.desk.search.search_link
    Uncaught (in promise)

Reproduced as a real Employee-role user: `search_link("Currency")` and
`search_link("Account")` both raise PermissionError, while
`search_link("Expense Claim Type")` succeeds.

The cause is one line. `api.get_doctype_fields` returns every field of a
supported type, filtered only on `amended_from`. It never asks whether the
CALLER can read the doctype a Link points at — so the client is handed controls
that can only ever error, and an employee is shown the accounting half of a form
that is not theirs to fill.

Two different fixes, because the fields differ:

* **Optional** links to unreadable doctypes are simply not sent. Hiding them
  loses nothing: they are set by accounts later, and an employee could not fill
  them anyway.
* **`currency` is `reqd=1`.** Hiding a required field would move the failure
  from the picker to the save, which is worse. It needs the permission instead —
  and a list of currency codes carries no sensitivity, which is why ERPNext
  already grants it to five other roles.

Bench-free: read from the AST. Run it as a FILE:

    python3 hrms/tests/test_form_fields_are_usable.py
"""

import ast
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = ROOT / "api/__init__.py"


def _fn(name):
	tree = ast.parse(API.read_text())
	fn = next(
		(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name),
		None,
	)
	assert fn is not None, f"api.{name} is missing"
	return fn


class TestUnusableLinksAreNotSent(unittest.TestCase):
	def setUp(self):
		self.src = ast.unparse(_fn("get_doctype_fields"))

	def test_it_checks_permission_on_the_link_target(self):
		"""Before this it filtered on fieldtype and `amended_from` alone."""
		self.assertIn("has_permission", self.src)

	def test_it_looks_at_the_link_target_not_the_form_doctype(self):
		"""`field.options` holds what a Link points AT. Checking the form's own
		doctype would pass everything — the caller can obviously read the form
		they just opened."""
		self.assertIn("options", self.src)

	def test_only_link_fields_are_filtered(self):
		"""A Data or Currency-typed field has no target to check, and dropping
		one for lack of a permission that does not apply would blank the form."""
		self.assertIn("Link", self.src)


class TestTheRequiredFieldIsGrantedNotHidden(unittest.TestCase):
	"""`currency` is reqd=1 on Expense Claim.

	Filtering it out would move the failure from a picker the employee can see
	to a save they cannot explain — strictly worse. It gets the permission."""

	def test_currency_is_still_required_on_expense_claim(self):
		d = json.loads((ROOT / "hr/doctype/expense_claim/expense_claim.json").read_text())
		currency = next(f for f in d["fields"] if f["fieldname"] == "currency")
		self.assertEqual(currency.get("reqd"), 1, "if this ever becomes optional, prefer filtering")

	def test_a_patch_grants_read_on_currency(self):
		patch = ROOT / "patches/v16_0/grant_employee_currency_read.py"
		self.assertTrue(patch.exists(), "no patch grants employees read on Currency")
		src = patch.read_text()
		self.assertIn("Currency", src)
		self.assertIn("read", src)

	def test_the_patch_grants_read_only(self):
		"""A reference list. Nobody files an expense by inventing a currency."""
		src = (ROOT / "patches/v16_0/grant_employee_currency_read.py").read_text()
		for flag in ("write", "create", "delete", "submit"):
			self.assertNotIn(f'"{flag}"', src, f"the patch grants {flag}; read is all that is needed")

	def test_it_is_registered(self):
		self.assertIn(
			"grant_employee_currency_read",
			(ROOT / "patches.txt").read_text(),
			"the patch exists but never runs",
		)


if __name__ == "__main__":
	unittest.main()
