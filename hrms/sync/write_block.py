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
) -> tuple[str, str]:
	"""Decide one write on a (possibly) mirrored row. Pure.

	`stamp` is the DB value of `synced_from_instance` (None for a new row);
	`incoming_stamp` is what the caller's payload carries. The DB value wins
	for existing rows — stripping the stamp from a request must not unlock
	the row — while a NEW row is judged on its payload: only the sync may
	insert stamped rows.
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
	if is_system_manager:
		return ALLOW_OVERRIDE, f"System Manager break-glass on a row mirrored from {effective}"
	return BLOCK, (
		f"mirrored from {effective} — during the parallel run this row is owned by its source instance"
	)


def _instance_unlocked(instance_name) -> bool:
	"""The cutover switch. A missing instance record stays locked (fail-closed)."""
	if not instance_name:
		return False
	return bool(frappe.db.get_value("HRMS ERP Instance", instance_name, "unlock_mirrored_writes"))


def block_mirrored_writes(doc, method=None):
	"""Doc-event hook (validate / before_update_after_submit / before_cancel /
	on_trash) for every mirrored doctype."""
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

	# Whatever was allowed, provenance itself must not drift: parity counts by
	# this stamp, so an edit that strips or rewrites it would corrupt the
	# cutover evidence silently.
	if not is_new and db_stamp and incoming_stamp != db_stamp and method == "validate":
		logger.info(
			"[write_block] restoring provenance stamp on %s %s (payload carried %r)",
			doc.doctype,
			doc.name,
			incoming_stamp,
		)
		doc.set(PROVENANCE_FIELD, db_stamp)
