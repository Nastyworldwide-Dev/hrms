"""How a repair endpoint reads its `dry_run` argument.

`cint("true")` and `cint("yes")` are 0 in Frappe, so `dry_run = cint(dry_run)`
turned a request that ASKED for a dry run into a live write — on endpoints that
insert punches, cancel and amend attendance, or re-price overtime. A dry run is
the safe default: only an explicit "off" value writes.
"""

import logging

logger = logging.getLogger(__name__)

_OFF = {"0", "false", "no", "off"}


def wants_dry_run(value) -> bool:
	"""True unless `value` explicitly switches the dry run off (0, False, "0", "false", "no", "off")."""
	if value is None:
		return True
	if isinstance(value, bool):
		return value
	if isinstance(value, int | float):
		return value != 0
	return str(value).strip().lower() not in _OFF
