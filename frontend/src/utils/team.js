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

// Day cells for the Team page's month picker (GCalendar). Dates are
// "YYYY-MM-DD" strings so this stays dayjs-free and node-testable. A team has
// no single per-day status, so the grid only marks the selected day (and
// today, when it is not the selected day) — never a present/leave tint.
export const buildTeamCalendarDays = (firstOfMonth, selectedDate, today) => {
	const month = firstOfMonth.slice(0, 7)
	const year = Number(month.slice(0, 4))
	const monthIndex = Number(month.slice(5, 7)) - 1
	const length = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate()
	const days = Array.from({ length }, (_, i) => {
		const day = i + 1
		const iso = `${month}-${String(day).padStart(2, "0")}`
		const state = iso === selectedDate ? "selected" : iso === today ? "today" : "none"
		return { day, state }
	})
	console.info("[team] calendar days:", month, length, "selected", selectedDate)
	return days
}

// One member's second line — the Team page's and the Calendar day sheet's
// shared words for a person's day (28 Sep 2026), so the two screens can never
// describe the same person differently. Pure: `__` translates, `fmt` formats
// (punch: a datetime to HH:mm, time: a shift time, day / shortDay: dates).
export function memberLine(member, __, fmt) {
	if (member.status === "On Leave") {
		const type = __(member.leave_type, null, "Leave Type")
		return `${type} · ${__("until")} ${fmt.shortDay(member.leave_until)}`
	}
	if (member.first_in || member.last_out) {
		// A check-out after midnight says so (owner, 26 Sep 2026): it belongs
		// to this work day, and "OUT 01:41" alone read as a missed check-out.
		const out = fmt.punch(member.last_out)
		return `${__("IN")} ${fmt.punch(member.first_in)} · ${__("OUT")} ${
			member.out_next_day ? __("{0} (next day)", [out]) : out
		}`
	}
	if (member.counted_on) {
		return __("Worked past midnight · counted on {0}", [fmt.day(member.counted_on)])
	}
	if (member.status === "Not In Yet" && member.shift_start) {
		return `${__("Shift")} ${fmt.time(member.shift_start)}–${fmt.time(member.shift_end)} · ${__(
			"no punch yet"
		)}`
	}
	if (member.status === "Absent") return __("No punch · no leave filed")
	return __(member.status)
}
