"""Pure unit tests for the script report's data-shaping helpers.

Runs without a Frappe install by stubbing the frappe module before the
report module imports it.
"""

import sys
import types
import unittest


# --- Stub frappe BEFORE any import of the report module ---
def _install_frappe_stub():
	if "frappe" in sys.modules:
		return
	stub = types.ModuleType("frappe")
	stub._ = lambda s: s
	stub._dict = dict
	stub.utils = types.ModuleType("frappe.utils")
	stub.utils.today = lambda: "2026-05-22"
	stub.utils.getdate = lambda x: x
	stub.utils.add_days = lambda d, n: d
	stub.db = types.SimpleNamespace(sql=lambda *a, **kw: [], get_value=lambda *a, **kw: "")
	sys.modules["frappe"] = stub
	sys.modules["frappe.utils"] = stub.utils


_install_frappe_stub()


# Load the report module directly from its file path so we skip the
# `hrms.__init__` chain (which imports frappe at top level).
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
	"_oora_report_under_test", os.path.join(_HERE, "out_of_radius_activity.py")
)
_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_module)

_apply_status_filter = _module._apply_status_filter
_reason_label = _module._reason_label


class TestApplyStatusFilter(unittest.TestCase):
	def _rows(self):
		return [
			{"status": "Pending"},
			{"status": "Approved"},
			{"status": "Approved"},
			{"status": "Rejected"},
			{"status": "Blocked"},
			{"status": "Misconfig"},
		]

	def test_all_passes_through(self):
		rows = self._rows()
		self.assertEqual(_apply_status_filter(rows, "All"), rows)

	def test_none_passes_through(self):
		rows = self._rows()
		self.assertEqual(_apply_status_filter(rows, None), rows)
		self.assertEqual(_apply_status_filter(rows, ""), rows)

	def test_filter_to_blocked(self):
		got = _apply_status_filter(self._rows(), "Blocked")
		self.assertEqual(len(got), 1)
		self.assertEqual(got[0]["status"], "Blocked")

	def test_filter_to_approved(self):
		got = _apply_status_filter(self._rows(), "Approved")
		self.assertEqual(len(got), 2)
		self.assertTrue(all(r["status"] == "Approved" for r in got))

	def test_filter_unknown_returns_empty(self):
		got = _apply_status_filter(self._rows(), "Nonsense")
		self.assertEqual(got, [])


class TestReasonLabel(unittest.TestCase):
	def test_known_reasons_have_distinct_labels(self):
		labels = {
			_reason_label("outside_radius"),
			_reason_label("no_shift_location"),
			_reason_label("no_radius"),
		}
		self.assertEqual(len(labels), 3)

	def test_outside_radius_mentions_strict(self):
		self.assertIn("strict", _reason_label("outside_radius").lower())

	def test_unknown_reason_returns_input(self):
		self.assertEqual(_reason_label("future_reason_code"), "future_reason_code")

	def test_none_reason(self):
		self.assertEqual(_reason_label(None), "")


if __name__ == "__main__":
	unittest.main()
