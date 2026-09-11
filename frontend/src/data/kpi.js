import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

// Team KPI is gated on DESIGNATION, not on a role: on this hub the approver
// role profile also carries the HR roles, so a role gate would have handed
// every HR user the whole company's appraisal scores. The server re-checks the
// designation on every read — this resource only decides whether to draw the tab.
export const canViewTeamKpi = createResource({
	url: "hrms.api.kpi.can_view_team_kpi",
	auto: true,
	cache: personalCacheKey("hrms:can_view_team_kpi"),
	onError(error) {
		console.warn("[kpi] team-view gate probe failed:", error?.messages?.[0] || error)
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
