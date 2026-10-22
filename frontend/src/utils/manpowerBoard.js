import dayjs from "dayjs"

import { departmentLabel } from "./departmentLabel.js"

// HR's manpower board in Nadi (S4, 22 Oct 2026): the rules the board and the Hiring section share, kept
// pure so they are tested without a browser. Owner rulings: .claude/plans/manpower-plan.md (HR sees a
// request from the moment it is SENT, under "Waiting for manager"; actions stay locked until the manager
// decides). The server's grouping is hrms.api.manpower.board_group; the board only draws what it sends.

//: The default translator: {0}, {1} filled in order. The pages pass the app's own `__`.
const plain = (text, args) =>
	args ? args.reduce((out, arg, i) => out.replace(`{${i}}`, arg), text) : text

//: The four lists, in the order they are drawn. `key` is the server's `group`.
export const BOARD_GROUPS = [
	{ key: "waiting_manager", title: "Waiting for manager" },
	{ key: "needs_hr", title: "Needs HR" },
	{ key: "recruiting", title: "Recruiting" },
	{ key: "done", title: "Done" },
]

//: Owner preference: summary first, tap to narrow; five rows, then "See all". No endless scroll.
export const PREVIEW = 5

//: Over this many days waiting on HR the Needs HR tile turns red (the server counts needs_hr_over_30).
const OVER_DAYS = 30

export const boardRoute = { name: "ManpowerHRBoardView", path: "/hr/manpower-requests" }

/**
 * The lists to draw: [{ key, title, count, shown, more }], empty lists left out. `opened` is the set of
 * list keys the person tapped See all on ({ needs_hr: true }). Rows keep the order the server gave.
 */
export function groupRows(rows, opened = {}) {
	return BOARD_GROUPS.map(({ key, title }) => {
		const all = (rows || []).filter((row) => row.group === key)
		const shown = opened[key] ? all : all.slice(0, PREVIEW)
		return { key, title, count: all.length, shown, more: all.length - shown.length }
	}).filter((group) => group.count > 0)
}

/**
 * The Needs HR tile: red past OVER_DAYS, and always a word and a shape too, never colour alone.
 * `counts` is the server's counts.
 */
export function needsHrState(counts, t = plain) {
	const over = Number(counts?.needs_hr_over_30) || 0
	return over > 0
		? { over: true, word: t("{0} over {1} days", [over, OVER_DAYS]), shape: "alert" }
		: { over: false, word: "", shape: "" }
}

//: What HR can move an approved request to. "Waiting for HR" is where it starts, not a button.
export const HIRING_CHOICES = [
	{ key: "Recruiting", label: "Recruiting" },
	{ key: "Filled", label: "Filled" },
	{ key: "Not proceeding", label: "Not proceeding" },
]

const FINAL = ["Filled", "Not proceeding"]
const blank = (value) => value === undefined || value === null || String(value).trim() === ""

/**
 * The Hiring section on the request detail: { visible, locked, start }. `start` is the segment that
 * begins selected: Recruiting once HR picked it up; "Waiting for HR" is not a button, so nothing.
 * Only HR sees it. Open: visible but locked (HR follows it, the manager decides first). Approved:
 * open for HR until Filled / Not proceeding, which are final (the section goes away). Rejected and
 * withdrawn: nothing for HR to do. The current state is the page's own status chip, not repeated here.
 */
export function hiringSection(doc, { isHR }) {
	if (!isHR || !doc) return { visible: false, locked: false, start: "" }
	if (doc.status === "Open") return { visible: true, locked: true, start: "" }
	const open = doc.status === "Approved" && !FINAL.includes(doc.hiring_status)
	return {
		visible: open,
		locked: false,
		start: open && doc.hiring_status === "Recruiting" ? "Recruiting" : "",
	}
}

/**
 * Every reason Save is dimmed, in the order they matter: [{ field, message }], at most one. The ONE
 * place the states that disable Save are listed (the blocked-Send rule): the page shows the message as
 * a visible line and the button points at it with aria-describedby.
 *
 * A save needs a CHANGE of status. HR's note rides with the change: the sender is told, and shown the
 * note, only when the hiring status moves (manpower_request.py on_update_after_submit), so a note on
 * its own would be stored and never seen. (The mockup let a note alone save; that is the one place this
 * differs, on purpose.)
 */
export function hiringProblems(doc, { isHR, approver = "", choice = "", note = "", t = plain }) {
	const problem = (field, message) => [{ field, message }]
	if (!isHR) return problem("role", t("Only HR can set the hiring status"))
	if (doc?.status === "Open")
		return problem(
			"status",
			approver ? t("{0} decides first", [approver]) : t("The approver decides first")
		)
	if (doc?.status !== "Approved")
		return problem("status", t("Nothing for HR to do on this request"))
	if (FINAL.includes(doc.hiring_status)) return problem("status", t("This request is closed"))
	if (blank(choice)) return problem("choice", t("Pick a status to save"))
	if (choice === doc.hiring_status) return problem("choice", t("Pick a different status to save"))
	if (choice === "Not proceeding" && blank(note))
		return problem("note", t("Say why you are not proceeding"))
	return []
}

/** A row's chip: { label, status } where `status` is the key GStatusChip colours by (word always shown). */
export function rowChip(row, t = plain) {
	if (row.group === "waiting_manager") return { label: t("With manager"), status: "waiting" }
	if (row.group === "needs_hr") return { label: t("Needs HR"), status: "waiting" }
	if (row.group === "recruiting") return { label: t("Recruiting"), status: "in progress" }
	if (row.status === "Rejected") return { label: t("Rejected"), status: "rejected" }
	if (row.status === "Withdrawn") return { label: t("Withdrawn"), status: "withdrawn" }
	if (row.hiring_status === "Filled") return { label: t("Filled"), status: "completed" }
	if (row.hiring_status === "Not proceeding")
		return { label: t("Not proceeding"), status: "closed" }
	return { label: t(row.hiring_status || row.status || "Done"), status: "closed" }
}

/**
 * A row's second line: "High urgency · Ops · 9 days waiting", or "... · Closed 12 Oct" once finished.
 * A request waiting on HR past OVER_DAYS says so in words as well as in the tile.
 */
/** "Driver ×3 · Hafiz Rahman": the position, the count when more than one, and who asked, in full. */
export function rowTitle(row) {
	const count = Number(row.headcount) > 1 ? ` ×${row.headcount}` : ""
	const who = (row.employee_name || "").trim()
	return `${row.position_title}${count}${who ? ` · ${who}` : ""}`
}

export function rowLine(row, { dept = departmentLabel, t = plain } = {}) {
	const days = Number(row.days_open) || 0
	let age = ""
	if (row.group === "done") {
		age = row.closed_on ? t("Closed {0}", [dayjs(row.closed_on).format("D MMM")]) : ""
	} else {
		age = t(days === 1 ? "{0} day waiting" : "{0} days waiting", [days])
		if (row.group === "needs_hr" && days > OVER_DAYS)
			age += ` · ${t("over {0} days", [OVER_DAYS])}`
	}
	return [
		row.urgency ? t("{0} urgency", [t(row.urgency)]) : "",
		row.department ? dept(row.department) : "",
		age,
	]
		.filter(Boolean)
		.join(" · ")
}
