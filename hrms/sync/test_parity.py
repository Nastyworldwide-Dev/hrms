"""The survey's doctype list, checked against a real installation.

`hrms/tests/test_sync_parity.py` is the exhaustive suite for this module and it
is bench-free by design — it loads `parity.py` from its path with a stub
`frappe`. What a stub cannot check is whether the names in
`UNMIRRORED_CANDIDATES` are real.

That matters because of how a miss presents. `source_survey` asks the remote for
a count and sorts a 404 into "not on that source at all", which is a legitimate
and unalarming answer — a source running an older HRMS genuinely lacks doctypes
this hub knows. A typo'd or renamed doctype produces the identical line. So the
failure mode of a bad name is not an error; it is a doctype that quietly reports
"nothing to see here" for ever, in the one report whose entire job is to say what
is being left behind.

The mirror had exactly that shape of blind spot already: Holiday List Assignment
was chased through a 403 and a 404 before anyone established the source had never
had the doctype at all.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.sync.test_parity
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.sync.parity import UNMIRRORED_CANDIDATES, _diff_field_fill
from hrms.sync.runner import DEFAULT_SYNC_DOCTYPES


class TestTheSurveyNamesRealDoctypes(FrappeTestCase):
	def test_every_candidate_exists_here(self):
		"""A name this site does not know cannot be counted on the source either —
		it just reports as absent, which is indistinguishable from good news."""
		missing = [doctype for doctype in UNMIRRORED_CANDIDATES if not frappe.db.exists("DocType", doctype)]
		self.assertEqual(
			missing,
			[],
			"UNMIRRORED_CANDIDATES names doctypes that do not exist — the survey will "
			"report them as 'not on that source' for ever: " + ", ".join(missing),
		)

	def test_every_mirrored_doctype_exists_here(self):
		"""The same hazard, one step worse: a bad name in the sync list is a
		doctype that silently never syncs."""
		missing = [doctype for doctype in DEFAULT_SYNC_DOCTYPES if not frappe.db.exists("DocType", doctype)]
		self.assertEqual(missing, [], "sync list names doctypes that do not exist: " + ", ".join(missing))

	def test_the_lists_do_not_overlap(self):
		"""Also asserted bench-free; repeated here because this is the file that
		runs against the site the survey actually reports on."""
		overlap = sorted(set(UNMIRRORED_CANDIDATES) & set(DEFAULT_SYNC_DOCTYPES))
		self.assertEqual(overlap, [], "mirrored, so not a gap: " + ", ".join(overlap))


class TestFieldFillDiff(unittest.TestCase):
	"""_diff_field_fill is the money path of field_completeness: it splits every blank
	on a mirrored row into the two causes that need OPPOSITE fixes. Pure, so asserted
	bench-free — the half-filled-employee problem (branch/grade/shift_location) reduces
	to exactly this classification."""

	def test_empty_here_but_filled_on_source_is_a_sync_gap(self):
		local = {"EMP-1": {"name": "EMP-1", "branch": None}}
		remote = {"EMP-1": {"name": "EMP-1", "branch": "Damansara"}}
		out = _diff_field_fill(["branch"], local, remote)
		self.assertEqual(out["sync_fidelity_gap_total"], 1)
		self.assertEqual(out["sync_fidelity_gaps"][0]["source_value"], "Damansara")
		self.assertEqual(out["source_data_gaps"], {})

	def test_empty_on_both_sides_is_a_source_gap_not_a_sync_gap(self):
		local = {"EMP-1": {"name": "EMP-1", "shift_location": ""}}
		remote = {"EMP-1": {"name": "EMP-1", "shift_location": ""}}
		out = _diff_field_fill(["shift_location"], local, remote)
		self.assertEqual(out["sync_fidelity_gap_total"], 0)
		self.assertEqual(out["source_data_gaps"], {"shift_location": 1})

	def test_filled_here_is_neither_gap_even_if_the_source_differs(self):
		local = {"EMP-1": {"name": "EMP-1", "grade": "G1"}}
		remote = {"EMP-1": {"name": "EMP-1", "grade": "G2"}}
		out = _diff_field_fill(["grade"], local, remote)
		self.assertEqual(out["sync_fidelity_gap_total"], 0)
		self.assertEqual(out["source_data_gaps"], {})
		self.assertEqual(out["per_field"]["grade"]["empty_here"], 0)

	def test_row_absent_on_source_cannot_be_a_sync_gap(self):
		# present here, no same-named row on the source: nothing to have carried, so
		# it is a source gap (or an orphan), never a sync-fidelity gap.
		out = _diff_field_fill(["branch"], {"EMP-9": {"name": "EMP-9", "branch": None}}, {})
		self.assertEqual(out["sync_fidelity_gap_total"], 0)
		self.assertEqual(out["source_data_gaps"], {"branch": 1})
