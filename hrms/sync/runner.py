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
#: `Holiday List`, `Shift Type` and `Shift Schedule` carry child tables, so they
#: are re-read one at a time through `client.get_doc` — see `CHILD_TABLE_DOCTYPES`.
#: A calendar mirrored without its `holidays` does not fail; it silently counts
#: every weekend and public holiday as a working day.
#:
#: `Department` remains deliberately absent, because it would CORRUPT rather than
#: dangle: it is a NestedSet, and its `lft`/`rgt` describe a position in the
#: SOURCE's tree. Writing them here produces a tree that is wrong on both sides.
#: A dangling link is visible and recoverable; that is not.
MASTER_DOCTYPES = (
	"Leave Type",
	"Designation",
	"Branch",
	"Employee Grade",
	"Holiday List",
	# Before Shift Type, which links to it, and before every stamped doctype that
	# does: Attendance, Employee Checkin and Shift Assignment all carry
	# `overtime_type`. Without it the overtime rates resolve to nothing and the
	# Replacement Leave bank the PWA shows has no rule behind it.
	"Overtime Type",
	# Employees arrive with `shift_location` set — "where this employee physically
	# clocks in", per the field's own description, and the carrier of the
	# `shift_rules` that drive automatic Shift Assignment. Mirrored without it,
	# those employees pointed at a record this site did not have and the rules had
	# nothing to run.
	"Shift Location",
	"Shift Type",
	"Shift Schedule",
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
	"Shift Schedule Assignment",
	"Shift Assignment",
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
	"Shift Schedule Assignment": {"employee": "Employee", "shift_schedule": "Shift Schedule"},
	"Shift Assignment": {"employee": "Employee", "shift_type": "Shift Type"},
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
	"Shift Schedule Assignment": ("Employee", "Shift Schedule"),
	"Shift Assignment": ("Employee", "Shift Type"),
}


def is_absent_on_source(error) -> bool:
	"""True when the remote answered "no such doctype" rather than failing.

	A source running an older HRMS simply does not have every doctype this hub
	mirrors — `Holiday List Assignment` on verifica-live, 2026-08-17. That is a
	version gap, not outstanding work, and treating it as a failure is permanent:
	the run degrades to Partial for ever, the watermark never advances because
	`Completed` requires nothing outstanding, and the cutover gate can never
	authorise however healthy the mirror is.

	404 only. A 500, a timeout or a dropped connection IS outstanding work and must
	still hold the watermark.
	"""
	return getattr(error, "status_code", None) == 404


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

#: Doctypes whose child tables are load-bearing, so each row is re-read through
#: the single-document endpoint before it is written.
#:
#: `client.get_list` cannot see a child table at all — `/api/resource/<doctype>`
#: is `frappe.client.get_list`, which selects parent columns only. Everything
#: here is low-cardinality policy (a handful of calendars and shift patterns per
#: company), so one extra request per row is the cheap half of the trade against
#: mirroring a Holiday List with no holidays in it.
CHILD_TABLE_DOCTYPES = frozenset(
	{"Holiday List", "Shift Type", "Shift Schedule", "Shift Location", "Overtime Type"}
)

#: Framework bookkeeping stripped from every CHILD row, on top of the parent set.
#:
#: A child carrying the source's `name`/`parent` would be inserted under another
#: instance's identifiers and belong to nothing here. `idx` goes with them
#: (it is already in `_UNMIRRORED_FIELDS`): Frappe numbers children from the list
#: order on insert, and the source's numbering would only stay authoritative
#: until a row is dropped. Order therefore comes from the list, and only from it.
_UNMIRRORED_CHILD_FIELDS = _UNMIRRORED_FIELDS | {
	"name",
	"parent",
	"parenttype",
	"parentfield",
	"docstatus",
}


def _mirror_children(rows: list) -> list:
	"""Child rows, scrubbed of the source's bookkeeping, in the source's order."""
	return [
		{key: value for key, value in row.items() if key not in _UNMIRRORED_CHILD_FIELDS}
		for row in rows
		if isinstance(row, dict)
	]


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
		# Child tables are dropped except where they ARE the record: a Holiday List
		# without its `holidays` is an empty calendar, and an empty calendar does
		# not fail — it counts every weekend as a working day.
		keep_children = doctype in CHILD_TABLE_DOCTYPES
		payload = {}
		for key, value in row.items():
			if key in _UNMIRRORED_FIELDS:
				continue
			if isinstance(value, list):
				if keep_children and value:
					payload[key] = _mirror_children(value)
				continue
			payload[key] = value
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


def _local_schema(doctype: str) -> tuple[set, dict]:
	"""(columns this site stores, {select fieldname: values it can represent}).

	Indirected through a module function so the bench-free tests can drive it and
	so a meta failure is recoverable rather than fatal.
	"""
	meta = frappe.get_meta(doctype)
	# Child tables are storable but are NOT parent columns — their rows live in
	# their own table, so `get_valid_columns` omits them. Leaving them out here
	# stripped `holidays`, `breaks`, `overtime_rates` and `repeat_on_days` from
	# every master, which is the exact silent-wrong-answer `CHILD_TABLE_DOCTYPES`
	# was built to prevent: a calendar with no holidays does not fail, it counts
	# every weekend as a working day.
	columns = set(meta.get_valid_columns()) | {field.fieldname for field in meta.get_table_fields()}

	selects = {}
	for field in meta.fields:
		if field.fieldtype != "Select":
			continue
		options = {option.strip() for option in (field.options or "").split("\n")}
		# A Select with no options constrains NOTHING. Frappe skips its own
		# validation for exactly this case — `base_document._validate_selects`
		# reads `if ... or not df.options: continue` — so the site will happily
		# store any value in such a field.
		#
		# Reading it as a constraint made the option set `{""}`: only the empty
		# string storable, every real value dropped. That is this mirror being
		# STRICTER than the site it writes to, which is never right and is silent
		# by design — the value goes missing and the row still saves.
		#
		# It cost every Shift Location its timezone. `Shift Location.timezone` is
		# a Select declaring no options, and Asia/Dubai, Asia/Kuala_Lumpur and
		# CST6CDT were all discarded from a field this site can store perfectly
		# well, on a hub whose whole job is knowing which wall clock a punch was
		# measured against.
		if options - {""}:
			selects[field.fieldname] = options

	return columns, selects


def _narrow_to_local_schema(doctype: str, payload: dict, stamped=None, columns=None) -> tuple[dict, dict]:
	"""Reduce a remote payload to what THIS site can actually store.

	The source's Employee is not this site's Employee. Two shapes of drift, one
	root, and both were costing whole records:

	* a column that exists only over there — `custom_reports_to_name` on
	  nasty-sg-dev. An INSERT survives it, because Frappe drops unknown keys in
	  `get_valid_dict`; an UPDATE goes through `db.set_value`, which builds a SET
	  clause from whatever it is handed, so 100+ existing employees failed on
	  every run with "Unknown column ... in 'SET'";
	* a Select the source has widened — E3 cost 173 people, B2 was next. Select
	  validation rejects the whole document, not the field.

	Chasing those one value and one field at a time never ends. An employee
	arriving without one unrepresentable field beats an employee not arriving, so
	the field is dropped and NAMED — silently discarding it would be the same
	class of hole in a different place.

	Fails open: if the schema cannot be read the payload passes through unchanged,
	because writing nothing is worse than writing what we were given.
	"""
	selects = {}
	if columns is None:
		try:
			columns, selects = _local_schema(doctype)
		except Exception as e:
			_log().warning("[sync] could not read local schema for %s: %s", doctype, e)
			return payload, {}

	# The provenance stamp is the one column that must never be dropped quietly.
	# On a site where `add_sync_provenance_fields` has not run it IS a column this
	# site lacks, and narrowing it away lands every row unstamped: parity counts
	# zero however many arrive, the write-block stops recognising mirrored rows
	# and lets anyone edit them, and the orphan count sees nothing. Three
	# guarantees broken at once, announced as a success. Failing loudly costs one
	# run and names `bench migrate` as the fix.
	is_stamped = doctype in STAMPED_DOCTYPES if stamped is None else stamped
	if is_stamped and PROVENANCE_FIELD in payload and PROVENANCE_FIELD not in columns:
		raise ValueError(
			f"{doctype} has no {PROVENANCE_FIELD} column on this site — run `bench migrate` "
			f"before syncing, or every mirrored row lands unstamped and unprotected"
		)

	narrowed, dropped = {}, {}
	for field, value in payload.items():
		if field not in columns:
			# No offending value to report — the column simply is not here.
			dropped[field] = None
			continue
		allowed = selects.get(field)
		# An empty value always fits: Frappe's own Select options carry a blank.
		if allowed and value not in ("", None) and value not in allowed:
			dropped[field] = value
			continue
		narrowed[field] = value
	return narrowed, dropped


def _write_row(doctype: str, remote_name: str, payload: dict) -> str:
	"""Upsert one row keyed by the remote name.

	Returns "inserted", "updated", or "skipped" (create-only doctype that already
	exists locally).

	Updates go through `db.set_value` rather than `save()` on purpose: mirrored
	Attendance rows arrive submitted, and a mirror must not re-run the source
	instance's validation against this site's (possibly different) masters.
	"""
	payload, dropped = _narrow_to_local_schema(doctype, payload)
	for field, value in dropped.items():
		# Keyed by field, collecting the distinct VALUES that could not be stored.
		# Naming the field tells an operator something is wrong; naming the value
		# tells HR what to go and correct on the source, which is the only place
		# it can be fixed.
		seen_values = _write_row.dropped_fields.setdefault(field, set())
		if value is not None:
			seen_values.add(str(value))

	if doctype in CREATE_ONLY_DOCTYPES and frappe.db.exists(doctype, remote_name):
		# Not even the identity fields: whatever is here locally wins, always.
		_log().debug("[sync] %s %s already exists locally, left untouched", doctype, remote_name)
		return "skipped"

	if frappe.db.exists(doctype, remote_name):
		frappe.db.set_value(doctype, remote_name, payload, update_modified=False)
		if doctype == "Employee":
			_reconcile_user_status(remote_name)
		return "updated"

	# A mirror copies an END STATE; it does not walk a lifecycle. Frappe derives
	# `_action` from the docstatus it is handed, so `insert()` with docstatus 1
	# means `_action == "submit"` and `on_submit` runs — here, against this site's
	# data, re-doing work the source instance already did.
	#
	# Measured rather than assumed: inserting one submitted Leave Allocation on a
	# test site created a Leave Ledger Entry. Inserting the same row as a draft
	# and then setting the docstatus created none, and the docstatus still stuck.
	#
	# That is a cascade, not a detail, because every on_submit in this app writes
	# into a doctype the mirror already holds at exact parity:
	#
	#   Leave Policy Assignment -> Leave Allocation -> Leave Ledger Entry
	#   Leave Application       -> Attendance
	#   Attendance Request      -> Attendance
	#   Shift Request           -> Shift Assignment
	#
	# Firing them would stack locally-generated rows on top of the mirrored ones —
	# leave balances roughly doubled, from a sync that reported success.
	#
	# It has not bitten yet only because the three submittables mirrored until now
	# (Attendance, Leave Ledger Entry, Shift Assignment) happen to define no
	# `on_submit` at all. Luck, not design, and it runs out the moment the leave
	# chain is mirrored.
	#
	# So every row is inserted as a DRAFT and moved to its final docstatus through
	# `db.set_value` — the same hook-free route every mirrored UPDATE already takes,
	# and the route the cancelled case has always used. This generalises that case
	# rather than adding a second mechanism beside it: docstatus 2 also stops
	# needing its submit-then-cancel dance, because nothing is being walked at all.
	final_docstatus = int(payload.get("docstatus") or 0)
	if final_docstatus:
		payload = dict(payload, docstatus=0)

	doc = frappe.get_doc({"doctype": doctype, **payload})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.insert(set_name=remote_name, ignore_if_duplicate=True)

	if final_docstatus:
		frappe.db.set_value(doctype, remote_name, {"docstatus": final_docstatus}, update_modified=False)
		_log().debug(
			"[sync] %s %s mirrored at docstatus %s without running submit hooks",
			doctype,
			remote_name,
			final_docstatus,
		)
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
COMPANY_SCOPED_DOCTYPES = frozenset(
	{"Employee", "Attendance", "Leave Ledger Entry", "Shift Assignment", "Shift Schedule Assignment"}
)

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


#: Longest `in` list to put into a single request. The filters travel in the GET
#: query string, and a proxy rejects an over-long request line with 400 — which is
#: what Employee Checkin started returning once the mirrored employee list grew
#: from 116 to 289. Not transient and not retryable, so it would have stayed
#: broken as the mirror got HEALTHIER: a failure that arrives with success.
MAX_FILTER_VALUES = 100


def _split_filters(filters):
	"""Yield filter sets small enough to survive a GET request line.

	Splits on the first over-long `in` list and repeats every other condition on
	each chunk, so the union of the chunks is exactly the original query. Order is
	preserved, and nothing is dropped: the pages within a chunk still walk their
	own total order, and the caller's counters accumulate across chunks.
	"""
	if not filters:
		yield filters
		return

	for field, condition in filters.items():
		if (
			isinstance(condition, tuple | list)
			and len(condition) == 2
			and condition[0] == "in"
			and len(condition[1]) > MAX_FILTER_VALUES
		):
			values = list(condition[1])
			for start in range(0, len(values), MAX_FILTER_VALUES):
				yield {**filters, field: ("in", values[start : start + MAX_FILTER_VALUES])}
			return

	yield filters


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
	_write_row.dropped_fields = {}
	unmet_parents: set[str] = set()
	row_errors: list[str] = []
	seen = set()

	for chunk in _split_filters(remote_filters):
		start = 0
		while True:
			page = client.get_list(
				doctype,
				filters=chunk or None,
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

				# The list endpoint cannot return child tables, so anything whose
				# children are load-bearing is re-read in full before it is written.
				if doctype in CHILD_TABLE_DOCTYPES:
					row = client.get_doc(doctype, remote_name) or row

				# Referential integrity, per row. Writing a row whose parent is absent
				# is what produced 5,821 orphan attendance records and then 266 orphan
				# employees; skipping is the only honest outcome.
				absent = missing_parents(doctype, row)
				if absent:
					orphaned += 1
					for parent in absent:
						unmet_parents.add(parent)
					_log().warning(
						"[sync] %s %s skipped: missing %s", doctype, remote_name, ", ".join(absent)
					)
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
		# STAMPED only: masters carry no provenance column, and filtering on one
		# they do not have is an OperationalError that fails the whole doctype —
		# then takes every dependent down with it. SYNC-00053 lost eleven of
		# fourteen doctypes to exactly this. Nothing is lost by skipping the check
		# either: a create-only master is never deleted here in the first place.
		if doctype in STAMPED_DOCTYPES:
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
		"dropped_fields": [
			f"{field} ({', '.join(sorted(values))})" if values else field
			for field, values in sorted(getattr(_write_row, "dropped_fields", {}).items())
		],
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


def _derive_holiday_assignments() -> None:
	"""Create any missing Holiday List Assignment from what the mirror just wrote.

	Reuses HRMS's own migration rather than restating its query: it already derives
	assignments from `Employee.holiday_list` and `Company.default_holiday_list`, and
	it is idempotent by construction — it creates only what does not exist. Two
	copies of that logic would drift, and a hub whose holiday arithmetic disagreed
	with the framework's would be a bad way to find that out.
	"""
	from hrms.patches.v16_0.create_holiday_list_assignments import execute

	execute()


def _notify_run_finished(run_name: str, instance_name: str, status: str, totals: dict) -> None:
	"""Put the outcome where a Desk user already looks: the bell.

	A pull takes minutes, and before this the operator was expected to sit on a
	list view and guess. A Notification Log entry survives them closing the tab,
	which a realtime toast does not.

	Addressed to whoever asked for the run — `frappe.enqueue` carries the session
	user into the worker, so that is the person who pressed the button.
	"""
	user = getattr(frappe.session, "user", None) if hasattr(frappe, "session") else None
	if not user or user == "Guest":
		return

	clean = status == "Completed"
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"document_type": "HRMS Sync Run",
			"document_name": run_name,
			"subject": _("Sync from {0}: {1}").format(instance_name, status),
			"email_content": _("Pulled {0}, written {1}, skipped {2}, orphaned {3}, errored {4}.").format(
				totals.get("pulled", 0),
				totals.get("written", 0),
				totals.get("skipped", 0),
				totals.get("orphaned", 0),
				totals.get("errored", 0),
			)
			+ ("" if clean else " " + _("Rows were left unwritten; the watermark is held.")),
		}
	).insert(ignore_permissions=True)


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
	# Committed immediately, and on purpose. In a web request Frappe commits at the
	# end; in a background job a later crash rolls the whole transaction back and
	# takes the evidence with it — which is how a run could vanish between
	# "queued" and the list view a minute later.
	frappe.db.commit()
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
	results, errors, failed, absent = [], [], [], []
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
				frappe.db.rollback()
				if is_absent_on_source(e):
					# A version gap, not a failure. Recorded so an operator can see
					# WHY nothing arrived, but it leaves no outstanding work, so it
					# must not hold the watermark or block the cutover gate.
					absent.append(doctype)
					errors.append(f"{doctype}: not present on the source instance — skipped")
					_log().warning("[sync] %s is not present on %s; skipping", doctype, instance_name)
					continue
				failed.append(doctype)
				errors.append(f"{doctype}: {e}")
				_log().error("[sync] %s failed: %s", doctype, e, exc_info=True)
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
			if result.get("dropped_fields"):
				# Named, not merely dropped: a field this site cannot store is a
				# real difference from the source, and an operator who never hears
				# about it will eventually wonder why a column is empty.
				errors.append(
					f"{doctype}: this site cannot store "
					f"{', '.join(result['dropped_fields'])} — written without them"
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
			"absent": absent,
			**totals,
		}
	except Exception as e:
		status = "Failed"
		errors.append(f"run aborted: {e}")
		_log().error("[sync] run %s aborted", run_name, exc_info=True)
		raise
	finally:
		frappe.flags.in_shadow_sync = False
		# Derived, never mirrored. A Holiday List Assignment is computed from
		# `Employee.holiday_list` and `Company.default_holiday_list`, both of which
		# have just landed — so pulling it over the wire as well would be two routes
		# to one state, and the source (an older HRMS) has no such doctype to pull
		# from anyway. Deriving is also what the hub wants: holiday policy is HR's
		# to own here, and a derived row carries no provenance stamp, so nothing
		# reverts an HR decision on the next run.
		try:
			_derive_holiday_assignments()
		except Exception as e:
			_log().warning("[sync] could not derive holiday list assignments: %s", e)
		_finish_run(run_name, status, totals, errors)
		# Telling somebody is strictly less important than the pull itself, so a
		# bell that will not ring must never turn a finished run into a failed one.
		try:
			_notify_run_finished(run_name, instance_name, status, totals)
		except Exception as e:
			_log().warning("[sync] could not notify %s about run %s: %s", instance_name, run_name, e)


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

#: A `Running` row older than the job could possibly live was abandoned by a
#: worker that died without reaching `_finish_run`. Past this it no longer counts
#: as "in flight", or one killed worker would block the button for ever.
STALE_RUN_AFTER_SECONDS = SYNC_JOB_TIMEOUT + 300


def sync_job_id(instance_name: str) -> str:
	"""One in-flight run per source instance.

	A second concurrent pull cannot corrupt anything — the upsert keys on the
	remote name — but it doubles the read load on what is live production for ten
	companies, and leaves two run records for one operator intent.
	"""
	return f"hrms-sync-{instance_name}"


def _job_status(job_id: str):
	"""rq's view of this instance's job, or None when there is nothing to see.

	Indirected through a module function so the bench-free tests can drive it, and
	so a redis hiccup is a None rather than a traceback out of a Desk button.
	"""
	from frappe.utils.background_jobs import get_job_status

	return get_job_status(job_id)


def _queue_workers(queue: str = SYNC_QUEUE) -> int:
	"""How many workers are actually consuming `queue`."""
	from frappe.utils.background_jobs import get_workers

	return len(get_workers(queue) or [])


def _clear_job(job_id: str) -> None:
	"""Drop a stuck rq job so a fresh one can take its place."""
	from frappe.utils.background_jobs import get_job

	job = get_job(job_id)
	if job:
		job.delete()
		_log().warning("[sync] cleared stuck job %s at an operator's request", job_id)


def _probe(fn, *args):
	"""Run an introspection call, or return None if it cannot answer.

	Fails OPEN by design. Redis unreachable, rq's API moved, a queue name this
	deployment does not have — none of that is a reason to refuse a sync. A run
	that happens twice is idempotent; a button that can never be pressed is not
	recoverable from the UI at all, which is exactly the hole this whole function
	exists to close.
	"""
	try:
		return fn(*args)
	except Exception as e:
		_log().warning("[sync] could not inspect the background queue: %s", e)
		return None


def running_run(instance_name: str) -> str | None:
	"""The run genuinely still in flight for this instance, if any.

	A `Running` row past `STALE_RUN_AFTER_SECONDS` is not in flight, it is the
	corpse of a worker that was killed before `_finish_run` — `_close_stale_runs`
	marks it Failed when the next run starts, and until then it must not be
	mistaken for a live one.
	"""
	rows = frappe.get_all(
		"HRMS Sync Run",
		filters={"source_instance": instance_name, "status": "Running"},
		fields=["name", "started_at"],
		order_by="started_at desc",
		limit=1,
	)
	if not rows:
		return None

	started_at = rows[0].get("started_at")
	try:
		if started_at and (now_datetime() - started_at).total_seconds() > STALE_RUN_AFTER_SECONDS:
			return None
	except TypeError:  # unparseable timestamp — treat it as live and let a human look
		pass
	return rows[0]["name"]


@frappe.whitelist(methods=["POST"])
def enqueue_sync(
	instance_name: str, doctypes: str | None = None, incremental: int = 1, force: int = 0
) -> dict:
	"""Queue a run and return immediately. The button's entry point.

	`run_sync` stays callable directly for bench and for tests; what it must not do
	any more is run inside a web request, where the gateway kills the worker
	partway and `sync_instance`'s `finally` never gets to record what happened.

	Every refusal names a REASON the operator can act on. The first version of this
	returned a bare "already in progress" whenever rq held a live job id, which on
	verifica-live meant a job sitting QUEUED on a queue with no worker: nothing was
	running, nothing ever would, and the button was permanently dead with a week-old
	Partial as the only thing to look at. Queue health is therefore part of the
	answer, and the authoritative "is a sync in flight" signal is the run record —
	something the operator can actually open — not an rq job id they cannot see.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	if not instance_name:
		frappe.throw(_("instance_name is required"))

	run = running_run(instance_name)
	if run:
		return {"queued": False, "reason": "already_running", "instance": instance_name, "run": run}

	status = _probe(_job_status, sync_job_id(instance_name))
	workers = _probe(_queue_workers, SYNC_QUEUE)

	# `workers == 0` is knowable and fatal; `workers is None` means we could not
	# ask, and not being able to ask must never block the operator.
	if workers == 0:
		_log().error(
			"[sync] refusing to queue %s: no worker is consuming the %s queue",
			instance_name,
			SYNC_QUEUE,
		)
		return {
			"queued": False,
			"reason": "no_worker",
			"instance": instance_name,
			"queue": SYNC_QUEUE,
		}

	if status == "started":
		return {"queued": False, "reason": "already_running", "instance": instance_name, "run": None}

	if status == "queued":
		# `force` is the operator's escape hatch for a job that is queued and never
		# starts. It is deliberately unable to touch a RUNNING one — the guard above
		# returns first — because that would kill live work mid-write. Without this
		# the only cure is a bench console, which a Frappe Cloud operator has not got.
		if not int(force or 0):
			return {"queued": False, "reason": "already_queued", "instance": instance_name}
		_probe(_clear_job, sync_job_id(instance_name))

	job = frappe.enqueue(
		"hrms.sync.runner.run_sync",
		queue=SYNC_QUEUE,
		timeout=SYNC_JOB_TIMEOUT,
		job_id=sync_job_id(instance_name),
		instance_name=instance_name,
		doctypes=doctypes,
		incremental=incremental,
	)

	_log().info("[sync] queued a background run for %s (job %s)", instance_name, getattr(job, "id", None))
	return {"queued": True, "instance": instance_name}


@frappe.whitelist()
def sync_status(instance_name: str) -> dict:
	"""What is actually happening for this instance, in terms the operator can use.

	Read-only, and deliberately whitelisted separately from `enqueue_sync` so the
	form can answer "is it stuck?" without starting anything.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	return {
		"instance": instance_name,
		"run": running_run(instance_name),
		"job": _probe(_job_status, sync_job_id(instance_name)),
		"workers": _probe(_queue_workers, SYNC_QUEUE),
		"queue": SYNC_QUEUE,
	}


@frappe.whitelist(methods=["POST"])
def run_sync(instance_name: str, doctypes: str | None = None, incremental: int = 1) -> dict:
	"""Desk/bench entry point. Kept thin: it only builds the client.

	POST-only for the same reason `company_shells.create_company_shells` is: this
	writes thousands of rows, and a state-mutating endpoint reachable by GET is a
	CSRF vector — a logged-in HR Manager loading an image tag would start a pull.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	from hrms.sync.client import RemoteInstanceClient

	return run_sync_with_client(
		instance_name,
		RemoteInstanceClient,
		doctypes=parse_doctypes(doctypes),
		incremental=bool(int(incremental)),
	)


def run_sync_with_client(instance_name: str, build_client, doctypes=None, incremental: bool = True) -> dict:
	"""Run a sync, recording a Failed run if the client cannot even be built.

	Building a `RemoteInstanceClient` resolves the URL and decrypts the
	credentials, so it raises on a rotated secret, a disabled instance or an
	unreachable host. That used to happen OUTSIDE anything that writes a run
	record: in a web request it surfaced as a red dialog, but moved into a
	background job it surfaced as nothing at all — the job died, no `HRMS Sync Run`
	appeared, and the operator could not tell "never started" from "still running".
	verifica-live, 2026-08-17: "Sync queued" at 13:02, and at 13:03 the newest run
	was still a week old.

	A run that cannot start is still a run, and has to say so.

	`build_client` is injected so this is testable without a bench; `run_sync`
	passes the real class.
	"""
	try:
		client = build_client(instance_name)
	except Exception as e:
		run_name = _start_run(instance_name, doctypes or DEFAULT_SYNC_DOCTYPES)
		_finish_run(
			run_name,
			"Failed",
			{"pulled": 0, "written": 0, "skipped": 0, "errored": 0, "orphaned": 0},
			[f"could not connect to {instance_name}: {e}"],
		)
		_log().error("[sync] %s: could not build a client: %s", instance_name, e)
		raise

	return sync_instance(client, doctypes=doctypes, incremental=incremental)
