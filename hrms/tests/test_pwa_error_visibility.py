"""A failed request must never be silent.

Components in this app are written `v-if="resource.data"`. A resource that
errored has no `.data`, so the component renders NOTHING — not an error, not an
empty state. Seventeen components share that shape, which means a missing
argument, an unmirrored doctype and a dropped connection all present identically:
a blank rectangle.

That is the single most expensive property in this codebase. Four unrelated
faults reached us as one report — "attendance has no calendar, requests are
missing" — and the week went on telling them apart, not on fixing them. Each fix
was small. Identifying which fix was needed was not, because nothing on screen
distinguished a broken endpoint from an empty table.

The fix is one seam, not seventeen templates: `setConfig("resourceFetcher", ...)`
in main.js is the single function every resource's request passes through, so a
wrapper there reports every failure exactly once. A template that forgets an
error branch is then merely ugly rather than mute.

These tests pin the seam, because it is one line and it is trivially and silently
undone — re-wiring raw `frappeRequest` restores the old behaviour with no visible
change to anything, which is precisely how it would come back.

Pure static check over the source — no bench, no site. Run as a FILE:

    python3 hrms/tests/test_pwa_error_visibility.py
"""

import pathlib
import re
import unittest

FRONTEND = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"
MAIN = FRONTEND / "main.js"
WRAPPER = FRONTEND / "utils" / "loudRequest.js"


class TestTheSeamIsWired(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.main = MAIN.read_text(encoding="utf-8")

	def test_the_resource_fetcher_is_wrapped(self):
		fetcher = re.search(r'setConfig\(\s*["\']resourceFetcher["\']\s*,\s*([^)]+)\)', self.main)
		self.assertIsNotNone(fetcher, "main.js must configure a resourceFetcher")
		self.assertIn(
			"makeLoudRequest",
			fetcher.group(1),
			"resourceFetcher must be wrapped — raw frappeRequest fails silently and "
			'every component that renders `v-if="resource.data"` goes blank',
		)

	def test_the_wrapper_is_imported(self):
		# Matched on the import statement itself. Splitting on "setConfig" to find
		# "everything above the call" does not work — `setConfig` is also a NAME in
		# frappe-ui's import list, so the split lands above the import being checked.
		self.assertRegex(
			self.main, r'import\s*\{[^}]*makeLoudRequest[^}]*\}\s*from\s*["\'][^"\']*loudRequest'
		)


class TestTheWrapperReportsAndRethrows(unittest.TestCase):
	"""There is no JS test runner in this project, so the wrapper's contract is
	read from its source. Crude, and it still pins the two properties whose loss
	would be invisible."""

	@classmethod
	def setUpClass(cls):
		cls.source = WRAPPER.read_text(encoding="utf-8")

	def test_it_logs_every_failure(self):
		"""Unconditional, before any filtering — the console line is what turns
		"the screen is blank" into a named endpoint in one step."""
		self.assertIn("console.error", self.source)

	def test_it_rethrows(self):
		"""Swallowing the error would break every `onError` callback and every
		try/catch around a `.submit()` in the app — a far worse bug than the one
		being fixed, and equally silent."""
		self.assertRegex(self.source, r"\bthrow error\b")

	def test_it_does_not_shout_over_a_logout(self):
		"""Session expiry fires in a burst as every mounted resource discovers it
		at once, and the router is already redirecting. Diagnostics, not noise."""
		self.assertIn("SILENT_EXCEPTIONS", self.source)
		self.assertIn("AuthenticationError", self.source)

	def test_repeats_are_collapsed(self):
		"""A calendar remounting on every month change must not stack toasts."""
		self.assertIn("REPEAT_WINDOW_MS", self.source)


if __name__ == "__main__":
	unittest.main()
