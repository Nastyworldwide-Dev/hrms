"""Single-writer enforcement for mirrored rows — the parallel-run write-block.

During the parallel run exactly one site writes for any given company. Rows
mirrored here by `hrms.sync.runner` carry `synced_from_instance`, and the
program's design decision is that violating single-writer must be *blocked in
code, not just policy*: HR approving or editing a mirrored row on this hub
would silently diverge from the source, and the next incremental pull would
either clobber the local change or preserve the divergence forever.

The decision itself (`plan_mirror_write`) is pure; the doc-event hook
gathers its inputs. Escape hatches, in precedence order:

* the sync itself (`frappe.flags.in_shadow_sync`) — the one legitimate writer;
* migrate / patch / install context — schema work must not brick on old rows;
* `unlock_mirrored_writes` on the HRMS ERP Instance record — THE cutover
  switch: per instance, deliberate, flipped by a human when this site takes
  over writing. A stamp pointing at a deleted instance record stays LOCKED
  (fail-closed); System Manager is the escape hatch;
* System Manager — break-glass for orphan cleanup and repairs, allowed but
  logged loudly, and the stamp itself is restored so provenance (which parity
  counts) cannot drift even then.

Known residual: server code writing via `frappe.db.set_value` bypasses doc
events entirely and cannot be caught here. The one such writer found in audit
— `hrms.utils.checkin_sweeper` — excludes mirrored rows at the query instead;
`test_write_block` pins that too.
"""

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

PROVENANCE_FIELD = "synced_from_instance"

#: Must stay identical to `hrms.sync.runner.DEFAULT_SYNC_DOCTYPES` — a doctype
#: that is mirrored but unguarded defeats the block. Not imported so this
#: module stays loadable without dragging the runner in; `test_write_block`
#: fails if the two lists ever drift apart.
MIRRORED_DOCTYPES = (
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Leave Ledger Entry",
)

ALLOW = "allow"
ALLOW_OVERRIDE = "allow-override"
BLOCK = "block"


def plan_mirror_write(
	stamp,
	*,
	is_new: bool,
	incoming_stamp=None,
	sync_active: bool = False,
	maintenance_active: bool = False,
	unlocked: bool = False,
	is_system_manager: bool = False,
	is_rename: bool = False,
) -> tuple[str, str]:
	"""Decide one write on a (possibly) mirrored row. Pure.

	`stamp` is the DB value of `synced_from_instance` (None for a new row);
	`incoming_stamp` is what the caller's payload carries. The DB value wins
	for existing rows — stripping the stamp from a request must not unlock
	the row — while a NEW row is judged on its payload: only the sync may
	insert stamped rows.

	A rename gets NO break-glass: the mirror upserts on the remote `name`, so
	renaming a mirrored row guarantees a duplicate on the next pull — that is
	data corruption whoever performs it, not an emergency repair (SEC-01).
	"""
	if sync_active:
		return ALLOW, "shadow sync is the writer"
	if maintenance_active:
		return ALLOW, "migrate/patch/install context"

	effective = incoming_stamp if is_new else stamp
	if not effective:
		return ALLOW, "not a mirrored row"
	if unlocked:
		return ALLOW, f"instance {effective} unlocked for local writes (cutover)"
	if is_system_manager and not is_rename:
		return ALLOW_OVERRIDE, f"System Manager break-glass on a row mirrored from {effective}"
	if is_rename:
		return BLOCK, (
			f"mirrored from {effective} — renaming would break the name-keyed mirror and "
			f"duplicate the row on the next pull"
		)
	return BLOCK, (
		f"mirrored from {effective} — during the parallel run this row is owned by its source instance"
	)


def stamp_to_persist(db_stamp, incoming_stamp, is_new: bool):
	"""The provenance value an allowed write may carry. Pure.

	For an existing row the DB value always wins — restoring a stripped stamp
	AND discarding a forged one (SEC-03: injecting a stamp onto a local row
	would corrupt parity counts, or self-lock the row read-only). A new row
	keeps its payload: a forged stamped insert is already BLOCKed upstream,
	so the only stamped inserts left are the sync's own.
	"""
	return incoming_stamp if is_new else db_stamp


def _instance_unlocked(instance_name) -> bool:
	"""The cutover switch. A missing instance record stays locked (fail-closed)."""
	if not instance_name:
		return False
	return bool(frappe.db.get_value("HRMS ERP Instance", instance_name, "unlock_mirrored_writes"))


def block_mirrored_writes(doc, method=None, *args):
	"""Doc-event hook (validate / before_update_after_submit / before_cancel /
	on_trash / before_rename) for every mirrored doctype. `*args` swallows the
	extra (old, new, merge) arguments the rename event passes."""
	is_new = bool(doc.is_new())
	db_stamp = None if is_new else frappe.db.get_value(doc.doctype, doc.name, PROVENANCE_FIELD)
	incoming_stamp = doc.get(PROVENANCE_FIELD)
	flags = frappe.flags

	action, reason = plan_mirror_write(
		db_stamp,
		is_new=is_new,
		incoming_stamp=incoming_stamp,
		sync_active=bool(getattr(flags, "in_shadow_sync", False)),
		maintenance_active=bool(
			getattr(flags, "in_migrate", False)
			or getattr(flags, "in_patch", False)
			or getattr(flags, "in_install", False)
		),
		unlocked=_instance_unlocked(db_stamp or incoming_stamp),
		is_system_manager=(frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()),
		is_rename=(method == "before_rename"),
	)

	if action == BLOCK:
		logger.warning(
			"[write_block] blocked %s on %s %s for %s: %s",
			method or "write",
			doc.doctype,
			doc.name,
			frappe.session.user,
			reason,
		)
		frappe.throw(
			_(
				"{0} {1} is mirrored from {2} and is read-only during the parallel run. "
				"Make this change on the source instance instead."
			).format(_(doc.doctype), doc.name, db_stamp or incoming_stamp),
			frappe.PermissionError,
		)

	if action == ALLOW_OVERRIDE:
		logger.warning(
			"[write_block] OVERRIDE: %s by %s on %s %s (%s)",
			method or "write",
			frappe.session.user,
			doc.doctype,
			doc.name,
			reason,
		)
		# Break-glass must be discoverable from the Desk, not only in server
		# logs a System Manager may never read (SEC-04). Error Log is the
		# lightest persistent, UI-queryable audit record available.
		frappe.log_error(
			title=f"Mirror write override: {doc.doctype} {doc.name}",
			message=f"{method or 'write'} by {frappe.session.user}: {reason}",
		)

	# Whatever was allowed, provenance itself must not drift: parity counts by
	# this stamp, so an edit that strips OR FORGES it would corrupt the
	# cutover evidence silently (SEC-03).
	if method == "validate":
		desired = stamp_to_persist(db_stamp, incoming_stamp, is_new)
		if incoming_stamp != desired:
			logger.warning(
				"[write_block] discarding provenance drift on %s %s (payload carried %r, keeping %r)",
				doc.doctype,
				doc.name,
				incoming_stamp,
				desired,
			)
			doc.set(PROVENANCE_FIELD, desired)
