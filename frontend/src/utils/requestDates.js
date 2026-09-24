// WHEN a request is for, in one line: "Wed 14 Oct" or "Wed 14 Oct – Fri 16 Oct".
//
// Read straight off the document, so it works on the approver's sheet, which
// loads the raw request. The old date lines (leave_dates, attendance_dates,
// shift_dates) were computed only by the requester's list transforms, so the
// sheet an approver opens from Approvals showed no date at all (alpha.6
// screen journey, 24 Sep 2026).
import dayjs from "dayjs"

//: doctype -> [start field, end field]. Expense Claim has no single "when":
//: each item carries its own date.
const RANGE = {
	"Leave Application": ["from_date", "to_date"],
	"Attendance Request": ["from_date", "to_date"],
	"Shift Request": ["from_date", "to_date"],
	"Compensatory Leave Request": ["work_from_date", "work_end_date"],
	"OT Request": ["ot_date", "ot_date"],
}

const day = (value) => dayjs(value).format("ddd D MMM")

export function requestDates(doc) {
	const fields = RANGE[doc?.doctype]
	if (!fields || !doc[fields[0]]) return ""
	const [from, to] = [doc[fields[0]], doc[fields[1]]]
	// A shift change with no end date runs until changed again.
	if (!to) return `From ${day(from)}`
	return from === to ? day(from) : `${day(from)} – ${day(to)}`
}
