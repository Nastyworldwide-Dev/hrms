"""Move enable_strict_geofence from Shift Type to Shift Assignment.

Up to v15.77.3 the strict-geofence flag was a property of the Shift Type, so
every assignment using "Day Shift" inherited the same strict/lenient mode.
From v15.77.4 the flag lives on the Shift Assignment itself so HR can mix
strict (HQ desk staff) and lenient (field reps, drivers) on the same shift
type.

This patch carries existing strict-mode configuration forward:

  For every Shift Type that has enable_strict_geofence=1 (the legacy column,
  still present on the table after migrate but no longer in the JSON), copy
  the flag onto every Shift Assignment that references it — but only when
  the assignment hasn't already been set explicitly.

The Shift Type column is left in place. Removing it requires an explicit
ALTER TABLE we don't run here; an HR admin can drop it manually once they
have verified the new behaviour, or we can ship that in a later patch.
"""

from __future__ import annotations

import logging

import frappe

logger = logging.getLogger(__name__)


def execute() -> None:
	# The Shift Type column may not exist on fresh installs that never ran
	# the legacy schema. Probe before reading.
	if not frappe.db.has_column("Shift Type", "enable_strict_geofence"):
		logger.info(
			"[patch.v15_77_4] Shift Type.enable_strict_geofence column not present — nothing to migrate"
		)
		return

	strict_shift_types = frappe.db.sql_list(
		"""
		SELECT name FROM `tabShift Type` WHERE enable_strict_geofence = 1
		"""
	)
	if not strict_shift_types:
		logger.info("[patch.v15_77_4] no Shift Types had enable_strict_geofence=1 — nothing to migrate")
		return

	frappe.db.sql(
		"""
		UPDATE `tabShift Assignment`
		SET enable_strict_geofence = 1
		WHERE shift_type IN %(types)s
		  AND COALESCE(enable_strict_geofence, 0) = 0
		""",
		{"types": tuple(strict_shift_types)},
	)
	logger.info(
		"[patch.v15_77_4] migrated strict-mode from Shift Types %s to their Shift Assignments",
		strict_shift_types,
	)
	frappe.db.commit()
