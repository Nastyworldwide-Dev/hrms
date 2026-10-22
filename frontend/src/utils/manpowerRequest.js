// Manpower Request in Nadi: the rules the wizard, the insert and the detail page share, kept pure so
// they are tested without a browser. Owner rulings: .claude/plans/manpower-plan.md (22 Oct 2026);
// the server's own rules: hrms/hr/doctype/manpower_request/manpower_request.py.
import dayjs from "dayjs"

import { departmentLabel } from "./departmentLabel.js"

export const DOCTYPE = "Manpower Request"

//: How soon -> urgency. A copy of manpower_request.py URGENCY_BY_HOW_SOON; the test reads the
//: server's file and pins the two equal, so they cannot drift.
export const URGENCY_BY_HOW_SOON = {
	"Within 2 weeks": "High",
	"3–4 weeks": "Medium",
	"1–2 months": "Low",
}

//: The location picker's extra choice: no listed site, so the sender says where (location_other).
export const OTHER_SITE = "Other"

export const MAX_HEADCOUNT = 50
export const BANDS = ["B", "C", "D", "E1", "E2", "F"]
export const EMPLOYMENT_TYPES = [
	{ value: "Full-Time", label: "Full-time", hint: "Permanent, full working week" },
	{ value: "Contract", label: "Contract", hint: "Fixed end date" },
	{ value: "Part-Time", label: "Part-time", hint: "Fewer hours a week" },
	{ value: "Internship", label: "Internship", hint: "Student or fresh starter" },
]
export const REQUEST_TYPES = [
	{ value: "New Headcount", label: "New job" },
	{ value: "Replacement", label: "Replacement" },
	{ value: "Project-Based", label: "Project-based" },
	{ value: "Business Expansion", label: "Business expansion" },
]

export const STEPS = [
	{ key: "position", title: "Position", sub: "Who do you need?" },
	{ key: "type", title: "Type", sub: "What kind of job is it?" },
	{ key: "why", title: "Why", sub: "Why do you need them, and how soon?" },
	{ key: "pay", title: "Pay", sub: "What can you pay?" },
	{ key: "requirements", title: "Requirements", sub: "What should they bring?" },
	{ key: "review", title: "Review", sub: "Check your answers, then send." },
]
export const REVIEW_STEP = STEPS.length - 1

export function blankModel({ department = "" } = {}) {
	return {
		position_title: "",
		headcount: 1,
		department,
		locationChoice: "",
		location_other: "",
		employment_type: "",
		request_type: "New Headcount",
		replacing_employee: "",
		replacing_label: "",
		how_soon: "",
		start_date: "",
		justification: "",
		band: "",
		budgeted_salary: "",
		proposed_salary: "",
	}
}

//: One answer's slot in the wizard's `extra` map: HR's question, by step and words.
export const questionKey = (q) => `${q.step}|${q.question}`

const blank = (value) => value === undefined || value === null || String(value).trim() === ""
const amount = (value) => Number(String(value ?? "").trim())
const problem = (field, message) => ({ field, message })

function fixedProblems(step, m, today) {
	const out = []
	if (step === 0) {
		if (blank(m.position_title)) out.push(problem("position_title", "Add the position title"))
		const count = Number(m.headcount)
		if (!Number.isInteger(count) || count < 1 || count > MAX_HEADCOUNT)
			out.push(problem("headcount", `Pick how many people you need, 1 to ${MAX_HEADCOUNT}`))
		if (blank(m.department)) out.push(problem("department", "Pick a department"))
		if (blank(m.locationChoice)) out.push(problem("locationChoice", "Pick a location"))
		else if (m.locationChoice === OTHER_SITE && blank(m.location_other))
			out.push(
				problem("location_other", "Say where they will work, and why none of the sites fit")
			)
	} else if (step === 1) {
		if (blank(m.employment_type)) out.push(problem("employment_type", "Pick an employment type"))
		if (blank(m.request_type))
			out.push(problem("request_type", "Pick what kind of request this is"))
		else if (m.request_type === "Replacement" && blank(m.replacing_employee))
			out.push(problem("replacing_employee", "Name the staff being replaced"))
	} else if (step === 2) {
		if (blank(m.how_soon)) out.push(problem("how_soon", "Pick how soon you need them"))
		if (blank(m.justification))
			out.push(problem("justification", "Add a short reason for this hire"))
		if (!blank(m.start_date) && String(m.start_date) <= today)
			out.push(problem("start_date", "Pick a start date after today"))
	} else if (step === 3) {
		if (blank(m.band)) out.push(problem("band", "Pick a pay band"))
		if (!(amount(m.budgeted_salary) > 0))
			out.push(problem("budgeted_salary", "Add the budgeted salary"))
		if (!(amount(m.proposed_salary) > 0))
			out.push(problem("proposed_salary", "Add the proposed salary"))
	}
	return out
}

//: The mistake in a non-blank answer, by the question's type, or "".
function kindProblem(question, answer) {
	const text = String(answer).trim()
	switch (question.answer_type) {
		case "Number":
			return /^-?\d+(\.\d+)?$/.test(text) ? "" : "Answer with a number"
		case "Money":
			return /^\d+(\.\d{1,2})?$/.test(text) ? "" : "Answer with an amount"
		case "Date":
			return /^\d{4}-\d{2}-\d{2}$/.test(text) ? "" : "Pick a date"
		case "Choice":
			return (question.choices || []).includes(text) ? "" : "Pick one of the choices"
		case "Yes-No":
			return ["Yes", "No"].includes(text) ? "" : "Answer Yes or No"
		default:
			return ""
	}
}

/**
 * Every reason Next is dimmed on step `step` (0-based), in the order the fields appear:
 * [{ field, message }]. The ONE place the states that disable Next are listed. Review (the last
 * step) has none of its own: Send is judged by nextBlock over all of them.
 */
export function stepProblems(
	step,
	model,
	extra = {},
	questions = [],
	{ today = dayjs().format("YYYY-MM-DD") } = {}
) {
	const out = fixedProblems(step, model, today)
	for (const question of questions) {
		if (Number(question.step) !== step + 1) continue
		const key = questionKey(question)
		const answer = extra[key]
		if (blank(answer)) {
			if (question.required) out.push(problem(key, `Answer: ${question.question}`))
			continue
		}
		const wrong = kindProblem(question, answer)
		if (wrong) out.push(problem(key, `${wrong}: ${question.question}`))
	}
	return out
}

/** The first unfinished step before Review: { step, message }, or null when all are done. */
export function nextBlock(model, extra, questions, options) {
	for (let step = 0; step < REVIEW_STEP; step++) {
		const [first] = stepProblems(step, model, extra, questions, options)
		if (first) return { step, message: first.message }
	}
	return null
}

/**
 * The document to insert. ALWAYS carries `employee`: create permission is checked before the
 * server fills it in (S1 review), so an empty one fails there with no field to fix.
 */
export function buildInsertPayload(model, extra, questions, employee) {
	if (!employee) throw new Error("Cannot send a manpower request without the sender's employee")
	const other = model.locationChoice === OTHER_SITE
	const replacing = model.request_type === "Replacement"
	return {
		doctype: DOCTYPE,
		employee,
		department: model.department,
		position_title: String(model.position_title).trim(),
		headcount: Number(model.headcount),
		employment_type: model.employment_type,
		request_type: model.request_type,
		how_soon: model.how_soon,
		justification: String(model.justification).trim(),
		band: model.band,
		budgeted_salary: amount(model.budgeted_salary),
		proposed_salary: amount(model.proposed_salary),
		...(other
			? { location_other: String(model.location_other).trim() }
			: { location: model.locationChoice }),
		...(replacing ? { replacing_employee: model.replacing_employee } : {}),
		...(blank(model.start_date) ? {} : { start_date: model.start_date }),
		answers: (questions || []).map((q) => ({
			step: String(q.step),
			question: q.question,
			answer_type: q.answer_type,
			required: q.required ? 1 : 0,
			answer: blank(extra?.[questionKey(q)]) ? "" : String(extra[questionKey(q)]).trim(),
		})),
	}
}

//: Withdraw is offered while the server allows it (manpower_request.py withdraw): the sender's own
//: request, waiting for the manager, or approved and still with HR (Waiting for HR / Recruiting).
const WITHDRAWABLE_HIRING = ["Waiting for HR", "Recruiting"]
export function canWithdraw(doc, me) {
	if (!doc || !me || doc.employee !== me) return false
	const docstatus = Number(doc.docstatus ?? 0)
	if (docstatus === 0) return doc.status === "Open"
	return (
		docstatus === 1 && doc.status === "Approved" && WITHDRAWABLE_HIRING.includes(doc.hiring_status)
	)
}

/** "Left 12 Sep" for a leaver, "" for staff still here. */
/** "Full-time · Replacement for Ravi Subra": the detail's one line, in the words the wizard used. */
export function detailKind(doc, t = (text, args) => (args ? text.replace("{0}", args[0]) : text)) {
	const employment =
		EMPLOYMENT_TYPES.find((e) => e.value === doc.employment_type)?.label || doc.employment_type
	const kind =
		doc.request_type === "Replacement"
			? t("Replacement for {0}", [doc.replacing_employee_name || doc.replacing_employee || ""])
			: t(REQUEST_TYPES.find((r) => r.value === doc.request_type)?.label || doc.request_type)
	return `${t(employment)} · ${kind}`
}

export function leftLabel(staff) {
	if (!staff || staff.status === "Active") return ""
	return staff.relieving_date ? `Left ${dayjs(staff.relieving_date).format("D MMM")}` : "Left"
}

/** The one-line summary on the approver's sheet: "Driver ×3 · Ops". */
export function summaryLine(doc) {
	if (doc?.doctype !== DOCTYPE) return ""
	const count = Number(doc.headcount) > 1 ? ` ×${doc.headcount}` : ""
	return `${doc.position_title || ""}${count} · ${departmentLabel(doc.department)}`
}

/**
 * The tracker as it will read once the withdraw lands (shown at once; Undo puts the old steps back).
 * The step the request was waiting at becomes the withdrawal; the input is not touched.
 */
export function optimisticWithdrawn(steps, { who, at, note }) {
	const stoppedAt = steps.findIndex((step) => step.state === "current")
	const index = stoppedAt >= 0 ? stoppedAt : 1
	return steps.map((step, i) =>
		i === index ? { ...step, state: "withdrawn", who, at, note: note || null } : step
	)
}

//: One shape per state, so colour is never the only signal (Apple: distinct shapes as well as colour).
const SHAPE = {
	done: "check",
	current: "dot",
	waiting: "hollow",
	rejected: "cross",
	withdrawn: "dash",
}
const TITLE = { sent: "Sent", manager: "Manager", hr: "HR", filled: "Filled" }

/**
 * Tracker steps from hrms.api.manpower.get_progress, as rows to draw:
 * { key, title, line, note, state, shape }. `t` translates (with {0} args); `when` formats a time.
 */
export function trackerRows(
	steps,
	{ t = (text, args) => (args ? text.replace("{0}", args[0]) : text), when = (x) => x } = {}
) {
	let stopped = false
	return steps.map((step) => {
		const named = (key) => (step.who ? t(`${key}: {0}`, [step.who]) : t(key))
		const at = step.at ? when(step.at) : ""
		const withAt = (word) => (at ? `${word} · ${at}` : word)
		let title = t(TITLE[step.key] || step.label)
		let line = ""
		if (step.state === "withdrawn") {
			title = step.who ? t("Withdrawn by {0}", [step.who]) : t("Withdrawn")
			line = at
		} else if (stopped && step.state === "waiting") {
			line = t("Not reached")
		} else if (step.key === "sent") {
			line = step.who ? withAt(step.who) : at
		} else if (step.key === "manager") {
			title = named("Manager")
			line =
				{
					current: t("Waiting for a decision"),
					done: withAt(t("Approved")),
					rejected: withAt(t("Rejected")),
				}[step.state] || ""
		} else if (step.key === "hr") {
			title = named("HR")
			const word = {
				waiting: t("Waiting"),
				current: step.who ? t("Recruiting") : t("Waiting for HR to pick it up"),
				done: t("Recruiting"),
				rejected: t("Not proceeding"),
			}[step.state]
			line =
				step.state === "waiting" || (step.state === "current" && !step.who) ? word : withAt(word)
		} else if (step.key === "filled") {
			line = step.state === "done" ? withAt(t("Filled")) : t("Not yet")
		}
		if (step.state === "rejected" || step.state === "withdrawn") stopped = true
		return {
			key: step.key,
			title,
			line,
			note: step.note || "",
			state: step.state,
			shape: SHAPE[step.state] || "hollow",
		}
	})
}

// ---- a draft kept on this phone only (an Open request goes to the approver, so nothing is saved
// on the server until Send). Per person; a blocked or full store is quiet.
const DRAFT_PREFIX = "hrms:manpower-draft:v1:"
export const draftKey = (user) => `${DRAFT_PREFIX}${user}`
const store = () => globalThis.localStorage

export function readDraft(user, storage = store()) {
	if (!user) return null
	try {
		const text = storage.getItem(draftKey(user))
		return text ? JSON.parse(text) : null
	} catch (error) {
		console.warn("[manpower] draft unreadable; ignored", error?.message)
		return null
	}
}

export function writeDraft(user, draft, storage = store()) {
	if (!user) return false
	try {
		storage.setItem(draftKey(user), JSON.stringify(draft))
		return true
	} catch (error) {
		console.warn("[manpower] draft not kept", error?.message)
		return false
	}
}

export function clearDraft(user, storage = store()) {
	if (!user) return
	try {
		storage.removeItem(draftKey(user))
	} catch (error) {
		console.warn("[manpower] draft not cleared", error?.message)
	}
}

// ---- the controls a question of HR's draws, in FormField's own terms
const YES_NO = [
	{ label: "Yes", value: "Yes" },
	{ label: "No", value: "No" },
]
const FIELD_OF = {
	"Short text": "Data",
	"Long text": "Small Text",
	Choice: "Select",
	Number: "Float",
	Money: "Currency",
	Date: "Date",
	"Yes-No": "Select",
}
export function questionField(question) {
	const fieldtype = FIELD_OF[question.answer_type] || "Data"
	if (question.answer_type === "Choice")
		return {
			fieldtype,
			documentList: (question.choices || []).map((c) => ({ label: c, value: c })),
		}
	if (question.answer_type === "Yes-No") return { fieldtype, documentList: YES_NO }
	return { fieldtype }
}

const money = (value) => `RM ${amount(value).toLocaleString("en-MY")}`

/**
 * Review: the answers by step, [{ step, title, rows: [{ label, value }] }] for steps 0-4. An empty
 * value is "" (the page says "Not answered"); `t` translates, `me` is the sender's name.
 */
export function reviewGroups(model, extra, questions, { t = (x) => x, me = "" } = {}) {
	const m = model
	const where =
		m.locationChoice === OTHER_SITE ? `${t("Other")}: ${m.location_other || ""}` : m.locationChoice
	const kind = REQUEST_TYPES.find((r) => r.value === m.request_type)
	const urgency = URGENCY_BY_HOW_SOON[m.how_soon]
	const fixed = [
		[
			["Title", m.position_title],
			["People needed", String(m.headcount)],
			["Department", departmentLabel(m.department)],
			["Location", where],
			["Reports to", me],
		],
		[
			[
				"Employment",
				EMPLOYMENT_TYPES.find((e) => e.value === m.employment_type)?.label || m.employment_type,
			],
			[
				"This is",
				m.request_type === "Replacement"
					? `${t("Replacement for")} ${m.replacing_label || m.replacing_employee || ""}`
					: kind?.label || "",
			],
		],
		[
			["How soon", m.how_soon ? `${m.how_soon} · ${urgency} ${t("urgency")}` : ""],
			["Reason", m.justification],
			["Start date", m.start_date ? dayjs(m.start_date).format("D MMM YYYY") : t("Not fixed")],
		],
		[
			["Band", m.band],
			["Budgeted", blank(m.budgeted_salary) ? "" : money(m.budgeted_salary)],
			["Proposed", blank(m.proposed_salary) ? "" : money(m.proposed_salary)],
		],
		[],
	]
	return STEPS.slice(0, REVIEW_STEP).map((s, step) => ({
		step,
		title: t(s.title),
		rows: [
			...fixed[step].map(([label, value]) => ({ label: t(label), value: String(value ?? "") })),
			...(questions || [])
				.filter((q) => Number(q.step) === step + 1)
				.map((q) => ({ label: q.question, value: String(extra?.[questionKey(q)] ?? "").trim() })),
		],
	}))
}

/** A request's stage in the owner's words, with the status key GStatusChip colours it by. */
export function stage(doc) {
	const hiring = {
		"Waiting for HR": { label: "Approved, waiting for HR", status: "submitted" },
		Recruiting: { label: "Recruiting", status: "in progress" },
		Filled: { label: "Filled", status: "completed" },
		"Not proceeding": { label: "Not proceeding", status: "closed" },
	}
	if (doc?.status === "Withdrawn") return { label: "Withdrawn", status: "withdrawn" }
	if (doc?.status === "Rejected") return { label: "Rejected", status: "rejected" }
	if (doc?.status === "Approved")
		return hiring[doc.hiring_status] || { label: "Approved", status: "approved" }
	return { label: "Waiting for manager", status: "waiting" }
}
