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
	doctype: "Leave Application",
	name,
	kind: "Time off",
	modified,
})
const ot = (name) => ({
	doctype: "OT Request",
	name,
	kind: "Overtime",
	modified: "2026-09-01 09:00:00",
})
const checkin = (name) => ({
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
