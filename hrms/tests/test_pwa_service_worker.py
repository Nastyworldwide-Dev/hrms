"""The PWA's service worker is served at /hrms/sw.js, so it can control /hrms.

alpha.12 C1 (measured 26 Sep 2026): the worker was registered from
/assets/hrms/frontend/sw.js, and a worker controls only pages under its own
folder, so it never controlled /hrms: `navigator.serviceWorker.controller` was
null and an offline relaunch failed with a WebKit error. Frappe cannot serve a
.js from www/ by itself (StaticPage refuses .js; TemplatePage would run the
minified bundle through Jinja), so a page renderer serves the built file byte
for byte, never cached, the same pattern nbdy_hub uses for /nbdy/sw.js.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_pwa_service_worker.py
"""

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestServedAtTheAppRoot(unittest.TestCase):
	def setUp(self):
		from hrms.www import service_worker as sw

		self.sw = sw
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		self._orig = sw.SW_FILE
		sw.SW_FILE = pathlib.Path(self.tmp.name) / "sw.js"
		self.addCleanup(lambda: setattr(sw, "SW_FILE", self._orig))

	def test_serves_the_built_file_byte_for_byte_never_cached(self):
		self.sw.SW_FILE.write_bytes(b"self.addEventListener('fetch', () => {});")
		page = self.sw.ServiceWorkerPage("hrms/sw.js")
		self.assertTrue(page.can_render())
		response = page.render()
		self.assertEqual(response.get_data(), b"self.addEventListener('fetch', () => {});")
		self.assertEqual(response.headers["Cache-Control"], "no-cache")
		self.assertEqual(response.mimetype, "application/javascript")
		# the app starts at /hrms (no slash); without this header the browser
		# refuses scope "/hrms" for a worker served under /hrms/
		self.assertEqual(response.headers["Service-Worker-Allowed"], "/hrms")

	def test_other_paths_and_a_missing_build_are_not_its_business(self):
		self.sw.SW_FILE.write_bytes(b"x")
		self.assertFalse(self.sw.ServiceWorkerPage("hrms").can_render())
		self.assertFalse(self.sw.ServiceWorkerPage("hrms/home").can_render())
		self.sw.SW_FILE.unlink()
		self.assertFalse(self.sw.ServiceWorkerPage("hrms/sw.js").can_render())


class TestEveryDoorUsesTheAppRootWorker(unittest.TestCase):
	def test_hooks_register_the_renderer(self):
		hooks = (ROOT / "hrms/hooks.py").read_text()
		self.assertIn('"hrms.www.service_worker.ServiceWorkerPage"', hooks)

	def test_the_app_and_the_update_prompt_register_the_same_url_and_scope(self):
		main = (ROOT / "frontend/src/main.js").read_text()
		vite = (ROOT / "frontend/vite.config.js").read_text()
		self.assertIn('"/hrms/sw.js"', main)
		self.assertNotIn('"/assets/hrms/frontend/sw.js"', main)
		self.assertIn('scope: "/hrms"', main)
		# vite-plugin-pwa's registerSW (UpdatePrompt) builds its URL from
		# buildBase + filename; it must name the same worker, or two workers
		# fight over the page
		self.assertIn('buildBase: "/hrms/"', vite)
		self.assertIn('filename: "sw.js"', vite)
		self.assertIn('scope: "/hrms"', vite)


if __name__ == "__main__":
	unittest.main()
