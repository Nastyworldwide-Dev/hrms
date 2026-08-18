// Pure grouping for the Team page — kept free of Vue so it stays testable
// with node --test (frontend/tests/team-grouping.test.mjs).
//
// Grouping is PRESENTATION ONLY: the member set is exactly what
// get_team_status returned (reports_to assignment, the authority rule), and
// this must never add, drop, or reorder-across members — the test pins that.

export const UNASSIGNED_DEPARTMENT = "No Department"

export const groupByDepartment = (members) => {
	const groups = new Map()
	for (const member of members || []) {
		const key = member.department || UNASSIGNED_DEPARTMENT
		if (!groups.has(key)) groups.set(key, [])
		groups.get(key).push(member)
	}
	// alphabetical sections, unassigned last; members keep the server's order
	return [...groups.entries()]
		.sort(([a], [b]) =>
			a === UNASSIGNED_DEPARTMENT ? 1 : b === UNASSIGNED_DEPARTMENT ? -1 : a.localeCompare(b)
		)
		.map(([department, rows]) => ({ department, members: rows }))
}
