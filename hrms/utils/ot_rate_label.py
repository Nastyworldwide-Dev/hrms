"""The rate an overtime claim is paid at, in HR's words (25 Sep 2026).

A claim's hours are split across the shift's rate bands in band order — the
order payroll prices them (`ot_calculation._ot_bands_for_day`). Most claims
land in one band ("1.5x"); an Off Day claim past its first 4 h spans two.
"""

import logging

logger = logging.getLogger(__name__)


def _hours(value) -> str:
	return f"{value:g}h"


def rate_label(bands) -> str:
	""" "1.5×", or "1.5× (4h) + 2.0× (1.5h)" when a claim spans bands. Pure."""
	bands = [b for b in bands or [] if b.get("hours")]
	if not bands:
		return ""
	if len(bands) == 1:
		return f"{bands[0]['rate']:.1f}×"
	return " + ".join(f"{b['rate']:.1f}× ({_hours(round(b['hours'], 2))})" for b in bands)
