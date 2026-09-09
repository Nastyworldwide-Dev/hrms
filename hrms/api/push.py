"""Push subscribe/unsubscribe, routed through the self-healing relay call.

`hooks.py` maps `frappe.push_notification.subscribe` and `.unsubscribe` here
(`override_whitelisted_methods`), so the PWA — which calls the framework's
endpoints by name — heals a cloned site's stale relay credentials without a
frontend change. Same signature, same `{success, message}` response.
"""

from __future__ import annotations

import logging

import frappe
from frappe.push_notification import PushNotification

from hrms.utils.push_relay import relay_call

logger = logging.getLogger(__name__)


@frappe.whitelist(methods=["GET"])
def subscribe(fcm_token: str, project_name: str) -> dict:
	logger.info("[push] subscribe project=%s", project_name)
	client = PushNotification(project_name)
	success, message = relay_call(client.add_token, frappe.session.user, fcm_token)
	return {"success": success, "message": message}


@frappe.whitelist(methods=["GET"])
def unsubscribe(fcm_token: str, project_name: str) -> dict:
	logger.info("[push] unsubscribe project=%s", project_name)
	client = PushNotification(project_name)
	success, message = relay_call(client.remove_token, frappe.session.user, fcm_token)
	return {"success": success, "message": message}
