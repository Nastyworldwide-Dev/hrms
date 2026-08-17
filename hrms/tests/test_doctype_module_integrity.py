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


class TestTheMigrationToolsAreReachable(unittest.TestCase):
	"""The registry and its run log must be findable without typing a URL.

	Seven workspaces carried 162 links between them and neither `HRMS ERP Instance`
	nor `HRMS Sync Run` appeared in any of them — so the only way to reach the one
	screen that starts and reports a migration was to edit the address bar. An
	operator who cannot find a tool cannot use it, and a run they cannot see is
	indistinguishable from one that never happened.
	"""

	WORKSPACES = pathlib.Path(__file__).resolve().parents[1] / "hr" / "workspace"

	def _all_links(self):
		targets = set()
		for path in self.WORKSPACES.glob("*/*.json"):
			for link in json.loads(path.read_text(encoding="utf-8")).get("links", []):
				if link.get("link_to"):
					targets.add(link["link_to"])
		return targets

	def test_the_erp_instance_registry_is_in_a_workspace(self):
		self.assertIn("HRMS ERP Instance", self._all_links())

	def test_the_sync_run_log_is_in_a_workspace(self):
		self.assertIn("HRMS Sync Run", self._all_links())

	def test_every_card_declares_the_number_of_links_under_it(self):
		"""Frappe slices links by the card's `link_count`; a wrong count silently
		drops the tail of a card off the sidebar."""
		for path in self.WORKSPACES.glob("*/*.json"):
			links = json.loads(path.read_text(encoding="utf-8")).get("links", [])
			card, seen = None, 0
			for link in [*links, {"type": "Card Break", "label": "<end>", "link_count": 0}]:
				if link["type"] == "Card Break":
					if card:
						self.assertEqual(
							seen,
							card["link_count"],
							f"{path.name}: card {card['label']!r} declares "
							f"{card['link_count']} links but {seen} follow it",
						)
					card, seen = link, 0
				else:
					seen += 1
