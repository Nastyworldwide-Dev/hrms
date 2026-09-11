"""Let hrms modules be imported and unit-tested where frappe is not installed.

The commit gate runs Python tests with the system interpreter, which has no
bench. Tests that only need `frappe.db` / `frappe.get_doc` stand-ins can still
run there: fabricate `frappe` and any `frappe.*` submodule on demand, keeping
the few pieces a module needs at import time real enough — `_dict`, `_`,
`whitelist` — and leaving every other attribute a MagicMock. On a real bench
the package exists and this is a no-op, so the same file runs either way:

    PYTHONPATH=. python3 hrms/tests/test_x.py                      # stub
    PYTHONPATH=. ~/verify-bench/env/bin/python hrms/tests/test_x.py  # real
"""

import importlib.abc
import importlib.util
import sys
import types
from unittest.mock import MagicMock


class _Dict(dict):
	"""frappe._dict: a dict whose keys are also attributes."""

	def __getattr__(self, key):
		return self.get(key)

	def __setattr__(self, key, value):
		self[key] = value


class _Document:
	"""Class-only base for importing controllers; deliberately supplies no fake lifecycle.

	MagicMock cannot stand in for a Python base class: its metaclass turns
	controller subclasses into mocks and prevents their real methods executing.
	Tests must provide their own document state or use real Frappe for lifecycle checks.
	"""


def install():
	try:
		import frappe

		return
	except ImportError:
		pass

	class _Loader(importlib.abc.Loader):
		def create_module(self, spec):
			module = types.ModuleType(spec.name)
			module.__getattr__ = lambda _name: MagicMock()
			module.__path__ = []
			if spec.name == "frappe.model.document":
				module.Document = _Document
			return module

		def exec_module(self, module):
			pass

	class _Finder(importlib.abc.MetaPathFinder):
		def find_spec(self, fullname, path=None, target=None):
			if fullname.startswith("frappe."):
				return importlib.util.spec_from_loader(fullname, _Loader())
			return None

	root = types.ModuleType("frappe")
	root.__path__ = []
	root._dict = _Dict
	root._ = lambda text, *args, **kwargs: text
	root.whitelist = lambda *args, **kwargs: lambda func: func
	# Placeholders so tests can patch.object() them; a test that reaches one
	# unpatched gets a loud MagicMock, not a silent pass.
	for name in ("db", "session", "local", "new_doc", "get_doc", "get_all", "get_cached_doc"):
		setattr(root, name, MagicMock(name=f"frappe.{name}"))

	# frappe.throw must RAISE, or every "rejects X" assertion passes vacuously.
	class ValidationError(Exception):
		pass

	class PermissionError(ValidationError):
		pass

	class DoesNotExistError(ValidationError):
		pass

	class TimestampMismatchError(ValidationError):
		pass

	def throw(msg, exc=ValidationError, *args, **kwargs):
		raise exc(msg)

	root.ValidationError = ValidationError
	root.PermissionError = PermissionError
	root.DoesNotExistError = DoesNotExistError
	root.TimestampMismatchError = TimestampMismatchError
	root.throw = throw
	# A REAL dict, not a MagicMock: `frappe.conf.get("flag")` on a MagicMock
	# returns a MagicMock, which is truthy — so every site-config kill switch
	# reads as ENABLED and the code under test takes its disabled path silently.
	root.conf = {}
	root.__getattr__ = lambda _name: MagicMock()
	sys.modules["frappe"] = root
	sys.modules["frappe.utils"] = _utils_module()
	sys.meta_path.insert(0, _Finder())


def _utils_module():
	"""frappe.utils with the handful of pure helpers modules call on real
	values at test time; everything else stays a MagicMock."""
	import datetime

	def get_datetime(value=None):
		if value is None:
			return datetime.datetime.now()
		if isinstance(value, datetime.datetime):
			return value
		if isinstance(value, datetime.date):
			return datetime.datetime.combine(value, datetime.time())
		text = str(value).strip().replace("T", " ")
		for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
			try:
				return datetime.datetime.strptime(text, fmt)
			except ValueError:
				continue
		raise ValueError(f"unparseable datetime {value!r}")

	def get_time(value):
		if isinstance(value, datetime.datetime):
			return value.time()
		if isinstance(value, datetime.time):
			return value
		if isinstance(value, datetime.timedelta):
			return (datetime.datetime.min + value).time()
		# ceiling: ISO strings only; upgrade when a test needs Frappe's dateutil fallback.
		return datetime.time.fromisoformat(value)

	def add_to_date(value=None, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0, **kwargs):
		if years or months:
			raise NotImplementedError("stub add_to_date covers weeks/days/hours/minutes/seconds only")
		return get_datetime(value) + datetime.timedelta(
			weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
		)

	def cint(value, default=0):
		try:
			return int(float(value))
		except (TypeError, ValueError):
			return default

	def flt(value, precision=None):
		try:
			return float(value)
		except (TypeError, ValueError):
			return 0.0

	module = types.ModuleType("frappe.utils")
	module.__path__ = []
	module.get_time = get_time
	module.get_datetime = get_datetime
	module.getdate = lambda value=None: get_datetime(value).date()
	module.get_datetime_str = lambda value: get_datetime(value).strftime("%Y-%m-%d %H:%M:%S.%f")
	module.now_datetime = datetime.datetime.now
	module.add_days = lambda value, days: get_datetime(value) + datetime.timedelta(days=days)
	module.add_to_date = add_to_date
	module.time_diff_in_hours = lambda later, earlier: (
		(get_datetime(later) - get_datetime(earlier)).total_seconds() / 3600
	)
	module.cint = cint
	module.flt = flt
	module.__getattr__ = lambda _name: MagicMock()
	return module
