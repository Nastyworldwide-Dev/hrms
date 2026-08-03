"""Let hrms modules that reach erpnext be imported in pure unit tests.

Several hrms modules import erpnext at load time (hrms.hr.utils, hrms.api).
Outside a bench erpnext isn't installed, so fabricate any erpnext.* module on
demand. On a real bench the package exists and this is a no-op.
"""

import importlib.abc
import importlib.util
import sys
import types
from unittest.mock import MagicMock


def install():
	try:
		import erpnext

		return
	except ImportError:
		pass

	class _Loader(importlib.abc.Loader):
		def create_module(self, spec):
			module = types.ModuleType(spec.name)
			module.__getattr__ = lambda _name: MagicMock()
			module.__path__ = []
			return module

		def exec_module(self, module):
			pass

	class _Finder(importlib.abc.MetaPathFinder):
		def find_spec(self, fullname, path=None, target=None):
			if fullname == "erpnext" or fullname.startswith("erpnext."):
				return importlib.util.spec_from_loader(fullname, _Loader())
			return None

	sys.meta_path.insert(0, _Finder())
