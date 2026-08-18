"""The parity gate's evidence must persist, and its pure read must stay pure.

The cutover exit criterion is N consecutive clean parity runs — but results
lived only in a Desk dialog, nothing stored them, and `is_cutover_ready` had
ZERO callers: the module's own promised threshold was stranded code, and "are
we ready to cut over?" was answerable only from an operator's memory.

The fix splits the entry points on the module's own contract ("it compares,
it never reconciles"):

  * `parity_check` (GET) stays PURE — a GET that writes an audit row would
    break the read-only promise its docstring makes;
  * `run_parity_check` (POST) runs the SAME shared report body and persists
    an `HRMS Parity Check` row;
  * `cutover_readiness` reads the stored trail through `is_cutover_ready` —
    the criterion finally has its caller.

Each pin below guards one way this can silently rot. AST/JSON only.
"""

import ast
import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent
PARITY = HRMS / "sync" / "parity.py"
DOCTYPE = HRMS / "hr" / "doctype" / "hrms_parity_check" / "hrms_parity_check.json"


def _function(name: str):
	for node in ast.walk(ast.parse(PARITY.read_text())):
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in hrms/sync/parity.py")


def _constants(func) -> set:
	return {n.value for n in ast.walk(func) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _calls(func) -> set:
	return {
		getattr(n.func, "id", None) or getattr(n.func, "attr", None)
		for n in ast.walk(func)
		if isinstance(n, ast.Call)
	}


class TestParityPersistence(unittest.TestCase):
	def test_the_pure_get_stays_pure(self):
		calls = _calls(_function("parity_check"))
		self.assertFalse(
			calls & {"insert", "new_doc", "save", "set_value", "get_doc"},
			"parity_check (GET) writes — the read-only contract its docstring makes "
			"is broken. Persist through run_parity_check (POST) instead.",
		)

	def test_the_post_persists_the_verdict(self):
		func = _function("run_parity_check")
		self.assertIn("HRMS Parity Check", _constants(func), "the POST no longer records a check")
		self.assertIn("insert", _calls(func))

	def test_both_paths_share_one_report_body(self):
		"""Two comparison bodies would drift — the exact gate-vs-sync failure this
		module documents. Both entry points must call the shared scoped report."""
		for name in ("parity_check", "run_parity_check"):
			self.assertIn(
				"_scoped_parity_report",
				_calls(_function(name)),
				f"{name} no longer uses the shared report body",
			)

	def test_is_cutover_ready_keeps_its_caller(self):
		"""The exit criterion was stranded once; it must not strand again."""
		self.assertIn("is_cutover_ready", _calls(_function("_readiness")))
		self.assertIn("_readiness", _calls(_function("cutover_readiness")))

	def test_audit_rows_are_evidence_not_editables(self):
		d = json.loads(DOCTYPE.read_text())
		self.assertEqual(d.get("in_create"), 1, "New-button hidden — rows come from code only")
		writable = [p["role"] for p in d["permissions"] if p.get("write") or p.get("create")]
		self.assertEqual(
			writable, [], f"evidence rows are editable by {writable} — an editable audit trail is not one"
		)


if __name__ == "__main__":
	unittest.main()
