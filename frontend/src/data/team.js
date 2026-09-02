import { createResource } from "frappe-ui"

// nav gate: the Team entry under More renders only for users with direct reports
export const hasTeam = createResource({
	url: "hrms.api.team.has_team",
	auto: true,
	cache: "hrms:has_team",
})

// gate for the RequestPanel's Team tabs: true when ANY approval work can
// route here (HR, direct reports, or named in an approver field/table).
// Deliberately not hasTeam — an assigned approver may manage nobody.
export const isApprover = createResource({
	url: "hrms.api.team.is_approver",
	auto: true,
	cache: "hrms:is_approver",
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

// The Nadi Team Roster grid: direct reports + their shifts across a week.
// params (start_date, end_date, manager?) set by the view before fetch.
export const teamRoster = createResource({
	url: "hrms.api.team.get_team_roster",
})

// Assign a shift to a team member. The server fences every write to the
// caller's own reports + company (hrms.api.roster._ensure_can_roster), so the
// UI never has to be the security boundary.
export const assignShift = createResource({
	url: "hrms.api.roster.insert_shift",
})
