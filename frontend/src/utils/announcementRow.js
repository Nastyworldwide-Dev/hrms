// One notice, drawn the same way on Home and on the board (owner-approved mockup, 27 Oct 2026).
// Pure, so the rules are testable without a page. The caller passes its own translator `__` and,
// where a date is worded, its own `ageOf(date)` (Home reads the device clock through $dayjs, the
// board reads the site clock through siteTime), so each screen keeps the output it always had.

//: The one badge a row wears. A WORD, never a bare dot (§14.1). One at a time: an unread policy is
//: both new and waiting, and the confirmation is the one that needs doing.
export function badgeFor(card, __) {
	// Red status text, as iOS marks urgency; lime is only the primary action (Q1).
	if (card.urgent && !card.read) return { variant: "urgent", text: __("Urgent") }
	if (card.needs_acknowledgement) return { variant: "open", text: __("Confirm") }
	if (!card.read) return { variant: "accent", text: __("New") }
	return null
}

//: What the reader needs to decide whether to open it: HR's one-line Summary (alpha.7 §10.1),
//: never text cut from the body; failing that, whether it wants something from them, and how old
//: it is. Not the category: the icon already says that.
export function subtitle(card, __, ageOf) {
	if (card.summary) return card.summary
	if (card.needs_acknowledgement) return __("Needs your confirmation")
	return card.publish_from ? ageOf(card.publish_from) : ""
}

//: The board's small caption on the right. The age, unless the line under the title already is
//: the age (a notice with no summary), which would print it twice in one row.
export function trailAge(card, __, ageOf) {
	if (!card.publish_from) return ""
	const age = ageOf(card.publish_from)
	return subtitle(card, __, ageOf) === age ? "" : age
}

//: The board's two sections. "To confirm" is the task (a policy waiting for a yes), kept in the
//: server's order; "Latest" is the reading, urgent first and then the server's order (Array.sort
//: is stable). A must-read that has been confirmed is just another notice and falls into Latest.
export function boardSections(rows) {
	const all = rows || []
	const toConfirm = all.filter((card) => card.needs_acknowledgement)
	const latest = all
		.filter((card) => !card.needs_acknowledgement)
		.sort((a, b) => Number(Boolean(b.urgent)) - Number(Boolean(a.urgent)))
	return { toConfirm, latest }
}

//: The notice's ONE meta line. `format` turns a date into "D MMM" on the caller's dayjs, so the
//: words here stay translatable and the date stays the caller's.
export function noticeDates(doc, __, format) {
	const from = doc.publish_from ? format(doc.publish_from) : ""
	const until = doc.publish_until ? format(doc.publish_until) : ""
	if (from && until) return __("Posted {0} · Shown until {1}", [from, until])
	if (from) return __("Posted {0}", [from])
	if (until) return __("Shown until {0}", [until])
	return ""
}
