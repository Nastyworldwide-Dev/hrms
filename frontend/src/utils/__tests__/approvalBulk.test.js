// What the Approvals page keeps for filter, pick and bulk approve (HR, 4 Oct
// 2026; owner, 5 Oct: no export, banner only). Pure helpers: the server decides
// what may be approved, this keeps the page's own bookkeeping honest.
import { test } from "node:test"
import assert from "node:assert/strict"
import {
	AMBER_DAYS,
	BULK_CAP,
	CHUNK_SIZE,
	RED_DAYS,
	activeFilters,
	afterApprove,
	ageTone,
	allState,
	banner,
	canBulk,
	canReject,
	chipLabel,
	chunks,
	daysWaiting,
	departmentOptions,
	effectiveReason,
	employeeOptions,
	filterRows,
	kindSummary,
	onlyYours,
	pruneFilters,
	rejectItems,
	sharedFor,
	rowDetails,
	sendInChunks,
	siteToday,
	searchRows,
	keepVisible,
	nothingTickable,
	sortRows,
	filterByKind,
	itemsFor,
	overCap,
	prune,
	rowKey,
	toggle,
	toggleAll,
	typeChips,
} from "../approvalBulk.js"

const leave = (name, modified = "2026-08-17 09:00:00") => ({
	section: "yours",
	doctype: "Leave Application",
	name,
	kind: "Time off",
	modified,
})
const ot = (name) => ({
	section: "yours",
	doctype: "OT Request",
	name,
	kind: "Overtime",
	modified: "2026-09-01 09:00:00",
})
const checkin = (name) => ({
	section: "yours",
	doctype: "Remote Checkin Request",
	name,
	kind: "Check-in outside the area",
	modified: "2026-09-02 08:47:00",
})

test("the page takes up to 100 at once, sent 10 at a time (owner ruling 8 Oct 2026; was 50 in one call)", () => {
	// the server still refuses a call of more than hrms.api.approval.BULK_CAP = 50, so the page
	// never sends more than CHUNK_SIZE in one call
	assert.equal(BULK_CAP, 100)
	assert.equal(CHUNK_SIZE, 10)
	assert.ok(CHUNK_SIZE <= 50)
})

test("days waiting is counted by the calendar, never negative", () => {
	assert.equal(daysWaiting("2026-08-17 09:00:00", "2026-10-05"), 49)
	assert.equal(daysWaiting("2026-10-05 23:59:00", "2026-10-05"), 0)
	assert.equal(daysWaiting("2026-10-06", "2026-10-05"), 0)
})

test("a line turns amber at 7 days and red at 14", () => {
	assert.equal([AMBER_DAYS, RED_DAYS].join(), "7,14")
	assert.equal(ageTone(6), "calm")
	assert.equal(ageTone(7), "amber")
	assert.equal(ageTone(13), "amber")
	assert.equal(ageTone(14), "red")
})

test("chips: All first with the total, then each kind, biggest first", () => {
	const chips = typeChips([leave("A"), leave("B"), ot("C")])
	assert.deepEqual(chips, [
		{ key: "", label: "All", count: 3 },
		{ key: "Time off", label: "Time off", count: 2 },
		{ key: "Overtime", label: "Overtime", count: 1 },
	])
})

test("filtering by a kind keeps only that kind; no kind keeps everything", () => {
	const rows = [leave("A"), ot("B"), leave("C")]
	assert.deepEqual(
		filterByKind(rows, "Time off").map((r) => r.name),
		["A", "C"]
	)
	assert.equal(filterByKind(rows, "").length, 3)
})

test("a check-in request is never decided in bulk", () => {
	assert.equal(canBulk(checkin("X")), false)
	assert.equal(canBulk(leave("A")), true)
	assert.equal(toggle(new Set(), checkin("X")).size, 0)
})

test("a tick is keyed by type and name, so two types may share a name", () => {
	assert.notEqual(rowKey(leave("A")), rowKey(ot("A")))
	let selected = toggle(new Set(), leave("A"))
	selected = toggle(selected, ot("A"))
	assert.equal(selected.size, 2)
	selected = toggle(selected, leave("A"))
	assert.equal(selected.size, 1)
})

test("select all in this filter ticks every pickable row and skips check-ins", () => {
	const rows = [leave("A"), ot("B"), checkin("C")]
	const selected = toggleAll(new Set(), rows)
	assert.equal(selected.size, 2)
	assert.equal(allState(selected, rows), "all")
})

test("select all again unticks only that filter's rows", () => {
	const filtered = [leave("A")]
	const other = ot("B")
	const selected = toggleAll(toggle(new Set(), other), filtered)
	assert.equal(selected.size, 2)
	const after = toggleAll(selected, filtered)
	assert.deepEqual([...after], [rowKey(other)])
})

test("the select-all control says none, some or all", () => {
	const rows = [leave("A"), leave("B")]
	assert.equal(allState(new Set(), rows), "none")
	assert.equal(allState(toggle(new Set(), rows[0]), rows), "some")
	assert.equal(allState(toggleAll(new Set(), rows), rows), "all")
	assert.equal(allState(new Set(), [checkin("C")]), "none")
})

test("a request that left the list is no longer ticked", () => {
	const selected = toggleAll(new Set(), [leave("A"), leave("B")])
	assert.deepEqual([...prune(selected, [leave("B")])], [rowKey(leave("B"))])
})

test("what is sent is only the ticked rows, with the revision the approver saw", () => {
	const rows = [leave("A", "2026-08-17 09:00:00"), ot("B"), leave("C")]
	const selected = toggle(toggle(new Set(), rows[0]), rows[1])
	assert.deepEqual(itemsFor(selected, rows), [
		{ doctype: "Leave Application", name: "A", modified: "2026-08-17 09:00:00" },
		{ doctype: "OT Request", name: "B", modified: "2026-09-01 09:00:00" },
	])
})

test("more than the cap is caught before the server is asked", () => {
	const many = new Set(Array.from({ length: BULK_CAP + 1 }, (_, i) => `k${i}`))
	assert.equal(overCap(many), true)
	assert.equal(overCap(new Set(["a"])), false)
})

test("the banner says how many wait and how long the oldest has", () => {
	assert.equal(banner([], "2026-10-05"), null)
	assert.deepEqual(banner([leave("A", "2026-08-17 09:00:00"), ot("B")], "2026-10-05"), {
		count: 2,
		oldest: "2026-08-17",
		days: 49,
	})
})

test("after approving, what was refused stays ticked and listed with its reason", () => {
	const rows = [leave("A"), leave("B"), leave("C")]
	const selected = toggleAll(new Set(), rows)
	const result = {
		approved: [{ doctype: "Leave Application", name: "A" }],
		refused: [{ doctype: "Leave Application", name: "B", reason: "No balance left." }],
	}
	const after = afterApprove(selected, result)
	assert.equal(after.approved, 1)
	assert.deepEqual(after.refused, result.refused)
	assert.equal(after.selected.has(rowKey(leave("A"))), false)
	assert.equal(after.selected.has(rowKey(leave("B"))), true)
})

test("today is the SITE's calendar day, not UTC's: 7:30 am Tuesday in Malaysia is still Monday in UTC", () => {
	// the page used new Date().toISOString().slice(0, 10), which is the UTC date. For an approver
	// at UTC+8 between midnight and 8 am every wait read one day short (and a request sent
	// late on Monday read "Today" on Tuesday morning).
	assert.equal(siteToday(new Date("2026-10-05T23:30:00Z"), "Asia/Kuala_Lumpur"), "2026-10-06")
	assert.equal(siteToday(new Date("2026-10-05T23:30:00Z"), "UTC"), "2026-10-05")
	assert.equal(siteToday(new Date("2026-10-05T16:00:00Z"), "Asia/Kuala_Lumpur"), "2026-10-06")
	assert.equal(siteToday(new Date("2026-10-05T15:59:00Z"), "Asia/Kuala_Lumpur"), "2026-10-05")
})

test("a bad time zone falls back to the browser's day instead of throwing", () => {
	assert.match(siteToday(new Date("2026-10-05T12:00:00Z"), "Not/AZone"), /^\d{4}-\d{2}-\d{2}$/)
	assert.match(siteToday(new Date("2026-10-05T12:00:00Z"), ""), /^\d{4}-\d{2}-\d{2}$/)
})

test("a request sent late on Monday has waited one day by Tuesday morning at site time", () => {
	const today = siteToday(new Date("2026-10-05T23:30:00Z"), "Asia/Kuala_Lumpur")
	assert.equal(daysWaiting("2026-10-05 23:30:00", today), 1)
})

// ---- the desktop Table view: search and sort over the same rows ----

const named = (name, who, kind, modified, when = "") => ({
	doctype: "Leave Application",
	name,
	who,
	kind,
	modified,
	when,
	detail: "",
})

test("search matches a name or a kind, ignoring case and extra spaces", () => {
	const rows = [
		named("A", "Ahmad Fazwan", "Time off", "2026-08-17 09:00:00"),
		named("B", "Nurul Ain", "Overtime", "2026-08-18 09:00:00"),
	]
	assert.deepEqual(
		searchRows(rows, "  fazwan ").map((r) => r.name),
		["A"]
	)
	assert.deepEqual(
		searchRows(rows, "OVERTIME").map((r) => r.name),
		["B"]
	)
	assert.equal(searchRows(rows, "").length, 2)
	assert.equal(searchRows(rows, "zzz").length, 0)
})

test("sorting by waiting since puts the oldest first, or last when reversed", () => {
	const rows = [
		named("new", "B", "Time off", "2026-09-30 09:00:00"),
		named("old", "A", "Time off", "2026-08-17 09:00:00"),
	]
	assert.deepEqual(
		sortRows(rows, "date", 1).map((r) => r.name),
		["old", "new"]
	)
	assert.deepEqual(
		sortRows(rows, "date", -1).map((r) => r.name),
		["new", "old"]
	)
})

test("sorting by person is alphabetical and does not touch the original list", () => {
	const rows = [named("1", "Zainab", "Time off", "x"), named("2", "Aisyah", "Time off", "y")]
	assert.deepEqual(
		sortRows(rows, "who", 1).map((r) => r.who),
		["Aisyah", "Zainab"]
	)
	assert.deepEqual(
		rows.map((r) => r.who),
		["Zainab", "Aisyah"]
	)
})

test("sorting by an unknown column keeps the order given", () => {
	const rows = [named("1", "B", "k", "x"), named("2", "A", "k", "y")]
	assert.deepEqual(
		sortRows(rows, "nope", 1).map((r) => r.name),
		["1", "2"]
	)
})

test("equal values keep their order, so the list does not shuffle on a re-sort", () => {
	const rows = [
		named("1", "Same", "k", "x"),
		named("2", "Same", "k", "x"),
		named("3", "Same", "k", "x"),
	]
	assert.deepEqual(
		sortRows(rows, "who", 1).map((r) => r.name),
		["1", "2", "3"]
	)
})

// ---- ticks follow what the approver can SEE (design + code review, 5 Oct 2026) ----

const yours = (name, kind = "Time off") => ({
	doctype: "Leave Application",
	name,
	kind,
	section: "yours",
	modified: "2026-08-17 09:00:00",
})
const theirs = (name) => ({ ...yours(name), section: "other" })

test("Other teams is gone (owner ruling 8 Oct 2026): rows not sent to the approver never reach the page", () => {
	// a personal cache written before the server stopped sending them can still hold such rows
	const rows = [yours("A"), theirs("B")]
	assert.deepEqual(
		onlyYours(rows).map((r) => r.name),
		["A"]
	)
	const ticked = toggleAll(new Set(), onlyYours(rows))
	assert.deepEqual([...ticked], [rowKey(yours("A"))])
})

test("a request is tickable unless it is a check-in (ticks always show since 8 Oct 2026)", () => {
	assert.equal(canBulk(yours("A")), true)
	assert.equal(canBulk({ ...yours("A"), doctype: "Remote Checkin Request" }), false)
})

test("changing the filter drops ticks that are no longer shown", () => {
	const rows = [yours("A"), yours("B", "Overtime")]
	const ticked = toggleAll(new Set(), rows)
	assert.equal(ticked.size, 2)
	const shown = rows.filter((r) => r.kind === "Overtime")
	assert.deepEqual([...keepVisible(ticked, shown)], [rowKey(yours("B", "Overtime"))])
})

test("what is sent is only what is ticked AND shown", () => {
	const rows = [yours("A"), yours("B", "Overtime")]
	const ticked = toggleAll(new Set(), rows)
	const shown = rows.filter((r) => r.kind === "Overtime")
	assert.deepEqual(
		itemsFor(keepVisible(ticked, shown), shown).map((i) => i.name),
		["B"]
	)
})

test("a filter with nothing tickable says so", () => {
	// only check-ins left: nothing to tick (Other teams no longer exists to be "nothing tickable" too)
	assert.equal(nothingTickable([{ ...yours("A"), doctype: "Remote Checkin Request" }]), true)
	assert.equal(nothingTickable([yours("A")]), false)
	assert.equal(nothingTickable([]), false)
})

// ---- bulk v2 (owner rulings 8 Oct 2026) ----

const tr = (text, args = []) => text.replace(/\{(\d+)\}/g, (_, i) => args[i])

test("chunks cut a list into pieces of ten, the last one shorter, and never lose an item", () => {
	const list = Array.from({ length: 25 }, (_, i) => i)
	assert.deepEqual(
		chunks(list).map((c) => c.length),
		[10, 10, 5]
	)
	assert.deepEqual(chunks(list).flat(), list)
	assert.equal(chunks(Array.from({ length: 100 }, (_, i) => i)).length, 10)
	assert.deepEqual(chunks([]), [])
	assert.deepEqual(chunks([1, 2, 3], 2), [[1, 2], [3]])
})

test("sendInChunks sends one chunk at a time, in order, and merges what each returned", async () => {
	const items = Array.from({ length: 25 }, (_, i) => ({
		doctype: "Leave Application",
		name: `L${i}`,
	}))
	let running = 0
	let widest = 0
	const sizes = []
	const progress = []
	const merged = await sendInChunks(
		items,
		async (part) => {
			running += 1
			widest = Math.max(widest, running)
			await new Promise((resolve) => setTimeout(resolve, 1))
			running -= 1
			sizes.push(part.length)
			// every fifth request is refused
			return {
				approved: part.filter((_, i) => i % 5),
				refused: part.filter((_, i) => !(i % 5)).map((p) => ({ ...p, reason: "no" })),
			}
		},
		"approved",
		(done, total) => progress.push([done, total])
	)
	assert.equal(widest, 1, "never two calls at once")
	assert.deepEqual(sizes, [10, 10, 5])
	assert.equal(merged.done.length + merged.refused.length, 25)
	// indexes 0 and 5 of each chunk of 10, index 0 of the chunk of 5: 2 + 2 + 1
	assert.equal(merged.refused.length, 5)
	// reported as each chunk goes out: "Approving 10 of 25…", never "0 of 25"
	assert.deepEqual(progress, [
		[10, 25],
		[20, 25],
		[25, 25],
	])
})

test("sendInChunks reads the key the endpoint answers with (reject_many says rejected)", async () => {
	const merged = await sendInChunks(
		[{ name: "a" }],
		async (part) => ({ rejected: part, refused: [] }),
		"rejected"
	)
	assert.deepEqual(merged.done, [{ name: "a" }])
})

test("a chunk that throws stops the rest: nothing more is sent", async () => {
	const items = Array.from({ length: 30 }, (_, i) => ({ name: `L${i}` }))
	let calls = 0
	await assert.rejects(
		sendInChunks(
			items,
			async (part) => {
				calls += 1
				if (calls === 2) throw new Error("offline")
				return { approved: part, refused: [] }
			},
			"approved"
		),
		/offline/
	)
	assert.equal(calls, 2)
})

const leaveRow = (over = {}) => ({
	doctype: "Leave Application",
	detail: "Annual Leave · 2 days",
	half_day: false,
	days: 2,
	balance_after: 3,
	attached: true,
	...over,
})

test("a time-off line says type, days, half day, balance left after, and a file", () => {
	assert.equal(
		rowDetails(leaveRow({ half_day: true }), tr),
		"Annual Leave · 2 days · Half day · 3 left after · File"
	)
	assert.equal(rowDetails(leaveRow(), tr), "Annual Leave · 2 days · 3 left after · File")
})

test("a half day keeps its AM or PM, as the old line said it", () => {
	const half = leaveRow({ half_day: true, days: 0.5, detail: "Annual Leave · Half day · AM" })
	assert.equal(rowDetails(half, tr), "Annual Leave · Half day · AM · 3 left after · File")
})

test("a time-off line leaves out what is absent: no balance, no file, one day, a half day says Half day once", () => {
	assert.equal(
		rowDetails(leaveRow({ balance_after: null, attached: false, days: 1 }), tr),
		"Annual Leave · 1 day"
	)
	assert.equal(
		rowDetails(leaveRow({ half_day: true, days: 0.5 }), tr),
		"Annual Leave · Half day · 3 left after · File"
	)
	// 0 left is still a number worth saying
	assert.match(rowDetails(leaveRow({ balance_after: 0 }), tr), /0 left after/)
})

test("a row from a cache older than the new keys falls back to the server's own detail", () => {
	assert.equal(
		rowDetails({ doctype: "Leave Application", detail: "Annual Leave · 2 days" }, tr),
		"Annual Leave · 2 days"
	)
})

test("an overtime line is the hours and the note", () => {
	const ot = { doctype: "OT Request", detail: "3h 30m", reason: "Month-end stock count" }
	assert.equal(rowDetails(ot, tr), "3h 30m · Month-end stock count")
	assert.equal(rowDetails({ ...ot, reason: "" }, tr), "3h 30m")
})

test("an expense line is the total, items, types and a receipt", () => {
	const claim = {
		doctype: "Expense Claim",
		detail: "MYR 120.00",
		items: 3,
		expense_types: ["Travel", "Meals"],
		attached: true,
		currency: "MYR",
	}
	assert.equal(rowDetails(claim, tr), "MYR 120.00 · 3 items · Travel, Meals · Receipt")
	assert.equal(
		rowDetails({ ...claim, items: 1, expense_types: ["Travel"], attached: false }, tr),
		"MYR 120.00 · 1 item · Travel"
	)
	assert.equal(rowDetails({ doctype: "Expense Claim", detail: "MYR 5.00" }, tr), "MYR 5.00")
})

test("a shift line is from-shift arrow to-shift; with no current shift it is the new one", () => {
	const shift = {
		doctype: "Shift Request",
		detail: "Night",
		current_shift: "Morning",
		new_shift: "Night",
	}
	assert.equal(rowDetails(shift, tr), "Morning → Night")
	assert.equal(rowDetails({ ...shift, current_shift: "" }, tr), "Night")
	assert.equal(rowDetails({ doctype: "Shift Request", detail: "Night" }, tr), "Night")
})

test("a Fix a day line is the reason and the in-out times", () => {
	const fix = {
		doctype: "Attendance Request",
		detail: "Work From Home",
		in_time: "09:00",
		out_time: "18:00",
	}
	assert.equal(rowDetails(fix, tr), "Work From Home · 09:00–18:00")
	assert.equal(rowDetails({ ...fix, out_time: "" }, tr), "Work From Home · In 09:00")
	assert.equal(rowDetails({ ...fix, in_time: "", out_time: "" }, tr), "Work From Home")
})

test("any other type shows the server's detail as it is", () => {
	assert.equal(rowDetails({ doctype: "Replacement Leave Claim", detail: "2 days" }, tr), "2 days")
	assert.equal(
		rowDetails({ doctype: "Remote Checkin Request", detail: "In · 120 m" }, tr),
		"In · 120 m"
	)
	assert.equal(rowDetails({ doctype: "Leave Application" }, tr), "")
})

const req = (name, over = {}) => ({
	section: "yours",
	doctype: "Leave Application",
	name,
	kind: "Time off",
	employee: "E1",
	who: "Aisyah",
	department: "Production",
	modified: "2026-08-17 09:00:00",
	from_date: "2026-10-12",
	to_date: "2026-10-14",
	...over,
})

test("filterRows narrows by kind, department and employee, all together", () => {
	const rows = [
		req("A"),
		req("B", { kind: "Overtime", doctype: "OT Request" }),
		req("C", { department: "Warehouse", employee: "E2", who: "Zul" }),
	]
	assert.deepEqual(
		filterRows(rows, {}).map((r) => r.name),
		["A", "B", "C"]
	)
	assert.deepEqual(
		filterRows(rows, { kind: "Time off" }).map((r) => r.name),
		["A", "C"]
	)
	assert.deepEqual(
		filterRows(rows, { department: "Warehouse" }).map((r) => r.name),
		["C"]
	)
	assert.deepEqual(
		filterRows(rows, { employee: "E1" }).map((r) => r.name),
		["A", "B"]
	)
	assert.deepEqual(
		filterRows(rows, { kind: "Time off", department: "Production" }).map((r) => r.name),
		["A"]
	)
})

test("the date range keeps a request whose own dates overlap it, edges included", () => {
	const rows = [
		req("in", { from_date: "2026-10-12", to_date: "2026-10-14" }),
		req("before", { from_date: "2026-10-01", to_date: "2026-10-05" }),
		req("after", { from_date: "2026-10-20", to_date: "2026-10-21" }),
		req("touchesStart", { from_date: "2026-10-08", to_date: "2026-10-10" }),
		req("touchesEnd", { from_date: "2026-10-15", to_date: "2026-10-17" }),
		req("spans", { from_date: "2026-10-01", to_date: "2026-10-30" }),
	]
	const names = (f) => filterRows(rows, f).map((r) => r.name)
	assert.deepEqual(names({ from: "2026-10-10", to: "2026-10-15" }), [
		"in",
		"touchesStart",
		"touchesEnd",
		"spans",
	])
	assert.deepEqual(names({ from: "2026-10-16" }), ["after", "touchesEnd", "spans"])
	assert.deepEqual(names({ to: "2026-10-04" }), ["before", "spans"])
})

test("a request with no dates is kept only when no date filter is set", () => {
	const rows = [
		req("none", { from_date: "", to_date: "" }),
		req("one", { from_date: "2026-10-12", to_date: "" }),
	]
	assert.deepEqual(
		filterRows(rows, {}).map((r) => r.name),
		["none", "one"]
	)
	assert.deepEqual(
		filterRows(rows, { from: "2026-10-12", to: "2026-10-12" }).map((r) => r.name),
		["one"]
	)
	assert.deepEqual(
		filterRows(rows, { from: "2026-10-13" }).map((r) => r.name),
		[]
	)
})

test("department and employee choices come from the loaded rows, once each, sorted", () => {
	const rows = [
		req("A", { department: "Warehouse", employee: "E2", who: "Zul" }),
		req("B"),
		req("C", { department: "" }),
		req("D", { department: "Production" }),
	]
	assert.deepEqual(departmentOptions(rows), [
		{ label: "Production", value: "Production" },
		{ label: "Warehouse", value: "Warehouse" },
	])
	assert.deepEqual(employeeOptions(rows), [
		{ label: "Aisyah", value: "E1" },
		{ label: "Zul", value: "E2" },
	])
})

test("the Filter button counts departments, employee and dates, dates once", () => {
	assert.equal(activeFilters({ department: "", employee: "", from: "", to: "" }), 0)
	assert.equal(
		activeFilters({ department: "QC", employee: "", from: "2026-10-01", to: "2026-10-02" }),
		2
	)
	assert.equal(activeFilters({ department: "QC", employee: "E1", from: "", to: "2026-10-02" }), 3)
})

test("a department or employee that has left the list is dropped from the filters", () => {
	const rows = [req("A")]
	assert.deepEqual(
		pruneFilters({ department: "Warehouse", employee: "E1", from: "x", to: "y" }, rows),
		{
			department: "",
			employee: "E1",
			from: "x",
			to: "y",
		}
	)
})

test("a chip reads label (count), the All chip too", () => {
	assert.equal(chipLabel({ key: "Time off", label: "Time off", count: 8 }, tr), "Time off (8)")
	assert.equal(chipLabel({ key: "", label: "All", count: 20 }, tr), "All (20)")
})

test("the confirm sheet sums the ticked requests per type, biggest first", () => {
	const rows = [
		req("A"),
		req("B"),
		req("C"),
		req("D", { kind: "Overtime" }),
		req("E", { kind: "Overtime" }),
	]
	assert.equal(kindSummary(rows, tr), "3 Time off · 2 Overtime")
	assert.equal(kindSummary([req("A")], tr), "1 Time off")
	assert.equal(kindSummary([], tr), "")
})

test("a rejected request uses its own reason, else the shared one", () => {
	assert.equal(effectiveReason("  too short notice ", "Peak week"), "too short notice")
	assert.equal(effectiveReason("   ", " Peak week "), "Peak week")
	assert.equal(effectiveReason(undefined, ""), "")
})

test("Reject stays off until every request has a reason of its own or the shared one", () => {
	const items = [
		{ doctype: "Leave Application", name: "A" },
		{ doctype: "Leave Application", name: "B" },
	]
	const key = (n) => rowKey({ doctype: "Leave Application", name: n })
	assert.equal(canReject(items, "", {}), false)
	assert.equal(canReject(items, "Peak week", {}), true)
	assert.equal(canReject(items, "   ", {}), false)
	assert.equal(canReject(items, "", { [key("A")]: "x" }), false, "B still has none")
	assert.equal(canReject(items, "", { [key("A")]: "x", [key("B")]: "y" }), true)
	assert.equal(canReject([], "Peak week", {}), false, "nothing to reject")
})

test("reject items carry the revision the approver saw and the reason that applies to each", () => {
	const items = [
		{ doctype: "Leave Application", name: "A", modified: "m1" },
		{ doctype: "OT Request", name: "B", modified: "m2" },
	]
	const own = { [rowKey(items[0])]: " not this week " }
	assert.deepEqual(rejectItems(items, "Peak week", own), [
		{ doctype: "Leave Application", name: "A", modified: "m1", reason: "not this week" },
		{ doctype: "OT Request", name: "B", modified: "m2", reason: "Peak week" },
	])
})

test("the shared reason sent with a reject is the typed one, else the first request's own (never empty)", () => {
	const items = [{ reason: "own one" }, { reason: "own two" }]
	assert.equal(sharedFor(items, "  Peak week "), "Peak week")
	assert.equal(sharedFor(items, "   "), "own one")
	assert.equal(sharedFor([], ""), "")
})
