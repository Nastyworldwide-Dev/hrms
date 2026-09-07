"""pytest without a bench: stub frappe, and skip the suites that need a site.

The commit gate runs the tests mapped to a change with the system
interpreter, where frappe is not installed. Two things must hold there:

* a pure unit test placed next to its module (hrms/api/test_x.py) is imported
  through the `hrms` package, whose __init__ imports frappe — so the stub has
  to be installed BEFORE collection, which is what this file is for;
* a suite written against a real site (FrappeTestCase, make_employee, ...)
  cannot run without one. It is skipped here, not failed, and reported as
  such; run it with `bench run-tests` on the verify bench instead.

On a bench, or wherever frappe imports, this file changes nothing.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

HAS_FRAPPE = importlib.util.find_spec("frappe") is not None

if not HAS_FRAPPE:
	sys.path.insert(0, str(Path(__file__).resolve().parent / "hrms" / "tests"))
	import _erpnext_stub
	import _frappe_stub

	_frappe_stub.install()
	_erpnext_stub.install()

_NEEDS_A_SITE = re.compile(
	r"frappe\.tests|FrappeTestCase|IntegrationTestCase|UnitTestCase|HRMSTestSuite"
	r"|hrms\.tests\.utils|hrms\.tests\.test_utils|make_employee|frappe\.set_user\("
)


def _needs_a_site(path):
	if HAS_FRAPPE or path.suffix != ".py" or not path.name.startswith("test_"):
		return False
	try:
		return bool(_NEEDS_A_SITE.search(path.read_text(errors="ignore")))
	except OSError:
		return False


class _SiteOnlyModule(pytest.Module):
	"""A suite that needs a site: collected as empty rather than imported."""

	def collect(self):
		sys.stderr.write(f"[conftest] {self.path.relative_to(Path.cwd())}: needs a bench site; skipped\n")
		return []


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makemodule(module_path, parent):
	# firstresult hook, and explicitly listed files reach it too — which
	# pytest_ignore_collect does not reliably do for command-line arguments.
	if _needs_a_site(module_path):
		return _SiteOnlyModule.from_parent(parent, path=module_path)
	return None


def pytest_sessionfinish(session, exitstatus):
	# Every selected file needed a site: nothing collected is not a failure.
	if not HAS_FRAPPE and exitstatus == 5:
		session.exitstatus = 0
