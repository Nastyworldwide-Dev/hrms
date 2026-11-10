"""Employee Status options (HR, 10 Nov 2026).

HR replaced ERPNext's Active / Inactive / Suspended / Left with five options:
Active, Resigned, Terminated, Deceased, Suspended.

* Inactive meant the same as Left on this site, so both became Resigned
  (patch `v16_0.employee_status_options`).
* Resigned works everywhere Left worked: it is the one leaver status.
* Terminated, Deceased and Suspended are selectable only. HR has not decided
  their rules yet; until then they behave like any other non-Active status
  (no login, otherwise treated as still employed).

The source ERP instances still send the old words; `to_current()` translates
them on the way in.

Pure on purpose: importable without a bench.
"""

ACTIVE = "Active"
RESIGNED = "Resigned"
TERMINATED = "Terminated"
DECEASED = "Deceased"
SUSPENDED = "Suspended"

#: The dropdown, in the order HR asked for.
STATUS_OPTIONS = (ACTIVE, RESIGNED, TERMINATED, DECEASED, SUSPENDED)

#: The status that works wherever "Left" used to.
LEAVER_STATUS = RESIGNED

#: The words used before 10 Nov 2026, and what each one is now.
RETIRED_STATUSES = {"Left": RESIGNED, "Inactive": RESIGNED}


def to_current(status: str | None) -> str | None:
	"""A retired status word mapped to its replacement; anything else unchanged."""
	return RETIRED_STATUSES.get(status, status)


def is_leaver(status: str | None) -> bool:
	"""True for Resigned, and for the retired Left/Inactive so a row written
	before the migration (or mirrored before translation) still counts."""
	return to_current(status) == LEAVER_STATUS
