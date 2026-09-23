// Group the Approvals list the way the owner approved it (23 Sep 2026):
// YOURS by department then kind; OTHER TEAMS by department and direct
// approver; one line per person per kind. Pure: the server already decided
// which rows exist and where each belongs (section, department,
// approver_name); this never drops or adds one.

//: Lines shown in a group before "See all".
export const GROUP_PREVIEW = 5
//: Lines added per "Show more" once a group is expanded. No infinite scroll.
export const PAGE_SIZE = 20

const byOldest = (a, b) => (a.oldest < b.oldest ? -1 : a.oldest > b.oldest ? 1 : 0)

function bucket(map, key, make) {
	if (!map.has(key)) map.set(key, make())
	return map.get(key)
}

//: One line per person per kind, oldest first.
function peopleOf(rows) {
	const people = new Map()
	for (const row of rows) {
		const person = bucket(people, row.employee || row.who, () => ({
			key: `${row.doctype}:${row.employee || row.who}`,
			who: row.who,
			kind: row.kind,
			doctype: row.doctype,
			rows: [],
			count: 0,
			hours: 0,
			oldest: row.modified,
		}))
		person.rows.push(row)
		person.count += 1
		person.hours += Number(row.hours) || 0
		if (row.modified < person.oldest) person.oldest = row.modified
	}
	return [...people.values()].sort(byOldest)
}

function kindsOf(rows) {
	const kinds = new Map()
	for (const row of rows) bucket(kinds, row.kind, () => []).push(row)
	return [...kinds.entries()]
		.map(([kind, list]) => {
			const people = peopleOf(list)
			return { key: kind, kind, count: list.length, people, oldest: people[0].oldest }
		})
		.sort(byOldest)
}

/**
 * @param {Array<object>} rows  get_waiting_for_me rows, any order
 * @returns {{total, yours: {count, departments}, other: {count, teams, startCollapsed}}}
 */
export function groupApprovals(rows) {
	const sorted = [...(rows || [])].sort((a, b) =>
		a.modified < b.modified ? -1 : a.modified > b.modified ? 1 : 0,
	)
	const yours = sorted.filter((row) => row.section === "yours")
	const other = sorted.filter((row) => row.section !== "yours")

	const departments = new Map()
	for (const row of yours) bucket(departments, row.department || "", () => []).push(row)
	const yourGroups = [...departments.entries()]
		.map(([name, list]) => ({
			key: `yours:${name}`,
			name,
			count: list.length,
			kinds: kindsOf(list),
			oldest: list[0].modified,
		}))
		.sort(byOldest)

	const teams = new Map()
	for (const row of other) {
		bucket(teams, `${row.department || ""}\u0000${row.approver_name || ""}`, () => []).push(row)
	}
	const teamGroups = [...teams.values()]
		.map((list) => ({
			key: `other:${list[0].department || ""}:${list[0].approver_name || ""}`,
			name: list[0].department || "",
			approverName: list[0].approver_name || "",
			count: list.length,
			// A team line lists people across kinds; the kind rides on each line.
			people: kindsOf(list)
				.flatMap((k) => k.people)
				.sort(byOldest),
			oldest: list[0].modified,
		}))
		.sort(byOldest)

	const otherLines = teamGroups.reduce((n, team) => n + team.people.length, 0)
	console.info(
		"[approvalGroups] grouped",
		sorted.length,
		"yours",
		yours.length,
		"other",
		other.length,
	)
	return {
		total: sorted.length,
		yours: { count: yours.length, departments: yourGroups },
		other: { count: other.length, teams: teamGroups, startCollapsed: otherLines > GROUP_PREVIEW },
	}
}

//: What a group shows now: five, then "See all"; expanded, twenty per page.
export function pageOf(lines, { expanded, pages }) {
	if (!expanded) {
		return { rows: lines.slice(0, GROUP_PREVIEW), seeAll: lines.length > GROUP_PREVIEW, left: 0 }
	}
	const rows = lines.slice(0, PAGE_SIZE * Math.max(1, pages))
	return { rows, seeAll: false, left: lines.length - rows.length }
}

function hoursText(hours) {
	const minutes = Math.round(hours * 60)
	const h = Math.floor(minutes / 60)
	const m = minutes % 60
	return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`
}

//: "Mohd Shazwan · 5 days · 14h 30m" for overtime; "Aisyah · 2 requests" else.
export function personLine(person, t) {
	if (person.doctype === "OT Request") {
		const days = person.count === 1 ? t("1 day") : t("{0} days", [person.count])
		return [person.who, days, person.hours ? hoursText(person.hours) : ""]
			.filter(Boolean)
			.join(" · ")
	}
	const count = person.count === 1 ? t("1 request") : t("{0} requests", [person.count])
	return `${person.who} · ${count}`
}
