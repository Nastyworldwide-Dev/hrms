// What the Approvals page needs to filter, pick and approve many at once (HR,
// 4 Oct 2026: "filter by request and bulk approve"; owner, 5 Oct: no export,
// banner only, phone and desktop; owner rulings 8 Oct 2026: only the approver's own
// requests, ticks always shown, reject in bulk, up to 100 at once). Pure: the server
// (approval.check_many / decide_many / reject_many) decides what may be decided; this
// only keeps the page's own bookkeeping honest.
// Tests: utils/__tests__/approvalBulk.test.js

//: Most one action takes (owner ruling 8 Oct 2026, was 50). Over it, the page asks the
//: approver to untick some before it ever calls the server.
export const BULK_CAP = 100

//: Most one call to the server carries. The server refuses a call over
//: hrms.api.approval.BULK_CAP = 50 and a long call risks a request timeout, so the page sends
//: the ticked requests ten at a time (check_many, decide_many and reject_many alike).
export const CHUNK_SIZE = 10

//: A line turns amber from this many days waiting, red from the second number.
export const AMBER_DAYS = 7
export const RED_DAYS = 14

//: Request types that are NOT decided in bulk: a check-in has its own sheet and
//: path (Remote Checkin Request). They stay one by one.
const ONE_BY_ONE = ["Remote Checkin Request"]

//: A request can be ticked unless it is a check-in (its own sheet). Ticks are always drawn on a
//: tickable row since 8 Oct 2026, so Select all follows the same rule and ticks nothing unseen.
export const canBulk = (row) => !ONE_BY_ONE.includes(row.doctype)

//: Owner ruling 8 Oct 2026: the page lists only requests sent to the approver. The server stopped
//: sending the others; a personal cache written before that can still hold them.
export const onlyYours = (rows) => (rows || []).filter((row) => row.section === "yours")

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

//: "Time off (8)": the chip's words (owner, 8 Oct 2026).
export const chipLabel = (chip, t) => `${chip.key ? t(chip.label) : t("All")} (${chip.count})`

const day = (value) => String(value || "").slice(0, 10)
const personOf = (row) => row.employee || row.who

//: Does the request's own date range [from_date, to_date] touch [from, to]? A request with one
//: date is that one day; with none it is kept only when no date filter is set.
function overlaps(row, from, to) {
	if (!from && !to) return true
	const start = day(row.from_date) || day(row.to_date)
	if (!start) return false
	const end = day(row.to_date) || start
	return (!to || start <= to) && (!from || end >= from)
}

//: Every filter of the page together: type, department, employee and a date range (ISO dates).
export function filterRows(
	rows,
	{ kind = "", department = "", employee = "", from = "", to = "" } = {}
) {
	return rows.filter(
		(row) =>
			(!kind || row.kind === kind) &&
			(!department || row.department === department) &&
			(!employee || personOf(row) === employee) &&
			overlaps(row, from, to)
	)
}

const byLabel = (a, b) => (a.label < b.label ? -1 : a.label > b.label ? 1 : 0)

//: Choices for the Filter sheet, built from the rows that are loaded.
export const departmentOptions = (rows) =>
	[...new Set(rows.map((row) => row.department).filter(Boolean))]
		.map((name) => ({ label: name, value: name }))
		.sort(byLabel)

export const employeeOptions = (rows) => {
	const people = new Map()
	for (const row of rows) if (personOf(row)) people.set(personOf(row), row.who || personOf(row))
	return [...people.entries()].map(([value, label]) => ({ label, value })).sort(byLabel)
}

//: How many filters are on, for the button: department, employee, and the dates as one.
export const activeFilters = ({ department, employee, from, to }) =>
	[department, employee, from || to].filter(Boolean).length

//: A department or employee that is no longer in the list is dropped from the filters, so the page
//: never sits empty behind a filter nobody can see. The employee is looked for inside the department.
export function pruneFilters(filters, rows) {
	const department = departmentOptions(rows).some((o) => o.value === filters.department)
		? filters.department
		: ""
	const inDepartment = filterRows(rows, { department })
	const employee = employeeOptions(inDepartment).some((o) => o.value === filters.employee)
		? filters.employee
		: ""
	return { ...filters, department, employee }
}

//: "3 Time off · 2 Overtime": what the confirm sheet is about, biggest type first.
export function kindSummary(rows, t) {
	const counts = new Map()
	for (const row of rows) counts.set(row.kind, (counts.get(row.kind) || 0) + 1)
	return [...counts.entries()]
		.sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))
		.map(([kind, count]) => `${count} ${t(kind)}`)
		.join(" · ")
}

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
//: At most BULK_CAP, the oldest first (the order the list shows): Select all on 150 used to tick
//: all 150 and refuse only at Approve (review of b47084495). The page says how many it left.
export function toggleAll(selected, rows) {
	const pickable = capped(rows)
	const next = new Set(selected)
	const all = pickable.length > 0 && pickable.every((row) => next.has(rowKey(row)))
	for (const row of pickable) all ? next.delete(rowKey(row)) : next.add(rowKey(row))
	return next
}

const capped = (rows) => rows.filter(canBulk).slice(0, BULK_CAP)

//: How many tickable rows Select all leaves out because of the cap.
export const leftOver = (rows) => Math.max(0, rows.filter(canBulk).length - BULK_CAP)

//: Selection state of the "Select all" control: "none" | "some" | "all"
export function allState(selected, rows) {
	const pickable = capped(rows)
	const ticked = pickable.filter((row) => selected.has(rowKey(row))).length
	return ticked === 0 ? "none" : ticked === pickable.length ? "all" : "some"
}

//: Ticks that are no longer shown (another chip, a request that left) are dropped, so the bar never
//: counts, and Approve never sends, a request the approver cannot see ticked.
export function keepVisible(selected, shownRows) {
	return prune(selected, shownRows)
}

//: A filter where nothing can be ticked (only check-ins): the page says why.
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

//: A list in pieces of `size`, in order; nothing lost, the last piece may be shorter.
export function chunks(list, size = CHUNK_SIZE) {
	const parts = []
	for (let at = 0; at < list.length; at += size) parts.push(list.slice(at, at + size))
	return parts
}

//: Send `items` to the server one piece at a time, in order, and merge the answers:
//: {done: what `doneKey` ("ready", "approved" or "rejected") listed, refused}. `onProgress(finished,
//: total)` is called before the first piece and as each piece comes back, so it counts only what the
//: server answered. A piece that throws stops the rest and the error goes to the caller: what went
//: through is then unknown, so nothing is guessed here.
export async function sendInChunks(items, send, doneKey, onProgress = () => {}) {
	const done = []
	const refused = []
	let finished = 0
	onProgress(finished, items.length)
	for (const part of chunks(items)) {
		const result = await send(part)
		finished += part.length
		onProgress(finished, items.length)
		done.push(...(result?.[doneKey] || []))
		refused.push(...(result?.refused || []))
	}
	return { done, refused }
}

//: The reason that applies to one request: its own if written, else the shared one.
export const effectiveReason = (own, shared) =>
	String(own || "").trim() || String(shared || "").trim()

//: Reject stays off until every request has a reason (own or shared). `own` is keyed by rowKey.
export const canReject = (items, shared, own) =>
	items.length > 0 && items.every((item) => effectiveReason(own[rowKey(item)], shared) !== "")

//: The `reason` sent beside the items: the typed shared one, else the first request's own, so the
//: call never carries an empty reason when every request has one of its own.
export const sharedFor = (items, shared) => String(shared || "").trim() || items[0]?.reason || ""

//: The items to send: the revision the approver saw, and the reason that applies to each.
export const rejectItems = (items, shared, own) =>
	items.map((item) => ({ ...item, reason: effectiveReason(own[rowKey(item)], shared) }))

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

//: After decide_many / reject_many: which ticked requests are still waiting (refused), and what to
//: tell the approver. `result` = {approved: [...], refused: [{name, doctype, reason}]}; for a
//: rejection the page passes what was rejected as `approved` (the rule is the same).
export function afterApprove(selected, result) {
	const done = new Set((result.approved || []).map((row) => rowKey(row)))
	const left = new Set([...selected].filter((key) => !done.has(key)))
	return {
		selected: left,
		approved: (result.approved || []).length,
		refused: result.refused || [],
	}
}

const plural = (t, n, one, many) => (Number(n) === 1 ? t(one) : t(many, [n]))
const number = (n) => String(Math.round(Number(n) * 10) / 10)

//: What a request is, on its row's second line (owner, 8 Oct 2026; the name and the dates stay in
//: the label). Parts that are absent are left out. A row from a cache older than the new row keys
//: reads as the server's own `detail`.
//: Time off "Annual Leave · 2 days · Half day · 3 left after · File"; Overtime "3h 30m · <note>";
//: Expense "MYR 120.00 · 3 items · Travel, Meals · Receipt"; Shift change "Morning → Night";
//: Fix a day "Work From Home · 09:00–18:00".
export function rowDetails(row, t) {
	const detail = row.detail || ""
	let parts = [detail]
	if (row.doctype === "Leave Application" && row.days != null) {
		// the server's detail is "<leave type> · …" and, for a half day, "… · Half day · AM"
		const segments = detail.split(" · ")
		const session = segments.find((s) => s === "AM" || s === "PM")
		const half = row.half_day ? [session ? `${t("Half day")} · ${session}` : t("Half day")] : []
		const days = Number(row.days)
		parts = [
			segments[0],
			// a single half day is already said by "Half day"
			...(row.half_day && days <= 0.5 ? [] : [plural(t, number(days), "1 day", "{0} days")]),
			...half,
			row.balance_after != null ? t("{0} left after", [number(row.balance_after)]) : "",
			row.attached ? t("File") : "",
		]
	} else if (row.doctype === "OT Request") {
		parts = [detail, row.reason]
	} else if (row.doctype === "Expense Claim" && row.items != null) {
		parts = [
			detail,
			row.items ? plural(t, row.items, "1 item", "{0} items") : "",
			(row.expense_types || []).join(", "),
			row.attached ? t("Receipt") : "",
		]
	} else if (row.doctype === "Shift Request" && (row.new_shift || row.current_shift)) {
		parts = [
			row.current_shift && row.new_shift
				? `${row.current_shift} → ${row.new_shift}`
				: row.new_shift || detail,
		]
	} else if (row.doctype === "Attendance Request") {
		const { in_time: inTime, out_time: outTime } = row
		parts = [
			detail,
			inTime && outTime
				? `${inTime}–${outTime}`
				: inTime
				? `${t("In")} ${inTime}`
				: outTime
				? `${t("Out")} ${outTime}`
				: "",
		]
	}
	return parts.filter(Boolean).join(" · ")
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
