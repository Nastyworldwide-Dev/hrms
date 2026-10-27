"""Serves the PWA service worker at /hrms/sw.js, byte for byte, never cached.

A service worker controls only pages under the folder it is served from. Built
into /assets/hrms/frontend/, it could never control /hrms, so the app had no
offline launch at all (alpha.12 C1, measured 26 Sep 2026). Frappe will not
serve it from www/ by itself: StaticPage refuses .js and TemplatePage would run
the minified bundle through Jinja. This page renderer (hooks.py
`page_renderer`) is tried before the built-in ones, for this one path only.
"""

import logging
from pathlib import Path

from werkzeug.wrappers import Response

logger = logging.getLogger(__name__)

BUILD = Path(__file__).resolve().parent.parent / "public" / "frontend"
ROUTE = "hrms/sw.js"
SW_FILE = BUILD / "sw.js"
# The page links its manifest at /hrms/manifest.webmanifest (vite buildBase "/hrms/",
# set for the worker). Unserved, Frappe answered it with the app page: no manifest,
# so Android offered no install and an iPhone saved no name or icon (27 Oct 2026).
MANIFEST_ROUTE = "hrms/manifest.webmanifest"
MANIFEST_FILE = BUILD / "manifest.webmanifest"


class ServiceWorkerPage:
	def __init__(self, path, http_status_code=None):
		self.path = (path or "").strip("/ ")
		self.http_status_code = http_status_code or 200

	def can_render(self):
		if self.path == MANIFEST_ROUTE:
			return MANIFEST_FILE.is_file()
		return self.path == ROUTE and SW_FILE.is_file()

	def render(self):
		"""The built sw.js (or the manifest) with no-cache, so a new deploy reaches phones on their next check."""
		if self.path == MANIFEST_ROUTE:
			return self._manifest()
		body = SW_FILE.read_bytes()
		response = Response(body, status=200, mimetype="application/javascript")
		response.headers["Cache-Control"] = "no-cache"
		response.headers["X-Content-Type-Options"] = "nosniff"
		# Served from /hrms/sw.js the worker may only cover /hrms/, but the app
		# starts at /hrms (no slash, the manifest's start_url and scope). The
		# browser rejected scope "/hrms" until the server allowed it.
		response.headers["Service-Worker-Allowed"] = "/hrms"
		logger.info("[hrms.sw] served %s bytes", len(body))
		return response

	def _manifest(self):
		"""The built manifest, as a manifest, never cached (a deploy may change it)."""
		body = MANIFEST_FILE.read_bytes()
		response = Response(body, status=200, mimetype="application/manifest+json")
		response.headers["Cache-Control"] = "no-cache"
		response.headers["X-Content-Type-Options"] = "nosniff"
		logger.info("[hrms.sw] served the manifest, %s bytes", len(body))
		return response
