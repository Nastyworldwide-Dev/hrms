"""One-way mirroring of HR data from another instance into this one.

Group HR consolidates onto this site. During the parallel run, HR data still
originates on the old instance and is mirrored here so that at cutover it is
simply already live. Mirrored rows therefore land in the **real** doctypes
(Employee, Attendance, ...) — not a staging table — and carry a provenance
stamp, `synced_from_instance`, that says where they came from. That stamp is
what makes them recognisable as read-only during the parallel run, and what
`hrms.sync.parity` counts.

Three properties are load-bearing and each has a test:

* **Idempotent.** The remote `name` is the key. A re-run updates in place; it
  can never produce a second copy of a row.
* **Incremental.** A `modified >` watermark, taken from the last *Completed*
  run, keeps repeat runs cheap. Only Completed advances it — a Partial run
  left some doctype behind, and moving the watermark past it would lose those
  rows forever.
* **Never deletes.** A local row with no remote counterpart is left alone and
  counted as skipped. Deletion is out of scope; a divergence is for a human to
  investigate, not for a cron job to resolve destructively.

Every run writes an `HRMS Sync Run` record, at start and again at the end,
including when it blows up.
"""

import json
import logging

import frappe
from frappe import _
from frappe.utils import now_datetime

_LOGGER = None


def _log():
	"""`frappe.logger` is site-bound — it opens the site's log file — so it is
	resolved lazily. Importing this module must not require a site, or the
	bench-free tests (and `bench --help`) break."""
	global _LOGGER
	if _LOGGER is None:
		try:
			_LOGGER = frappe.logger("hrms")
		except Exception:  # no site context (tests, CLI)
			_LOGGER = logging.getLogger("hrms")
	return _LOGGER


#: Custom field stamped on every mirrored row. Read by `hrms.sync.parity`.
PROVENANCE_FIELD = "synced_from_instance"

#: Mirrored during the parallel run, in dependency order — Employee first, so
#: rows that link to it have something to point at.
DEFAULT_SYNC_DOCTYPES = (
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Leave Ledger Entry",
)

PAGE_SIZE = 500

#: Never copied from the remote row: framework bookkeeping that must be owned
#: by this site, or that Frappe recomputes on write.
_UNMIRRORED_FIELDS = frozenset(
	{
		"doctype",
		"modified",
		"modified_by",
		"owner",
		"creation",
		"idx",
		"_user_tags",
		"_comments",
		"_assign",
		"_liked_by",
		"_seen",
	}
)


def get_provenance_custom_fields() -> dict:
	"""Custom field definitions merged into `hrms.setup.get_custom_fields()`.

	They must come from the install path, not only a patch: `install_app`
	records every patch as already applied on a fresh site, so a patch-only
	field would never exist on a new install.
	"""
	definition = {
		"fieldname": PROVENANCE_FIELD,
		"fieldtype": "Data",
		"label": _("Synced From Instance"),
		"description": _("Mirrored from this ERP instance. Read-only during the parallel run."),
		"read_only": 1,
		"no_copy": 1,
		"allow_on_submit": 1,
		"print_hide": 1,
		"search_index": 1,
	}
	return {doctype: [dict(definition)] for doctype in DEFAULT_SYNC_DOCTYPES}


def get_watermark(instance_name: str) -> str | None:
	"""Start time of the last fully Completed run for this instance.

	Its *start* time, not its finish time: a row modified remotely while the
	run was in flight may or may not have been seen, and re-pulling it is free
	where missing it is not.
	"""
	last = frappe.get_all(
		"HRMS Sync Run",
		filters={"source_instance": instance_name, "status": "Completed"},
		fields=["started_at"],
		order_by="started_at desc",
		limit=1,
	)
	watermark = last[0]["started_at"] if last else None
	_log().info("[sync] watermark for %s: %s", instance_name, watermark or "none (full pull)")
	return watermark


def _mirror_payload(row: dict, instance_name: str) -> dict:
	"""Remote row -> the flat fields written locally, provenance included."""
	payload = {k: v for k, v in row.items() if k not in _UNMIRRORED_FIELDS and not isinstance(v, list)}
	payload.pop("name", None)
	payload[PROVENANCE_FIELD] = instance_name
	return payload


def _write_row(doctype: str, remote_name: str, payload: dict) -> str:
	"""Upsert one row keyed by the remote name. Returns "inserted" or "updated".

	Updates go through `db.set_value` rather than `save()` on purpose: mirrored
	Attendance rows arrive submitted, and a mirror must not re-run the source
	instance's validation against this site's (possibly different) masters.
	"""
	if frappe.db.exists(doctype, remote_name):
		frappe.db.set_value(doctype, remote_name, payload, update_modified=False)
		return "updated"

	doc = frappe.get_doc({"doctype": doctype, **payload})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.insert(set_name=remote_name, ignore_if_duplicate=True)
	return "inserted"


def _count_local_orphans(doctype: str, instance_name: str, seen: set) -> int:
	"""Rows mirrored here earlier that the remote no longer returned.

	Counted, logged, and then deliberately left alone — see module docstring.
	Only meaningful on a full pull; an incremental pull legitimately returns
	only what changed.
	"""
	local = frappe.get_all(
		doctype,
		filters={PROVENANCE_FIELD: instance_name},
		pluck="name",
	)
	orphans = [name for name in local if name not in seen]
	if orphans:
		_log().warning(
			"[sync] %s: %s local row(s) absent remotely, left untouched (e.g. %s)",
			doctype,
			len(orphans),
			orphans[0],
		)
	return len(orphans)


def sync_doctype(client, doctype: str, since=None, page_size: int = PAGE_SIZE, filters=None) -> dict:
	"""Mirror one doctype from `client` into this site.

	Pulls in pages ordered by `modified`, upserting on the remote `name`.
	Returns counts; raises only if the remote or the database does — callers
	decide whether that degrades the run to Partial.
	"""
	remote_filters = dict(filters or {})
	if since:
		remote_filters["modified"] = (">", since)

	pulled = written = inserted = updated = skipped = 0
	seen = set()
	start = 0

	while True:
		page = client.get_list(
			doctype,
			filters=remote_filters or None,
			fields=["*"],
			limit=page_size,
			start=start,
			order_by="modified asc",
		)
		if not page:
			break

		for row in page:
			pulled += 1
			remote_name = row.get("name")
			if not remote_name:
				skipped += 1
				_log().warning("[sync] %s: remote row without a name, skipped", doctype)
				continue

			seen.add(remote_name)
			outcome = _write_row(doctype, remote_name, _mirror_payload(row, client.instance_name))
			written += 1
			if outcome == "inserted":
				inserted += 1
			else:
				updated += 1

		if len(page) < page_size:
			break
		start += page_size

	if not since:
		skipped += _count_local_orphans(doctype, client.instance_name, seen)

	_log().info(
		"[sync] %s from %s: pulled=%s inserted=%s updated=%s skipped=%s (since=%s)",
		doctype,
		client.instance_name,
		pulled,
		inserted,
		updated,
		skipped,
		since or "beginning",
	)
	return {
		"doctype": doctype,
		"pulled": pulled,
		"written": written,
		"inserted": inserted,
		"updated": updated,
		"skipped": skipped,
	}


def _start_run(instance_name: str, doctypes) -> str:
	run = frappe.get_doc(
		{
			"doctype": "HRMS Sync Run",
			"source_instance": instance_name,
			"status": "Running",
			"started_at": now_datetime(),
			"doctypes_synced": ", ".join(doctypes),
		}
	)
	run.flags.ignore_permissions = True
	run.insert(ignore_permissions=True)
	_log().info("[sync] run %s started for %s (%s)", run.name, instance_name, ", ".join(doctypes))
	return run.name


def _finish_run(run_name: str, status: str, totals: dict, errors: list) -> None:
	"""Close the audit record. Called from a finally block, so it must not
	raise — a failure to record the outcome would mask the real failure."""
	try:
		frappe.db.set_value(
			"HRMS Sync Run",
			run_name,
			{
				"status": status,
				"finished_at": now_datetime(),
				"rows_pulled": totals.get("pulled", 0),
				"rows_written": totals.get("written", 0),
				"rows_skipped": totals.get("skipped", 0),
				"error_log": "\n".join(errors)[:100000] if errors else None,
			},
		)
		frappe.db.commit()
		_log().info(
			"[sync] run %s finished: status=%s pulled=%s written=%s skipped=%s",
			run_name,
			status,
			totals.get("pulled", 0),
			totals.get("written", 0),
			totals.get("skipped", 0),
		)
	except Exception:
		_log().error("[sync] run %s: could not record outcome", run_name, exc_info=True)


def sync_instance(client, doctypes=None, since=None, incremental: bool = True) -> dict:
	"""Mirror every doctype from one instance, recording an `HRMS Sync Run`.

	One doctype failing degrades the run to Partial; the rest still sync. Any
	other failure marks the run Failed and re-raises, because that is a bug,
	not a data condition.
	"""
	doctypes = list(doctypes or DEFAULT_SYNC_DOCTYPES)
	instance_name = client.instance_name

	if since is None and incremental:
		since = get_watermark(instance_name)

	run_name = _start_run(instance_name, doctypes)
	totals = {"pulled": 0, "written": 0, "skipped": 0}
	results, errors, failed = [], [], []
	status = "Failed"

	try:
		for doctype in doctypes:
			try:
				result = sync_doctype(client, doctype, since=since)
			except Exception as e:  # one doctype must not abort the run
				failed.append(doctype)
				errors.append(f"{doctype}: {e}")
				_log().error("[sync] %s failed: %s", doctype, e, exc_info=True)
				frappe.db.rollback()
				continue

			results.append(result)
			for key in totals:
				totals[key] += result[key]
			frappe.db.commit()

		if not failed:
			status = "Completed"
		elif len(failed) < len(doctypes):
			status = "Partial"
		else:
			status = "Failed"
		return {
			"run": run_name,
			"instance": instance_name,
			"status": status,
			"since": since,
			"results": results,
			"failed": failed,
			**totals,
		}
	except Exception as e:
		status = "Failed"
		errors.append(f"run aborted: {e}")
		_log().error("[sync] run %s aborted", run_name, exc_info=True)
		raise
	finally:
		_finish_run(run_name, status, totals, errors)


@frappe.whitelist()
def run_sync(instance_name: str, doctypes: str | None = None, incremental: int = 1) -> dict:
	"""Desk/bench entry point. Kept thin: it only builds the client."""
	frappe.only_for(("System Manager", "HR Manager"))
	from hrms.sync.client import RemoteInstanceClient

	selected = json.loads(doctypes) if isinstance(doctypes, str) and doctypes else doctypes
	return sync_instance(
		RemoteInstanceClient(instance_name),
		doctypes=selected,
		incremental=bool(int(incremental)),
	)
