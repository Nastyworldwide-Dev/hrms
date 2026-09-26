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

ROUTE = "hrms/sw.js"
SW_FILE = Path(__file__).resolve().parent.parent / "public" / "frontend" / "sw.js"


class ServiceWorkerPage:
	def __init__(self, path, http_status_code=None):
		self.path = (path or "").strip("/ ")
		self.http_status_code = http_status_code or 200

	def can_render(self):
		return self.path == ROUTE and SW_FILE.is_file()

	def render(self):
		"""The built sw.js with no-cache, so a new deploy reaches phones on their next check."""
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
