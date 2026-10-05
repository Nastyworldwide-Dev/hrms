// What the Approvals page keeps for filter, pick and bulk approve (HR, 4 Oct
// 2026; owner, 5 Oct: no export, banner only). Pure helpers: the server decides
// what may be approved, this keeps the page's own bookkeeping honest.
import { test } from "node:test"
import assert from "node:assert/strict"
import {
	AMBER_DAYS,
	BULK_CAP,
	RED_DAYS,
	afterApprove,
	ageTone,
	allState,
	banner,
	canBulk,
	daysWaiting,
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

test("the cap matches the server's (hrms.api.approval.BULK_CAP = 50)", () => {
	assert.equal(BULK_CAP, 50)
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

test("only the Yours rows can be ticked: Other-teams rows show no tick, so Select all must not take them", () => {
	const rows = [yours("A"), theirs("B")]
	const ticked = toggleAll(new Set(), rows)
	assert.deepEqual([...ticked], [rowKey(yours("A"))])
	assert.equal(canBulk(theirs("B")), false)
	assert.equal(toggle(new Set(), theirs("B")).size, 0)
})

test("a request is tickable only when the approver can see it ticked", () => {
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
	assert.equal(nothingTickable([{ ...yours("A"), doctype: "Remote Checkin Request" }]), true)
	assert.equal(nothingTickable([yours("A")]), false)
	assert.equal(nothingTickable([]), false)
})
