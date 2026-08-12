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

// HR-only: managers with direct reports, for the "Team of" selector.
// Non-HR users receive [] and the selector stays hidden.
export const teamManagers = createResource({
	url: "hrms.api.team.get_managers",
	auto: true,
	cache: "hrms:team_managers",
})
