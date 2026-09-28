// The Calendar day sheet's team, grouped by status (owner, 28 Sep 2026: all of
// the team, grouped, five names then See all). The rows are the server's
// (hrms.api.team.member_statuses, the Team page's own rule); this only orders
// them, and never adds, drops or re-labels a member.

//: The order a manager reads a day in: who is here, who is not yet, then the rest.
const ORDER = ["Present", "Not In Yet", "Absent", "On Leave", "Off"]

export const DAY_TEAM_PREVIEW = 5

export function dayTeamGroups(members) {
	const groups = new Map()
	for (const member of members || []) {
		if (!groups.has(member.status)) groups.set(member.status, [])
		groups.get(member.status).push(member)
	}
	const rank = (status) => {
		const i = ORDER.indexOf(status)
		return i === -1 ? ORDER.length : i
	}
	const out = [...groups.entries()]
		.sort(([a], [b]) => rank(a) - rank(b))
		.map(([status, rows]) => ({ status, members: rows }))
	console.info("[dayTeamGroups]", out.map((g) => `${g.status}:${g.members.length}`).join(" "))
	return out
}
