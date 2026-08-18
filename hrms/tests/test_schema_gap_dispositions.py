"""Schema gaps must carry rulings, and unruled or unmet gaps must block READY.

The run logs named the same dropped fields for weeks — correct narration that
nobody had adjudicated. Undecided data loss with a cutover due date is debt,
and "bugs in plain sight" was the accurate complaint: the day the source
retires, everything never mirrored and never ruled on is lost, not deferred.

The ledger turns that wallpaper into a burn-down list with teeth:

  * every gap the evidence reports needs a ruling on the instance record;
  * "Not needed on hub" is met by existing — recorded intent;
  * any other ruling is met only when its gap stops appearing;
  * cutover readiness refuses READY while anything is unruled or unmet.

Pure cases for the evaluator; AST pins for every leg of the chain, so no
single edit can quietly disconnect evidence from enforcement.
"""

import ast
import json
import os
import pathlib
import sys
import unittest

sys.path.insert(0, os.getcwd())

HRMS = pathlib.Path(__file__).resolve().parent.parent
PARITY = HRMS / "sync" / "parity.py"
RUNNER = HRMS / "sync" / "runner.py"


def _load_evaluator():
	tree = ast.parse(PARITY.read_text())
	func = next(
		n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "evaluate_dispositions"
	)
	module = ast.Module(body=[func], type_ignores=[])
	namespace = {}
	exec(compile(ast.fix_missing_locations(module), "<evaluate_dispositions>", "exec"), namespace)
	return namespace["evaluate_dispositions"]


def _function(path, name):
	for node in ast.walk(ast.parse(path.read_text())):
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {path.name}")


def _calls(func):
	return {
		getattr(n.func, "id", None) or getattr(n.func, "attr", None)
		for n in ast.walk(func)
		if isinstance(n, ast.Call)
	}


def _constants(func):
	return {n.value for n in ast.walk(func) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


class TestEvaluator(unittest.TestCase):
	def setUp(self):
		self.evaluate = _load_evaluator()

	def test_unruled_gaps_block(self):
		verdict = self.evaluate(["field:Employee.payment_amount"], {})
		self.assertEqual(verdict["unruled"], ["field:Employee.payment_amount"])
		self.assertTrue(verdict["blocking"])

	def test_not_needed_is_met_by_existing(self):
		verdict = self.evaluate(["absent:Overtime Type"], {"absent:Overtime Type": "Not needed on hub"})
		self.assertFalse(verdict["blocking"])

	def test_fix_at_source_blocks_while_the_gap_persists(self):
		gap = "value:Employee.performance_band=E3"
		verdict = self.evaluate([gap], {gap: "Fix at source"})
		self.assertEqual(verdict["unmet"], [gap])
		self.assertTrue(verdict["blocking"])

	def test_a_done_ruling_costs_nothing(self):
		"""The gap left the evidence — HR fixed E3 at the source, say."""
		verdict = self.evaluate([], {"value:Employee.performance_band=E3": "Fix at source"})
		self.assertFalse(verdict["blocking"])

	def test_add_before_cutover_blocks_until_the_field_lands(self):
		gap = "field:Employee.payment_amount"
		self.assertTrue(self.evaluate([gap], {gap: "Add before cutover"})["blocking"])
		self.assertFalse(self.evaluate([], {gap: "Add before cutover"})["blocking"])


class TestTheChainStaysConnected(unittest.TestCase):
	def test_runner_emits_canonical_keys(self):
		func = _function(RUNNER, "sync_doctype")
		constants = " ".join(_constants(func))
		for prefix in ("value:", "field:"):
			self.assertIn(prefix, constants, f"sync_doctype stopped emitting {prefix} gap keys")

	def test_runner_persists_gaps_on_the_run(self):
		func = _function(RUNNER, "_finish_run")
		self.assertIn("schema_gaps", _constants(func), "run records no longer store gap keys")

	def test_ruled_narration_leaves_the_error_log(self):
		func = _function(RUNNER, "sync_instance")
		self.assertIn(
			"_gap_rulings",
			_calls(func),
			"sync_instance no longer consults rulings — settled facts pollute Error Log again",
		)

	def test_survey_evidence_rides_every_recorded_check(self):
		func = _function(PARITY, "run_parity_check")
		self.assertIn("source_inventory", _calls(func))
		self.assertIn("unmirrored_with_data", _constants(func))

	def test_readiness_enforces_dispositions(self):
		func = _function(PARITY, "_readiness")
		calls = _calls(func)
		self.assertIn("evaluate_dispositions", calls)
		self.assertIn("_latest_run_gaps", calls)
		self.assertIn("_instance_rulings", calls)

	def test_the_verdict_is_actually_gated_not_just_computed(self):
		"""Calling the evaluator and ignoring it would pass the pin above — the
		first mutation run proved exactly that. READY must be ASSIGNED from the
		blocking result: an assignment to verdict["ready"] whose right side
		reaches into the dispositions."""
		func = _function(PARITY, "_readiness")
		for node in ast.walk(func):
			if not isinstance(node, ast.Assign):
				continue
			target = node.targets[0]
			if (
				isinstance(target, ast.Subscript)
				and isinstance(target.slice, ast.Constant)
				and target.slice.value == "ready"
			):
				rhs = {
					n.value
					for n in ast.walk(node.value)
					if isinstance(n, ast.Constant) and isinstance(n.value, str)
				}
				if "blocking" in rhs:
					return
		self.fail(
			"_readiness computes dispositions but never gates verdict['ready'] on "
			"blocking — the ledger has evidence and no teeth"
		)

	def test_ruling_options_are_exactly_the_three(self):
		doctype = json.loads(
			(HRMS / "hr" / "doctype" / "hrms_schema_gap_ruling" / "hrms_schema_gap_ruling.json").read_text()
		)
		ruling = next(f for f in doctype["fields"] if f["fieldname"] == "ruling")
		self.assertEqual(
			[o for o in ruling["options"].split("\n") if o],
			["Not needed on hub", "Add before cutover", "Fix at source"],
			"the evaluator's one-rule semantics depend on exactly these options",
		)

	def test_instance_carries_the_rulings_table(self):
		doctype = json.loads(
			(HRMS / "hr" / "doctype" / "hrms_erp_instance" / "hrms_erp_instance.json").read_text()
		)
		table = next((f for f in doctype["fields"] if f["fieldname"] == "schema_gap_rulings"), None)
		self.assertIsNotNone(table, "the rulings table left the instance form")
		self.assertEqual(table["options"], "HRMS Schema Gap Ruling")


if __name__ == "__main__":
	unittest.main()
