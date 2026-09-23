"""The PWA boot carries the site's time zone.

Without it `frontend/src/utils/siteTime.js` fell back to Asia/Dubai on every
site, so a Malaysia-time (UTC+8) approval stamped 18:31 rendered as 22:31 and
read "in an hour" in Notifications (owner screenshot, 23 Sep 2026).

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_pwa_boot_timezone.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.www import hrms as pwa


class BootTimeZone(unittest.TestCase):
	def _boot(self, tz):
		with (
			patch.object(pwa, "load_translations", lambda boot: None),
			patch.object(pwa, "get_default_route", lambda: "/hrms"),
			patch.object(pwa, "get_system_timezone", lambda: tz, create=True),
		):
			return pwa.get_boot()

	def test_boot_sends_the_site_zone_where_siteTime_reads_it(self):
		boot = self._boot("Asia/Kuala_Lumpur")
		self.assertEqual(boot["sysdefaults"]["time_zone"], "Asia/Kuala_Lumpur")

	def test_the_zone_is_whatever_system_settings_says(self):
		# get_system_timezone never returns None (Frappe defaults it), so the
		# client's Dubai fallback is now only for a boot that predates this.
		self.assertEqual(self._boot("Europe/Rome")["sysdefaults"]["time_zone"], "Europe/Rome")


if __name__ == "__main__":
	unittest.main()
