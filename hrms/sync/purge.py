"""Remove what one instance's mirror pulled — and nothing else.

WHY THIS EXISTS
---------------
Deleting mirrored rows by hand does not work, and the reason is not the one it
looks like. Reproduced on a bench: a System Manager deleting a mirrored Employee
gets `ALLOW_OVERRIDE` from `write_block.plan_mirror_write`, the override is
logged exactly as designed — and then Frappe's own link validation refuses:

    LinkExistsError: Cannot delete ... Employee HR-EMP-00001 is linked with
    Employee Checkin EMP-CKIN-08-2026-000001

Employee is the last thing `runner.DEFAULT_SYNC_DOCTYPES` writes, so it is the
thing everything else points at. Removing it needs its mirrored Attendance,
Employee Checkin, Leave Ledger Entry and the rest gone first — and each of those
is write-blocked too. The operator is left deleting in dependency order by hand
and reading "Bulk Operation Failed: 107 documents" with no reason attached.

`runner._count_local_orphans` already counts rows the source no longer has and
its module docstring says deletion "is out of scope; a divergence is for a
human to" resolve. This is the tool that human never had.

WHAT IT WILL NOT DO
-------------------
* It never touches a row without this instance's provenance stamp. Not a local
  row, not another instance's mirror.
* It never passes `force=True`. `force` skips the link check, which is the one
  thing standing between a mirror cleanup and deleting hub-owned records — a
  hub-side Leave Application written against a mirrored employee during the
  parallel run is exactly risk R2, and it is reported rather than destroyed.
* It never runs without the caller typing the instance name back. Absent that,
  it reports what it would delete and stops.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _

from hrms.overrides.company_scope import require_unfenced
from hrms.sync.runner import PROVENANCE_FIELD, STAMPED_DOCTYPES

logger = logging.getLogger(__name__)


def purge_order() -> tuple[str, ...]:
	"""Reverse of the sync's write order: children before the rows they link to.

	STAMPED_DOCTYPES, not DEFAULT_SYNC_DOCTYPES. The masters — Department, Leave
	Type, Designation, Shift Type, Holiday List and the rest — are HR-owned here
	and carry NO provenance field, so filtering them by it is a SQL error on a
	column that does not exist. Caught on a bench; the stubbed test could not see
	it, because a fake `get_all` answers for any doctype you ask it about.

	They must not be purged in any case. A Company shell's system of record is
	this hub, not the source, so deleting one to tidy a mirror would remove
	something the mirror never owned.

	Derived rather than restated, so a doctype joining the sync joins the purge
	in the right position for free — the two orders cannot drift.
	"""
	return tuple(reversed(STAMPED_DOCTYPES))


def _stamped(doctype: str, instance_name: str) -> list[str]:
	return frappe.get_all(doctype, filters={PROVENANCE_FIELD: instance_name}, pluck="name")


@frappe.whitelist(methods=["POST"])
def purge_instance(instance_name: str, confirm: str | None = None) -> dict:
	"""Delete every row this hub mirrored from `instance_name`. DESTRUCTIVE.

	Without `confirm` this is a dry run: it reports the counts and deletes
	nothing. With `confirm`, the value must equal `instance_name` exactly —
	a typed confirmation, because "are you sure?" on a bulk delete is a
	formality and typing the name is not.

	Returns per-doctype counts, plus every row a LOCAL document still links to.
	Those are not failures to retry: something the hub owns points at them, and
	that link is the answer to whether the row should go at all.
	"""
	frappe.only_for("System Manager")
	require_unfenced(_("purge a mirrored instance"))

	dry_run = confirm is None
	if not dry_run and confirm != instance_name:
		frappe.throw(
			_("Type the instance name exactly to confirm: expected {0}").format(instance_name),
			frappe.ValidationError,
		)

	counts: dict[str, int] = {}
	blocked: list[dict] = []
	deleted = 0

	for doctype in purge_order():
		names = _stamped(doctype, instance_name)
		if not names:
			continue
		counts[doctype] = len(names)
		if dry_run:
			continue

		for name in names:
			try:
				# No force=True, deliberately. See the module docstring.
				frappe.delete_doc(doctype, name, ignore_permissions=True)
				deleted += 1
			except frappe.LinkExistsError as e:
				blocked.append({"doctype": doctype, "name": name, "reason": str(e)[:300]})
			except Exception as e:  # broad: one bad row must not strand the rest
				blocked.append({"doctype": doctype, "name": name, "reason": f"{type(e).__name__}: {e}"[:300]})

	total = sum(counts.values())
	if dry_run:
		logger.info(
			"[purge] DRY RUN %s: %d mirrored row(s) across %d doctype(s)", instance_name, total, len(counts)
		)
		return {"instance": instance_name, "dry_run": True, "counts": counts, "total": total, "blocked": []}

	frappe.db.commit()
	logger.warning(
		"[purge] %s: deleted %d of %d mirrored row(s); %d blocked by a local link",
		instance_name,
		deleted,
		total,
		len(blocked),
	)
	frappe.log_error(
		title=f"Mirror purge: {instance_name} ({deleted} deleted, {len(blocked)} blocked)",
		message=(
			f"Purged rows mirrored from {instance_name}.\n\n"
			f"Deleted {deleted} of {total} stamped rows, in reverse sync order.\n"
			+ "\n".join(f"  {d}: {n}" for d, n in counts.items())
			+ (
				"\n\nBlocked - a LOCAL document links to these, so they were left in\n"
				"place rather than force-deleted. Resolve the linking record first:\n"
				+ "\n".join(f"  {b['doctype']} {b['name']}: {b['reason']}" for b in blocked[:50])
				if blocked
				else ""
			)
		),
	)
	return {
		"instance": instance_name,
		"dry_run": False,
		"counts": counts,
		"total": total,
		"deleted": deleted,
		"blocked": blocked,
	}


@frappe.whitelist(methods=["POST"])
def release_instance_stamp(instance_name: str, confirm: str | None = None) -> dict:
	"""Clear the provenance stamp on rows mirrored from `instance_name`.

	DELETES NOTHING. It only forgets which instance a row came from, turning a
	mirrored row into a hub-owned one.

	This is the recovery `purge_instance` cannot be, and the guard in
	`runner.plan_cross_instance_write` needs it to exist. That guard stops a
	second instance overwriting a first one's rows — and on a hub that already
	ran two colliding instances it stands in the way of the repair: rows stamped
	by a cloned dev instance that are really LIVE employees get refused when the
	live instance next syncs, because dev got there first.

	Purge cannot repair that. It deletes by the stamp, and the stamp is the thing
	that is wrong; that is precisely how a real record was lost on this system.

	Clearing the stamp instead works because `plan_cross_instance_write` already
	lets the first writer take an UNSTAMPED row. So the sequence is: release the
	clone's stamp, run a full sync from the real source, and it reclaims
	everything that source genuinely holds and rewrites the content. Whatever is
	still unstamped afterwards is the answer nobody had — the rows that only ever
	existed on the clone.

	Dry run unless `confirm` equals `instance_name`, the same contract as
	`purge_instance`. Less destructive is not undoable: once the stamp is gone,
	which instance a row came from is no longer recorded anywhere.
	"""
	frappe.only_for("System Manager")
	require_unfenced(_("release a mirrored instance's provenance"))

	dry_run = confirm is None
	if not dry_run and confirm != instance_name:
		frappe.throw(
			_("Type the instance name exactly to confirm: expected {0}").format(instance_name),
			frappe.ValidationError,
		)

	counts: dict[str, int] = {}
	for doctype in purge_order():
		names = _stamped(doctype, instance_name)
		if not names:
			continue
		counts[doctype] = len(names)
		if dry_run:
			continue
		for name in names:
			# update_modified=False deliberately: `modified` drives the
			# incremental watermark, so bumping tens of thousands of rows would
			# make the next sync re-read a window it has already covered, and
			# would read as the source having changed everything at once.
			frappe.db.set_value(doctype, name, PROVENANCE_FIELD, None, update_modified=False)

	total = sum(counts.values())
	if dry_run:
		logger.info("[release] DRY RUN %s: %d stamped row(s) would be released", instance_name, total)
		return {"instance": instance_name, "dry_run": True, "counts": counts, "total": total}

	frappe.db.commit()
	logger.warning(
		"[release] %s: released %d row(s) — they are now hub-owned and can be reclaimed by a full sync",
		instance_name,
		total,
	)
	return {"instance": instance_name, "dry_run": False, "counts": counts, "total": total}
