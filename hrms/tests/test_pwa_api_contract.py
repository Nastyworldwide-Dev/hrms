"""The contract between the Nadi PWA and its own API layer (pre-2.0 R2).

`hrms/api/` is the PWA's backend. It is not Desk: no doctype renders these,
no workspace links them, and the only caller of most of them is
`frontend/src`. That makes the two sides one unit with no compiler between
them — a renamed endpoint, a dropped guard or a method left unpinned breaks a
screen silently, at run time, for one employee at a time.

Three rules, each one a defect this repo has already paid for:

1. EVERY ENDPOINT THE PWA CALLS EXISTS. A rename is invisible until somebody
   taps the screen that calls it.

2. EVERY ENDPOINT PINS ITS HTTP METHOD. No writer is GET-reachable today —
   checked, 22 Sep 2026 — but nothing stops the next one being added without
   `methods=["POST"]`, and a write reachable by GET is a write a link can
   perform: an <img src> in an email, a URL in a chat, no CSRF token needed.
   `attendance_fix_day` already pins all thirteen of its own; this generalises
   what that file decided.

3. EVERY ENDPOINT CHECKS SOMETHING, or says in the file why it does not.
   `@frappe.whitelist()` alone means "any logged-in user may call this".
   That is correct for a currency list and wrong for anything employee-shaped,
   and the difference must be a decision on the record rather than an
   omission nobody notices.

    PYTHONPATH=. python3 hrms/tests/test_pwa_api_contract.py
"""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = ROOT / "api"
FRONTEND = ROOT.parent / "frontend/src"

#: Endpoints that may answer a GET because they are PUBLIC REFERENCE DATA:
#: the same answer for every employee, no personal information, nothing a link
#: could change. Each one is a decision; anything not named here must pin POST.
#: Kept as a set rather than a decorator argument so the whole list is readable
#: in one place — the point is that it is SHORT.
OPEN_READS = {
	"__init__.py": {
		"get_company_currencies",
		"get_currency_symbols",
		"get_expense_claim_types",
		"get_doctype_states",
		"get_hr_settings",
	},
	"system_settings.py": {"get_timezones"},
	# The HR contact card is a DIRECTORY: who in HR to ask, with the work
	# details they publish for exactly that purpose. Every employee is meant to
	# see it, which is why the query filters on the HR ROLE rather than on the
	# caller — revoking the role removes the card with no re-save. Audited
	# 22 Sep 2026: the SQL selects company/personal email and cell number, so
	# this is a deliberate publication, not an accident.
	"hr_contacts.py": {"list_hr_contacts", "employee_with_hr_role_query"},
}


def endpoints(path):
	"""[(name, decorator args, body)] for every whitelisted function in a file."""
	source = path.read_text(encoding="utf-8")
	found = []
	for match in re.finditer(r"@frappe\.whitelist\(([^)]*)\)\s*\ndef (\w+)\(", source):
		name = match.group(2)
		body = re.search(rf"\ndef {name}\(.*?(?=\n@frappe\.whitelist|\Z)", source, re.S)
		found.append((name, match.group(1), body.group(0) if body else ""))
	return found


def api_files():
	return sorted(p for p in API.glob("*.py") if not p.name.startswith("test_"))


class TestThePWACallsOnlyEndpointsThatExist(unittest.TestCase):
	def test_every_endpoint_the_frontend_names_is_defined(self):
		"""A renamed endpoint is invisible until somebody taps the screen."""
		defined = set()
		for path in api_files():
			module = "hrms.api" if path.name == "__init__.py" else f"hrms.api.{path.stem}"
			for name, _, _ in endpoints(path):
				defined.add(f"{module}.{name}")

		called = set()
		for path in FRONTEND.rglob("*"):
			if path.suffix not in (".js", ".vue") or "__tests__" in str(path):
				continue
			for match in re.finditer(r"hrms\.api\.([a-z_0-9.]+)", path.read_text(encoding="utf-8")):
				called.add("hrms.api." + match.group(1).rstrip("."))

		# A private helper mentioned in a comment is not a call; so is the bare
		# module name. Only dotted paths that resolve to a public function count.
		missing = {
			name
			for name in called - defined
			if name != "hrms.api" and "._" not in name and name.count(".") >= 3
		}
		self.assertEqual(missing, set(), "the PWA calls endpoints that do not exist")


class TestEveryEndpointPinsItsMethod(unittest.TestCase):
	def test_nothing_answers_an_unpinned_request(self):
		unpinned = []
		for path in api_files():
			allowed = OPEN_READS.get(path.name, set())
			for name, args, _ in endpoints(path):
				if "methods=" in args:
					continue
				unpinned.append(f"{path.name}:{name}")
			del allowed  # the exemption is for the guard rule, not this one
		self.assertEqual(
			unpinned,
			[],
			'pin methods=["POST"] (or name it in OPEN_READS, with a reason)',
		)

	def test_the_open_reads_really_are_public_reference_data(self):
		"""The exemption list is the weak point, so it is checked rather than
		trusted: an entry that touches Employee, or writes, is not reference
		data and does not belong here."""
		for filename, names in OPEN_READS.items():
			path = API / filename
			bodies = {name: body for name, _, body in endpoints(path)}
			for name in names:
				self.assertIn(name, bodies, f"{filename}:{name} is exempted but does not exist")
				body = bodies[name]
				for forbidden in (".save(", ".insert(", ".submit(", ".cancel(", ".delete(", "db_set"):
					self.assertNotIn(forbidden, body, f"{filename}:{name} WRITES; it cannot be an open read")
				self.assertNotIn(
					'"Employee"', body, f"{filename}:{name} reads Employee; that is not reference data"
				)


class TestEveryEndpointChecksSomething(unittest.TestCase):
	#: Any of these in the body means the endpoint reasoned about who is asking.
	#: Deliberately broad: the rule is "a guard exists", not "a guard is
	#: spelled this way" — several of these delegate to a helper that throws.
	GUARDS = (
		"only_for",
		"has_permission",
		"_require",
		"company_visible",
		"PermissionError",
		"get_roles",
		"frappe.throw",
		"identity",
		"own_employee",
		"is_hr",
		"_decide",
		"_get_visible",
		"_ensure",
		"_can_",
		"visible",
		"permitted",
		"approver",
		"session.user",
		# The identity helpers: `get_employee()` resolves the CALLER's own
		# employee and nobody else's, so an endpoint built on it is scoped by
		# construction rather than by a check it could forget.
		"get_employee(",
		"require_employee",
		"own_employees",
		"_decision_access",
		"_validate_employee_filters",
		"HR_CONTACT_ROLES",
	)

	def test_every_endpoint_guards_or_is_a_named_open_read(self):
		unguarded = []
		for path in api_files():
			allowed = OPEN_READS.get(path.name, set())
			for name, args, body in endpoints(path):
				if name in allowed or "allow_guest" in args:
					continue
				if not any(guard in body for guard in self.GUARDS):
					unguarded.append(f"{path.name}:{name}")
		self.assertEqual(
			unguarded,
			[],
			"an endpoint with no guard is callable by any logged-in user",
		)


if __name__ == "__main__":
	unittest.main()
