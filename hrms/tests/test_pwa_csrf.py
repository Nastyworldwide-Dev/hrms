"""Every unsafe raw fetch from the PWA must carry the CSRF token.

Reported as "users can only sign in with Microsoft SSO — email and password does
not work". Two different failures wearing one costume, and the second is ours:

  POST /api/method/login                                   401 Unauthorized
  POST /api/method/frappe.core.doctype.user.user.reset_password   400 Bad Request

The 401 is honest — an SSO-provisioned user has no password, so the credentials
really are wrong. The recovery route out of that is Forgot Password, and the 400
is why it was a dead end.

`frappe.CSRFTokenError.http_status_code` is 400, and `LoginManager.
validate_csrf_token` returns early in exactly three cases: no token was ever
saved on the session, the request header matches the saved one, or the referrer
appears in `allowed_referrers` — a site-config list that is empty by default, so
same-origin earns nothing.

The trap is the first case. Guest looks exempt, and is not: `hrms/www/hrms.py`
renders the login page through `frappe.sessions.get_csrf_token()`, which
GENERATES a token for the guest session. Loading the page is what arms the check
that then rejects the page's own POST. `reset_password` never ran — which is
also why "check whether outgoing email is configured" was the wrong first
question. Nothing had reached the mail layer to fail.

frappe-ui's `createResource` sets the header itself, so every call through it was
fine and this stayed invisible. Only hand-rolled fetches can get it wrong, three
already did it correctly, and the fourth — written for a guest endpoint, where
the exemption feels most plausible — did not.

Hence a rule about the shape rather than a fix for the one call site.

Pure static check over the source — no bench, no site. Run as a FILE:

    python3 hrms/tests/test_pwa_csrf.py
"""

import pathlib
import re
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = HRMS_ROOT.parent / "frontend" / "src"

HEADER = "X-Frappe-CSRF-Token"
UNSAFE = ("POST", "PUT", "DELETE", "PATCH")

# `fetcher` is the injected-for-tests alias of `fetch` in resetPassword.js — the
# indirection that let this call site sit outside a plain `fetch(` search.
CALL = re.compile(r"\b(?:fetch|fetcher)\s*\(")

# How far above the call to look for a `headers` object built separately, which
# is how the three correct call sites are written.
LOOKBEHIND_LINES = 25


def _options_block(source: str, index: int) -> str:
	"""The `{...}` options argument of the call starting at `index`."""
	start = source.find("{", index)
	if start < 0:
		return ""
	depth = 0
	for position in range(start, len(source)):
		if source[position] == "{":
			depth += 1
		elif source[position] == "}":
			depth -= 1
			if depth == 0:
				return source[start : position + 1]
	return source[start:]


def _unsafe_calls():
	"""[(path, line, context)] for every raw fetch using an unsafe method."""
	found = []
	for path in sorted(FRONTEND.rglob("*")):
		if path.suffix not in (".js", ".vue"):
			continue
		source = path.read_text(encoding="utf-8")
		for match in CALL.finditer(source):
			options = _options_block(source, match.end() - 1)
			method = re.search(r"""method:\s*["'](\w+)["']""", options)
			if not method or method.group(1).upper() not in UNSAFE:
				continue
			line = source[: match.start()].count("\n") + 1
			# A `headers` object assembled above the call is the established
			# pattern here, so the window has to reach back over it.
			behind = "\n".join(source[: match.start()].splitlines()[-LOOKBEHIND_LINES:])
			found.append((path.relative_to(FRONTEND), line, behind + options))
	return found


class TestRawFetchesSendTheCSRFToken(unittest.TestCase):
	def test_the_scan_finds_the_known_call_sites(self):
		"""Guards the guard. `fetcher(` is why the first sweep of this came back
		clean while the broken call sat in the file being swept."""
		calls = _unsafe_calls()
		self.assertGreaterEqual(len(calls), 4, f"expected the known raw fetches, found {len(calls)}")
		files = {str(path) for path, _line, _ctx in calls}
		self.assertIn("utils/resetPassword.js", files, "the reset-password fetch must be in scope")

	def test_no_unsafe_raw_fetch_omits_the_token(self):
		offenders = [f"{path}:{line}" for path, line, context in _unsafe_calls() if HEADER not in context]
		self.assertEqual(
			offenders,
			[],
			f"raw fetch without {HEADER} — frappe answers 400 CSRFTokenError: " + ", ".join(offenders),
		)


class TestThePageStillProvidesTheToken(unittest.TestCase):
	"""The header is only as good as the value, and the value crosses from Python
	to the template to `globalThis`. Break any link and every fetch above starts
	sending nothing — silently, because the client can only warn."""

	def test_both_entry_points_expose_the_token(self):
		for page in ("hrms", "roster"):
			source = (HRMS_ROOT / "www" / f"{page}.py").read_text(encoding="utf-8")
			self.assertIn("get_csrf_token()", source, f"www/{page}.py must resolve a csrf token")
			self.assertIn("context.csrf_token", source, f"www/{page}.py must pass csrf_token to the template")

	def test_the_template_publishes_it_to_the_window(self):
		html = (HRMS_ROOT / "www" / "hrms.html").read_text(encoding="utf-8")
		self.assertRegex(
			html,
			r"window\.csrf_token\s*=\s*[\"']\{\{\s*csrf_token\s*\}\}[\"']",
			"hrms.html must publish csrf_token to the window for the fetches to read",
		)


if __name__ == "__main__":
	unittest.main()
