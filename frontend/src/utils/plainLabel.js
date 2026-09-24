// The person's word for a doctype field label (alpha.6 C1).
//
// Labels arrive as the ERP names them. This is the ONE table that turns them
// into plain words, applied to every field label FormField draws, so every
// form, including ones added later, gets the same words. Keys are lower-case;
// matching ignores case. A label not in the table passes through.
//
// Sources: Apple HIG Writing (plain, familiar words, verbs on buttons);
// GOV.UK style (no jargon). Word choices follow the app's glossary
// (utils/requestKind.js: "Time off", "Overtime", "Fix a day").

export const PLAIN_LABELS = {
	"leave type": "Kind of leave",
	"leave approver": "Goes to",
	"expense approver": "Goes to",
	approver: "Goes to",
	"from date": "From",
	"to date": "To",
	explanation: "Note",
	"ot date": "Day you worked",
	"claimed hours": "Hours",
	"shift type": "New shift",
	"expense claim type": "Type",
	"sanctioned amount": "Approved amount",
	"total leave days": "Days",
	"leave balance before application": "Days left before this",
	"leave approver name": "Goes to",
	"expense date": "Date",
	"in time": "In",
	"out time": "Out",
	// The approver's sheet (data/config/requestSummaryFields.js).
	"leave balance": "Days left",
	"total attendance days": "Days",
	"total shift days": "Days",
	"punch-verified ot (hours)": "Hours from check-ins",
	compensation: "Paid as",
	"work from date": "Worked from",
	"work end date": "Worked to",
	employee: "Who",
}

export function plainLabel(label) {
	if (!label) return ""
	return PLAIN_LABELS[String(label).trim().toLowerCase()] || label
}
