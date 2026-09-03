"""Move every naming counter past the rows already on disk.

THE FAILURE, from production, and reproduced on a bench before this was written:

    Employee Checkin EMP-CKIN-08-2026-000001 already exists

An employee taps Check In and the app hands them a document name the mirror has
already used, and the same holds for every mirrored doctype that numbers itself.

The advance loop this patch once spelled out now lives in one place —
hrms.utils.naming_series_repair, over runner.advance_series_past — so the deploy
patch, the broader re-heal patch and the after-import hook cannot drift apart.
Scoped to STAMPED_DOCTYPES to preserve this patch's original reach (the mirror
set); the newer patch widens it to the request doctypes. Forward-only, never
destructive, safe to re-run.
"""

import logging

import frappe

from hrms.sync.runner import STAMPED_DOCTYPES

logger = logging.getLogger(__name__)


def execute():
	logger.info("[repair_mirrored_naming_series] repairing counters over the mirror set")
	from hrms.utils.naming_series_repair import repair_naming_series

	moved = repair_naming_series(STAMPED_DOCTYPES)
	if moved:
		frappe.db.commit()
		lines = "\n".join(f"  {dt}: {counters}" for dt, counters in sorted(moved.items()))
		print(f"[repair_mirrored_naming_series] advanced counters on {len(moved)} doctype(s):\n{lines}")
	else:
		print("[repair_mirrored_naming_series] every counter already past its rows")
