"""An expense line carries its own receipt (owner, 20 Oct 2026, alpha.60 #2).

Before: one file for the whole claim, asked for at the bottom of the form.
Now: each line has a `receipt` (Attach). The PWA uploads it at once with no
parent, so the claim holds only a URL. The server therefore checks three things:

* validate: a receipt is a File the claim's owner (or the saver) uploaded, or one
  already attached to this claim. A line cannot point at somebody else's file.
* validate, once the decision is Approved (so the approver's dry run guides them
  before the press, and the submit is refused too): a line whose Expense Claim
  Type has "Receipt Required" (default on) carries a receipt. A Rejection needs
  none. A claim made before this release (a claim-level file and no line
  receipts at all) is exempt: its one file is its proof.
* on_update: each receipt is attached to the claim, so the approver can open it.

Rules lifted from expense_claim.py by AST (the controller imports erpnext). The
File table is a small honest stand-in that answers the same filters the rules ask.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_an_expense_line_carries_its_own_receipt.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

SOURCE = (
	pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype" / "expense_claim" / "expense_claim.py"
)

OWNER = "staff@example.com"
STRANGER = "someone.else@example.com"
APPROVER = "boss@example.com"


class _Refused(Exception):
	pass


def _tree():
	return ast.parse(SOURCE.read_text())


def _class():
	return next(n for n in _tree().body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim")


def _lift(node, label, name, namespace):
	assert node is not None, f"{label} is missing"
	exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace[name]


def _method(name, namespace):
	fn = next((n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == name), None)
	return _lift(fn, f"ExpenseClaim.{name}", name, namespace)


def _module_fn(name, namespace):
	fn = next((n for n in _tree().body if isinstance(n, ast.FunctionDef) and n.name == name), None)
	return _lift(fn, name, name, namespace)


def _calls(method_name):
	fn = next(n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == method_name)
	return [
		n.func.attr for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
	]


class FileTable:
	"""The File doctype, as far as the receipt rules read it."""

	def __init__(self, *rows):
		self.rows = [
			SimpleNamespace(
				name=r["name"],
				file_url=r["file_url"],
				owner=r.get("owner", OWNER),
				attached_to_doctype=r.get("attached_to_doctype"),
				attached_to_name=r.get("attached_to_name"),
				attached_to_field=r.get("attached_to_field"),
			)
			for r in rows
		]
		self.writes = []

	def get_all(self, doctype, filters=None, fields=None, limit_page_length=None, **kwargs):
		assert doctype == "File"
		assert limit_page_length, "the read is bounded"

		def matches(row, key, want):
			if isinstance(want, tuple):
				op, value = want
				assert op == "!=", op
				return (getattr(row, key) or "") != value
			return getattr(row, key) == want

		found = [r for r in self.rows if all(matches(r, k, v) for k, v in (filters or {}).items())]
		return found[:limit_page_length]

	def set_value(self, doctype, name, values):
		assert doctype == "File" and isinstance(values, dict)
		self.writes.append((name, values))
		row = next(r for r in self.rows if r.name == name)
		for key, value in values.items():
			setattr(row, key, value)


def _env(files, types=None, user=OWNER):
	"""The names the lifted rules read, with the File table behind them."""
	types = {"Parking": 1, "Meal": 1, "Toll": 0, **(types or {})}
	frappe = MagicMock()
	frappe.throw.side_effect = _Refused
	frappe.session.user = user
	frappe.db.set_value.side_effect = files.set_value
	frappe.get_all.side_effect = files.get_all
	frappe.get_cached_value.side_effect = lambda dt, name, field: types.get(name)
	ns = {"frappe": frappe, "_": lambda s: s, "logger": MagicMock()}
	for helper in ("receipt_files", "may_use_as_receipt", "has_claim_level_file"):
		ns[helper] = _module_fn(helper, ns)
	return ns


def _claim(*lines, status="Approved", name="HR-EXP-1", owner=OWNER, saved=None):
	"""Each line is (expense_type, receipt_url or None). `saved` is the stored copy's
	receipts by row name; None means a claim being made."""
	rows = [
		SimpleNamespace(name=f"r{i}", idx=i + 1, expense_type=t, receipt=r) for i, (t, r) in enumerate(lines)
	]
	before = (
		SimpleNamespace(expenses=[SimpleNamespace(name=n, receipt=r) for n, r in saved.items()])
		if saved is not None
		else None
	)
	return SimpleNamespace(
		name=name,
		owner=owner,
		approval_status=status,
		expenses=rows,
		get=lambda f: rows if f == "expenses" else None,
		is_new=lambda: saved is None,
		get_doc_before_save=lambda: before,
	)


class TestOnlyYourOwnFileIsAReceipt(unittest.TestCase):
	def check(self, claim, files, user=OWNER):
		_method("validate_receipts", _env(files, user=user))(claim)

	def test_someone_elses_file_is_refused(self):
		files = FileTable({"name": "F1", "file_url": "/private/files/a.pdf", "owner": STRANGER})
		with self.assertRaises(_Refused):
			self.check(_claim(("Parking", "/private/files/a.pdf")), files)

	def test_a_url_with_no_file_is_refused(self):
		with self.assertRaises(_Refused):
			self.check(_claim(("Parking", "/private/files/ghost.pdf")), FileTable())

	def test_the_owners_own_file_is_accepted(self):
		files = FileTable({"name": "F1", "file_url": "/private/files/a.pdf", "owner": OWNER})
		self.check(_claim(("Parking", "/private/files/a.pdf")), files)

	def test_a_file_the_saver_uploaded_is_accepted(self):
		"""HR filling in for staff: the claim is theirs, so is the file."""
		files = FileTable({"name": "F1", "file_url": "/private/files/a.pdf", "owner": APPROVER})
		self.check(_claim(("Parking", "/private/files/a.pdf"), owner=STRANGER), files, user=APPROVER)

	def test_a_file_already_on_this_claim_is_accepted(self):
		files = FileTable(
			{
				"name": "F1",
				"file_url": "/private/files/a.pdf",
				"owner": STRANGER,
				"attached_to_doctype": "Expense Claim",
				"attached_to_name": "HR-EXP-1",
			}
		)
		self.check(_claim(("Parking", "/private/files/a.pdf")), files, user=APPROVER)

	def test_one_url_with_two_file_rows_is_judged_by_the_owners(self):
		"""The same bytes uploaded twice get one URL and one File row per upload."""
		files = FileTable(
			{"name": "F1", "file_url": "/private/files/a.pdf", "owner": STRANGER},
			{"name": "F2", "file_url": "/private/files/a.pdf", "owner": OWNER},
		)
		self.check(_claim(("Parking", "/private/files/a.pdf")), files)

	def test_a_receipt_saved_earlier_is_not_asked_again(self):
		"""Its file may be gone since (HR cleaned the File list): that must not block the
		approver from deciding the claim, it was judged when the line was saved."""
		claim = _claim(("Parking", "/private/files/gone.pdf"), saved={"r0": "/private/files/gone.pdf"})
		self.check(claim, FileTable())

	def test_a_receipt_swapped_on_a_saved_claim_is_checked(self):
		claim = _claim(("Parking", "/private/files/ghost.pdf"), saved={"r0": "/private/files/old.pdf"})
		with self.assertRaises(_Refused):
			self.check(claim, FileTable())

	def test_a_line_with_no_receipt_is_not_checked_here(self):
		self.check(_claim(("Parking", None), ("Meal", "")), FileTable())

	def test_the_refusal_names_the_row(self):
		env = _env(FileTable())
		claim = _claim(("Parking", None), ("Meal", "/private/files/ghost.pdf"))
		with self.assertRaises(_Refused):
			_method("validate_receipts", env)(claim)
		message = env["frappe"].throw.call_args.args[0]
		self.assertEqual(message, "Row #2: that receipt file was not found.")


class TestARequiredTypeNeedsItsReceiptToBeDecided(unittest.TestCase):
	def require(self, claim, files=None):
		_method("require_receipts", _env(files or FileTable()))(claim)

	def test_a_required_type_with_no_receipt_is_refused(self):
		with self.assertRaises(_Refused):
			self.require(_claim(("Parking", None)))

	def test_the_refusal_names_the_row_and_the_type(self):
		env = _env(FileTable())
		claim = _claim(("Toll", None), ("Parking", None))
		with self.assertRaises(_Refused):
			_method("require_receipts", env)(claim)
		message = env["frappe"].throw.call_args.args[0]
		self.assertEqual(message, "Row #2: add the receipt for Parking.")

	def test_a_type_with_receipt_required_off_passes_without_one(self):
		self.require(_claim(("Toll", None)))

	def test_every_line_with_a_receipt_passes(self):
		self.require(_claim(("Parking", "/private/files/a.pdf"), ("Meal", "/private/files/b.pdf")))

	def test_one_bare_required_line_among_good_ones_is_refused(self):
		with self.assertRaises(_Refused):
			self.require(_claim(("Parking", "/private/files/a.pdf"), ("Meal", None)))

	def test_an_old_claim_with_its_one_claim_level_file_still_passes(self):
		"""Made before the per-line receipt: its file sits on the claim, no line has one."""
		old = FileTable(
			{
				"name": "F1",
				"file_url": "/private/files/old.pdf",
				"attached_to_doctype": "Expense Claim",
				"attached_to_name": "HR-EXP-1",
				"attached_to_field": "",
			}
		)
		self.require(_claim(("Parking", None), ("Meal", None)), old)

	def test_a_claim_level_file_does_not_excuse_a_claim_that_has_line_receipts(self):
		"""Once a line carries a receipt this is a new-style claim: every required line needs one."""
		files = FileTable(
			{
				"name": "F1",
				"file_url": "/private/files/old.pdf",
				"attached_to_doctype": "Expense Claim",
				"attached_to_name": "HR-EXP-1",
			}
		)
		with self.assertRaises(_Refused):
			self.require(_claim(("Parking", "/private/files/a.pdf"), ("Meal", None)), files)

	def test_a_line_receipt_filed_under_the_claim_is_not_a_claim_level_file(self):
		"""on_update attaches line receipts to the claim (field "receipt"). Clearing the
		line's receipt afterwards must not turn that leftover into an old claim's proof."""
		leftover = FileTable(
			{
				"name": "F1",
				"file_url": "/private/files/a.pdf",
				"attached_to_doctype": "Expense Claim",
				"attached_to_name": "HR-EXP-1",
				"attached_to_field": "receipt",
			}
		)
		with self.assertRaises(_Refused):
			self.require(_claim(("Parking", None)), leftover)

	def test_a_file_on_another_claim_excuses_nothing(self):
		other = FileTable(
			{
				"name": "F1",
				"file_url": "/private/files/old.pdf",
				"attached_to_doctype": "Expense Claim",
				"attached_to_name": "HR-EXP-2",
			}
		)
		with self.assertRaises(_Refused):
			self.require(_claim(("Parking", None)), other)

	def test_a_rejection_needs_no_receipt(self):
		"""An approver rejects a claim for its missing receipt; that must not be refused."""
		self.require(_claim(("Parking", None), status="Rejected"))


class TestEachReceiptIsFiledUnderItsClaim(unittest.TestCase):
	def link(self, claim, files, user=OWNER):
		env = _env(files, user=user)
		_method("link_receipts", env)(claim)
		return env

	def test_an_unattached_receipt_is_attached_to_the_claim(self):
		files = FileTable({"name": "F1", "file_url": "/private/files/a.pdf"})
		self.link(_claim(("Parking", "/private/files/a.pdf")), files)
		self.assertEqual(
			files.writes,
			[
				(
					"F1",
					{
						"attached_to_doctype": "Expense Claim",
						"attached_to_name": "HR-EXP-1",
						"attached_to_field": "receipt",
					},
				)
			],
		)

	def test_a_receipt_already_on_the_claim_is_left_alone(self):
		files = FileTable(
			{
				"name": "F1",
				"file_url": "/private/files/a.pdf",
				"attached_to_doctype": "Expense Claim",
				"attached_to_name": "HR-EXP-1",
				"attached_to_field": "receipt",
			}
		)
		self.link(_claim(("Parking", "/private/files/a.pdf")), files)
		self.assertEqual(files.writes, [])

	def test_someone_elses_unattached_file_is_never_taken_over(self):
		files = FileTable({"name": "F1", "file_url": "/private/files/a.pdf", "owner": STRANGER})
		self.link(_claim(("Parking", "/private/files/a.pdf")), files)
		self.assertEqual(files.writes, [])

	def test_a_file_attached_elsewhere_is_not_moved(self):
		files = FileTable(
			{
				"name": "F1",
				"file_url": "/private/files/a.pdf",
				"attached_to_doctype": "Expense Claim",
				"attached_to_name": "HR-EXP-2",
			}
		)
		self.link(_claim(("Parking", "/private/files/a.pdf")), files)
		self.assertEqual(files.writes, [])

	def test_a_line_with_no_receipt_touches_nothing(self):
		files = FileTable({"name": "F1", "file_url": "/private/files/a.pdf"})
		self.link(_claim(("Parking", None)), files)
		self.assertEqual(files.writes, [])

	def test_each_line_attaches_its_own_file(self):
		files = FileTable(
			{"name": "F1", "file_url": "/private/files/a.pdf"},
			{"name": "F2", "file_url": "/private/files/b.pdf"},
		)
		self.link(_claim(("Parking", "/private/files/a.pdf"), ("Meal", "/private/files/b.pdf")), files)
		self.assertEqual([w[0] for w in files.writes], ["F1", "F2"])


class TestTheControllerRunsTheRules(unittest.TestCase):
	def test_validate_checks_the_receipts(self):
		self.assertIn("validate_receipts", _calls("validate"))

	def test_receipts_are_checked_after_the_mileage_lines_are_priced(self):
		calls = _calls("validate")
		self.assertLess(calls.index("set_mileage_amounts"), calls.index("validate_receipts"))

	def test_the_decision_requires_the_receipts_inside_validate(self):
		"""validate, not before_submit: the approver's dry run (_approve_would_refuse)
		runs validate only, and must be able to say why Approve is not offered."""
		calls = _calls("validate")
		self.assertIn("require_receipts", calls)
		self.assertLess(calls.index("validate_receipts"), calls.index("require_receipts"))

	def test_saving_files_the_receipts_under_the_claim(self):
		self.assertIn("link_receipts", _calls("on_update"))


if __name__ == "__main__":
	unittest.main()
