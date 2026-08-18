"""The abandoned-IN sweeper must judge each IN against ITS OWN session.

_has_matching_close used to accept ANY later OUT as closing an IN, so the
buried-forgotten-checkout case — IN Mon (forgotten), IN Tue, OUT Tue — was
never tagged: Tuesday's OUT "closed" Monday's session and HR's abandoned-IN
alert stayed silent about the very row the PWA banner was surfacing. It also
counted REJECTED late-OUTs as closing, so one rejected resubmission suppressed
the tag forever.

This was the third divergent implementation of "does this IN have a closing
OUT" (the OT pairing engine and submit_late_checkout each had their own). The
sweeper now matches submit_late_checkout's rule: bounded by the next IN,
rejected OUTs excluded, NULL statuses probed separately (SQL three-valued
logic would silently drop legacy rows from a bare !=).

AST only — no bench required.
"""

import ast
import pathlib
import unittest

SWEEPER = pathlib.Path(__file__).resolve().parent.parent / "utils" / "checkin_sweeper.py"


def _close_fn():
	for node in ast.walk(ast.parse(SWEEPER.read_text())):
		if isinstance(node, ast.FunctionDef) and node.name == "_has_matching_close":
			return node
	raise AssertionError("_has_matching_close not found")


class TestSweeperSessionBound(unittest.TestCase):
	def _constants(self):
		return {
			n.value for n in ast.walk(_close_fn()) if isinstance(n, ast.Constant) and isinstance(n.value, str)
		}

	def test_close_check_is_bounded_by_the_next_in(self):
		constants = self._constants()
		self.assertIn("between", constants, "the any-later-OUT check is back — buried INs go untagged")
		self.assertIn("IN", constants, "the next-IN session bound is gone")

	def test_rejected_outs_do_not_close_a_session(self):
		self.assertIn(
			"Rejected",
			self._constants(),
			"a rejected late-OUT closes the session again — one rejected "
			"resubmission would suppress the abandoned tag forever",
		)


if __name__ == "__main__":
	unittest.main()
