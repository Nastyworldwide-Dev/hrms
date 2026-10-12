"""Where Nadi opens on Desk for someone who cannot open its Desk home.

The Nadi app's Desk home is the Shift & Attendance workspace (hooks.app_home),
gated to HR and Shift Supervisors. Plain staff clicked Nadi and reached "No
permission for Page"; owner, 2 Oct 2026 (ruling b): send them to the PWA.
Frappe already worked out which workspaces this user may open, so the gate is
read from the boot, never restated.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

DESK_HOME = "Shift & Attendance"
PWA_HOME = "/hrms"
APP_ICON = "Nadi"
APP_NAME = "hrms"


def send_plain_staff_to_pwa(bootinfo):
	"""extend_bootinfo hook.

	It runs inside every frappe.sessions.get(), /desk and /board included, so a
	raise here is a 500 for the whole page (SessionBootFailed). Live, 12 Oct
	2026: desktop_icons was None for a Projects-only user and the loop crashed.
	Every key is read as optional, and a failure is logged, never raised: the
	worst outcome is that the Nadi tile keeps its Desk link.
	"""
	try:
		pages = (bootinfo.get("workspaces") or {}).get("pages") or []
		if DESK_HOME in {p.name for p in pages}:
			return
		for icon in bootinfo.get("desktop_icons") or []:
			if icon.label == APP_ICON:
				icon.link = PWA_HOME
		for app in bootinfo.get("app_data") or []:
			if app.get("app_name") == APP_NAME:
				app["app_route"] = PWA_HOME
		logger.info("[desk_boot] %s cannot open %s; Nadi opens the PWA", frappe.session.user, DESK_HOME)
	except Exception:
		logger.exception("[desk_boot] could not redirect Nadi to the PWA for %s", frappe.session.user)
