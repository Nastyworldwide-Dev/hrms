"""A mileage line is paid distance x the type's rate (owner, 14 Oct 2026).

HR sets the rate per km on the Expense Claim Type, or per company in its
Accounts row. Staff type only the distance; the server prices the line on
every draft save. Rules lifted by AST (the controller imports erpnext):

    python3 hrms/tests/test_expense_mileage.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

CONTROLLER = (
	pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype" / "expense_claim" / "expense_claim.py"
)


class _Refused(Exception):
	pass


def _flt(v, precision=None):
	v = float(v or 0)
	return round(v, precision) if precision is not None else v


def _module_fn(name, namespace):
	tree = ast.parse(CONTROLLER.read_text())
	fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(CONTROLLER), "exec"), namespace)
	return namespace[name]


def _method(name, namespace):
	tree = ast.parse(CONTROLLER.read_text())
	body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim").body
	fn = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(CONTROLLER), "exec"), namespace)
	return namespace[name]


TYPE_RATE = {"Mileage Car": 0.6, "Mileage Motor": 0.3, "Parking": 0}
COMPANY_RATE = {("Mileage Car", "Shenzhen"): 1.2}


class TestRate(unittest.TestCase):
	def setUp(self):
		frappe = MagicMock()
		frappe.db.get_value.side_effect = lambda dt, f, field: COMPANY_RATE.get((f["parent"], f["company"]))
		frappe.get_cached_value.side_effect = lambda dt, name, field: TYPE_RATE.get(name)
		self.rate = _module_fn("mileage_rate", {"frappe": frappe, "flt": _flt})

	def test_the_types_rate_for_any_company(self):
		self.assertEqual(self.rate("Mileage Car", "NW"), 0.6)
		self.assertEqual(self.rate("Mileage Motor", "NW"), 0.3)

	def test_a_companys_own_rate_wins(self):
		self.assertEqual(self.rate("Mileage Car", "Shenzhen"), 1.2)

	def test_an_ordinary_type_has_no_rate(self):
		self.assertEqual(self.rate("Parking", "NW"), 0)
		self.assertEqual(self.rate(None, "NW"), 0)


class TestLines(unittest.TestCase):
	def setUp(self):
		frappe = MagicMock()
		frappe.throw.side_effect = _Refused
		ns = {
			"frappe": frappe,
			"_": lambda s: s,
			"flt": _flt,
			"logger": MagicMock(),
			"mileage_rate": lambda t, c: TYPE_RATE.get(t, 0),
		}
		self.price = _method("set_mileage_amounts", ns)

	def claim(self, *rows, new=True, docstatus=0, saved=None):
		lines = []
		for i, (t, km, amount, sanctioned) in enumerate(rows):
			line = SimpleNamespace(
				name=f"r{i}",
				idx=i + 1,
				expense_type=t,
				distance_km=km,
				amount=amount,
				sanctioned_amount=sanctioned,
			)
			line.precision = lambda f: 2
			lines.append(line)
		before = (
			SimpleNamespace(
				expenses=[SimpleNamespace(name=n, expense_type=t, distance_km=k) for n, t, k in (saved or [])]
			)
			if saved is not None
			else None
		)
		return SimpleNamespace(
			name="HR-EXP-1",
			company="NW",
			docstatus=docstatus,
			expenses=lines,
			get=lambda f: lines,
			is_new=lambda: new,
			get_doc_before_save=lambda: before,
		)

	def test_the_line_is_paid_km_times_rate(self):
		c = self.claim(("Mileage Car", 70, 0, 0))
		self.price(c)
		self.assertEqual((c.expenses[0].amount, c.expenses[0].sanctioned_amount), (42.0, 42.0))

	def test_a_typed_over_amount_is_corrected(self):
		c = self.claim(("Mileage Motor", 10, 999, 999))
		self.price(c)
		self.assertEqual(c.expenses[0].amount, 3.0)

	def test_a_mileage_line_needs_a_distance(self):
		with self.assertRaises(_Refused):
			self.price(self.claim(("Mileage Car", 0, 10, 10)))

	def test_an_ordinary_line_is_left_alone(self):
		c = self.claim(("Parking", 0, 12, 12))
		self.price(c)
		self.assertEqual(c.expenses[0].amount, 12)

	def test_an_approvers_reduced_amount_is_kept_on_a_saved_draft(self):
		c = self.claim(("Mileage Car", 70, 42.0, 30.0), new=False, saved=[("r0", "Mileage Car", 70)])
		self.price(c)
		self.assertEqual(c.expenses[0].sanctioned_amount, 30.0)

	def test_a_line_saved_before_the_type_had_a_rate_is_not_stuck(self):
		c = self.claim(("Mileage Car", 0, 25, 25), new=False, saved=[("r0", "Mileage Car", 0)])
		self.price(c)
		self.assertEqual(c.expenses[0].amount, 25)

	def test_a_decided_claim_keeps_what_was_approved(self):
		c = self.claim(("Mileage Car", 70, 50, 50), docstatus=1)
		self.price(c)
		self.assertEqual(c.expenses[0].amount, 50)


if __name__ == "__main__":
	unittest.main()
