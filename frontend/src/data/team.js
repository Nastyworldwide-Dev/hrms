import { createResource } from "frappe-ui"

// nav gate: the Team entry under More renders only for users with direct reports
export const hasTeam = createResource({
	url: "hrms.api.team.has_team",
	auto: true,
	cache: "hrms:has_team",
})

// one day of team status; params set by the Team view before fetch
export const teamStatus = createResource({
	url: "hrms.api.team.get_team_status",
})
