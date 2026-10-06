"""The same expense cannot be claimed twice; a look-alike is flagged, not refused.

Owner ruling R1 (6 Oct 2026): BLOCK exact duplicates, WARN on near ones.

Exact = another LIVE claim of the same employee (not cancelled, not Rejected,
not this document, not the claim this one amends) has an expense row with the
same type + date + amount as a row here, or two rows of this claim match.
Near = same type + date, different amount: saved, with an orange warning.

The rule is lifted from expense_claim.py by AST (the module imports erpnext).
Its ONE query runs for real, against sqlite tables shaped like the two
doctypes, so the employee / docstatus / Rejected / amended_from / date filters
are exercised, not assumed. Expected values come from the ruling, not the code.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_expense_claim_duplicates.py
"""

import ast
import datetime
import functools
import pathlib
import re
import sqlite3
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fake_document import FakeDocument

SOURCE = (
	pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype" / "expense_claim" / "expense_claim.py"
)

EMPLOYEE = "HR-EMP-0001"
OTHER_EMPLOYEE = "HR-EMP-0002"


class ValidationError(Exception):
	pass


def _class():
	tree = ast.parse(SOURCE.read_text())
	return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim")


def _lift_method(name, namespace):
	fn = next((n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == name), None)
	assert fn is not None, f"ExpenseClaim.{name} is missing"
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace[name]


def _lift_function(name, namespace):
	fn = next(
		(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == name),
		None,
	)
	assert fn is not None, f"{name} is missing from expense_claim.py"
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace[name]


def _getdate(value):
	if isinstance(value, datetime.date):
		return value
	return datetime.date.fromisoformat(str(value))


class _Site:
	"""Two tables, a `frappe` whose only read is `db.sql`, and what was shown to the user."""

	def __init__(self):
		self.db = sqlite3.connect(":memory:")
		self.db.executescript(
			"""
			create table `tabExpense Claim` (
				name text, employee text, docstatus int, approval_status text, creation text
			);
			create table `tabExpense Claim Detail` (
				parent text, parenttype text, parentfield text, idx int,
				expense_type text, expense_date text, amount real
			);
			"""
		)
		self.reads = 0
		self.messages = []
		self._created = 0
		frappe = SimpleNamespace(
			ValidationError=ValidationError,
			throw=self._throw,
			msgprint=lambda msg, **kw: self.messages.append((msg, kw)),
			db=SimpleNamespace(sql=self._sql),
		)
		self.ns = {
			"frappe": frappe,
			"_": lambda text: text,
			"flt": lambda v, precision=None: round(float(v or 0), precision if precision is not None else 9),
			"getdate": _getdate,
			"formatdate": lambda d: _getdate(d).strftime("%d-%m-%Y"),
			"fmt_money": lambda amount, precision=None: f"{float(amount):,.{precision or 2}f}",
			"get_link_to_form": lambda doctype, name: name,
			"logger": MagicMock(),
		}
		self.check = _lift_method("validate_no_duplicate_expenses", self.ns)
		self.new_lines = _lift_method("_new_expense_lines", self.ns)
		# the one rule, shared by the save check above and the Nadi read below
		_lift_function("near_duplicate_claims", self.ns)
		_lift_function("near_duplicate_sentences", self.ns)
		self.methods = {
			name: _lift_method(name, self.ns)
			for name in (
				"_checks_for_duplicates",
				"_dated_expense_lines",
				"_other_claim_lines",
				"near_duplicate_notes",
			)
		}

	@staticmethod
	def _throw(msg, exc=None):
		raise (exc or ValidationError)(msg)

	def _sql(self, query, values=None, as_dict=False):
		"""frappe.db.sql's named placeholders, with tuples expanded the way the driver does."""
		self.reads += 1
		args = []

		def bind(match):
			value = (values or {})[match.group(1)]
			if isinstance(value, tuple):
				args.extend(value)
				return "(" + ",".join("?" * len(value)) + ")"
			args.append(value)
			return "?"

		cursor = self.db.execute(re.sub(r"%\((\w+)\)s", bind, query), args)
		names = [c[0] for c in cursor.description]
		return [SimpleNamespace(**dict(zip(names, row, strict=True))) for row in cursor.fetchall()]

	def file(self, name, rows, employee=EMPLOYEE, docstatus=1, approval_status="Draft"):
		"""A claim already in the database. rows = [(type, date, amount), ...]."""
		self._created += 1
		self.db.execute(
			"insert into `tabExpense Claim` values (?, ?, ?, ?, ?)",
			(name, employee, docstatus, approval_status, f"2026-10-0{self._created} 09:00:00"),
		)
		for idx, (expense_type, date, amount) in enumerate(rows, 1):
			self.db.execute(
				"insert into `tabExpense Claim Detail` values (?, 'Expense Claim', 'expenses', ?, ?, ?, ?)",
				(name, idx, expense_type, date, amount),
			)

	def claim(self, rows, name="HR-EXP-NEW", employee=EMPLOYEE, **fields):
		"""The claim being saved. rows = [(type, date, amount), ...]."""
		lines = [
			FakeDocument(
				"Expense Claim Detail", idx=i, expense_type=t, expense_date=d, amount=a, sanctioned_amount=a
			)
			for i, (t, d, a) in enumerate(rows, 1)
		]
		doc = FakeDocument(
			"Expense Claim",
			name=name,
			employee=employee,
			docstatus=fields.pop("docstatus", 0),
			approval_status=fields.pop("approval_status", "Draft"),
			expenses=lines,
			precision=lambda *args: 2,
			get_doc_before_save=fields.pop("get_doc_before_save", lambda: None),
			**fields,
		)
		# the real helper, bound to this fake (the method under test calls self._new_expense_lines())
		doc._new_expense_lines = lambda precision: self.new_lines(doc, precision)
		for name, method in self.methods.items():
			setattr(doc, name, functools.partial(method, doc))
		return doc


class TestDuplicateExpenseClaims(unittest.TestCase):
	def setUp(self):
		self.site = _Site()

	def run_check(self, doc):
		return self.site.check(doc)

	# -- exact duplicates are refused ---------------------------------------

	def test_the_same_expense_on_another_live_claim_is_refused_and_names_that_claim(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		doc = self.site.claim([("Travel", "2026-10-01", 50.0)])
		with self.assertRaises(ValidationError) as caught:
			self.run_check(doc)
		message = str(caught.exception)
		self.assertIn("HR-EXP-0001", message)
		self.assertIn("This expense is already claimed on", message)
		self.assertIn("Travel", message)
		self.assertIn("01-10-2026", message)
		self.assertIn("50.00", message)
		self.assertIn("change the description and amount, or ask HR", message)

	def test_a_duplicate_among_several_rows_is_found(self):
		self.site.file("HR-EXP-0001", [("Meals", "2026-10-02", 12.5), ("Travel", "2026-10-01", 50.0)])
		doc = self.site.claim([("Parking", "2026-10-01", 5.0), ("Travel", "2026-10-01", 50.0)])
		with self.assertRaises(ValidationError) as caught:
			self.run_check(doc)
		self.assertIn("HR-EXP-0001", str(caught.exception))

	def test_a_draft_claim_counts_as_claimed(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], docstatus=0)
		with self.assertRaises(ValidationError):
			self.run_check(self.site.claim([("Travel", "2026-10-01", 50.0)]))

	def test_two_identical_rows_in_the_same_claim_are_refused(self):
		doc = self.site.claim([("Travel", "2026-10-01", 50.0), ("Travel", "2026-10-01", 50.0)])
		with self.assertRaises(ValidationError) as caught:
			self.run_check(doc)
		self.assertIn("Rows 1 and 2", str(caught.exception))
		self.assertEqual(self.site.messages, [])

	# -- what is not a duplicate --------------------------------------------

	def test_a_rejected_claim_is_not_counted(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], approval_status="Rejected")
		self.run_check(self.site.claim([("Travel", "2026-10-01", 50.0)]))
		self.assertEqual(self.site.messages, [], "a Rejected claim is not a near duplicate either")

	def test_a_cancelled_claim_is_not_counted(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], docstatus=2)
		self.run_check(self.site.claim([("Travel", "2026-10-01", 50.0)]))
		self.assertEqual(self.site.messages, [])

	def test_the_claim_this_one_amends_is_not_counted_even_if_it_is_still_live(self):
		# Cancelled is excluded by docstatus; this proves amended_from is excluded by name.
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], docstatus=1)
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001-1", amended_from="HR-EXP-0001"
		)
		self.run_check(doc)
		self.assertEqual(self.site.messages, [])

	def test_the_amended_cancelled_original_is_not_counted(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], docstatus=2)
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001-1", amended_from="HR-EXP-0001"
		)
		self.run_check(doc)

	def test_an_amend_is_still_checked_against_every_other_claim(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], docstatus=2)
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 50.0)], docstatus=1)
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001-1", amended_from="HR-EXP-0001"
		)
		with self.assertRaises(ValidationError) as caught:
			self.run_check(doc)
		self.assertIn("HR-EXP-0002", str(caught.exception))

	def test_saving_a_claim_again_does_not_clash_with_its_own_stored_rows(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], docstatus=0)
		self.run_check(self.site.claim([("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001"))
		self.assertEqual(self.site.messages, [])

	def test_a_different_employees_same_expense_is_fine(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], employee=OTHER_EMPLOYEE)
		self.run_check(self.site.claim([("Travel", "2026-10-01", 50.0)]))
		self.assertEqual(self.site.messages, [], "someone else's claim is not a near duplicate")

	def test_a_different_type_or_date_is_fine(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		self.run_check(self.site.claim([("Meals", "2026-10-01", 50.0), ("Travel", "2026-10-02", 50.0)]))
		self.assertEqual(self.site.messages, [])

	def test_the_first_claim_can_still_be_approved_when_a_later_copy_exists(self):
		# found live on fresh.local, 6 Oct: a copy filed before this rule (or by
		# Desk) made the ORIGINAL unapprovable. The later one is the duplicate.
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], docstatus=0)  # the original, first
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 50.0)], docstatus=0)  # the copy, later
		stored = self.site.claim([("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001")  # its lines, unchanged
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0)],
			name="HR-EXP-0001",
			approval_status="Approved",
			creation="2026-10-01 09:00:00",
			get_doc_before_save=lambda: stored,
		)
		self.run_check(doc)  # no refusal

	def test_the_later_copy_is_still_refused(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0)], name="HR-EXP-0002", creation="2026-10-09 09:00:00"
		)
		with self.assertRaises(ValidationError):
			self.run_check(doc)

	def test_an_old_draft_edited_to_copy_a_newer_claim_is_refused(self):
		# review of the earlier-only fix: an older draft whose ROWS change is a new
		# claim in all but name, so it is checked against every other live claim
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 50.0)])  # the newer claim
		before = self.site.claim([("Meals", "2026-09-01", 9.0)], name="HR-EXP-0001")  # what it was
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0)],
			name="HR-EXP-0001",
			creation="2026-09-01 09:00:00",
			get_doc_before_save=lambda: before,
		)
		with self.assertRaises(ValidationError):
			self.run_check(doc)

	def test_two_claims_made_in_the_same_second_still_see_each_other(self):
		# review: a strict "earlier than" let two claims created in one second pass;
		# ties are broken by name, so exactly one of the two is the original
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		created = self.site.db.execute(
			"select creation from `tabExpense Claim` where name='HR-EXP-0001'"
		).fetchone()[0]
		later = self.site.claim([("Travel", "2026-10-01", 50.0)], name="HR-EXP-0002", creation=created)
		with self.assertRaises(ValidationError):
			self.run_check(later)
		stored = self.site.claim([("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001")
		first = self.site.claim(
			[("Travel", "2026-10-01", 50.0)],
			name="HR-EXP-0001",
			creation=created,
			get_doc_before_save=lambda: stored,
		)
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 50.0)])
		self.site.db.execute("update `tabExpense Claim` set creation=? where name='HR-EXP-0002'", (created,))
		self.run_check(first)  # the original (lower name) stays approvable

	def test_adding_a_receipt_to_the_original_is_not_refused_for_its_old_line(self):
		# final review of E1: original draft A, a later copy B of its first line;
		# A gets a second receipt. Only the NEW line is compared with every claim;
		# A's old line is still only compared with earlier claims.
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 50.0)])  # the later copy B
		self.site.db.execute(
			"update `tabExpense Claim` set creation='2026-10-09 09:00:00' where name='HR-EXP-0002'"
		)
		before = self.site.claim([("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001")
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0), ("Meals", "2026-10-01", 12.0)],
			name="HR-EXP-0001",
			creation="2026-10-01 09:00:00",
			get_doc_before_save=lambda: before,
		)
		self.run_check(doc)  # no refusal

	def test_a_changed_line_that_copies_a_later_claim_is_still_refused(self):
		self.site.file("HR-EXP-0002", [("Meals", "2026-10-01", 12.0)])  # later claim
		self.site.db.execute(
			"update `tabExpense Claim` set creation='2026-10-09 09:00:00' where name='HR-EXP-0002'"
		)
		before = self.site.claim([("Travel", "2026-10-01", 50.0)], name="HR-EXP-0001")
		doc = self.site.claim(
			[("Travel", "2026-10-01", 50.0), ("Meals", "2026-10-01", 12.0)],
			name="HR-EXP-0001",
			creation="2026-10-01 09:00:00",
			get_doc_before_save=lambda: before,
		)
		with self.assertRaises(ValidationError):
			self.run_check(doc)

	def test_rejecting_a_duplicate_is_never_blocked_by_the_rule(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		doc = self.site.claim([("Travel", "2026-10-01", 50.0)], approval_status="Rejected")
		self.run_check(doc)
		self.assertEqual(self.site.reads, 0, "a Rejected claim is not checked at all")

	# -- near duplicates warn and save --------------------------------------

	def test_same_type_and_date_with_another_amount_warns_and_saves(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		self.run_check(self.site.claim([("Travel", "2026-10-01", 55.0)]))
		self.assertEqual(len(self.site.messages), 1)
		text, kwargs = self.site.messages[0]
		self.assertEqual(kwargs.get("indicator"), "orange")
		self.assertIn("You already claimed a Travel on 01-10-2026 in HR-EXP-0001", text)
		self.assertIn("Check it is not the same expense.", text)

	def test_the_warning_is_shown_once_however_many_rows_and_claims_match(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 60.0)])
		self.run_check(self.site.claim([("Travel", "2026-10-01", 55.0), ("Travel", "2026-10-01", 57.0)]))
		self.assertEqual(len(self.site.messages), 1)
		text = self.site.messages[0][0]
		self.assertIn("HR-EXP-0001", text)
		self.assertIn("HR-EXP-0002", text)

	# -- cost --------------------------------------------------------------

	def test_a_ten_row_claim_costs_one_database_read(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-03", 9.0)])
		rows = [("Travel", f"2026-10-{day:02d}", 10.0 + day) for day in range(1, 11)]
		self.run_check(self.site.claim(rows))
		self.assertEqual(self.site.reads, 1)

	def test_validate_runs_the_check_after_the_amounts_are_rounded(self):
		validate = next(n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = [
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]
		self.assertIn("validate_no_duplicate_expenses", calls)
		self.assertLess(calls.index("calculate_total_amount"), calls.index("validate_no_duplicate_expenses"))


class TestNearDuplicateNotes(unittest.TestCase):
	"""The Nadi read: the warning validate shows, for a claim already saved.

	Nadi never shows a msgprint (frappe-ui drops _server_messages on success), so
	hrms.api.near_duplicate_expenses asks the same rule for the saved claim.
	"""

	def setUp(self):
		self.site = _Site()

	def test_a_near_copy_is_named_in_plain_words(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		notes = self.site.claim([("Travel", "2026-10-01", 55.0)]).near_duplicate_notes()
		self.assertEqual(
			notes,
			["You already claimed a Travel on 01-10-2026 in HR-EXP-0001. Check it is not the same expense."],
		)

	def test_the_read_answers_with_what_the_save_warning_says(self):
		# one rule, not two: same claims, same wording, whichever way it is asked
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		self.site.file("HR-EXP-0002", [("Meals", "2026-10-02", 12.0), ("Travel", "2026-10-01", 60.0)])
		doc = self.site.claim([("Travel", "2026-10-01", 55.0), ("Meals", "2026-10-02", 13.0)])
		self.run_check(doc)
		shown = self.site.messages[0][0].split("<br>")
		self.assertEqual(doc.near_duplicate_notes(), shown)
		self.assertEqual(len(shown), 3)

	def run_check(self, doc):
		return self.site.check(doc)

	def test_a_claim_the_caller_may_not_open_is_not_named(self):
		# review of N1: the Nadi read names only claims the caller may open
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		self.site.file("HR-EXP-0007", [("Travel", "2026-10-01", 70.0)])
		doc = self.site.claim([("Travel", "2026-10-01", 55.0)])
		notes = doc.near_duplicate_notes(may_open=lambda name: name != "HR-EXP-0007")
		self.assertEqual(len(notes), 1)
		self.assertIn("HR-EXP-0001", notes[0])
		self.assertNotIn("HR-EXP-0007", " ".join(notes))

	def test_nothing_to_say_is_an_empty_list(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		self.assertEqual(self.site.claim([("Meals", "2026-10-01", 55.0)]).near_duplicate_notes(), [])
		self.assertEqual(self.site.claim([]).near_duplicate_notes(), [])

	def test_the_claim_itself_and_the_one_it_amends_are_not_named(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 55.0)])  # the saved claim's own rows
		doc = self.site.claim(
			[("Travel", "2026-10-01", 55.0)], name="HR-EXP-0002", amended_from="HR-EXP-0001"
		)
		self.assertEqual(doc.near_duplicate_notes(), [])

	def test_someone_elses_claim_and_a_dead_claim_are_not_named(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)], employee=OTHER_EMPLOYEE)
		self.site.file("HR-EXP-0002", [("Travel", "2026-10-01", 50.0)], approval_status="Rejected")
		self.site.file("HR-EXP-0003", [("Travel", "2026-10-01", 50.0)], docstatus=2)
		self.assertEqual(self.site.claim([("Travel", "2026-10-01", 55.0)]).near_duplicate_notes(), [])

	def test_a_rejected_or_cancelled_claim_is_not_looked_up_at_all(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-01", 50.0)])
		for fields in ({"approval_status": "Rejected"}, {"docstatus": 2}):
			self.assertEqual(
				self.site.claim([("Travel", "2026-10-01", 55.0)], **fields).near_duplicate_notes(), []
			)
		self.assertEqual(self.site.reads, 0)

	def test_a_ten_row_claim_costs_one_database_read(self):
		self.site.file("HR-EXP-0001", [("Travel", "2026-10-03", 9.0)])
		rows = [("Travel", f"2026-10-{day:02d}", 10.0 + day) for day in range(1, 11)]
		self.assertEqual(len(self.site.claim(rows).near_duplicate_notes()), 1)
		self.assertEqual(self.site.reads, 1)

	def test_save_check_and_read_share_the_one_rule(self):
		tree = _class()
		calls = {
			name: {
				n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
				for n in ast.walk(fn)
				if isinstance(n, ast.Call) and isinstance(n.func, (ast.Attribute, ast.Name))
			}
			for name, fn in ((f.name, f) for f in tree.body if isinstance(f, ast.FunctionDef))
			if name in ("validate_no_duplicate_expenses", "near_duplicate_notes")
		}
		for shared in ("_other_claim_lines", "near_duplicate_claims", "near_duplicate_sentences"):
			self.assertIn(shared, calls["validate_no_duplicate_expenses"])
			self.assertIn(shared, calls["near_duplicate_notes"])


if __name__ == "__main__":
	unittest.main()
