import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

// Team KPI is gated on DESIGNATION, not on a role: on this hub the approver
// role profile also carries the HR roles, so a role gate would have handed
// every HR user the whole company's appraisal scores. The server re-checks the
// designation on every read — this resource only decides whether to draw the tab.
export const canViewTeamKpi = createResource({
	url: "hrms.api.kpi.can_view_team_kpi",
	auto: true,
	// v2: this used to answer a BOOLEAN. It answers the TIER now
	// ("manager" | "ceo" | "hr"), and the cache is idb-backed and survives a
	// reload — so without a new key a returning manager hydrates `true`, which
	// is truthy but is not "manager", and their tab mislabels itself for one
	// paint. Bump the key whenever the SHAPE of the answer changes.
	cache: personalCacheKey("hrms:can_view_team_kpi:v2"),
	onError(error) {
		console.warn("[kpi] team-view gate probe failed:", error?.messages?.[0] || error)
	},
})

// One person's KRA detail — the My KPI layout pointed at somebody else. The
// only KPI endpoint that takes an employee, so it is the only one whose safety
// is by CHECK rather than by construction: hrms.api.kpi._require_kpi_read runs
// before a single row is read, and throws for anyone outside the caller's tier.
export const employeeKpi = createResource({
	url: "hrms.api.kpi.get_employee_kpi",
	onError(error) {
		console.warn("[kpi] employee detail failed:", error?.messages?.[0] || error)
	},
})

// ONE LEVEL of the department tree — the node's roll-up, the departments
// directly inside it, and the people standing in it. CEO and HR only; a
// manager's scope is people, not org structure, and the server refuses them.
export const departmentKpi = createResource({
	url: "hrms.api.kpi.get_department_kpi",
	onError(error) {
		console.warn("[kpi] department tree failed:", error?.messages?.[0] || error)
	},
})

// Read-only company scores by department; params (year, cycle, department)
// are set by the view before fetch.
export const teamKpi = createResource({
	url: "hrms.api.kpi.get_team_kpi",
	onError(error) {
		console.warn("[kpi] team view failed:", error?.messages?.[0] || error)
	},
})
