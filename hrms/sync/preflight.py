"""One-pass source-permission probe for the multi-instance sync.

A sync run discovers a 403 — the source API user cannot read a doctype — one
doctype at a time, and a Partial run only names the ones it reached before it
stopped. That turned "grant the source user read access" into a repeated
run-read-error-fix loop (on verifica-live it was one doctype out of fourteen,
found the slow way).

This probes EVERY doctype the sync pulls in a single pass and returns the full
readable / blocked split, so an admin fixes all the source permissions at once.
Read-only: it lists at most one row per doctype and writes nothing.

    bench --site <hub> execute hrms.sync.preflight.check_source_permissions --args '["Handa"]'
"""

import logging

import frappe
from frappe import _

from hrms.sync.client import RemoteInstanceClient, RemoteInstanceError
from hrms.sync.runner import DEFAULT_SYNC_DOCTYPES

logger = logging.getLogger(__name__)

HR_MANAGER_ROLE = "HR Manager"


@frappe.whitelist()
def check_source_permissions(instance_name: str) -> dict:
	"""Probe read access on every synced doctype at the source `instance_name`.

	Returns {readable, blocked_403, other_errors, remedy}. A doctype in
	`blocked_403` means the source API user has no read permission on it THERE —
	the fix is on the source, not the hub. Gated to HR Manager / System Manager
	because it reveals the source's permission surface.
	"""
	frappe.only_for(("System Manager", HR_MANAGER_ROLE))

	client = RemoteInstanceClient(instance_name)
	readable: list[str] = []
	blocked: list[str] = []
	other: list[dict] = []

	for doctype in DEFAULT_SYNC_DOCTYPES:
		try:
			client.get_list(doctype, limit=1)
			readable.append(doctype)
		except RemoteInstanceError as exc:
			if getattr(exc, "status_code", None) == 403:
				blocked.append(doctype)
			else:
				other.append({"doctype": doctype, "error": str(exc)})
		except Exception as exc:  # nosemgrep: a probe must never abort the whole report
			other.append({"doctype": doctype, "error": str(exc)})

	logger.info(
		"[sync] preflight %s: %d readable, %d blocked (403), %d other",
		instance_name,
		len(readable),
		len(blocked),
		len(other),
	)
	return {
		"instance": instance_name,
		"readable": readable,
		"blocked_403": blocked,
		"other_errors": other,
		"remedy": (
			_(
				"On the source, grant the API user read permission on the blocked "
				"doctypes — the HR Manager role covers all of them — then re-run the sync."
			)
			if blocked
			else _("All synced doctypes are readable at the source.")
		),
	}
