// One timeline step in plain words (alpha.13 slice 1). The server sends
// {what, who, when, note?}; `who` is a person's name or null, never a login.

const WORDS = {
	sent: "Sent",
	approved: "Approved",
	rejected: "Not approved",
	cancelled: "Cancelled",
}

//: "Approved by W0 approver", or just "Approved" when no name is known.
export function timelineLine(step, __) {
	const word = __(WORDS[step.what] || step.what)
	return step.who ? __("{0} by {1}", [word, step.who]) : word
}
