"""A select value compared in Python must be one the field actually declares.

Two live defects found by audit on 11 Sep 2026, both of this shape:

  * leave_policy_assignment.py:164 compares `assignment_based_on == "Leave
    Policy"`. The field declares "", "Leave Period", "Joining Date". The test
    is therefore ALWAYS false, so every Leave Allocation created by a policy
    assignment is written with leave_period = "" — even when the assignment IS
    based on a leave period. leave_encashment.py:346 then carries the blank
    forward.
  * employee_referral.py:54 compares against "In process"; the field declares
    "In Process". Half the intended branch is dead.

Neither raises. A string that matches nothing is indistinguishable from a
branch that was not meant to run, which is why both survived.

This gate reads the doctype JSON and the controller source — no site, so the
commit gate runs it on the system interpreter.
"""

import json
import pathlib
import re
import unittest

HRMS = pathlib.Path(__file__).resolve().parents[1]

#: `self.<field> == "<value>"` and the `!=` / `in [...]` forms beside it.
_EQ = re.compile(r'(\w+)\.(\w+)\s*(?:==|!=)\s*"([^"]+)"')
_IN = re.compile(r"(\w+)\.(\w+)\s+(?:not\s+)?in\s+[\[\(]([^\]\)]*)[\]\)]")
_STR = re.compile(r'"([^"]*)"')
#: `name = frappe.get_doc("Some Doctype", ...)` — how a controller reaches
#: another doctype's select, which is where the Employee Referral defect lived.
_GET_DOC = re.compile(r'(\w+)\s*=\s*frappe\.(?:get_doc|get_cached_doc|new_doc)\(\s*"([^"]+)"')


def _all_select_options() -> dict:
	"""Doctype name -> {fieldname -> declared values}, for static Selects."""
	out = {}
	for path in HRMS.rglob("doctype/*/*.json"):
		try:
			doc = json.loads(path.read_text())
		except (OSError, ValueError):
			continue
		# Some files under doctype/ are list-shaped fixtures, not DocTypes.
		if not isinstance(doc, dict) or doc.get("doctype") != "DocType" or not doc.get("name"):
			continue
		fields = {}
		for field in doc.get("fields", []):
			if field.get("fieldtype") != "Select":
				continue
			options = field.get("options")
			# Options that name a doctype or carry a jinja expression are
			# filled at runtime; there is nothing static to check.
			if not isinstance(options, str) or "{" in options:
				continue
			fields[field["fieldname"]] = {line.strip() for line in options.split("\n")}
		if fields:
			out[doc["name"]] = fields
	return out


def _doctype_of(path: pathlib.Path, by_doctype: dict) -> str | None:
	"""The doctype a controller belongs to, so `self.` resolves."""
	sibling = path.with_suffix(".json")
	if not sibling.exists():
		return None
	try:
		name = json.loads(sibling.read_text()).get("name")
	except (OSError, ValueError):
		return None
	return name if name in by_doctype else None


def _undeclared(path: pathlib.Path, by_doctype: dict):
	source = path.read_text()
	# What each local name refers to: `self` plus every get_doc in this module.
	local = {name: doctype for name, doctype in _GET_DOC.findall(source) if doctype in by_doctype}
	own = _doctype_of(path, by_doctype)
	if own:
		local["self"] = own
	if not local:
		return

	def check(var, field, values, start):
		doctype = local.get(var)
		options = by_doctype.get(doctype, {}).get(field) if doctype else None
		if not options:
			return
		for value in values:
			if value not in options:
				line = source[:start].count("\n") + 1
				yield (
					f"{path.relative_to(HRMS.parent)}:{line} {var}.{field} -> {value!r} "
					f"({doctype} declares {sorted(options)})"
				)

	for match in _EQ.finditer(source):
		yield from check(match.group(1), match.group(2), [match.group(3)], match.start())
	for match in _IN.finditer(source):
		yield from check(match.group(1), match.group(2), _STR.findall(match.group(3)), match.start())


class TestSelectLiteralsAreDeclared(unittest.TestCase):
	def test_every_compared_select_value_is_one_the_field_declares(self):
		by_doctype = _all_select_options()
		self.assertTrue(by_doctype, "no doctype JSON found — the scan is not reaching the app")
		bad = []
		for path in HRMS.rglob("*.py"):
			if path.name.startswith("test_") or "/tests/" in str(path):
				continue
			bad.extend(_undeclared(path, by_doctype))
		self.assertEqual(
			sorted(bad),
			[],
			"a select value compared here is not one the field declares, so the branch is dead:\n"
			+ "\n".join(sorted(bad)),
		)
