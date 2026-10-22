// HR's manpower board in Nadi: how the rows are grouped, when Needs HR turns red, and every reason the
// Hiring Save is dimmed. Expected words come from the owner's rulings (.claude/plans/manpower-plan.md,
// round 2: HR sees a request from the moment it is SENT; actions stay locked until the manager decides)
// and the approved mockup (tabs 6 and 7), not from the code under test.
// Run: cd frontend && node --experimental-test-module-mocks --test src/utils/__tests__/manpowerBoard.test.js
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import {
	BOARD_GROUPS,
	PREVIEW,
	HIRING_CHOICES,
	groupRows,
	needsHrState,
	hiringSection,
	hiringProblems,
	boardRoute,
	rowChip,
	rowLine,
	rowTitle,
} from "../manpowerBoard.js"

const row = (name, group, extra = {}) => ({ name, group, position_title: name, ...extra })
const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("the four lists are Waiting for manager, Needs HR, Recruiting, Done, in that order", () => {
	assert.deepEqual(
		BOARD_GROUPS.map((g) => [g.key, g.title]),
		[
			["waiting_manager", "Waiting for manager"],
			["needs_hr", "Needs HR"],
			["recruiting", "Recruiting"],
			["done", "Done"],
		]
	)
})

test("a list with nothing in it is not drawn", () => {
	const groups = groupRows([row("A", "recruiting")])
	assert.deepEqual(
		groups.map((g) => g.key),
		["recruiting"]
	)
})

test("each list shows five and says how many more (owner: summary first, 5 then See all)", () => {
	const rows = Array.from({ length: 8 }, (_, i) => row(`R${i}`, "needs_hr"))
	assert.equal(PREVIEW, 5)
	const [group] = groupRows(rows)
	assert.equal(group.count, 8)
	assert.equal(group.shown.length, 5)
	assert.equal(group.more, 3)
	assert.deepEqual(
		group.shown.map((r) => r.name),
		["R0", "R1", "R2", "R3", "R4"]
	)
})

test("See all opens one list and leaves the others at five", () => {
	const rows = [
		...Array.from({ length: 7 }, (_, i) => row(`N${i}`, "needs_hr")),
		...Array.from({ length: 7 }, (_, i) => row(`W${i}`, "waiting_manager")),
	]
	const groups = groupRows(rows, { needs_hr: true })
	const by = Object.fromEntries(groups.map((g) => [g.key, g]))
	assert.equal(by.needs_hr.shown.length, 7)
	assert.equal(by.needs_hr.more, 0)
	assert.equal(by.waiting_manager.shown.length, 5)
})

test("a request keeps the order the server gave inside its list", () => {
	const [group] = groupRows([row("B", "done"), row("A", "done")])
	assert.deepEqual(
		group.shown.map((r) => r.name),
		["B", "A"]
	)
})

test("Needs HR goes red past 30 days, with a word and a shape, never colour alone", () => {
	const hot = needsHrState({ needs_hr: 3, needs_hr_over_30: 2 })
	assert.equal(hot.over, true)
	assert.equal(hot.word, "2 over 30 days")
	assert.equal(hot.shape, "alert")
	const calm = needsHrState({ needs_hr: 3, needs_hr_over_30: 0 })
	assert.equal(calm.over, false)
	assert.equal(calm.word, "")
	assert.equal(calm.shape, "")
})

test("the hiring choices are Recruiting, Filled, Not proceeding; Waiting for HR is a start value, not a button", () => {
	assert.deepEqual(
		HIRING_CHOICES.map((c) => c.key),
		["Recruiting", "Filled", "Not proceeding"]
	)
})

const approved = (hiring_status = "Waiting for HR") => ({
	status: "Approved",
	docstatus: 1,
	hiring_status,
})

test("only HR is offered the Hiring section", () => {
	assert.equal(hiringSection(approved(), { isHR: false }).visible, false)
	assert.equal(hiringSection(approved(), { isHR: true }).visible, true)
})

test("an Open request shows Hiring locked: HR can follow it, not act", () => {
	const section = hiringSection({ status: "Open", docstatus: 0 }, { isHR: true })
	assert.equal(section.visible, true)
	assert.equal(section.locked, true)
})

test("Filled and Not proceeding are final: the section goes away", () => {
	assert.equal(hiringSection(approved("Filled"), { isHR: true }).visible, false)
	assert.equal(hiringSection(approved("Not proceeding"), { isHR: true }).visible, false)
})

test("a rejected or withdrawn request has nothing for HR to do", () => {
	assert.equal(hiringSection({ status: "Rejected", docstatus: 1 }, { isHR: true }).visible, false)
	assert.equal(hiringSection({ status: "Withdrawn", docstatus: 0 }, { isHR: true }).visible, false)
})

test("Recruiting starts selected on a request HR already picked up; Waiting for HR selects nothing", () => {
	assert.equal(hiringSection(approved("Recruiting"), { isHR: true }).start, "Recruiting")
	assert.equal(hiringSection(approved("Waiting for HR"), { isHR: true }).start, "")
})

const problems = (doc, state) =>
	hiringProblems(doc, { isHR: true, approver: "W0 approver", choice: "", note: "", ...state }).map(
		(p) => p.message
	)

test("while it is Open Save is blocked with the approver's name first", () => {
	assert.deepEqual(problems({ status: "Open", docstatus: 0 }, { choice: "Recruiting" }), [
		"W0 approver decides first",
	])
})

test("an Open request with no approver name still says who decides", () => {
	assert.deepEqual(problems({ status: "Open", docstatus: 0 }, { approver: "" }), [
		"The approver decides first",
	])
})

test("nothing picked: say what to do, note or no note", () => {
	assert.deepEqual(problems(approved(), {}), ["Pick a status to save"])
	assert.deepEqual(problems(approved(), { note: "Posted" }), ["Pick a status to save"])
})

test("picking the status it already has is blocked even with a note: the sender is only told of a change", () => {
	assert.deepEqual(problems(approved("Recruiting"), { choice: "Recruiting" }), [
		"Pick a different status to save",
	])
	assert.deepEqual(problems(approved("Recruiting"), { choice: "Recruiting", note: "Posted" }), [
		"Pick a different status to save",
	])
})

test("Not proceeding without a note is blocked and says why", () => {
	assert.deepEqual(problems(approved(), { choice: "Not proceeding" }), [
		"Say why you are not proceeding",
	])
	assert.deepEqual(problems(approved(), { choice: "Not proceeding", note: "  " }), [
		"Say why you are not proceeding",
	])
	assert.deepEqual(problems(approved(), { choice: "Not proceeding", note: "Budget cut" }), [])
})

test("a good choice on an approved request has no problem", () => {
	assert.deepEqual(problems(approved(), { choice: "Recruiting" }), [])
	assert.deepEqual(problems(approved(), { choice: "Filled" }), [])
})

test("someone who is not HR is told so, not left with a silent Save", () => {
	const out = hiringProblems(approved(), { isHR: false, choice: "Recruiting" }).map(
		(p) => p.message
	)
	assert.deepEqual(out, ["Only HR can set the hiring status"])
})

test("a closed request cannot be saved again", () => {
	assert.deepEqual(problems(approved("Filled"), { choice: "Recruiting" }), [
		"This request is closed",
	])
})

test("the board's route name is the one the router and More use", () => {
	assert.equal(boardRoute.name, "ManpowerHRBoardView")
	assert.equal(boardRoute.path, "/hr/manpower-requests")
	const router = read("../../router/manpower.js")
	assert.match(router, /name: "ManpowerHRBoardView"/)
	assert.match(router, /path: "\/hr\/manpower-requests"/)
	assert.match(router, /import\("@\/views\/manpower\/ManpowerHRBoard\.vue"\)/)
})

test("each row's chip says where it stands in the owner's words, with a status key the chip colours by", () => {
	const chip = (group, extra) => rowChip(row("A", group, extra))
	assert.deepEqual(chip("waiting_manager", { status: "Open" }), {
		label: "With manager",
		status: "waiting",
	})
	assert.deepEqual(chip("needs_hr", { status: "Approved" }), {
		label: "Needs HR",
		status: "waiting",
	})
	assert.deepEqual(chip("recruiting", { status: "Approved", hiring_status: "Recruiting" }), {
		label: "Recruiting",
		status: "in progress",
	})
	assert.deepEqual(chip("done", { status: "Approved", hiring_status: "Filled" }), {
		label: "Filled",
		status: "completed",
	})
	assert.deepEqual(chip("done", { status: "Approved", hiring_status: "Not proceeding" }), {
		label: "Not proceeding",
		status: "closed",
	})
	assert.deepEqual(chip("done", { status: "Rejected" }), { label: "Rejected", status: "rejected" })
	assert.deepEqual(chip("done", { status: "Withdrawn" }), {
		label: "Withdrawn",
		status: "withdrawn",
	})
})

test("a live row reads 'High urgency · Ops · 9 days waiting'; a closed one says when it closed", () => {
	const dept = (d) => d.split(" - ")[0]
	assert.equal(
		rowLine(
			row("A", "waiting_manager", { urgency: "High", department: "Ops - NW", days_open: 9 }),
			{ dept }
		),
		"High urgency · Ops · 9 days waiting"
	)
	assert.equal(
		rowLine(row("A", "needs_hr", { urgency: "Low", department: "Ops - NW", days_open: 1 }), {
			dept,
		}),
		"Low urgency · Ops · 1 day waiting"
	)
	assert.equal(
		rowLine(
			row("A", "done", {
				urgency: "Medium",
				department: "Ops - NW",
				days_open: 28,
				closed_on: "2026-10-12",
			}),
			{ dept }
		),
		"Medium urgency · Ops · Closed 12 Oct"
	)
})

test("a request waiting on HR past 30 days says so in words on its own row", () => {
	const line = rowLine(row("A", "needs_hr", { urgency: "High", department: "Ops", days_open: 35 }))
	assert.match(line, /35 days waiting · over 30 days$/)
	const manager = rowLine(
		row("A", "waiting_manager", { urgency: "High", department: "Ops", days_open: 35 })
	)
	assert.doesNotMatch(manager, /over 30/)
})

test("a row with no urgency or department still reads cleanly", () => {
	assert.equal(rowLine(row("A", "waiting_manager", { days_open: 0 })), "0 days waiting")
})

test("the words go through the translator the page passes in, with the approver's name", () => {
	// a stand-in `__` that marks what it translated, so a word that skipped it shows
	const seen = []
	const t = (text, args = []) => {
		seen.push(text)
		return `«${args.reduce((out, arg, i) => out.replace(`{${i}}`, arg), text)}»`
	}
	const out = hiringProblems(
		{ status: "Open", docstatus: 0 },
		{ isHR: true, approver: "Aiman", t }
	)
	assert.deepEqual(seen, ["{0} decides first"])
	assert.equal(out[0].message, "«Aiman decides first»")
	assert.equal(needsHrState({ needs_hr_over_30: 2 }, t).word, "«2 over 30 days»")
})

test("a board row names the sender in full, the count only when more than one", () => {
	// S4 browser check (22 Oct): "Store Supervisor · W0" kept only the first word of "W0 manager",
	// the same slip S3 fixed on the detail page
	assert.equal(
		rowTitle({ position_title: "Store Supervisor", headcount: 1, employee_name: "W0 manager" }),
		"Store Supervisor · W0 manager"
	)
	assert.equal(
		rowTitle({ position_title: "Driver", headcount: 3, employee_name: "Hafiz Rahman" }),
		"Driver ×3 · Hafiz Rahman"
	)
	assert.equal(rowTitle({ position_title: "Cook", headcount: 1 }), "Cook")
})
