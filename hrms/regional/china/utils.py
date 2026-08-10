# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import flt

logger = logging.getLogger(__name__)

# Social insurance rates and contribution-base bands are CITY-specific and
# revised annually (usually in July). The city is a formula argument, never a
# constant — add an entry here per city we hire in and update the bands each
# year. Shanghai figures below are the 2025/26 published band.
CITY_SOCIAL_INSURANCE = {
	"shanghai": {
		"base_floor": 7384,
		"base_cap": 36921,
		"rates": {
			"pension": {"employee": 0.08, "employer": 0.16},
			"medical": {"employee": 0.02, "employer": 0.095},
			"unemployment": {"employee": 0.005, "employer": 0.005},
			"injury": {"employee": 0.0, "employer": 0.0026},
			"housing_fund": {"employee": 0.07, "employer": 0.07},
		},
	},
}


def get_china_social_insurance(
	base, component: str, share: str = "employee", city: str = "shanghai"
) -> float:
	"""Monthly social insurance / housing fund contribution for a wage,
	clamped to the city's contribution-base band.

	Usable in Salary Component formulas, e.g.:
	    get_china_social_insurance(base, 'pension', 'employee', 'shanghai')
	"""
	city_config = CITY_SOCIAL_INSURANCE.get((city or "").strip().lower())
	if not city_config:
		frappe.throw(
			_("No China social insurance rates configured for city {0}. Known cities: {1}").format(
				city, ", ".join(sorted(CITY_SOCIAL_INSURANCE))
			)
		)
	rates = city_config["rates"].get(component)
	if not rates or share not in rates:
		frappe.throw(_("Unknown China social insurance component/share: {0}/{1}").format(component, share))

	wage = flt(base)
	if wage <= 0:
		return 0.0
	clamped = min(max(wage, city_config["base_floor"]), city_config["base_cap"])
	contribution = round(clamped * rates[share], 2)
	logger.debug(
		"[cn_payroll] city=%s component=%s share=%s wage=%s contribution=%s",
		city,
		component,
		share,
		wage,
		contribution,
	)
	return contribution
