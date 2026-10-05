"""The one-time cut of open Overtime Pay claims to the half hour (owner ruling, 5 Oct 2026).

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_band_open_ot_claims_patch.py
(The same patch was also run against the real database on fresh.local with a savepoint: 1.37 -> 1.0,
1.6 -> 1.5, 1.5 and 0.4 and Replacement Leave, Rejected and decided claims untouched, a second run a no-op.)
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.patches.v16_0 import band_open_ot_claims_to_half_hours as patch_module

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _rows(*pairs):
	return [frappe._dict(name=f"OT-{i}", claimed_hours=hours) for i, hours in enumerate(pairs)]


class TestBandOpenOtClaims(unittest.TestCase):
	def _run(self, rows):
		self.comments = []
		doc = MagicMock()
		doc.add_comment.side_effect = lambda kind, text: self.comments.append(text)
		with (
			patch.object(patch_module.frappe, "get_doc", return_value=doc),
			patch.object(patch_module.frappe, "get_all", return_value=rows) as get_all,
			patch.object(patch_module.frappe.db, "exists", return_value=True),
			patch.object(patch_module.frappe.db, "set_value") as set_value,
			patch.object(patch_module, "flt", side_effect=float),
		):
			patch_module.execute()
		return get_all, set_value

	def test_only_open_overtime_pay_claims_are_asked_for(self):
		get_all, _ = self._run([])
		filters = get_all.call_args.kwargs["filters"]
		self.assertEqual(filters["docstatus"], 0)
		self.assertEqual(filters["compensation"], "Overtime Pay")
		# "Open" only: a draft saved in Desk as Approved or Rejected was decided by someone (review of eb32c90c8)
		self.assertEqual(filters["status"], "Open")

	def test_a_claim_between_steps_is_cut_down_and_logged_without_touching_modified(self):
		_, set_value = self._run(_rows(1.37, 1.6))
		calls = {c.args[1]: c.args[3] for c in set_value.call_args_list}
		self.assertEqual(calls, {"OT-0": 1.0, "OT-1": 1.5})
		for call in set_value.call_args_list:
			self.assertIs(call.kwargs.get("update_modified"), False)

	def test_the_old_figure_is_kept_on_the_claim_as_a_comment(self):
		# the patch log is not written on a bench and a column write leaves no Version row: without the
		# comment the old figure is gone (migration check of eb32c90c8)
		self._run(_rows(1.37, 1.6))
		self.assertEqual(len(self.comments), 2)
		self.assertIn("1.37", self.comments[0])
		self.assertIn("1.0", self.comments[0])
		self.assertIn("1.6", self.comments[1])
		self.assertIn("1.5", self.comments[1])

	def test_a_claim_left_alone_gets_no_comment(self):
		self._run(_rows(1.5, 0.4))
		self.assertEqual(self.comments, [])

	def test_a_claim_already_on_a_step_or_under_half_an_hour_is_left_alone(self):
		_, set_value = self._run(_rows(1.5, 2.0, 0.4))
		set_value.assert_not_called()

	def test_it_is_listed_in_patches_txt_after_model_sync(self):
		text = (HRMS_ROOT / "patches.txt").read_text()
		self.assertIn("hrms.patches.v16_0.band_open_ot_claims_to_half_hours", text.split("[post_model_sync]")[1])

	def test_the_patch_file_exists_for_the_line_in_patches_txt(self):
		self.assertTrue((HRMS_ROOT / "patches" / "v16_0" / "band_open_ot_claims_to_half_hours.py").is_file())


if __name__ == "__main__":
	unittest.main()
