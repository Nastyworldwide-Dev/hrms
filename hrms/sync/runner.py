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
#: `test_sync_runner` asserts the order, so a reorder is a failing test rather
#: than a silent breakage.
#: Company is deliberately NOT here. Creating one programmatically means running
#: ERPNext's company setup, and on this version that path is broken two different
#: ways: with `chart_of_accounts` unset it dies on "list index out of range", and
#: with it set it dies on `'Company' object has no attribute
#: 'update_default_account'`. Both were hit on verifica-live (SYNC-00002 and
#: SYNC-00003). A mirror has no business fighting the destination's setup wizard,
#: so companies are created by a human through the UI and the sync merely reports
#: which ones are missing — see `missing_parents` in each doctype's result.
#:
#: Masters the mirrored rows LINK to. Pulled first, create-only, never stamped.
#:
#: `_write_row` inserts with `ignore_links=True`, so before this existed a
#: mirrored employee whose designation was absent here landed pointing at nothing,
#: and a mirrored Leave Ledger Entry produced a balance for a leave type this site
#: could not name. Neither failed; the data was simply wrong in a way only a
#: person reading a report would catch.
#:
#: They are NOT stamped and NOT write-blocked, exactly like the Company shells:
#: on this hub HR owns them. `_write_row` leaves an existing local row untouched,
#: so a Leave Type whose flags HR has tuned here — and those flags drive balance
#: arithmetic — is never reverted to the source's copy.
#:
#: Two are deliberately absent, because they would CORRUPT rather than dangle:
#:
#: * `Department` is a NestedSet. Its `lft`/`rgt` describe a position in the
#:   SOURCE's tree; writing them here produces a tree that is wrong on both sides.
#: * `Holiday List` keeps its holidays in a child table, and `/api/resource` does
#:   not return child tables even with `fields=["*"]`. It would arrive as an empty
#:   calendar, and an empty calendar does not fail — it silently miscomputes
#:   attendance and leave.
#:
#: A dangling link is visible and recoverable. Either of those is neither.
MASTER_DOCTYPES = (
	"Leave Type",
	"Designation",
	"Branch",
	"Employee Grade",
)

#: The mirror proper: stamped with provenance, held read-only by
#: `hrms.sync.write_block` during the parallel run, and counted by
#: `hrms.sync.parity`. Order is load-bearing — Employee first so the three
#: doctypes that link to it have something to point at.
STAMPED_DOCTYPES = (
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Leave Ledger Entry",
)

#: What a run pulls, in order: every master before every row that links to one.
DEFAULT_SYNC_DOCTYPES = MASTER_DOCTYPES + STAMPED_DOCTYPES

#: Link fields whose target must already exist locally before a row may be
#: written: doctype -> {fieldname: parent doctype}.
#:
#: Checked PER ROW, which is the lesson of SYNC-00003. Doctype-level gating was
#: not enough: Company "completed" having written nothing (its rows errored
#: individually, so it never raised), Employee proceeded, and 266 employees
#: landed pointing at companies that did not exist. A row whose parent is absent
#: is skipped and counted — never written, never guessed at.
ROW_DEPENDENCIES = {
	"Employee": {"company": "Company"},
	"Attendance": {"employee": "Employee"},
	"Employee Checkin": {"employee": "Employee"},
	"Leave Ledger Entry": {"employee": "Employee"},
}


def missing_parents(doctype: str, row: dict) -> list[str]:
	"""Parents this row points at that do not exist here yet.

	Returned as "Doctype: name" so the caller can tell an operator exactly what to
	create, which is the whole point — the alternative is a foreign key error
	buried in a traceback, or worse, an orphan.
	"""
	missing = []
	for fieldname, parent_doctype in ROW_DEPENDENCIES.get(doctype, {}).items():
		value = row.get(fieldname)
		if value and not frappe.db.exists(parent_doctype, value):
			missing.append(f"{parent_doctype}: {value}")
	return missing


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
	# Leave Type as well as Employee: a ledger row whose leave type never landed
	# still writes, and then reports a balance against a type this site cannot
	# name. Better to skip the pass and say so than to publish a nameless balance.
	"Leave Ledger Entry": ("Employee", "Leave Type"),
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
CREATE_ONLY_DOCTYPES = frozenset({"Company", *MASTER_DOCTYPES})

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

#: Sort key for the paged pull, and it must be UNIQUE.
#:
#: Pagination is offset-based (`limit_start`), so the remote has to return a
#: stable total order or an offset means nothing. `modified asc` alone does not
#: give one: a bulk update on the source stamps thousands of employees with the
#: same `modified` to the second, and the remote is entitled to return those ties
#: in a different order for page 1 than for page 2. A row sitting on a page
#: boundary is then either returned twice — harmless, the upsert is idempotent —
#: or never returned at all, which is an employee that silently does not exist
#: here. `name` is the primary key, so appending it makes the order total.
PAGE_ORDER = "modified asc, name asc"

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

#: Fields this hub owns even on a mirrored row: the mirror neither writes nor
#: overwrites them.
#:
#: `Employee.user_id` is the login mapping, and it belongs to whichever site the
#: person signs in to — not to the source instance. Mirroring it was actively
#: harmful in three ways:
#:
#:   * `User` is not a synced doctype, so a mirrored `user_id` regularly pointed
#:     at a User that does not exist here (inserts pass `ignore_links=True`, and
#:     updates go through `db.set_value`, so nothing objected);
#:   * a source ERP that manages staff without portal users mirrors `user_id`
#:     empty, and the person can then never resolve on this hub;
#:   * worst, it made the fix *look* like it worked. Setting `user_id` here by
#:     hand survived exactly until the next incremental pull, which quietly put
#:     it back. That is why the login failure kept coming back for one user at a
#:     time and why a per-user database fix was never the answer.
#:
#: `hrms.utils.identity` now establishes the link on first login, from
#: `company_email` — which IS mirrored, so the ERP stays authoritative for the
#: identity *data* while the hub owns the *mapping*.
LOCALLY_OWNED_FIELDS = {
	"Employee": ("user_id",),
}


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
	# STAMPED_DOCTYPES, not DEFAULT_SYNC_DOCTYPES: the masters are HR-owned here
	# and must stay unstamped, or the write-block would lock HR out of their own
	# Leave Types and `parity` would count masters as mirrored rows.
	return {doctype: [dict(definition)] for doctype in STAMPED_DOCTYPES}


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


def _mirror_payload(row: dict, instance_name: str, doctype: str) -> dict:
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

	for field in LOCALLY_OWNED_FIELDS.get(doctype, ()):
		payload.pop(field, None)

	for key, value in _REQUIRED_DEFAULTS.get(doctype, {}).items():
		payload.setdefault(key, value)

	# Masters and Company shells stay unstamped — they are HR-owned on this hub,
	# and a stamp would hand them to the write-block and to parity's row counts.
	if doctype in STAMPED_DOCTYPES:
		payload[PROVENANCE_FIELD] = instance_name
	return payload


def _reconcile_user_status(employee: str) -> None:
	"""Restore the `User.enabled` <-> `Employee.status` invariant that `db.set_value` skips.

	ERPNext enforces it in `Employee.on_update` -> `update_user_status()`. The
	mirror updates existing rows with `frappe.db.set_value`, which fires no doc
	events, so the invariant silently rotted in both directions:

	  * an employee set Left or Inactive on the source instance kept an ENABLED
	    User here — they authenticated normally and then dead-ended on
	    `/hrms/invalid-employee`, which reads as a broken app rather than as the
	    correct refusal it actually is;
	  * a re-activated employee kept a DISABLED User and could not authenticate
	    at all, which reads the same way and is a genuine lockout.

	Idempotent, and silent when there is nothing to change. Never raises: a
	mirror run must not abort because one linked User could not be saved.
	"""
	user_id, status = frappe.db.get_value("Employee", employee, ["user_id", "status"]) or (None, None)
	if not user_id or not frappe.db.exists("User", user_id):
		return

	should_be_enabled = 1 if status == "Active" else 0
	if frappe.db.get_value("User", user_id, "enabled") == should_be_enabled:
		return

	try:
		user = frappe.get_doc("User", user_id)
		user.enabled = should_be_enabled
		user.flags.ignore_permissions = True
		user.save(ignore_permissions=True)
	except Exception as e:
		_log().error("[sync] could not reconcile User %s with employee %s: %s", user_id, employee, e)
		return

	_log().warning(
		"[sync] User %s %s to match employee %s status %s",
		user_id,
		"enabled" if should_be_enabled else "disabled",
		employee,
		status,
	)


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
		if doctype == "Employee":
			_reconcile_user_status(remote_name)
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


#: Doctypes carrying a `company` Link the SOURCE can filter on directly.
#: `Employee Checkin` is absent because it has no such field — see `scope_filter`.
COMPANY_SCOPED_DOCTYPES = frozenset({"Employee", "Attendance", "Leave Ledger Entry"})

#: An allow-list that filtered down to nothing must still be an allow-list. Sent
#: as an empty `IN ()` it is a SQL error on the remote; dropped entirely it
#: becomes "no filter", which is how a scoped run quietly pulls the whole source.
_MATCHES_NOTHING = "__hrms_sync_no_such_row__"


def instance_companies(instance_name: str) -> list[str]:
	"""The companies this instance is registered to serve, in a stable order.

	Empty means unmapped, and unmapped means "pull everything" — the behaviour
	every existing instance already has. Narrowing silently to nothing because a
	table has not been filled in would be a worse failure than the one this fixes.
	"""
	return frappe.get_all(
		"HRMS ERP Instance Company",
		filters={"parent": instance_name},
		pluck="company",
		order_by="company asc",
	)


def scope_filter(doctype: str, companies: list[str], instance_name: str) -> dict | None:
	"""Restrict the remote read to the companies this instance actually serves.

	The `Companies Served` table was already the answer to "whose employees belong
	on this hub" — it drives the staff ERP redirect and every HR (Instance) user's
	fence — but `sync_instance` never passed it down, so a hub registered for 7 of
	the source's 10 companies mirrored all 10. Nothing was even reported: every
	company existed locally, so no row was skipped for a missing parent.

	`Employee Checkin` carries no `company` field, so it is fenced by the employees
	the Employee pass just mirrored instead. That is why this is evaluated per
	doctype inside the loop rather than computed up front, and why Employee must
	precede Employee Checkin in `DEFAULT_SYNC_DOCTYPES` — it does.

	Masters have no company at all and are never filtered: sending them a `company`
	filter would make the remote reject the read.
	"""
	if not companies:
		return None

	if doctype in COMPANY_SCOPED_DOCTYPES:
		return {"company": ("in", list(companies))}

	if doctype == "Employee Checkin":
		employees = frappe.get_all("Employee", filters={PROVENANCE_FIELD: instance_name}, pluck="name")
		# ponytail: inlines the employee list into the request. Fine at the group's
		# ~10^2 staff; at 10^4 this wants a saved filter on the source instead.
		return {"employee": ("in", employees or [_MATCHES_NOTHING])}

	return None


def sync_doctype(client, doctype: str, since=None, page_size: int = PAGE_SIZE, filters=None) -> dict:
	"""Mirror one doctype from `client` into this site.

	Pulls in pages ordered by `modified`, upserting on the remote `name`.
	Returns counts; raises only if the remote or the database does — callers
	decide whether that degrades the run to Partial.
	"""
	remote_filters = dict(filters or {})
	if since:
		remote_filters["modified"] = (">", since)

	pulled = written = inserted = updated = skipped = errored = orphaned = 0
	unmet_parents: set[str] = set()
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
			order_by=PAGE_ORDER,
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

			# Referential integrity, per row. Writing a row whose parent is absent
			# is what produced 5,821 orphan attendance records and then 266 orphan
			# employees; skipping is the only honest outcome.
			absent = missing_parents(doctype, row)
			if absent:
				orphaned += 1
				for parent in absent:
					unmet_parents.add(parent)
				_log().warning("[sync] %s %s skipped: missing %s", doctype, remote_name, ", ".join(absent))
				continue

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

	# A doctype that pulled rows and wrote NONE has not succeeded, whatever the
	# mix of errors and skips. SYNC-00003 slipped through the old
	# `errored == pulled` check because one of ten rows was skipped rather than
	# errored, so Company reported success having written nothing and Employee
	# ran on that basis.
	if pulled and not written and (errored or orphaned):
		detail = "; ".join(row_errors) or f"{orphaned} row(s) missing parents: {sorted(unmet_parents)}"
		raise RuntimeError(f"no rows written out of {pulled}: {detail}")

	return {
		"doctype": doctype,
		"pulled": pulled,
		"written": written,
		"inserted": inserted,
		"updated": updated,
		"skipped": skipped,
		"errored": errored,
		"orphaned": orphaned,
		"missing_parents": sorted(unmet_parents),
		"row_errors": row_errors,
	}


def _close_stale_runs(instance_name: str) -> int:
	"""Mark orphaned `Running` rows for this instance as Failed, and say so.

	`_finish_run` is called from a `finally`, so the only way a run stays `Running`
	is a process that was KILLED rather than allowed to raise: the gateway timing
	out the old synchronous endpoint, an rq job timeout, or a redeploy mid-run.
	Left alone that row is indistinguishable from a live run for ever, and the
	operator has no way to tell a stuck sync from a working one.

	Safe to do at the start of the next run because `enqueue_sync` deduplicates per
	instance — at most one run per source is ever genuinely in flight, and this
	only ever executes at the start of that one. Scoped to the instance so a
	concurrent pull of a DIFFERENT source is never touched.
	"""
	stale = frappe.get_all(
		"HRMS Sync Run",
		filters={"source_instance": instance_name, "status": "Running"},
		pluck="name",
	)
	for name in stale:
		frappe.db.set_value(
			"HRMS Sync Run",
			name,
			{
				"status": "Failed",
				"error_log": "Run did not finish — the worker was killed before it could "
				"report. Counts are whatever had been committed at that point; the "
				"watermark did not advance, so nothing was lost.",
			},
		)
		_log().warning("[sync] closed out stale run %s for %s", name, instance_name)
	return len(stale)


def _start_run(instance_name: str, doctypes) -> str:
	_close_stale_runs(instance_name)
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
				"rows_orphaned": totals.get("orphaned", 0),
				"rows_errored": totals.get("errored", 0),
				"error_log": "\n".join(errors)[:100000] if errors else None,
			},
		)
		frappe.db.commit()
		_log().info(
			"[sync] run %s finished: status=%s pulled=%s written=%s skipped=%s orphaned=%s errored=%s",
			run_name,
			status,
			totals.get("pulled", 0),
			totals.get("written", 0),
			totals.get("skipped", 0),
			totals.get("orphaned", 0),
			totals.get("errored", 0),
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

	companies = instance_companies(instance_name)
	if companies:
		_log().info("[sync] %s scoped to %s: %s", instance_name, len(companies), ", ".join(companies))
	else:
		_log().warning(
			"[sync] %s serves no registered companies — pulling every company on the source. "
			"Fill in Companies Served to scope it.",
			instance_name,
		)

	if since is None and incremental:
		since = get_watermark(instance_name)

	run_name = _start_run(instance_name, doctypes)
	totals = {"pulled": 0, "written": 0, "skipped": 0, "errored": 0, "orphaned": 0}
	results, errors, failed = [], [], []
	status = "Failed"

	blocked = []
	# The write-block (hrms/sync/write_block.py) exempts this flag: the sync is
	# the one legitimate writer of mirrored rows during the parallel run.
	frappe.flags.in_shadow_sync = True
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
				# Evaluated here, not up front: Employee Checkin's scope is the
				# employees the Employee pass has just written.
				result = sync_doctype(
					client, doctype, since=since, filters=scope_filter(doctype, companies, instance_name)
				)
			except Exception as e:  # an independent doctype must not abort the run
				failed.append(doctype)
				errors.append(f"{doctype}: {e}")
				_log().error("[sync] %s failed: %s", doctype, e, exc_info=True)
				frappe.db.rollback()
				continue

			results.append(result)
			for key in totals:
				totals[key] += result[key]
			# Named, not merely counted: an operator who reads "1 row orphaned"
			# still does not know WHICH company to create. This line is the entire
			# repair instruction, and without it the run record said Completed and
			# nothing else.
			if result["missing_parents"]:
				errors.append(
					f"{doctype}: {result['orphaned']} row(s) skipped, missing "
					f"{', '.join(result['missing_parents'])}"
				)
			for row_error in result["row_errors"]:
				errors.append(f"{doctype}: {row_error}")
			frappe.db.commit()

		# Rows count, not only doctypes. `get_watermark` accepts Completed runs
		# alone precisely so unfinished work is re-pulled next time — but
		# "unfinished" used to mean only a doctype that raised. A doctype that
		# pulled 500 employees, wrote 499 and skipped one for a missing Company
		# still reported Completed, so the watermark moved past that employee and
		# no later incremental run ever asked for them again. They existed on the
		# source and simply were not here, permanently, until somebody happened to
		# run a full pull by hand.
		#
		# `skipped` is deliberately NOT counted: it means a create-only doctype
		# that already exists locally, or a local row the remote no longer
		# returns. Neither is outstanding work.
		unwritten = totals["orphaned"] + totals["errored"]
		if unwritten:
			errors.append(
				f"{unwritten} row(s) not written (orphaned={totals['orphaned']} "
				f"errored={totals['errored']}) — watermark held so they are re-pulled"
			)
			_log().warning(
				"[sync] run %s left %s row(s) unwritten; holding the watermark", run_name, unwritten
			)

		unfinished = len(failed) + len(blocked)
		if not unfinished and not unwritten:
			status = "Completed"
		elif unfinished >= len(doctypes):
			status = "Failed"
		else:
			status = "Partial"
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
		frappe.flags.in_shadow_sync = False
		_finish_run(run_name, status, totals, errors)


def parse_doctypes(doctypes) -> tuple[str, ...] | None:
	"""Accept what a human would actually type.

	`Company,Employee` is the obvious thing to put in a URL, and requiring a JSON
	array meant the browser ate the quotes and the caller got
	`JSONDecodeError: Expecting value` — a parser complaint that says nothing
	about what to do instead. Both forms are accepted now; None means "the
	defaults".
	"""
	if doctypes is None or doctypes == "":
		return None
	if not isinstance(doctypes, str):
		return tuple(doctypes)

	text = doctypes.strip()
	if text.startswith("["):
		try:
			return tuple(json.loads(text))
		except json.JSONDecodeError:
			# Very likely quotes stripped by a URL bar: [Company,Employee]
			text = text.strip("[]")

	names = tuple(part.strip().strip("\"'") for part in text.split(",") if part.strip())
	if not names:
		raise ValueError(f"could not read a doctype list from {doctypes!r}")
	return names


#: A full pull is minutes, not seconds. `default` tops out at 300s and the HTTP
#: gateway gives up long before that — verifica-live, 2026-08-17: "Request Timed
#: Out" on the first full pull, worker killed mid-run. `long` is 1500s.
SYNC_QUEUE = "long"
SYNC_JOB_TIMEOUT = 1500


def sync_job_id(instance_name: str) -> str:
	"""One in-flight run per source instance.

	A second concurrent pull cannot corrupt anything — the upsert keys on the
	remote name — but it doubles the read load on what is live production for ten
	companies, and leaves two run records for one operator intent.
	"""
	return f"hrms-sync-{instance_name}"


@frappe.whitelist(methods=["POST"])
def enqueue_sync(instance_name: str, doctypes: str | None = None, incremental: int = 1) -> dict:
	"""Queue a run and return immediately. The button's entry point.

	`run_sync` stays callable directly for bench and for tests; what it must not do
	any more is run inside a web request, where the gateway kills the worker
	partway and `sync_instance`'s `finally` never gets to record what happened.

	Progress needs no polling from here: `_start_run` writes the `HRMS Sync Run`
	row before the first remote read, and the Desk list view updates itself.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	if not instance_name:
		frappe.throw(_("instance_name is required"))

	job = frappe.enqueue(
		"hrms.sync.runner.run_sync",
		queue=SYNC_QUEUE,
		timeout=SYNC_JOB_TIMEOUT,
		job_id=sync_job_id(instance_name),
		deduplicate=True,
		instance_name=instance_name,
		doctypes=doctypes,
		incremental=incremental,
	)

	if job is None:
		_log().info("[sync] a run for %s is already in flight; not queueing another", instance_name)
		return {"queued": False, "reason": "already_running", "instance": instance_name}

	_log().info("[sync] queued a background run for %s", instance_name)
	return {"queued": True, "instance": instance_name}


@frappe.whitelist(methods=["POST"])
def run_sync(instance_name: str, doctypes: str | None = None, incremental: int = 1) -> dict:
	"""Desk/bench entry point. Kept thin: it only builds the client.

	POST-only for the same reason `company_shells.create_company_shells` is: this
	writes thousands of rows, and a state-mutating endpoint reachable by GET is a
	CSRF vector — a logged-in HR Manager loading an image tag would start a pull.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	from hrms.sync.client import RemoteInstanceClient

	return sync_instance(
		RemoteInstanceClient(instance_name),
		doctypes=parse_doctypes(doctypes),
		incremental=bool(int(incremental)),
	)
