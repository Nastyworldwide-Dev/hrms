"""Honest stand-ins for a Frappe document and the Employee table, for stub tests.

Before this, each test built its own stand-in and each got a different piece
wrong (28-29 Sep 2026): a dict that allowed `doc[field] = x` (a real Document
raises TypeError), no `db_set`, and Employee reads that answered one field at
a time while the approval chain reads several at once. Each gap let a real
defect past a green test. Shaped on the installed Frappe
(frappe/model/base_document.py, frappe/model/document.py): attribute access,
get / set, db_set, run_method, is_new — and no item access.

Checked by hrms/tests/test_fake_document_is_honest.py.
"""

from __future__ import annotations


class _Row(dict):
	"""frappe._dict as db.get_value(..., as_dict=True) returns it."""

	def __getattr__(self, key):
		return self.get(key)


class FakeDocument:
	"""A document with fields, as controllers and the approval code use it."""

	def __init__(self, doctype: str, **fields):
		object.__setattr__(self, "doctype", doctype)
		object.__setattr__(self, "db_writes", [])
		object.__setattr__(self, "methods_run", [])
		for key, value in fields.items():
			object.__setattr__(self, key, value)

	def __getattr__(self, key):
		# Frappe returns None for an unset field on attribute access too.
		return None

	def __getitem__(self, key):
		raise TypeError(f"'{self.doctype}' object is not subscriptable")

	def __setitem__(self, key, value):
		raise TypeError(f"'{self.doctype}' object does not support item assignment")

	def get(self, key, filters=None, limit=None, default=None):
		value = self.__dict__.get(key)
		return default if value is None else value

	def set(self, key, value, as_value=False):
		object.__setattr__(self, key, value)

	def db_set(self, fieldname, value=None, update_modified=True, **kwargs):
		if isinstance(fieldname, dict):
			for key, val in fieldname.items():
				self.set(key, val)
				self.db_writes.append((key, val))
			return
		self.set(fieldname, value)
		self.db_writes.append((fieldname, value))

	def run_method(self, method, *args, **kwargs):
		self.methods_run.append(method)
		handler = self.__dict__.get(f"_on_{method}")
		return handler(self) if handler else None

	def is_new(self) -> bool:
		return not self.__dict__.get("name")


def fake_employees(rows: dict[str, dict]):
	"""A `frappe.db.get_value` side effect for the Employee table.

	Answers one field, a list of fields, and as_dict — the three ways the
	approval chain and the fences read an Employee. Status defaults to Active.
	Anything that is not an Employee read returns None.
	"""

	def get_value(doctype, name=None, fieldname=None, *args, **kwargs):
		if doctype != "Employee" or not isinstance(name, str):
			return None
		row = rows.get(name)
		if row is None:
			return None
		full = {"status": "Active", **row, "name": name}
		if isinstance(fieldname, list | tuple):
			return _Row({f: full.get(f) for f in fieldname})
		return full.get(fieldname)

	return get_value
