// Pure grouping for the Team page — kept free of Vue so it stays testable
// with node --test (frontend/tests/team-grouping.test.mjs).
//
// Grouping is PRESENTATION ONLY: the member set is exactly what
// get_team_status returned (reports_to assignment, the authority rule), and
// this must never add, drop, or reorder-across members — the test pins that.

export const UNASSIGNED_DEPARTMENT = "No Department"

// The "Team of" selector's option tree (HR request 2026-08-19): "My team"
// pinned first as its own label-less group, then managers grouped by
// department (alphabetical, No Department last — groupByDepartment's rule),
// each labelled "Name · team size". Shaped for frappe-ui's Autocomplete,
// which renders {group, items} natively and searches across labels.
export const buildManagerOptions = (managers, myTeamLabel = "My team") => {
	const pinned = {
		group: myTeamLabel,
		hideLabel: true,
		items: [{ label: myTeamLabel, value: "" }],
	}
	const grouped = groupByDepartment(managers).map(({ department, members }) => ({
		group: department,
		items: members.map((manager) => ({
			label: manager.team_size
				? `${manager.employee_name} · ${manager.team_size}`
				: manager.employee_name,
			value: manager.name,
		})),
	}))
	console.info("[team] manager options:", grouped.length, "department group(s)")
	return [pinned, ...grouped]
}

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
