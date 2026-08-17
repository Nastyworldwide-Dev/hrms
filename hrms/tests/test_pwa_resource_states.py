"""A screen that gates on `resource.data` must say when the request failed.

Twenty components in this app render only `v-if="<resource>.data"`. A resource
that errored has no `.data`, so eighteen of them drew the same blank rectangle
for four different conditions: loading, empty, failed, and not-permitted.

`LeaveBalance.vue` was the worst of them and the clearest illustration. Its
`hasBalances` is false when the request FAILED just as surely as when the
employee genuinely has none, so a failure rendered the empty state — the words
"You have no leaves allocated", asserted about a question that had never been
answered. HR read that as their leave data being wrong. It was, but not in the
way the screen claimed.

`utils/loudRequest.js` made failures audible in the console; this makes them
visible on the page, and the two are not substitutes. A toast is gone in five
seconds and a console is not open.

EXEMPTIONS ARE PART OF THE CONTRACT, not holes in it. A badge count that fails
should render no badge; an avatar that fails should render no avatar. Forcing an
error box into those places would make the app noisier without making it
clearer, so each exemption is listed below with the reason it is one, and adding
to the list requires saying why in this file.

Pure static check over the source — no bench, no site. Run as a FILE:

    python3 hrms/tests/test_pwa_resource_states.py
"""

import pathlib
import re
import unittest

FRONTEND = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"

#: Components that gate on `.data` and legitimately show nothing when it fails.
#: Decoration, not information — each is a thing whose absence IS the correct
#: rendering of "we could not read it".
EXEMPT = {
	"components/BaseLayout.vue": "unread badge count — a failed count means no badge, not an alarm",
	"views/Notifications.vue": "the same unread badge count",
	"views/Profile.vue": "avatar image — falls back to initials, which is already the empty rendering",
	"views/Login.vue": "SSO provider list — password login still works without it, and an error box on the login page would be alarming and useless",
}

GATE = re.compile(r'v-if="[\w.?]*\b(\w+)\.data')


def _components_gating_on_data():
	"""{path: True} for every component whose render depends on a resource."""
	found = {}
	for path in sorted(FRONTEND.rglob("*.vue")):
		source = path.read_text(encoding="utf-8")
		if GATE.search(source):
			found[str(path.relative_to(FRONTEND))] = source
	return found


class TestEveryDataGatedScreenReportsFailure(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.components = _components_gating_on_data()

	def test_the_scan_found_the_components(self):
		"""Guards the guard — an empty scan would pass everything below."""
		self.assertGreater(len(self.components), 15, "expected ~20 data-gated components")
		self.assertIn("components/LeaveBalance.vue", self.components)

	def test_each_one_handles_the_error_case(self):
		offenders = [
			name
			for name, source in self.components.items()
			if name not in EXEMPT and "ResourceError" not in source and ".error" not in source
		]
		self.assertEqual(
			offenders,
			[],
			"these render nothing when their request fails, which reads as 'no data' "
			"rather than 'we could not read it' — add <ResourceError> or list an "
			"exemption with its reason: " + ", ".join(offenders),
		)

	def test_exemptions_are_real_files(self):
		"""An exemption for a renamed or deleted file silently exempts nothing, and
		would hide the next real offender behind a stale name."""
		missing = [name for name in EXEMPT if not (FRONTEND / name).exists()]
		self.assertEqual(missing, [], "exempt files that no longer exist: " + ", ".join(missing))

	def test_exemptions_actually_gate_on_data(self):
		"""If it no longer gates on `.data` it does not need exempting, and leaving
		it here just grows a list nobody prunes."""
		stale = [name for name in EXEMPT if name not in self.components]
		self.assertEqual(stale, [], "exemptions that no longer gate on .data: " + ", ".join(stale))


class TestTheLeaveBalanceDoesNotLieAboutZero(unittest.TestCase):
	"""Singled out because it is the one that was actually reported, and because
	the failure mode is worse than a blank panel: it makes a confident false
	statement about someone's entitlement."""

	def setUp(self):
		self.source = (FRONTEND / "components" / "LeaveBalance.vue").read_text(encoding="utf-8")

	def test_the_error_branch_precedes_the_empty_state(self):
		"""`v-else` takes whatever is left, so the error branch has to come first or
		a failure still renders 'You have no leaves allocated'."""
		error_at = self.source.find("ResourceError")
		empty_at = self.source.find("EmptyState")
		self.assertNotEqual(error_at, -1, "LeaveBalance must handle the error case")
		self.assertNotEqual(empty_at, -1, "LeaveBalance must keep its empty state")
		self.assertLess(error_at, empty_at, "the error branch must be tested before the v-else")


if __name__ == "__main__":
	unittest.main()
