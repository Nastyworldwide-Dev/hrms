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

#: Mirrored during the parallel run, in **dependency order** — the tuple order is
#: the sync order and is load-bearing, not incidental:
#:
#: 1. Company — `Employee.company` is a Link, so the target must already exist
#:    locally or every mirrored Employee lands with a dangling company.
#: 2. Employee — rows that link to it have something to point at.
#: 3. the rest, all of which link to Employee.
#:
#: `test_sync_runner` asserts Company precedes Employee, so a reorder is a
#: failing test rather than a silent breakage.
DEFAULT_SYNC_DOCTYPES = (
	"Company",
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Leave Ledger Entry",
)

#: What each doctype's rows point at. If a prerequisite fails, its dependents are
#: SKIPPED, never attempted.
#:
#: Learned the hard way on verifica-live 2026-08-10 (SYNC-00002): Company and
#: Employee both failed, the run carried on regardless, and 5,821 Attendance,
#: Employee Checkin and Leave Ledger Entry rows landed pointing at an employee
#: and a company that did not exist on the destination. Per-doctype failure
#: containment is right for INDEPENDENT doctypes and actively harmful for
#: dependent ones — ordering alone buys nothing without this.
SYNC_DEPENDENCIES = {
	"Employee": ("Company",),
	"Attendance": ("Employee",),
	"Employee Checkin": ("Employee",),
	"Leave Ledger Entry": ("Employee",),
}


def blocked_by(doctype: str, failed: set[str] | frozenset[str]) -> list[str]:
	"""Prerequisites of `doctype` that failed, transitively.

	Transitive matters: Company failing must block Attendance, which only names
	Employee as its prerequisite.
	"""
	blockers, seen, queue = [], set(), list(SYNC_DEPENDENCIES.get(doctype, ()))
	while queue:
		dep = queue.pop(0)
		if dep in seen:
			continue
		seen.add(dep)
		if dep in failed:
			blockers.append(dep)
		queue.extend(SYNC_DEPENDENCIES.get(dep, ()))
	return blockers


#: Mirrored **create-only**: absent locally -> create a shell; present locally ->
#: never touched, not even to refresh the identity fields.
#:
#: Company is here because a local Company owns finance configuration — chart of
#: accounts, cost centres, default accounts — that a mirror has no business
#: overwriting. Creating a shell Company is nevertheless safe on this hub: the
#: companies mirrored here are HR-only on this site (no ledger, no transactions);
#: the record exists so `Employee.company` resolves. Requiring HR to hand-create
#: them instead would be strictly worse — one typo and every mirrored Employee
#: links to a company that does not exist.
CREATE_ONLY_DOCTYPES = frozenset({"Company"})

#: Identity-only projection for create-only doctypes. Everything else on the
#: remote row — accounting defaults above all — is deliberately dropped.
MIRRORED_FIELDS = {
	"Company": ("company_name", "abbr", "default_currency", "country"),
}

#: Values the DESTINATION requires that the identity projection above omits.
#:
#: `Company.on_update` builds the default chart of accounts, and it is not
#: optional — `doc.insert()` runs post-save hooks, so there is no way to create a
#: Company shell without it. With `chart_of_accounts` unset, ERPNext indexes into
#: an empty template list and the insert dies with "list index out of range",
#: which is exactly how Company failed on verifica-live in SYNC-00002.
#:
#: Consequence worth knowing: each mirrored Company therefore brings a standard
#: account tree onto this hub. Harmless here — these companies are HR-only, with
#: no ledger activity — but it is not the weightless row the name "shell" implies.
_REQUIRED_DEFAULTS = {
	"Company": {"chart_of_accounts": "Standard"},
}

PAGE_SIZE = 500

#: Per-row failures recorded verbatim on the run before truncating. Schema drift
#: usually hits every row the same way, so a handful is diagnostic and 4,000
#: would just bury the run record.
MAX_ROW_ERRORS_REPORTED = 10

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


def _mirror_payload(row: dict, instance_name: str, doctype: str | None = None) -> dict:
	"""Remote row -> the flat fields written locally, provenance included.

	Doctypes listed in `MIRRORED_FIELDS` are narrowed to an allow-list; every
	other doctype copies whatever the remote returned minus `_UNMIRRORED_FIELDS`.
	"""
	allowed = MIRRORED_FIELDS.get(doctype)
	if allowed:
		payload = {k: row[k] for k in allowed if row.get(k) is not None}
	else:
		payload = {k: v for k, v in row.items() if k not in _UNMIRRORED_FIELDS and not isinstance(v, list)}
	payload.pop("name", None)

	for key, value in _REQUIRED_DEFAULTS.get(doctype, {}).items():
		payload.setdefault(key, value)

	payload[PROVENANCE_FIELD] = instance_name
	return payload


def _write_row(doctype: str, remote_name: str, payload: dict) -> str:
	"""Upsert one row keyed by the remote name.

	Returns "inserted", "updated", or "skipped" (create-only doctype that already
	exists locally).

	Updates go through `db.set_value` rather than `save()` on purpose: mirrored
	Attendance rows arrive submitted, and a mirror must not re-run the source
	instance's validation against this site's (possibly different) masters.
	"""
	if doctype in CREATE_ONLY_DOCTYPES and frappe.db.exists(doctype, remote_name):
		# Not even the identity fields: whatever is here locally wins, always.
		_log().debug("[sync] %s %s already exists locally, left untouched", doctype, remote_name)
		return "skipped"

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

	pulled = written = inserted = updated = skipped = errored = 0
	row_errors: list[str] = []
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
			try:
				outcome = _write_row(
					doctype, remote_name, _mirror_payload(row, client.instance_name, doctype)
				)
			except Exception as e:  # one bad row must not lose the other 5,000
				# Almost always schema drift: the source holds a value this site's
				# field definition cannot represent (a Select option added there
				# and not here). Surface it per row and keep going — silently
				# coercing the value would corrupt the mirror, and failing the
				# whole doctype loses good rows for one bad one.
				errored += 1
				if len(row_errors) < MAX_ROW_ERRORS_REPORTED:
					row_errors.append(f"{remote_name}: {e}")
				_log().error("[sync] %s %s could not be written: %s", doctype, remote_name, e)
				frappe.db.rollback()
				continue

			if outcome == "inserted":
				written += 1
				inserted += 1
			elif outcome == "updated":
				written += 1
				updated += 1
			else:  # create-only doctype, already present locally
				skipped += 1

		if len(page) < page_size:
			break
		start += page_size

	if not since:
		skipped += _count_local_orphans(doctype, client.instance_name, seen)

	_log().info(
		"[sync] %s from %s: pulled=%s inserted=%s updated=%s skipped=%s errored=%s (since=%s)",
		doctype,
		client.instance_name,
		pulled,
		inserted,
		updated,
		skipped,
		errored,
		since or "beginning",
	)

	# Every row failing is not "tolerated drift", it is a broken doctype — and a
	# dependent doctype must not then be told its prerequisite succeeded.
	if pulled and errored == pulled:
		raise RuntimeError(f"every row failed ({errored}/{pulled}): {'; '.join(row_errors)}")

	return {
		"doctype": doctype,
		"pulled": pulled,
		"written": written,
		"inserted": inserted,
		"updated": updated,
		"skipped": skipped,
		"errored": errored,
		"row_errors": row_errors,
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

	blocked = []
	try:
		for doctype in doctypes:
			# A dependent doctype is not attempted once its prerequisite failed:
			# its rows would reference employees or companies that do not exist
			# here. Skipping is the only safe outcome — see SYNC_DEPENDENCIES.
			blockers = blocked_by(doctype, set(failed))
			if blockers:
				blocked.append(doctype)
				errors.append(f"{doctype}: skipped — depends on failed {', '.join(blockers)}")
				_log().warning("[sync] %s skipped: prerequisite(s) %s failed", doctype, ", ".join(blockers))
				continue

			try:
				result = sync_doctype(client, doctype, since=since)
			except Exception as e:  # an independent doctype must not abort the run
				failed.append(doctype)
				errors.append(f"{doctype}: {e}")
				_log().error("[sync] %s failed: %s", doctype, e, exc_info=True)
				frappe.db.rollback()
				continue

			results.append(result)
			for key in totals:
				totals[key] += result[key]
			frappe.db.commit()

		unfinished = len(failed) + len(blocked)
		if not unfinished:
			status = "Completed"
		elif unfinished < len(doctypes):
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
			"blocked": blocked,
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
