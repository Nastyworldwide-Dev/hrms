"""`hrms.setup.get_custom_fields()` must define each field exactly once.

The definition is a plain list per doctype, and `create_custom_fields` walks it in
order. Two entries for one fieldname are not an error — the later one simply
wins, silently.

That is how E3 survived being removed. `performance_band` was declared TWICE
under `Employee`, so deleting the value from one block left the other intact and
authoritative, and the field kept its old options through a change that read as
applied. A duplicate does not break a site; it breaks the assumption that editing
a definition changes anything, which is worse, because the next person reads the
block they found and believes it.

The band list is pinned alongside, because it is not derived from the data — HR
own it. B2 is a band in use and belongs. E3 was a data-entry mistake on the
source, confirmed by HR, and stays out: a destination that widens to accept
whatever arrives has stopped being a schema.

Read with AST rather than imported, like every other static guard here, so it
needs no site and no stub of frappe's import graph to drift against. Run as a
FILE:

    python3 hrms/tests/test_custom_field_definitions.py
"""

import ast
import pathlib
import unittest

SETUP = pathlib.Path(__file__).resolve().parents[1] / "setup.py"


def _definitions() -> dict[str, list[dict]]:
	"""{doctype: [{key: literal}]} for every field `get_custom_fields()` declares.

	Only literal keys and values are read; anything computed (a `_()` call, a
	name) is skipped, which is fine — nothing this file asserts on is computed.
	"""
	tree = ast.parse(SETUP.read_text(encoding="utf-8"))
	function = next(
		node
		for node in ast.walk(tree)
		if isinstance(node, ast.FunctionDef) and node.name == "get_custom_fields"
	)

	found: dict[str, list[dict]] = {}
	for mapping in (n for n in ast.walk(function) if isinstance(n, ast.Dict)):
		for key, value in zip(mapping.keys, mapping.values, strict=True):
			if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
				continue
			if not isinstance(value, ast.List):
				continue
			fields = []
			for element in value.elts:
				if not isinstance(element, ast.Dict):
					continue
				definition = {
					k.value: v.value
					for k, v in zip(element.keys, element.values, strict=True)
					if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)
				}
				if "fieldname" in definition:
					fields.append(definition)
			if fields:
				found.setdefault(key.value, []).extend(fields)
	return found


class TestNoFieldIsDefinedTwice(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.definitions = _definitions()

	def test_the_scan_found_the_definitions(self):
		"""Guards the guard — an empty read would pass everything below."""
		self.assertIn("Employee", self.definitions)
		self.assertGreater(sum(len(v) for v in self.definitions.values()), 20)

	def test_every_fieldname_appears_once_per_doctype(self):
		offenders = []
		for doctype, definitions in sorted(self.definitions.items()):
			names = [d["fieldname"] for d in definitions]
			offenders += [
				f"{doctype}.{name} x{names.count(name)}"
				for name in sorted(set(names))
				if names.count(name) > 1
			]

		self.assertEqual(
			offenders,
			[],
			"duplicate custom field definitions — the last silently wins, so editing "
			"the other changes nothing: " + ", ".join(offenders),
		)


class TestPerformanceBandIsHROwned(unittest.TestCase):
	"""Six bands. Values arriving from the source do not get to add a seventh.

	B2 and E3 both reach the mirror from the source ERP, and NEITHER has ever
	appeared in this code — checked across version-16, as-hr_kpi and the hotfix
	branch, which all carry the same six. They are data-entry values, and HR have
	confirmed both are mistakes to fix over there.

	B2 was briefly added here on a first reading of that conversation, which is the
	whole reason this class is explicit about both: the pressure to widen a
	destination until it accepts whatever arrives is constant, feels helpful, and
	ends with a Select that constrains nothing — the same state `Shift Location.
	timezone` was already in.
	"""

	def _options(self):
		employee = _definitions()["Employee"]
		band = next(d for d in employee if d["fieldname"] == "performance_band")
		return [option for option in band["options"].split("\n") if option]

	def test_neither_source_only_value_is_accepted(self):
		"""Refusing costs one field and names it on the run; the employee still
		writes, and the value self-heals once HR correct it at the source."""
		for value in ("B2", "E3"):
			self.assertNotIn(value, self._options(), f"{value} is source data, not a band")

	def test_the_scheme_is_intact(self):
		self.assertEqual(self._options(), ["B", "C", "D", "E1", "E2", "F"])


if __name__ == "__main__":
	unittest.main()
