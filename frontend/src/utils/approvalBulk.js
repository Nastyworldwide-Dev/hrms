// What the Approvals page needs to filter, pick and approve many at once (HR,
// 4 Oct 2026: "filter by request and bulk approve"; owner, 5 Oct: no export,
// banner only, phone and desktop). Pure: the server (approval.check_many /
// decide_many) decides what may be approved; this only keeps the page's own
// bookkeeping honest. Tests: views/__tests__/approvals-bulk.test.js

//: Most one bulk call carries (hrms.api.approval.BULK_CAP). Over it, the page
//: asks the approver to untick some before it ever calls the server.
export const BULK_CAP = 50

//: A line turns amber from this many days waiting, red from the second number.
export const AMBER_DAYS = 7
export const RED_DAYS = 14

//: Request types that are NOT decided in bulk: a check-in has its own sheet and
//: path (Remote Checkin Request). They stay one by one.
const ONE_BY_ONE = ["Remote Checkin Request"]

//: A request can be ticked only when the approver can SEE a tick on it: select mode draws ticks on
//: the Yours section only (Other teams are someone else's to decide first), and a check-in has its
//: own sheet. Select all must follow the same rule or it ticks rows nobody can see.
export const canBulk = (row) => !ONE_BY_ONE.includes(row.doctype) && row.section === "yours"

//: Today's calendar day IN THE SITE'S TIME ZONE ("2026-10-06"), not UTC's. The page used the UTC
//: date, so an approver at UTC+8 between midnight and 8 am saw every wait one day short. A zone
//: the browser does not know falls back to the browser's own day instead of throwing.
export function siteToday(now = new Date(), timeZone = "") {
	try {
		return new Intl.DateTimeFormat("en-CA", { timeZone: timeZone || undefined }).format(now)
	} catch {
		return new Intl.DateTimeFormat("en-CA").format(now)
	}
}

// whole days between two dates, by the calendar (never negative)
export function daysWaiting(since, today) {
	const a = Date.UTC(...ymd(since))
	const b = Date.UTC(...ymd(today))
	return Math.max(0, Math.round((b - a) / 86400000))
}

function ymd(value) {
	const [y, m, d] = String(value).slice(0, 10).split("-").map(Number)
	return [y, m - 1, d]
}

//: "calm" | "amber" | "red": how long this request has been waiting
export function ageTone(days) {
	return days >= RED_DAYS ? "red" : days >= AMBER_DAYS ? "amber" : "calm"
}

//: Chips: [{key, label, count}], "All" first, then each kind that has requests.
export function typeChips(rows) {
	const counts = new Map()
	for (const row of rows) counts.set(row.kind, (counts.get(row.kind) || 0) + 1)
	return [
		{ key: "", label: "All", count: rows.length },
		...[...counts.entries()]
			.sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))
			.map(([kind, count]) => ({ key: kind, label: kind, count })),
	]
}

export const filterByKind = (rows, kind) => (kind ? rows.filter((row) => row.kind === kind) : rows)

//: The id one request is ticked by (doctype + name: a name can repeat across types).
export const rowKey = (row) => `${row.doctype}::${row.name}`

//: Tick or untick one request. Never ticks one that is not decided in bulk.
export function toggle(selected, row) {
	if (!canBulk(row)) return selected
	const next = new Set(selected)
	const key = rowKey(row)
	next.has(key) ? next.delete(key) : next.add(key)
	return next
}

//: "Select all in this filter": every row of the filter that can be ticked; if
//: they are all ticked already, untick them (and only them).
export function toggleAll(selected, rows) {
	const pickable = rows.filter(canBulk)
	const next = new Set(selected)
	const all = pickable.length > 0 && pickable.every((row) => next.has(rowKey(row)))
	for (const row of pickable) all ? next.delete(rowKey(row)) : next.add(rowKey(row))
	return next
}

//: Selection state of the "Select all" control: "none" | "some" | "all"
export function allState(selected, rows) {
	const pickable = rows.filter(canBulk)
	const ticked = pickable.filter((row) => selected.has(rowKey(row))).length
	return ticked === 0 ? "none" : ticked === pickable.length ? "all" : "some"
}

//: Ticks that are no longer shown (another chip, a request that left) are dropped, so the bar never
//: counts, and Approve never sends, a request the approver cannot see ticked.
export function keepVisible(selected, shownRows) {
	return prune(selected, shownRows)
}

//: A filter where nothing can be ticked (only check-ins, or only Other teams): the page says why.
export const nothingTickable = (rows) => rows.length > 0 && !rows.some(canBulk)

//: A request that left the list (decided, or gone) is no longer ticked.
export function prune(selected, rows) {
	const live = new Set(rows.map(rowKey))
	return new Set([...selected].filter((key) => live.has(key)))
}

//: The rows to send to the server: only ticked ones, with the revision the
//: approver saw (`modified`), in the order the list shows them.
export function itemsFor(selected, rows) {
	return rows
		.filter((row) => selected.has(rowKey(row)))
		.map((row) => ({ doctype: row.doctype, name: row.name, modified: row.modified }))
}

//: Plain words under the sticky bar.
export const overCap = (selected) => selected.size > BULK_CAP

//: The banner above the list. null when nothing waits.
export function banner(rows, today) {
	if (!rows.length) return null
	const oldest = rows.reduce((a, b) => (a.modified < b.modified ? a : b)).modified
	return {
		count: rows.length,
		oldest: String(oldest).slice(0, 10),
		days: daysWaiting(oldest, today),
	}
}

//: After decide_many: which ticked requests are still waiting (refused), and
//: what to tell the approver. `result` = {approved: [...], refused: [{name, doctype, reason}]}
export function afterApprove(selected, result) {
	const done = new Set((result.approved || []).map((row) => rowKey(row)))
	const left = new Set([...selected].filter((key) => !done.has(key)))
	return {
		selected: left,
		approved: (result.approved || []).length,
		refused: result.refused || [],
	}
}

//: Search for the Table view: a name or a kind, ignoring case and extra spaces.
export function searchRows(rows, text) {
	const needle = String(text || "")
		.trim()
		.toLowerCase()
	if (!needle) return rows
	return rows.filter((row) => `${row.who} ${row.kind}`.toLowerCase().includes(needle))
}

const SORT_KEYS = { date: "modified", who: "who", kind: "kind" }

//: Sort for the Table view. A copy: the list the groups read is never reordered. Equal values
//: keep their order (the sort is stable), so a re-sort does not shuffle the list.
export function sortRows(rows, column, direction = 1) {
	const key = SORT_KEYS[column]
	if (!key) return rows
	return [...rows].sort((a, b) => (a[key] < b[key] ? -1 : a[key] > b[key] ? 1 : 0) * direction)
}
