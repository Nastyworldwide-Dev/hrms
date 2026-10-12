"""Plain staff who click Nadi on Desk land in the PWA (owner, 2 Oct 2026, ruling b).

Nadi's Desk home is the Shift & Attendance workspace, open to HR and Shift
Supervisors only. Everyone else used to reach "No permission for Page"; their
Nadi tile and app-switcher entry now point at /hrms.

	PYTHONPATH=. python3 hrms/tests/test_desk_boot.py
"""

import pathlib
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

from hrms.desk_boot import PWA_HOME, send_plain_staff_to_pwa


def _boot(pages):
	# frappe._dict, as the real bootinfo is: hooks read it with .get() and attributes
	return frappe._dict(
		workspaces={"pages": [SimpleNamespace(name=p) for p in pages]},
		desktop_icons=[
			SimpleNamespace(label="Nadi", link="/desk/shift-&-attendance"),
			SimpleNamespace(label="Shift & Attendance", link=None),
		],
		app_data=[
			{"app_name": "erpnext", "app_route": "/desk/home"},
			{"app_name": "hrms", "app_route": "/desk/shift-&-attendance"},
		],
	)


class TestPlainStaffGoToPwa(unittest.TestCase):
	def test_plain_staff_are_sent_to_the_pwa(self):
		boot = _boot(["Home"])
		send_plain_staff_to_pwa(boot)
		self.assertEqual(boot.desktop_icons[0].link, PWA_HOME)
		self.assertEqual(boot.app_data[1]["app_route"], PWA_HOME)
		self.assertEqual(PWA_HOME, "/hrms")

	def test_hr_and_supervisors_keep_the_desk_home(self):
		boot = _boot(["Home", "Shift & Attendance"])
		send_plain_staff_to_pwa(boot)
		self.assertEqual(boot.desktop_icons[0].link, "/desk/shift-&-attendance")
		self.assertEqual(boot.app_data[1]["app_route"], "/desk/shift-&-attendance")

	def test_other_apps_are_untouched(self):
		boot = _boot([])
		send_plain_staff_to_pwa(boot)
		self.assertEqual(boot.app_data[0]["app_route"], "/desk/home")
		self.assertIsNone(boot.desktop_icons[1].link)


class TestBootHookNeverBreaksThePage(unittest.TestCase):
	"""Live, 12 Oct 2026: bootinfo.desktop_icons was None for a Projects-only user, the hook
	raised TypeError, Frappe turned it into SessionBootFailed, and /desk and /board gave 500."""

	def test_no_desktop_icons_is_not_an_error(self):
		boot = _boot(["Home"])
		boot.desktop_icons = None
		send_plain_staff_to_pwa(boot)
		self.assertEqual(boot.app_data[1]["app_route"], PWA_HOME)

	def test_missing_keys_are_not_an_error(self):
		send_plain_staff_to_pwa(frappe._dict(workspaces={"pages": []}))

	def test_no_workspaces_is_not_an_error(self):
		send_plain_staff_to_pwa(frappe._dict(workspaces=None, desktop_icons=None, app_data=None))

	def test_a_surprise_inside_the_hook_is_logged_not_raised(self):
		boot = _boot(["Home"])
		boot.desktop_icons = [object()]  # no .label
		send_plain_staff_to_pwa(boot)

if __name__ == "__main__":
	unittest.main()
