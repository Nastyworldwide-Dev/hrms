"""The Nadi app icon must keep its children, or it stops being a launcher.

Frappe decides whether an app icon opens a workspace modal or navigates on one
condition (frappe/desk/page/desktop/desktop.js:1123):

    if (this.child_icons?.length && (icon_type == "App" || icon_type == "Folder"))

`child_icons` is assembled by matching each icon's `parent_icon` against the
parent's `label`. So a single mismatched string turns the launcher into a plain
link, silently — which is exactly what happened when the rebrand renamed the
parent and the patch deleted the old record out from under nine children that
still pointed at it.

This pins the fixture side of that contract. The database side is pinned by
hrms/tests/test_repair_nadi_desktop_icon_children.py, and the delivery side —
whether an edit to these files ever reaches a site at all — by
scripts/check_fixture_timestamps.py.

Pure static check over the shipped JSON. No bench, no site.
Run in file mode — importing the package would drag in frappe:

    python3 hrms/tests/test_desktop_icon_fixtures.py
"""

import json
import pathlib
import unittest

ICON_DIR = pathlib.Path(__file__).resolve().parents[1] / "desktop_icon"

#: The parent every HR workspace icon hangs off. Renamed from "Frappe HR" by
#: patches/v16_0/rename_frappe_hr_desktop_icon.py.
APP_LABEL = "Nadi"


def load_icons():
	return {path.name: json.loads(path.read_text()) for path in sorted(ICON_DIR.glob("*.json"))}


class TestDesktopIconFixtures(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.icons = load_icons()
		cls.by_label = {i["label"]: i for i in cls.icons.values()}

	def test_exactly_one_app_icon_and_it_is_the_brand(self):
		apps = [i for i in self.icons.values() if i.get("icon_type") == "App"]
		self.assertEqual([a["label"] for a in apps], [APP_LABEL])

	def test_the_app_icon_has_no_parent(self):
		self.assertFalse(self.by_label[APP_LABEL].get("parent_icon"))

	def test_every_other_icon_hangs_off_the_app_icon(self):
		orphans = [
			i["label"]
			for i in self.icons.values()
			if i.get("icon_type") != "App" and i.get("parent_icon") != APP_LABEL
		]
		self.assertEqual(orphans, [], f"icons not parented to {APP_LABEL!r}: {orphans}")

	def test_no_parent_icon_dangles(self):
		"""A `parent_icon` naming a label no fixture ships is the shape of the
		outage: the modal condition reads it, finds nothing, and the icon
		degrades to a link with no error anywhere."""
		labels = set(self.by_label)
		dangling = {
			i["label"]: i["parent_icon"]
			for i in self.icons.values()
			if i.get("parent_icon") and i["parent_icon"] not in labels
		}
		self.assertEqual(dangling, {})

	def test_the_launcher_would_render_a_modal(self):
		"""The desktop.js condition, evaluated against the fixtures."""
		app = self.by_label[APP_LABEL]
		children = [i for i in self.icons.values() if i.get("parent_icon") == APP_LABEL]
		self.assertTrue(
			children and app.get("icon_type") in ("App", "Folder"),
			"Nadi would navigate instead of opening its workspace modal",
		)
		self.assertEqual(len(children), 9)

	def test_no_icon_carries_the_retired_brand(self):
		stale = [
			i["label"]
			for i in self.icons.values()
			if "Frappe HR" in (i.get("label", ""), i.get("parent_icon") or "")
		]
		self.assertEqual(stale, [])


if __name__ == "__main__":
	unittest.main()
