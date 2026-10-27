"""The PWA's service worker is served at /hrms/sw.js, so it can control /hrms.

alpha.12 C1 (measured 26 Sep 2026): the worker was registered from
/assets/hrms/frontend/sw.js, and a worker controls only pages under its own
folder, so it never controlled /hrms: `navigator.serviceWorker.controller` was
null and an offline relaunch failed with a WebKit error. Frappe cannot serve a
.js from www/ by itself (StaticPage refuses .js; TemplatePage would run the
minified bundle through Jinja), so a page renderer serves the built file byte
for byte, never cached, the same pattern nbdy_hub uses for /nbdy/sw.js.

    python3 -m pytest -q hrms/www/test_service_worker.py
"""

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
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


class TestTheManifestIsServedWhereThePageLinksIt(unittest.TestCase):
	"""27 Oct 2026: nobody could install the app. buildBase "/hrms/" (alpha.12, for the
	worker) also moved the page's <link rel="manifest"> to /hrms/manifest.webmanifest,
	which Frappe answered with the app's HTML page. With no manifest, Android Chrome
	offers no install, and an iPhone's Add to Home Screen has no app name or icon."""

	def setUp(self):
		from hrms.www import service_worker as sw

		self.sw = sw
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		self._orig = sw.MANIFEST_FILE
		sw.MANIFEST_FILE = pathlib.Path(self.tmp.name) / "manifest.webmanifest"
		self.addCleanup(lambda: setattr(sw, "MANIFEST_FILE", self._orig))

	def test_the_linked_url_returns_the_built_manifest_as_a_manifest(self):
		self.sw.MANIFEST_FILE.write_bytes(b'{"name":"Nadi"}')
		page = self.sw.ServiceWorkerPage("hrms/manifest.webmanifest")
		self.assertTrue(page.can_render())
		response = page.render()
		self.assertEqual(response.get_data(), b'{"name":"Nadi"}')
		self.assertEqual(response.mimetype, "application/manifest+json")
		self.assertEqual(response.headers["Cache-Control"], "no-cache")

	def test_the_page_links_the_url_this_serves(self):
		built = ROOT / "hrms/www/hrms.html"
		if not built.is_file():
			self.skipTest("no build")
		self.assertIn('rel="manifest" href="/hrms/manifest.webmanifest"', built.read_text())

	def test_a_missing_build_is_not_its_business(self):
		self.assertFalse(self.sw.ServiceWorkerPage("hrms/manifest.webmanifest").can_render())

	def test_the_route_reaches_the_renderer_before_the_app_catch_all(self):
		# without its own rule, /hrms/<path:app_path> rewrote it to "hrms" (the app page)
		hooks = (ROOT / "hrms/hooks.py").read_text()
		own = hooks.find(
			'{"from_route": "/hrms/manifest.webmanifest", "to_route": "hrms/manifest.webmanifest"}'
		)
		self.assertGreater(own, 0)
		self.assertLess(own, hooks.find('"/hrms/<path:app_path>"'))


class TestEveryDoorUsesTheAppRootWorker(unittest.TestCase):
	def test_hooks_register_the_renderer(self):
		hooks = (ROOT / "hrms/hooks.py").read_text()
		self.assertIn('"hrms.www.service_worker.ServiceWorkerPage"', hooks)

	def test_the_app_and_the_update_prompt_register_the_same_url_and_scope(self):
		# registration moved from main.js into utils/serviceWorker.js (registerAppWorker)
		main = (ROOT / "frontend/src/utils/serviceWorker.js").read_text()
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
