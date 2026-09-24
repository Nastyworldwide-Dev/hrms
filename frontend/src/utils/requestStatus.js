// The ONE status rule for a request chip: list rows, the detail header and the
// review sheet all read this. Six row components used to each derive their
// own (audit 21 Sep 2026, C-M-6), so the same request read Open / Draft /
// Pending on three screens, and a Desk-saved decision that was never submitted
// (status=Approved, docstatus=0 — A-H4) rendered as a green "Approved" while
// no balance had moved.

// Chip variants, measured over glass — see GStatusChip.vue for the contrast
// figures. Keys are English and lower-case: the lookup happens BEFORE
// translation, so a Malay label still gets its colour. An unknown state
// renders neutral rather than throwing (Frappe workflow states are open-ended).
const STATUS_VARIANTS = {
	draft: "neutral",
	// The one word every pending request says on screen. Open / Draft /
	// Pending stay in the DB untouched — see WAITING below.
	waiting: "attention",
	open: "attention",
	pending: "attention",
	unpaid: "attention",
	submitted: "progress",
	"approved & draft": "progress",
	"approved & unpaid": "progress",
	"approved & submitted": "progress",
	"approved, not paid yet": "progress",
	approved: "success",
	paid: "success",
	rejected: "danger",
	cancelled: "muted",
	// attendance states — TeamDashboard mapped these by hand and noted "the DS
	// has no red variant"; it does now, so Absent stops rendering as a brand chip
	present: "success",
	absent: "danger",
	"on leave": "progress",
	"half day": "attention",
	// Employee Issue — an issue being worked on is in flight, a finished one is
	// done. Both used to fall through to neutral, so IssueList painted a closed
	// issue the same grey as an untouched one.
	"in progress": "progress",
	completed: "success",
	// Helpdesk (HD Ticket) statuses — Replied means "waiting on you"
	replied: "progress",
	paused: "neutral",
	resolved: "success",
	closed: "muted",
}

const DECIDED = ["Approved", "Rejected", "Cancelled"]

// ONE waiting word on screen (owner ruling, 21 Sep 2026). The seven request
// doctypes store three different pending words — Open, Draft and Pending — and
// a staff member reading two of their own requests side by side saw two words
// for one state. The stored word is left alone: it is wired into list filters,
// Desk views, reports and every existing row, so changing it would be a data
// migration, not a wording fix. Only the label changes.
const WAITING = "Waiting"

// Decision field and the doctype's own pending word — mirrors
// hrms/api/approval.py DECIDE_THEN_SUBMIT. A row is pending until it is
// SUBMITTED, whatever the field says: the decision is only real once
// docstatus is 1 (that is when the ledger/attendance/allocation moves).
const REQUEST_TYPES = {
	"Leave Application": { field: "status", pending: "Open" },
	"Attendance Request": { field: "status", pending: "Open" },
	"OT Request": { field: "status", pending: "Open" },
	"Replacement Leave Claim": { field: "status", pending: "Open" },
	"Compensatory Leave Request": { field: "status", pending: "Open" },
	"Shift Request": { field: "status", pending: "Draft" },
	// Not submittable: it has no docstatus, so its decision field is the whole
	// truth. Listed here so RemoteApprovals reads the same rule as every other
	// surface instead of hand-rolling a chip on `status === "Approved"`.
	"Remote Checkin Request": { field: "status", pending: "Pending" },
	"Expense Claim": {
		field: "approval_status",
		pending: "Draft",
		// get_expense_claims sends no docstatus; `status` is Frappe's own
		// docstatus mirror on this doctype (Draft / Submitted, Unpaid, Paid / Cancelled).
		docstatus: (doc) => ({ Draft: 0, Cancelled: 2 }[doc.status] ?? (doc.status ? 1 : undefined)),
		// A second axis after approval: payment. Finance reads "Approved & Unpaid".
		submitted(doc) {
			if (doc.approval_status === "Rejected") return "Rejected"
			// The person's words (alpha.6 W1): approved, money not yet paid out.
			if (doc.approval_status === "Approved" && ["Unpaid", "Submitted"].includes(doc.status)) {
				return "Approved, not paid yet"
			}
			return doc.status || "Approved"
		},
	},
}

/**
 * @returns {{ label: string, variant: string, pending: boolean }}
 *   label   — the English word for the chip; translate it at the call site
 *   variant — GStatusChip variant, looked up from the English label
 *   pending — true while the request still needs a decision OR a submit
 */
export function requestStatus(doctype, doc = {}) {
	const rule = REQUEST_TYPES[doctype]
	const decision = doc[rule?.field ?? "status"]
	const raw = doc.docstatus ?? rule?.docstatus?.(doc)
	const docstatus = raw === undefined || raw === null ? undefined : Number(raw)

	let label
	let pending = false
	if (docstatus === 2) {
		label = "Cancelled"
	} else if (docstatus === 0 || (docstatus === undefined && !DECIDED.includes(decision))) {
		pending = true
		// A decided draft says the pending word, not the decision it has not
		// yet carried out. An unknown doctype keeps its own state word (a
		// Shift Assignment is "Active"), and says nothing when it has none.
		if (rule && DECIDED.includes(decision)) {
			// A-H4: the Desk Save path left a decision that never ran.
			console.info("[requestStatus] decided draft shown as pending", doctype, doc.name)
			label = WAITING
		} else if (rule) {
			label = WAITING
		} else {
			// An unknown doctype keeps its own state word (a Shift Assignment
			// is "Active"); we do not know that its draft means "waiting".
			label = decision || ""
		}
	} else if (rule?.submitted) {
		label = rule.submitted(doc)
	} else {
		// `status` missing from an older payload: a submitted request is Approved
		label = decision || (rule ? "Approved" : "")
	}
	return { label, variant: chipVariant(label), pending }
}

// Older call sites (OT views) want just the word.
export function requestStatusChip(doc = {}, doctype = "OT Request") {
	return requestStatus(doctype, doc).label
}

export function chipVariant(status) {
	return (
		STATUS_VARIANTS[
			String(status ?? "")
				.trim()
				.toLowerCase()
		] ?? "neutral"
	)
}
