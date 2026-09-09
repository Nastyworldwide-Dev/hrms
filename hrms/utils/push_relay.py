"""Self-healing calls to the Frappe push notification relay.

Frappe's relay client (`frappe.push_notification.PushNotification`) registers
a site with the central relay once and stores the API key and secret in
`Push Notification Settings`. From then on it reuses them blindly. A site built
from a COPY of another site (verifica-live from nasty-live, September 2026)
inherits the source's credentials, so every relay call identifies as the old
site while naming the new one in `site_name`. The relay refuses with a
PermissionError on the Notification User it tries to create for the new site,
and every subscribe and every push send on the new site fails.

`relay_call` recognises that refusal, clears the stored credentials, and
retries once. `_get_credential` then registers THIS site's hostname and stores
fresh credentials, so the retry and everything after it succeed. One retry,
never a loop; any other failure is left exactly as it was.
"""

from __future__ import annotations

import logging
import re

import frappe

logger = logging.getLogger(__name__)

SETTINGS = "Push Notification Settings"

#: `<endpoint>@notification.frappe` — the relay's per-site API user, quoted in
#: its permission refusal. Logged so the operator can see WHOSE key was stored.
_RELAY_USER = re.compile(r"([\w.\-]+)@notification\.frappe")


def is_relay_permission_error(exc: BaseException) -> bool:
	"""The relay refused our credentials for a row it expects us to own."""
	text = str(exc)
	return "PermissionError" in text and "Notification User" in text


def reset_relay_credentials(exc: BaseException | None = None) -> None:
	"""Forget the stored relay credentials so the next call re-registers."""
	stale_user = _RELAY_USER.search(str(exc)) if exc is not None else None
	logger.warning(
		"[push_relay] relay refused the stored credentials (registered as %s); clearing them so this site re-registers",
		stale_user.group(0) if stale_user else "unknown",
	)
	frappe.db.set_single_value(SETTINGS, "api_key", None)
	frappe.db.set_single_value(SETTINGS, "api_secret", None)


def relay_call(fn, *args, **kwargs):
	"""Run one relay call; on a credential refusal, re-register and retry once."""
	try:
		return fn(*args, **kwargs)
	except Exception as exc:
		if not is_relay_permission_error(exc):
			raise
		reset_relay_credentials(exc)
	logger.info("[push_relay] retrying %s with fresh relay credentials", getattr(fn, "__name__", fn))
	return fn(*args, **kwargs)
