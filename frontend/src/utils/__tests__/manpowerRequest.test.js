// Manpower Request in Nadi: the rules the wizard, the insert and the detail page share.
// Expected values come from the owner's rulings (.claude/plans/manpower-plan.md) and the server's
// own rules (hrms/hr/doctype/manpower_request/manpower_request.py), not from the code under test.
// Run: cd frontend && node --experimental-test-module-mocks --test src/utils/__tests__/manpowerRequest.test.js
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import {
	URGENCY_BY_HOW_SOON,
	OTHER_SITE,
	STEPS,
	blankModel,
	questionKey,
	stepProblems,
	nextBlock,
	buildInsertPayload,
	canWithdraw,
	leftLabel,
	optimisticWithdrawn,
	detailKind,
	trackerRows,
	draftKey,
	questionField,
	reviewGroups,
	stage,
	summaryLine,
	readDraft,
	writeDraft,
	clearDraft,
} from "../manpowerRequest.js"

const TODAY = "2026-10-22"
const asked = (msgs) => msgs.map((p) => p.message)

const complete = () => ({
	...blankModel({ department: "Marketing - NW" }),
	position_title: "Marketing Executive",
	headcount: 2,
	locationChoice: "Shah Alam HQ",
	employment_type: "Full-Time",
	request_type: "New Headcount",
	how_soon: "Within 2 weeks",
	justification: "Two resigned",
	band: "D",
	budgeted_salary: "4000",
	proposed_salary: "4500",
})

const Q = (step, question, extra = {}) => ({
	step,
	question,
	answer_type: "Short text",
	choices: [],
	required: 0,
	help: null,
	...extra,
})

test("six steps in the owner's order", () => {
	assert.deepEqual(
		STEPS.map((s) => s.title),
		["Position", "Type", "Why", "Pay", "Requirements", "Review"]
	)
})

test("the urgency map equals the server's, word for word", () => {
	const py = readFileSync(
		fileURLToPath(
			new URL("../../../../hrms/hr/doctype/manpower_request/manpower_request.py", import.meta.url)
		),
		"utf8"
	)
	const block = py.match(/URGENCY_BY_HOW_SOON = \{([\s\S]*?)\}/)[1]
	const server = Object.fromEntries(
		[...block.matchAll(/"([^"]+)":\s*"([^"]+)"/g)].map((m) => [m[1], m[2]])
	)
	assert.deepEqual(URGENCY_BY_HOW_SOON, server)
	assert.deepEqual(URGENCY_BY_HOW_SOON, {
		"Within 2 weeks": "High",
		"3–4 weeks": "Medium",
		"1–2 months": "Low",
	})
})

test("the department starts as the sender's own", () => {
	assert.equal(blankModel({ department: "Ops - NW" }).department, "Ops - NW")
	assert.equal(blankModel({}).department, "")
	assert.equal(blankModel({}).headcount, 1)
})

test("step 1: every state that blocks Next says why, in the mockup's words", () => {
	const m = complete()
	assert.deepEqual(stepProblems(0, m, {}, [], { today: TODAY }), [])
	assert.deepEqual(asked(stepProblems(0, blankModel({}), {}, [], { today: TODAY })), [
		"Add the position title",
		"Pick a department",
		"Pick a location",
	])
	assert.deepEqual(
		asked(stepProblems(0, { ...m, position_title: "   " }, {}, [], { today: TODAY })),
		["Add the position title"]
	)
	assert.deepEqual(asked(stepProblems(0, { ...m, headcount: 0 }, {}, [], { today: TODAY })), [
		"Pick how many people you need, 1 to 50",
	])
	assert.deepEqual(asked(stepProblems(0, { ...m, headcount: 51 }, {}, [], { today: TODAY })), [
		"Pick how many people you need, 1 to 50",
	])
})

test("Other location needs words; a listed site clears them", () => {
	const m = { ...complete(), locationChoice: OTHER_SITE, location_other: "" }
	assert.deepEqual(asked(stepProblems(0, m, {}, [], { today: TODAY })), [
		"Say where they will work, and why none of the sites fit",
	])
	assert.deepEqual(
		stepProblems(0, { ...m, location_other: "Client office in Cyberjaya" }, {}, [], {
			today: TODAY,
		}),
		[]
	)
})

test("step 2: a replacement must name the staff; a new job need not", () => {
	const m = complete()
	assert.deepEqual(stepProblems(1, m, {}, [], { today: TODAY }), [])
	assert.deepEqual(
		asked(
			stepProblems(1, { ...m, employment_type: "", request_type: "" }, {}, [], { today: TODAY })
		),
		["Pick an employment type", "Pick what kind of request this is"]
	)
	const replacing = { ...m, request_type: "Replacement", replacing_employee: "" }
	assert.deepEqual(asked(stepProblems(1, replacing, {}, [], { today: TODAY })), [
		"Name the staff being replaced",
	])
	assert.deepEqual(
		stepProblems(1, { ...replacing, replacing_employee: "HR-EMP-9" }, {}, [], { today: TODAY }),
		[]
	)
})

test("step 3: how soon and a reason are needed; a start date must be after today", () => {
	const m = complete()
	assert.deepEqual(stepProblems(2, m, {}, [], { today: TODAY }), [])
	assert.deepEqual(
		asked(stepProblems(2, { ...m, how_soon: "", justification: " " }, {}, [], { today: TODAY })),
		["Pick how soon you need them", "Add a short reason for this hire"]
	)
	assert.deepEqual(asked(stepProblems(2, { ...m, start_date: TODAY }, {}, [], { today: TODAY })), [
		"Pick a start date after today",
	])
	assert.deepEqual(
		stepProblems(2, { ...m, start_date: "2026-10-23" }, {}, [], { today: TODAY }),
		[]
	)
	assert.deepEqual(stepProblems(2, { ...m, start_date: "" }, {}, [], { today: TODAY }), [])
})

test("step 4: a band and two salaries above zero", () => {
	const m = complete()
	assert.deepEqual(stepProblems(3, m, {}, [], { today: TODAY }), [])
	assert.deepEqual(
		asked(
			stepProblems(3, { ...m, band: "", budgeted_salary: "", proposed_salary: "0" }, {}, [], {
				today: TODAY,
			})
		),
		["Pick a pay band", "Add the budgeted salary", "Add the proposed salary"]
	)
})

test("HR's questions block their own step when required, and only then", () => {
	const questions = [
		Q(5, "Draft job description", { required: 1, answer_type: "Long text" }),
		Q(5, "KPIs", { required: 0 }),
		Q(3, "What happens if it is late?", { required: 1 }),
	]
	const key = questionKey(questions[0])
	assert.deepEqual(asked(stepProblems(4, complete(), {}, questions, { today: TODAY })), [
		"Answer: Draft job description",
	])
	assert.deepEqual(
		stepProblems(4, complete(), { [key]: "Run campaigns" }, questions, { today: TODAY }),
		[]
	)
	// a step-3 question renders on step 3, after the fixed fields
	assert.deepEqual(asked(stepProblems(2, complete(), {}, questions, { today: TODAY })), [
		"Answer: What happens if it is late?",
	])
	assert.deepEqual(stepProblems(1, complete(), {}, questions, { today: TODAY }), [])
})

test("an answer of the wrong kind is named, by the question's type", () => {
	const number = Q(5, "Years needed", { answer_type: "Number" })
	const money = Q(5, "Allowance", { answer_type: "Money" })
	const date = Q(5, "Needed by", { answer_type: "Date" })
	const choice = Q(5, "Qualification", { answer_type: "Choice", choices: ["SPM", "Diploma"] })
	const yesNo = Q(5, "Industry experience", { answer_type: "Yes-No" })
	const qs = [number, money, date, choice, yesNo]
	const bad = {
		[questionKey(number)]: "three",
		[questionKey(money)]: "RM abc",
		[questionKey(date)]: "tomorrow",
		[questionKey(choice)]: "PhD",
		[questionKey(yesNo)]: "Maybe",
	}
	assert.deepEqual(asked(stepProblems(4, complete(), bad, qs, { today: TODAY })), [
		"Answer with a number: Years needed",
		"Answer with an amount: Allowance",
		"Pick a date: Needed by",
		"Pick one of the choices: Qualification",
		"Answer Yes or No: Industry experience",
	])
	const good = {
		[questionKey(number)]: "3",
		[questionKey(money)]: "250.50",
		[questionKey(date)]: "2026-11-01",
		[questionKey(choice)]: "Diploma",
		[questionKey(yesNo)]: "Yes",
	}
	assert.deepEqual(stepProblems(4, complete(), good, qs, { today: TODAY }), [])
	// an optional question left blank is fine whatever its type
	assert.deepEqual(stepProblems(4, complete(), {}, qs, { today: TODAY }), [])
})

test("Review names the first unfinished step, and nothing when all is done", () => {
	assert.equal(nextBlock(complete(), {}, [], { today: TODAY }), null)
	const m = { ...complete(), band: "" }
	assert.deepEqual(nextBlock(m, {}, [], { today: TODAY }), { step: 3, message: "Pick a pay band" })
})

test("the insert always carries the sender's employee, and the answers as the server stores them", () => {
	const questions = [
		Q(5, "Draft job description", { required: 1, answer_type: "Long text" }),
		Q(5, "KPIs"),
	]
	const extra = { [questionKey(questions[0])]: "  Run campaigns  " }
	const doc = buildInsertPayload(
		{ ...complete(), start_date: "2026-12-01" },
		extra,
		questions,
		"HR-EMP-1"
	)
	assert.equal(doc.doctype, "Manpower Request")
	assert.equal(doc.employee, "HR-EMP-1")
	assert.equal(doc.department, "Marketing - NW")
	assert.equal(doc.position_title, "Marketing Executive")
	assert.equal(doc.headcount, 2)
	assert.equal(doc.location, "Shah Alam HQ")
	assert.equal(doc.location_other, undefined)
	assert.equal(doc.budgeted_salary, 4000)
	assert.equal(doc.proposed_salary, 4500)
	assert.equal(doc.start_date, "2026-12-01")
	assert.deepEqual(doc.answers, [
		{
			step: "5",
			question: "Draft job description",
			answer_type: "Long text",
			required: 1,
			answer: "Run campaigns",
		},
		{ step: "5", question: "KPIs", answer_type: "Short text", required: 0, answer: "" },
	])
})

test("no session employee, no insert: it must not be sent without one", () => {
	assert.throws(() => buildInsertPayload(complete(), {}, [], ""), /employee/i)
	assert.throws(() => buildInsertPayload(complete(), {}, [], undefined), /employee/i)
})

test("Other site sends the words and no location; a replacement sends the person, a new job does not", () => {
	const other = buildInsertPayload(
		{ ...complete(), locationChoice: OTHER_SITE, location_other: "Client office" },
		{},
		[],
		"E1"
	)
	assert.equal(other.location, undefined)
	assert.equal(other.location_other, "Client office")
	const repl = buildInsertPayload(
		{ ...complete(), request_type: "Replacement", replacing_employee: "E7" },
		{},
		[],
		"E1"
	)
	assert.equal(repl.replacing_employee, "E7")
	const fresh = buildInsertPayload({ ...complete(), replacing_employee: "E7" }, {}, [], "E1")
	assert.equal(fresh.replacing_employee, undefined, "a stale pick does not travel with a new job")
	assert.equal(fresh.start_date, undefined, "no start date when none is fixed")
})

test("Withdraw is offered while the server allows it, to the sender only", () => {
	const me = "E1"
	const row = (over) => ({
		employee: "E1",
		docstatus: 0,
		status: "Open",
		hiring_status: "",
		...over,
	})
	assert.equal(canWithdraw(row({}), me), true, "waiting for the manager")
	assert.equal(
		canWithdraw(row({ docstatus: 1, status: "Approved", hiring_status: "Waiting for HR" }), me),
		true
	)
	assert.equal(
		canWithdraw(row({ docstatus: 1, status: "Approved", hiring_status: "Recruiting" }), me),
		true
	)
	assert.equal(
		canWithdraw(row({ docstatus: 1, status: "Approved", hiring_status: "Filled" }), me),
		false
	)
	assert.equal(
		canWithdraw(row({ docstatus: 1, status: "Approved", hiring_status: "Not proceeding" }), me),
		false
	)
	assert.equal(canWithdraw(row({ docstatus: 1, status: "Rejected" }), me), false)
	assert.equal(canWithdraw(row({ status: "Withdrawn" }), me), false)
	assert.equal(canWithdraw(row({ employee: "E2" }), me), false, "the approver reading it does not")
	assert.equal(canWithdraw(null, me), false)
})

test("a leaver is marked with the day they left; staff still here are not", () => {
	assert.equal(leftLabel({ status: "Active", relieving_date: null }), "")
	assert.equal(leftLabel({ status: "Left", relieving_date: "2026-09-12" }), "Left 12 Sep")
	assert.equal(leftLabel({ status: "Left", relieving_date: null }), "Left")
})

const steps = (over = {}) => [
	{
		key: "sent",
		label: "Sent",
		who: "Hafiz Rahman",
		at: "2026-10-20 09:12:00",
		state: "done",
		note: null,
	},
	{ key: "manager", label: "Manager", who: "Aiman Yusof", at: null, state: "current", note: null },
	{ key: "hr", label: "HR", who: null, at: null, state: "waiting", note: null },
	{ key: "filled", label: "Filled", who: null, at: null, state: "waiting", note: null },
	...(over.extra || []),
]

test("a withdrawn request shows the withdrawal where it stopped, the rest not reached", () => {
	const out = optimisticWithdrawn(steps(), {
		who: "Hafiz Rahman",
		at: "2026-10-22 09:55:00",
		note: "Covered now",
	})
	assert.deepEqual(
		out.map((s) => s.state),
		["done", "withdrawn", "waiting", "waiting"]
	)
	assert.equal(out[1].note, "Covered now")
	assert.equal(out[1].who, "Hafiz Rahman")
	// the input is left alone, so Undo can show it again
	assert.equal(steps()[1].state, "current")
	// stopped at HR: the manager keeps its approval
	const atHr = steps().map((s) =>
		s.key === "manager" ? { ...s, state: "done" } : s.key === "hr" ? { ...s, state: "current" } : s
	)
	assert.deepEqual(
		optimisticWithdrawn(atHr, { who: "H", at: "2026-10-22 09:55:00" }).map((s) => s.state),
		["done", "done", "withdrawn", "waiting"]
	)
})

test("every tracker state is a shape AND a word, in the mockup's wording", () => {
	const t = (s, args) => (args ? s.replace("{0}", args[0]) : s)
	const row = (key, state, over = {}) => ({
		key,
		label: { sent: "Sent", manager: "Manager", hr: "HR", filled: "Filled" }[key],
		who: null,
		at: null,
		note: null,
		state,
		...over,
	})
	const one = (r) => trackerRows([r], { t })[0]
	const rows = (list) => trackerRows(list, { t })
	assert.equal(one(row("sent", "done", { who: "Hafiz Rahman" })).title, "Sent")
	assert.equal(one(row("sent", "done", { who: "Hafiz Rahman" })).line, "Hafiz Rahman")
	assert.equal(
		one(row("manager", "current", { who: "Aiman Yusof" })).title,
		"Manager: Aiman Yusof"
	)
	assert.equal(
		one(row("manager", "current", { who: "Aiman Yusof" })).line,
		"Waiting for a decision"
	)
	assert.equal(one(row("manager", "done")).line, "Approved")
	assert.equal(one(row("manager", "rejected", { note: "No budget" })).line, "Rejected")
	assert.equal(one(row("manager", "rejected", { note: "No budget" })).note, "No budget")
	assert.equal(one(row("hr", "waiting")).line, "Waiting")
	assert.equal(one(row("hr", "current")).line, "Waiting for HR to pick it up")
	assert.equal(one(row("hr", "current", { who: "Hana Ismail" })).line, "Recruiting")
	assert.equal(one(row("hr", "done", { who: "Hana Ismail" })).line, "Recruiting")
	assert.equal(one(row("hr", "rejected")).line, "Not proceeding")
	assert.equal(one(row("filled", "waiting")).line, "Not yet")
	assert.equal(one(row("filled", "done")).line, "Filled")
	// the whole name: "W0 manager" read "Withdrawn by W0" (S3 browser check, 22 Oct)
	assert.equal(
		one(row("manager", "withdrawn", { who: "Hafiz Rahman" })).title,
		"Withdrawn by Hafiz Rahman"
	)
	assert.equal(one(row("manager", "withdrawn")).title, "Withdrawn")
	// the shape differs per state, so colour is never the only signal
	const shapes = ["done", "current", "waiting", "rejected", "withdrawn"].map(
		(s) => one(row("hr", s)).shape
	)
	assert.equal(new Set(shapes).size, 5)
	// after a withdrawal the later steps are not reached
	const after = rows(
		optimisticWithdrawn(steps(), {
			who: "Hafiz Rahman",
			at: "2026-10-22 09:55:00",
			note: "Covered now",
		})
	)
	assert.deepEqual(
		after.map((r) => r.line),
		["Hafiz Rahman · 2026-10-20 09:12:00", "2026-10-22 09:55:00", "Not reached", "Not reached"]
	)
	// the time is the page's to format
	const timed = trackerRows([row("manager", "done", { at: "X" })], {
		t,
		when: () => "21 Oct, 10:05 am",
	})[0]
	assert.equal(timed.line, "Approved · 21 Oct, 10:05 am")
})

test("the approver's one-line summary reads 'Driver ×3 · Ops'", () => {
	assert.equal(
		summaryLine({
			doctype: "Manpower Request",
			position_title: "Driver",
			headcount: 3,
			department: "Ops - NW",
		}),
		"Driver ×3 · Ops"
	)
	assert.equal(
		summaryLine({
			doctype: "Manpower Request",
			position_title: "Driver",
			headcount: 1,
			department: "Ops - NW",
		}),
		"Driver · Ops"
	)
	assert.equal(summaryLine({ doctype: "Leave Application" }), "")
})

test("a draft is kept on this phone, per person, and a broken store never throws", () => {
	const store = new Map()
	const storage = {
		getItem: (k) => (store.has(k) ? store.get(k) : null),
		setItem: (k, v) => void store.set(k, v),
		removeItem: (k) => void store.delete(k),
	}
	assert.equal(readDraft("a@x.com", storage), null)
	assert.equal(
		writeDraft("a@x.com", { step: 2, model: { position_title: "Driver" }, extra: {} }, storage),
		true
	)
	assert.equal(readDraft("a@x.com", storage).model.position_title, "Driver")
	assert.equal(readDraft("b@x.com", storage), null, "someone else on the same phone sees nothing")
	clearDraft("a@x.com", storage)
	assert.equal(readDraft("a@x.com", storage), null)
	// corrupt JSON, a full store, a blocked store: all quiet
	writeDraft("a@x.com", { step: 1 }, storage)
	store.set(draftKey("a@x.com"), "{not json")
	assert.equal(readDraft("a@x.com", storage), null)
	const broken = {
		getItem() {
			throw new Error("blocked")
		},
		setItem() {
			throw new Error("quota")
		},
		removeItem() {
			throw new Error("blocked")
		},
	}
	assert.equal(readDraft("a@x.com", broken), null)
	assert.equal(writeDraft("a@x.com", { step: 0 }, broken), false)
	assert.doesNotThrow(() => clearDraft("a@x.com", broken))
	assert.equal(writeDraft("", { step: 0 }, storage), false, "no user, no draft")
})

test("each answer type draws the control the brief names", () => {
	const field = (answer_type, choices = []) => questionField({ answer_type, choices })
	assert.equal(field("Short text").fieldtype, "Data")
	assert.equal(field("Long text").fieldtype, "Small Text")
	assert.equal(field("Number").fieldtype, "Float")
	assert.equal(field("Money").fieldtype, "Currency")
	assert.equal(field("Date").fieldtype, "Date")
	const choice = field("Choice", ["SPM", "Diploma"])
	assert.equal(choice.fieldtype, "Select")
	assert.deepEqual(choice.documentList, [
		{ label: "SPM", value: "SPM" },
		{ label: "Diploma", value: "Diploma" },
	])
	assert.deepEqual(
		field("Yes-No").documentList.map((o) => o.value),
		["Yes", "No"]
	)
	assert.equal(
		field("Something New").fieldtype,
		"Data",
		"an unknown type is still a box to type in"
	)
})

test("Review groups the answers by step, each with the step to edit", () => {
	const q = Q(5, "Draft job description", { required: 1, answer_type: "Long text" })
	const groups = reviewGroups(
		{
			...complete(),
			locationChoice: OTHER_SITE,
			location_other: "Client office",
			start_date: "2026-12-01",
		},
		{ [questionKey(q)]: "Run campaigns" },
		[q],
		{ t: (x) => x, me: "Hafiz Rahman" }
	)
	assert.deepEqual(
		groups.map((g) => [g.step, g.title]),
		[
			[0, "Position"],
			[1, "Type"],
			[2, "Why"],
			[3, "Pay"],
			[4, "Requirements"],
		]
	)
	const rows = Object.fromEntries(groups.flatMap((g) => g.rows.map((r) => [r.label, r.value])))
	assert.equal(rows["Title"], "Marketing Executive")
	assert.equal(rows["People needed"], "2")
	assert.equal(rows["Department"], "Marketing")
	assert.equal(rows["Location"], "Other: Client office")
	assert.equal(rows["Reports to"], "Hafiz Rahman")
	assert.equal(rows["How soon"], "Within 2 weeks · High urgency")
	assert.equal(rows["Start date"], "1 Dec 2026")
	assert.equal(rows["Band"], "D")
	assert.equal(rows["Budgeted"], "RM 4,000")
	assert.equal(rows["Draft job description"], "Run campaigns")
	const empty = reviewGroups(complete(), {}, [Q(5, "KPIs")], { t: (x) => x, me: "H" })
	assert.equal(
		empty.at(-1).rows[0].value,
		"",
		"an unanswered question reads blank, the page says Not answered"
	)
})

test("a request's stage reads in the owner's words, with the chip key that colours it", () => {
	const row = (over) => ({ docstatus: 0, status: "Open", hiring_status: "", ...over })
	const one = (over) => stage(row(over))
	assert.deepEqual(one({}), { label: "Waiting for manager", status: "waiting" })
	assert.deepEqual(one({ docstatus: 1, status: "Approved", hiring_status: "Waiting for HR" }), {
		label: "Approved, waiting for HR",
		status: "submitted",
	})
	assert.equal(
		one({ docstatus: 1, status: "Approved", hiring_status: "Recruiting" }).label,
		"Recruiting"
	)
	assert.equal(one({ docstatus: 1, status: "Approved", hiring_status: "Filled" }).label, "Filled")
	assert.equal(
		one({ docstatus: 1, status: "Approved", hiring_status: "Not proceeding" }).label,
		"Not proceeding"
	)
	assert.equal(one({ docstatus: 1, status: "Rejected" }).label, "Rejected")
	assert.equal(one({ status: "Withdrawn" }).label, "Withdrawn")
	assert.equal(one({ docstatus: 1, status: "Withdrawn" }).label, "Withdrawn")
})

test("the detail names the employment type and the replaced person in plain words", () => {
	assert.equal(
		detailKind({
			employment_type: "Full-Time",
			request_type: "Replacement",
			replacing_employee: "HR-EMP-7",
			replacing_employee_name: "Ravi Subra",
		}),
		"Full-time · Replacement for Ravi Subra"
	)
	assert.equal(
		detailKind({ employment_type: "Part-Time", request_type: "New Headcount" }),
		"Part-time · New job"
	)
})
