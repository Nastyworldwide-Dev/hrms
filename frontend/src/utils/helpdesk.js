// Pure helpers for the native Helpdesk screens — Vue-free so node --test can
// pin them (frontend/tests/helpdesk-utils.test.mjs).

// Helpdesk ships five default statuses. The chips group them by what the
// employee has to do: nothing (open, waiting on an agent), read/answer
// (replied), or nothing ever again (resolved/closed). Sites can add custom
// statuses; anything unmapped only ever appears under All.
const BUCKET = {
	open: "open",
	paused: "open",
	replied: "replied",
	resolved: "resolved",
	closed: "resolved",
}

export const CHIPS = [
	{ key: "all", label: "All" },
	{ key: "open", label: "Open" },
	{ key: "replied", label: "Awaiting you" },
	{ key: "resolved", label: "Resolved" },
]

export function filterTickets(list, chip) {
	const rows = list || []
	if (!chip || chip === "all") return rows
	return rows.filter((t) => BUCKET[String(t.status || "").toLowerCase()] === chip)
}

// "Replied" is the agent's word; to the employee it means "your turn".
export function statusLabel(status) {
	if (!status) return ""
	return String(status).toLowerCase() === "replied" ? "Awaiting you" : status
}

function displayName(user, fallback) {
	if (user && typeof user === "object") return user.full_name || user.name || fallback || ""
	return fallback || ""
}

// One chronological thread: the ticket's own description first (as the
// raiser), then every communication and comment by creation time. `kind` is
// "me" only when the message came from the viewer, so an HR user reading
// someone else's ticket sees the raiser as a distinct party, not as "me".
export function threadFromTicket(ticket, viewer) {
	if (!ticket) return []
	const me = (email) =>
		!!viewer && !!email && String(email).toLowerCase() === String(viewer).toLowerCase()
	const items = []

	if (ticket.description) {
		items.push({
			id: `desc-${ticket.name || ""}`,
			kind: me(ticket.raised_by) ? "me" : "agent",
			who: ticket.raised_by_name || ticket.raised_by || "",
			html: ticket.description,
			when: ticket.creation || ticket.opening_date || "",
		})
	}

	for (const c of ticket.communications || []) {
		const email = c.sent_or_received === "Sent" && c.user?.name ? c.user.name : c.sender
		items.push({
			id: c.name,
			kind: me(email) ? "me" : "agent",
			who: displayName(c.user, email),
			html: c.content || "",
			when: c.creation || c.communication_date || "",
		})
	}

	for (const k of ticket.comments || []) {
		items.push({
			id: k.name,
			kind: me(k.commented_by) ? "me" : "agent",
			who: displayName(k.user, k.commented_by),
			html: k.content || "",
			when: k.creation || "",
		})
	}

	// the description is pinned first; everything else sorts by time
	const [head, ...rest] =
		items.length && items[0].id.startsWith("desc-") ? items : [null, ...items]
	rest.sort((a, b) => String(a.when).localeCompare(String(b.when)))
	const thread = head ? [head, ...rest] : rest
	console.info("[helpdesk] thread built:", thread.length, "message(s)")
	return thread
}
