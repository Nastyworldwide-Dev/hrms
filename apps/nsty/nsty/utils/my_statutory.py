"""Malaysian statutory contribution helpers — EPF / SOCSO / EIS (2024 rates).

Public API:
    get_epf(gross_pay, dob, party='employee') -> float
    get_socso(gross_pay, party='employee') -> float
    get_eis(gross_pay, party='employee') -> float

`party` is 'employee' or 'employer'. All amounts are in MYR.
The SOCSO/EIS lookup tables follow the PERKESO Schedule (Act 4 / Act 800).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date, datetime

logger = logging.getLogger(__name__)

EPF_MIN_WAGE = 100.0
EPF_SENIOR_AGE = 60
SOCSO_CATEGORY_1_CEILING = 5000.0  # employee SOCSO stops above this
INSURED_WAGE_CAP = 4000.0  # SOCSO/EIS insured-wage cap


# -----------------------------------------------------------------------------
# SOCSO 2024 — Category 1 (Employment Injury + Invalidity)
# Each row: (wage_from, wage_to, employee_contribution, employer_contribution)
# Values follow the PERKESO Schedule for monthly contributions.
# -----------------------------------------------------------------------------
SOCSO_2024_TABLE: list[tuple[float, float, float, float]] = [
	(0.00, 30.00, 0.10, 0.40),
	(30.01, 50.00, 0.20, 0.70),
	(50.01, 70.00, 0.30, 1.10),
	(70.01, 100.00, 0.50, 1.50),
	(100.01, 140.00, 0.70, 2.10),
	(140.01, 200.00, 1.00, 2.95),
	(200.01, 300.00, 1.50, 4.35),
	(300.01, 400.00, 2.00, 6.15),
	(400.01, 500.00, 2.50, 7.85),
	(500.01, 600.00, 3.00, 9.65),
	(600.01, 700.00, 3.50, 11.35),
	(700.01, 800.00, 4.00, 13.15),
	(800.01, 900.00, 4.75, 14.75),
	(900.01, 1000.00, 5.25, 16.55),
	(1000.01, 1100.00, 5.75, 18.15),
	(1100.01, 1200.00, 6.25, 19.85),
	(1200.01, 1300.00, 6.75, 21.55),
	(1300.01, 1400.00, 7.25, 23.15),
	(1400.01, 1500.00, 7.75, 24.75),
	(1500.01, 1600.00, 8.25, 26.35),
	(1600.01, 1700.00, 8.75, 28.05),
	(1700.01, 1800.00, 9.25, 29.65),
	(1800.01, 1900.00, 9.75, 31.25),
	(1900.01, 2000.00, 10.25, 32.85),
	(2000.01, 2100.00, 10.75, 34.45),
	(2100.01, 2200.00, 11.25, 36.15),
	(2200.01, 2300.00, 11.75, 37.75),
	(2300.01, 2400.00, 12.25, 39.35),
	(2400.01, 2500.00, 12.75, 40.95),
	(2500.01, 2600.00, 13.25, 42.65),
	(2600.01, 2700.00, 13.75, 44.25),
	(2700.01, 2800.00, 14.25, 45.85),
	(2800.01, 2900.00, 14.75, 47.45),
	(2900.01, 3000.00, 15.25, 49.15),
	(3000.01, 3100.00, 15.75, 50.75),
	(3100.01, 3200.00, 16.25, 52.35),
	(3200.01, 3300.00, 16.75, 53.95),
	(3300.01, 3400.00, 17.25, 55.65),
	(3400.01, 3500.00, 17.75, 57.25),
	(3500.01, 3600.00, 18.25, 58.85),
	(3600.01, 3700.00, 18.75, 60.45),
	(3700.01, 3800.00, 19.25, 62.15),
	(3800.01, 3900.00, 19.75, 63.75),
	(3900.01, 4000.00, 20.25, 65.35),
	# Above the insured-wage cap (RM4000) all wages contribute at the ceiling row.
	(4000.01, float("inf"), 24.75, 86.65),
]


# -----------------------------------------------------------------------------
# EIS 2024 — Employment Insurance System (Act 800)
# Each row: (wage_from, wage_to, employee_contribution, employer_contribution)
# Both employee and employer contribute 0.2% of insured wage (capped at RM4000).
# -----------------------------------------------------------------------------
EIS_2024_TABLE: list[tuple[float, float, float, float]] = [
	(0.00, 30.00, 0.05, 0.05),
	(30.01, 50.00, 0.10, 0.10),
	(50.01, 70.00, 0.15, 0.15),
	(70.01, 100.00, 0.20, 0.20),
	(100.01, 140.00, 0.25, 0.25),
	(140.01, 200.00, 0.35, 0.35),
	(200.01, 300.00, 0.50, 0.50),
	(300.01, 400.00, 0.70, 0.70),
	(400.01, 500.00, 0.90, 0.90),
	(500.01, 600.00, 1.10, 1.10),
	(600.01, 700.00, 1.30, 1.30),
	(700.01, 800.00, 1.50, 1.50),
	(800.01, 900.00, 1.70, 1.70),
	(900.01, 1000.00, 1.90, 1.90),
	(1000.01, 1100.00, 2.10, 2.10),
	(1100.01, 1200.00, 2.30, 2.30),
	(1200.01, 1300.00, 2.50, 2.50),
	(1300.01, 1400.00, 2.70, 2.70),
	(1400.01, 1500.00, 2.90, 2.90),
	(1500.01, 1600.00, 3.10, 3.10),
	(1600.01, 1700.00, 3.30, 3.30),
	(1700.01, 1800.00, 3.50, 3.50),
	(1800.01, 1900.00, 3.70, 3.70),
	(1900.01, 2000.00, 3.90, 3.90),
	(2000.01, 2100.00, 4.10, 4.10),
	(2100.01, 2200.00, 4.30, 4.30),
	(2200.01, 2300.00, 4.50, 4.50),
	(2300.01, 2400.00, 4.70, 4.70),
	(2400.01, 2500.00, 4.90, 4.90),
	(2500.01, 2600.00, 5.10, 5.10),
	(2600.01, 2700.00, 5.30, 5.30),
	(2700.01, 2800.00, 5.50, 5.50),
	(2800.01, 2900.00, 5.70, 5.70),
	(2900.01, 3000.00, 5.90, 5.90),
	(3000.01, 3100.00, 6.10, 6.10),
	(3100.01, 3200.00, 6.30, 6.30),
	(3200.01, 3300.00, 6.50, 6.50),
	(3300.01, 3400.00, 6.70, 6.70),
	(3400.01, 3500.00, 6.90, 6.90),
	(3500.01, 3600.00, 7.10, 7.10),
	(3600.01, 3700.00, 7.30, 7.30),
	(3700.01, 3800.00, 7.50, 7.50),
	(3800.01, 3900.00, 7.70, 7.70),
	(3900.01, 4000.00, 7.90, 7.90),
	(4000.01, float("inf"), 7.90, 7.90),
]


def _lookup_bracket(
	table: Iterable[tuple[float, float, float, float]],
	gross_pay: float,
	party: str,
) -> float:
	party_idx = 2 if party == "employee" else 3
	for wage_from, wage_to, ee, er in table:
		if wage_from <= gross_pay <= wage_to:
			return ee if party_idx == 2 else er
	return 0.0


def _age_on(dob: date | datetime | str | None, ref: date | None = None) -> int | None:
	if not dob:
		return None
	if isinstance(dob, str):
		try:
			dob = datetime.strptime(dob[:10], "%Y-%m-%d").date()
		except ValueError:
			logger.warning("[my_statutory] Unparseable DOB: %s", dob)
			return None
	if isinstance(dob, datetime):
		dob = dob.date()
	ref = ref or date.today()
	years = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
	return years


def get_epf(gross_pay: float, dob, party: str = "employee") -> float:
	"""EPF contribution per PERKESO/KWSP 2024 rules.

	Employee: 11% (0% if age >= 60).
	Employer: 13% if gross_pay <= 5000 else 12% (4% if age >= 60).
	Returns 0 if gross_pay < RM100.
	"""
	if not gross_pay or gross_pay < EPF_MIN_WAGE:
		return 0.0

	age = _age_on(dob)
	senior = age is not None and age >= EPF_SENIOR_AGE
	logger.info(
		"[my_statutory] EPF lookup gross_pay=%.2f party=%s age=%s",
		gross_pay,
		party,
		age,
	)

	if party == "employee":
		rate = 0.0 if senior else 0.11
	else:
		if senior:
			rate = 0.04
		else:
			rate = 0.13 if gross_pay <= 5000 else 0.12

	return round(gross_pay * rate, 2)


def get_socso(gross_pay: float, party: str = "employee") -> float:
	"""SOCSO Category 1 contribution from the 2024 PERKESO Schedule.

	Insured wage capped at RM4000. Employee SOCSO does not apply when
	gross_pay > RM5000 (Category 2 — employer-only contributes via EIS-equivalent
	invalidity scheme, handled elsewhere).
	"""
	if not gross_pay or gross_pay <= 0:
		return 0.0
	if party == "employee" and gross_pay > SOCSO_CATEGORY_1_CEILING:
		return 0.0

	insured = min(gross_pay, INSURED_WAGE_CAP)
	amount = _lookup_bracket(SOCSO_2024_TABLE, insured, party)
	logger.info(
		"[my_statutory] SOCSO lookup gross_pay=%.2f insured=%.2f party=%s amount=%.2f",
		gross_pay,
		insured,
		party,
		amount,
	)
	return round(amount, 2)


def get_eis(gross_pay: float, party: str = "employee") -> float:
	"""EIS contribution from the 2024 PERKESO Act 800 Schedule.

	Both employee and employer contribute 0.2% of insured wage (cap RM4000).
	"""
	if not gross_pay or gross_pay <= 0:
		return 0.0

	insured = min(gross_pay, INSURED_WAGE_CAP)
	amount = _lookup_bracket(EIS_2024_TABLE, insured, party)
	logger.info(
		"[my_statutory] EIS lookup gross_pay=%.2f insured=%.2f party=%s amount=%.2f",
		gross_pay,
		insured,
		party,
		amount,
	)
	return round(amount, 2)
