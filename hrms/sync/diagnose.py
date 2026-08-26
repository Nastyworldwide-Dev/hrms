"""What is actually in this hub, and which source does it really belong to?

READ-ONLY. Nothing here writes, deletes, or syncs. Safe to run on production at
any time, including mid-sync.

Run it with:

    bench --site <site> execute hrms.sync.diagnose.main

...or paste into `bench --site <site> console`.

Why this exists
---------------
The mirror keys every row on the SOURCE's document name. That is fine while each
registered instance owns distinct records, and it breaks completely when two
instances hold the SAME records — which is exactly what a dev ERP cloned from
live is: the same employees, the same names, twice.

Before the guard in `runner.plan_cross_instance_write`, the second instance to
sync simply overwrote the first one's stamp:

    pull from Nasty-Live -> stamp is 'Nasty-Live'
    pull from Nasty-Dev  -> stamp is 'Nasty-Dev'
    rows for this employee: 1

So on a hub that ran both, `synced_from_instance` does not currently mean "came
from here". It means "was touched last by here". Everything downstream reads
that field: purge deletes by it, parity counts by it, the write-block locks by
it. This script exists to tell you how far that drift went BEFORE you act on any
of them — above all before pressing Purge, which deletes by the stamp and cannot
know it is wrong.

Reading the output
------------------
The bottom line is the verdict. In short:

  ONE SOURCE       nothing to do; the stamps mean what they say
  DEV REGISTERED   the risk is live; re-sync from live BEFORE purging anything
"""

import logging

import frappe
from frappe import _

from hrms.overrides.company_scope import require_unfenced

logger = logging.getLogger(__name__)

#: Doctypes carrying the provenance stamp. Kept as a literal rather than
#: imported from `sync.runner` so this stays paste-into-console runnable on a
#: site whose app version predates any given release.
STAMPED = (
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Leave Ledger Entry",
	"Leave Allocation",
	"Leave Application",
	"Leave Policy Assignment",
	"Shift Assignment",
	"Shift Schedule Assignment",
	"Attendance Request",
	"Shift Request",
	"Appraisal",
)


@frappe.whitelist()
def source_census() -> dict:
	"""`main`, for the Desk button — same numbers, no terminal.

	`main` prints, and printing is unreachable from a browser: Frappe's own
	System Console runs Python through `safe_exec`, whose output comes from
	`log()` rather than stdout, so the formatted report never appears. Asking an
	operator to open a shell to find out whether their data is safe is asking
	most operators not to find out.

	GET-only and whitelisted for read: it counts and returns. `main` still
	exists for a terminal, and both share `assess` so the two cannot disagree
	about the verdict.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	# Role checks answer "is this person HR?" and nothing more. This census
	# counts rows across EVERY company on the site and names every registered
	# source instance, so an HR (Company) user — HR Manager plus a Company
	# fence — would read a hub-wide picture their fence exists to withhold.
	#
	# Caught by test_sync_endpoints_are_fenced, which asserts exactly this for
	# every endpoint in this package. It was right and I had missed it.
	require_unfenced(_("read the source census"))
	instances = _instances()
	rows = []
	totals: dict[str, int] = {}
	for doctype in STAMPED:
		if not frappe.db.table_exists(doctype):
			continue
		counts = _counts_by_stamp(doctype)
		if not sum(counts.values()):
			continue
		for stamp, n in counts.items():
			if stamp:
				totals[stamp] = totals.get(stamp, 0) + n
		rows.append(
			{
				"doctype": doctype,
				"total": sum(counts.values()),
				"hub_owned": counts.get(None, 0) + counts.get("", 0),
				# Filtered BEFORE sorting, not after: the unstamped bucket's key is
				# None, and sorting str against None is a TypeError. Caught on a
				# bench — every hub has that bucket, so this would have thrown on
				# the first real click.
				"by_source": dict(sorted((k, v) for k, v in counts.items() if k)),
			}
		)

	out = {"rows": rows, "by_instance": totals, "instances": instances}
	out.update(assess(instances, totals))
	logger.info("[diagnose] census: %s across %d doctype(s)", out["verdict"], len(rows))
	return out


def assess(instances: list[dict], totals: dict) -> dict:
	"""Is this hub's provenance trustworthy? Pure — `main` only formats it.

	Kept pure and separate because this one branch decides whether somebody
	presses Purge, and Purge is irreversible: it already cost a real record here,
	deleting live rows that happened to carry a dev stamp.

	`instances` are the REGISTERED sources; `totals` is {stamp: rows} found on
	the rows themselves. Both are consulted because they are different
	populations and either alone gets the answer wrong in exactly the case that
	matters:

	  * two enabled instances that have not synced yet leave `totals` with one
	    key or none — stamps alone would call that clean and only speak up after
	    the collision;
	  * a disabled clone that already stamped rows leaves `instances` looking
	    settled — registrations alone would call THAT clean, and it is the state
	    this system was actually left in.

	`unlocked` is reported separately and deliberately kept out of the verdict:
	it is not a divergence, but it is the most destructive switch on the form and
	must not be silent either.
	"""
	registered = {i["name"] for i in instances}
	return {
		"verdict": "one-source"
		if len([k for k, v in totals.items() if v]) <= 1 and len(registered) <= 1
		else "multi-source",
		"claiming": sorted(k for k, v in totals.items() if v),
		"orphan_stamps": sorted(set(totals) - registered),
		"unlocked": sorted(i["name"] for i in instances if i.get("unlock_mirrored_writes")),
	}


def _instances() -> list[dict]:
	return frappe.get_all(
		"HRMS ERP Instance",
		fields=["name", "enabled", "url", "unlock_mirrored_writes"],
		order_by="name",
	)


def _counts_by_stamp(doctype: str) -> dict:
	"""{stamp or None: rows}. One grouped query, not one per instance."""
	rows = frappe.db.sql(
		f"""
		SELECT synced_from_instance AS stamp, COUNT(*) AS n
		FROM `tab{doctype}` GROUP BY synced_from_instance
		""",
		as_dict=True,
	)
	return {r["stamp"]: r["n"] for r in rows}


def main() -> dict:
	out = {}
	instances = _instances()

	print("\n=== REGISTERED SOURCES " + "=" * 47)
	if not instances:
		print("  none — this hub pulls from nothing")
	for i in instances:
		flags = []
		if i["enabled"]:
			flags.append("ENABLED")
		else:
			flags.append("disabled")
		if i["unlock_mirrored_writes"]:
			flags.append("*** WRITES UNLOCKED ***")
		print(f"  {i['name']:<24} {', '.join(flags):<28} {i.get('url') or ''}")
	out["instances"] = instances

	print("\n=== WHERE THE ROWS SAY THEY CAME FROM " + "=" * 32)
	print(f"  {'doctype':<28}{'total':>8}{'hub-owned':>12}   by source")
	totals = {}
	for doctype in STAMPED:
		if not frappe.db.table_exists(doctype):
			continue
		counts = _counts_by_stamp(doctype)
		total = sum(counts.values())
		if not total:
			continue
		own = counts.get(None, 0) + counts.get("", 0)
		stamped = {k: v for k, v in counts.items() if k}
		for k, v in stamped.items():
			totals[k] = totals.get(k, 0) + v
		by_source = ", ".join(f"{k}={v}" for k, v in sorted(stamped.items())) or "-"
		print(f"  {doctype:<28}{total:>8}{own:>12}   {by_source}")
	out["by_instance"] = totals

	# A stamp naming an instance that is not registered is the clearest possible
	# evidence of drift: those rows cannot be re-synced, and purge cannot reach
	# them either, because both work through the instance record.
	verdict = assess(instances, totals)
	out.update(verdict)

	if verdict["orphan_stamps"]:
		print("\n  !! stamped with an instance that is NOT registered:")
		for s in verdict["orphan_stamps"]:
			print(f"     {s}: {totals[s]} row(s) — neither syncable nor purgeable")

	print("\n=== VERDICT " + "=" * 58)
	if verdict["unlocked"]:
		print(f"  !! WRITES UNLOCKED on {', '.join(verdict['unlocked'])}.")
		print("     Local edits to those rows will be OVERWRITTEN by the next pull.")
		print("     Unlock is for AFTER cutover, and only once that instance stops syncing.")

	if verdict["verdict"] == "one-source":
		print("  ONE SOURCE. Stamps mean what they say. Nothing to untangle.")
	else:
		print(f"  MORE THAN ONE SOURCE is in play: {', '.join(verdict['claiming']) or '(none synced yet)'}")
		print("  If any of them is a CLONE of another (a dev ERP copied from live),")
		print("  the stamps are unreliable: they record who synced LAST, not origin.")
		print()
		print("  DO NOT PURGE. Purge deletes by the stamp and would take live rows.")
		print("  Safe order:")
		print("    1. disable every instance except the real live one")
		print("    2. run a FULL sync from live — it re-stamps and restores content")
		print("    3. re-run this script; whatever still names the clone is dev-only")
		print("    4. only then purge, and unregister the clone")

	print("=" * 70)
	return out


if __name__ == "__main__":
	main()
