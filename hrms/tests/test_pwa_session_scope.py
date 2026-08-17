"""Every auto-firing PWA call must resolve the caller's own employee.

The PWA is session-scoped: it knows who is signed in and does not, in general,
know their Employee id. `hrms.api.get_leave_balance_map` already carries the scar
from that migration in its own comment —

    "The endpoint became session-scoped (the PWA calls it with no arguments) but
     the guard was left above the assignment, so every call raised
     UnboundLocalError before reaching any of this."

— and seven endpoints were left behind by it, each still declaring `employee` as
a required positional argument. A call without it raises `TypeError` before a
line of the body runs, and the UI then renders NOTHING: a resource that errored
has no `.data`, and the templates are written `v-if="x.data"`.

That is the whole reported defect — no attendance calendar, no My/Team/History
requests, no expense summary, no upcoming shifts. Four features, one cause, and
nothing on screen to connect them.

Two reasons to pin it structurally rather than fix four cases:

* it fails silently, as a blank panel and a console nobody is reading;
* the frontend cannot compensate. Eleven call sites pass
  `employee: employeeResource.data.name` through a STATIC `params` object,
  evaluated once at module load — before the session employee has resolved.

So the contract lives on the server: for anything the PWA fires automatically,
`employee` is optional and defaults to the session's own. Passing one explicitly
still works and is still permission-checked; that is how a manager reads their
team, and it is why this file only judges AUTO-FIRING resources. An endpoint
invoked from a button with explicit arguments is a different thing.

Pure static check over the source — no bench, no site. Run as a FILE:

    python3 hrms/tests/test_pwa_session_scope.py
"""

import ast
import pathlib
import re
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = HRMS_ROOT.parent / "frontend" / "src"


def _whitelisted_signatures() -> dict[str, list[str]]:
	"""{dotted path: [required argument names]} for every whitelisted function."""
	signatures = {}
	for path in HRMS_ROOT.rglob("*.py"):
		if "__pycache__" in str(path) or path.name.startswith("test_"):
			continue
		try:
			tree = ast.parse(path.read_text(encoding="utf-8"))
		except SyntaxError:
			continue
		module = str(path.relative_to(HRMS_ROOT.parent).with_suffix("")).replace("/", ".")
		module = module.removesuffix(".__init__")
		for node in ast.walk(tree):
			if not isinstance(node, ast.FunctionDef):
				continue
			if not any(
				(isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "whitelist")
				or getattr(d, "attr", "") == "whitelist"
				for d in node.decorator_list
			):
				continue
			args = [a.arg for a in node.args.args]
			cutoff = len(args) - len(node.args.defaults)
			signatures[f"{module}.{node.name}"] = args[:cutoff]
	return signatures


def _brace_block(source: str, index: int) -> str:
	"""The `{...}` starting at or after `index`, brace-matched."""
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
				return source[position and start : position + 1]
	return source[start:]


def _auto_firing_calls() -> dict[str, set[str]]:
	"""{endpoint: parameter names it sends} for resources that fire on their own.

	`auto: true` means the request goes out as soon as the component mounts, with
	exactly the parameters declared beside it — nothing gets a chance to add one.
	Those are the calls that can blank a screen.
	"""
	calls = {}
	for path in FRONTEND.rglob("*"):
		if path.suffix not in (".js", ".vue"):
			continue
		source = path.read_text(encoding="utf-8")
		for match in re.finditer(r"createResource\s*\(", source):
			body = _brace_block(source, match.end() - 1)
			url = re.search(r'url:\s*"(hrms\.[\w.]+)"', body)
			if not url or not re.search(r"auto:\s*true", body):
				continue
			keys: set[str] = set()
			for keyword in ("makeParams", "params"):
				marker = re.search(keyword + r"\s*(\(\))?\s*[:(]?", body)
				if marker:
					keys |= set(re.findall(r"(\w+)\s*:", _brace_block(body, marker.end())))
			calls.setdefault(url.group(1), set()).update(keys)
	return calls


class TestPWAEndpointsAreSessionScoped(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.signatures = _whitelisted_signatures()
		cls.calls = _auto_firing_calls()

	def test_the_scan_found_both_sides(self):
		"""Guards the guard — an empty scan would pass everything below."""
		self.assertGreater(len(self.calls), 10, "no auto-firing PWA calls found; the scan is broken")
		self.assertGreater(len(self.signatures), 100, "no whitelisted functions found")

	def test_no_auto_firing_call_requires_an_argument_it_does_not_send(self):
		"""The contract, stated once for every endpoint rather than per bug report."""
		offenders = []
		for url, sent in sorted(self.calls.items()):
			missing = [a for a in self.signatures.get(url, []) if a not in sent]
			if missing:
				offenders.append(f"{url} needs {missing}")

		self.assertEqual(
			offenders,
			[],
			"auto-firing PWA calls missing a required argument — these render blank: " + "; ".join(offenders),
		)

	def test_the_frontend_never_captures_the_employee_at_module_load(self):
		"""`params: {employee: employeeResource.data.name}` is evaluated ONCE, when
		the module is imported — before the session employee has resolved.

		`makeParams()` is read per request instead. The server-side default makes
		this survivable either way, but a static capture is a load-order landmine
		whose only symptom is an empty screen.
		"""
		offenders = []
		for path in FRONTEND.rglob("*"):
			if path.suffix not in (".js", ".vue"):
				continue
			source = path.read_text(encoding="utf-8")
			for match in re.finditer(r"employee:\s*employeeResource\.data\.\w+", source):
				preceding = source[: match.start()].rsplit("createResource", 1)[-1]
				if "makeParams" not in preceding:
					line = source[: match.start()].count("\n") + 1
					offenders.append(f"{path.relative_to(FRONTEND)}:{line}")

		self.assertEqual(
			offenders,
			[],
			"static employee capture (use makeParams() so it is read per request): " + ", ".join(offenders),
		)


if __name__ == "__main__":
	unittest.main()
