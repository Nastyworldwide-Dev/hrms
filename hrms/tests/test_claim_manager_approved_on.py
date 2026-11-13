"""Manager Approved On: a stored, filterable date on Expense Claim (owner, 13 Nov 2026).

The list shows it beside Total Claimed Amount and HR filter claims by it. It is
stamped when the manager's approval moves the claim on to HR, and a patch fills
it on existing claims from their own change history.

    python3 -m pytest -q hrms/tests/test_claim_manager_approved_on.py
"""

import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parents[1]
DOC = HRMS / "hr" / "doctype" / "expense_claim"


def _meta():
	return json.loads((DOC / "expense_claim.json").read_text())


class TestTheField(unittest.TestCase):
	def test_it_is_a_read_only_datetime_in_the_list_beside_total_claimed(self):
		meta = _meta()
		field = {f["fieldname"]: f for f in meta["fields"]}["manager_approved_on"]
		self.assertEqual(field["fieldtype"], "Datetime")
		self.assertEqual(field.get("read_only"), 1)
		self.assertEqual(field.get("in_list_view"), 1)
		self.assertEqual(field.get("in_standard_filter"), 1)
		self.assertTrue(field.get("allow_on_submit"), "stays on a submitted claim")
		order = meta["field_order"]
		self.assertEqual(order.index("manager_approved_on"), order.index("total_claimed_amount") + 1)


class TestWhenItIsSet(unittest.TestCase):
	def test_the_manager_step_stamps_it(self):
		source = (HRMS / "api" / "approval.py").read_text()
		step = source.index("The manager approved: the claim moves on to HR")
		block = source[step : step + 600]
		self.assertIn("manager_approved_on", block)
		self.assertLess(block.index("manager_approved_on"), block.index("doc.save()"))


class TestTheBackfill(unittest.TestCase):
	def test_existing_claims_take_the_date_from_their_history(self):
		from hrms.patches.v16_0.backfill_claim_manager_approved_on import manager_approved_at

		versions = [
			{
				"creation": "2026-11-01 08:00:00",
				"data": json.dumps({"changed": [["approval_status", "Draft", "Waiting for HR"]]}),
			},
			{
				"creation": "2026-11-12 09:15:00",
				"data": json.dumps({"changed": [["approval_status", "Draft", "Waiting for HR"]]}),
			},
			{
				"creation": "2026-11-13 10:00:00",
				"data": json.dumps({"changed": [["approval_status", "Waiting for HR", "Approved"]]}),
			},
		]
		# history from before the claim existed (a reused name) is not its own
		self.assertEqual(manager_approved_at(versions, since="2026-11-10 00:00:00"), "2026-11-12 09:15:00")
		self.assertIsNone(manager_approved_at([], since="2026-11-10 00:00:00"))

	def test_the_column_is_added_to_saved_report_views(self):
		source = (HRMS / "patches" / "v16_0" / "backfill_claim_manager_approved_on.py").read_text()
		self.assertIn(
			'add_report_columns("Expense Claim", ["manager_approved_on"], after="total_claimed_amount")',
			source,
		)
		self.assertIn(
			"hrms.patches.v16_0.backfill_claim_manager_approved_on", (HRMS / "patches.txt").read_text()
		)


if __name__ == "__main__":
	unittest.main()


class TestOneStepClaimsBefore5Nov(unittest.TestCase):
	"""Owner, 13 Nov 2026: a claim approved in one step before the two steps (5 Nov) shows
	"Approved by Wan Natrah, on 29-10-2026" on the form, yet the list column was blank.
	Its approval by the claim's own approver is its manager approval."""

	def _v(self, when, owner, old, new):
		return {
			"creation": when,
			"owner": owner,
			"data": json.dumps({"changed": [["approval_status", old, new]]}),
		}

	def test_a_one_step_approval_by_the_claims_approver_counts(self):
		from hrms.patches.v16_0.backfill_claim_manager_approved_on import manager_approved_at

		versions = [self._v("2026-10-29 19:12:42", "ann.natrah@x", "Draft", "Approved")]
		self.assertEqual(
			manager_approved_at(versions, since="2026-10-20 00:00:00", approver="ann.natrah@x"),
			"2026-10-29 19:12:42",
		)

	def test_a_one_step_approval_by_someone_else_does_not(self):
		from hrms.patches.v16_0.backfill_claim_manager_approved_on import manager_approved_at

		versions = [self._v("2026-10-29 19:12:42", "hr@x", "Draft", "Approved")]
		self.assertIsNone(manager_approved_at(versions, since="2026-10-20 00:00:00", approver="ann.natrah@x"))

	def test_the_two_step_manager_approval_still_wins(self):
		from hrms.patches.v16_0.backfill_claim_manager_approved_on import manager_approved_at

		versions = [
			self._v("2026-11-12 09:15:00", "azhar@x", "Draft", "Waiting for HR"),
			self._v("2026-11-13 10:00:00", "hr@x", "Waiting for HR", "Approved"),
		]
		self.assertEqual(
			manager_approved_at(versions, since="2026-11-10 00:00:00", approver="azhar@x"),
			"2026-11-12 09:15:00",
		)


class TestTheSecondPass(unittest.TestCase):
	def test_it_runs_on_sites_where_the_first_pass_already_ran(self):
		patches = (HRMS / "patches.txt").read_text()
		self.assertIn("hrms.patches.v16_0.backfill_claim_manager_approved_on_one_step", patches)

	def test_the_column_goes_into_the_saved_list_layout(self):
		from hrms.patches.v16_0.show_deciding_status_in_list_views import add_status_column

		saved = json.dumps(
			[{"fieldname": "status", "label": "Status"}, {"fieldname": "grand_total", "label": "Grand Total"}]
		)
		updated = json.loads(add_status_column(saved, "manager_approved_on", "Manager Approved On"))
		self.assertEqual(updated[-1]["fieldname"], "manager_approved_on")
		self.assertIsNone(
			add_status_column(json.dumps(updated), "manager_approved_on", "Manager Approved On")
		)
