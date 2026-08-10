"""Every doctype directory must be a working Python module.

Frappe calls `load_doctype_module()` during `bench migrate` for each doctype it
syncs, and imports `<app>.<module>.doctype.<name>.<name>`. A directory holding
only a `.json` therefore aborts the whole migrate part-way through, leaving the
site in maintenance mode:

    ModuleNotFoundError: No module named
        'hrms.hr.doctype.hrms_erp_instance_company.hrms_erp_instance_company'
    ImportError: Module import failed for HRMS ERP Instance Company,
        the DocType you're trying to open might be deleted.

That is exactly what happened on verifica-live on 2026-08-10: the
`HRMS ERP Instance Company` child table shipped with `__init__.py` and its
`.json` but no controller. Child tables need a controller just as much as
parent doctypes do — it is easy to forget precisely because the class is
usually empty.

Pure static check over the repo — no bench, no site.
"""

import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _doctype_dirs():
	"""Every directory that ships a doctype definition."""
	for json_path in HRMS_ROOT.glob("*/doctype/*/*.json"):
		folder = json_path.parent
		if json_path.stem != folder.name:
			continue  # e.g. a dashboard/chart json living alongside
		try:
			doc = json.loads(json_path.read_text(encoding="utf-8"))
		except (json.JSONDecodeError, UnicodeDecodeError):
			continue
		if isinstance(doc, dict) and doc.get("doctype") == "DocType":
			yield folder, doc


class TestDoctypeModuleIntegrity(unittest.TestCase):
	def test_every_doctype_has_a_controller(self):
		missing = [
			str(folder.relative_to(HRMS_ROOT) / f"{folder.name}.py")
			for folder, _ in _doctype_dirs()
			if not (folder / f"{folder.name}.py").exists()
		]
		self.assertEqual(
			missing,
			[],
			"doctype folders without a controller module — bench migrate will abort on these: "
			+ ", ".join(missing),
		)

	def test_every_doctype_folder_is_a_package(self):
		missing = [
			str(folder.relative_to(HRMS_ROOT) / "__init__.py")
			for folder, _ in _doctype_dirs()
			if not (folder / "__init__.py").exists()
		]
		self.assertEqual(missing, [], "doctype folders missing __init__.py: " + ", ".join(missing))

	def test_child_tables_are_covered_too(self):
		"""The regression that motivated this file was a child table."""
		children = [(f, d) for f, d in _doctype_dirs() if d.get("istable")]
		self.assertTrue(children, "expected at least one child-table doctype in the repo")
		for folder, _ in children:
			with self.subTest(doctype=folder.name):
				self.assertTrue(
					(folder / f"{folder.name}.py").exists(),
					f"child table {folder.name} has no controller",
				)


if __name__ == "__main__":
	unittest.main()
