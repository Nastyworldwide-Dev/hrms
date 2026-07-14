# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging
from math import ceil

import frappe
from frappe import _
from frappe.utils import flt

logger = logging.getLogger(__name__)

# PERKESO Category 1 (Employment Injury + Invalidity) contribution schedule.
# The official table is banded in RM100 steps and computes each band's
# contribution as a percentage of the band midpoint, rounded to 5 sen.
# Wage ceiling RM6,000 effective 1 Oct 2024 — review when PERKESO revises it.
SOCSO_WAGE_CEILING = 6000
SOCSO_RATES = {
	"employee": 0.005,
	"employer": 0.0175,
}

# EIS (Act 800) mirrors the SOCSO banding at 0.2% per side, same ceiling.
EIS_RATE = 0.002


def _band_midpoint(wage: float) -> float:
	if wage >= SOCSO_WAGE_CEILING:
		return SOCSO_WAGE_CEILING - 50
	return ceil(wage / 100) * 100 - 50


def _round_to_5_sen(amount: float) -> float:
	return round(amount * 20) / 20


def get_socso_contribution(base, share: str = "employee") -> float:
	"""Monthly SOCSO contribution for a wage, per the banded schedule.

	Usable in Salary Component formulas:
	    get_socso_contribution(base, 'employee')
	    get_socso_contribution(base, 'employer')
	"""
	if share not in SOCSO_RATES:
		frappe.throw(_("SOCSO share must be 'employee' or 'employer', got {0}.").format(share))
	wage = flt(base)
	if wage <= 0:
		return 0.0
	contribution = _round_to_5_sen(_band_midpoint(wage) * SOCSO_RATES[share])
	logger.debug("[my_payroll] socso share=%s wage=%s contribution=%s", share, wage, contribution)
	return contribution


def get_eis_contribution(base) -> float:
	"""Monthly EIS contribution (identical for employee and employer).

	Usable in Salary Component formulas: get_eis_contribution(base)
	"""
	wage = flt(base)
	if wage <= 0:
		return 0.0
	return _round_to_5_sen(_band_midpoint(wage) * EIS_RATE)
