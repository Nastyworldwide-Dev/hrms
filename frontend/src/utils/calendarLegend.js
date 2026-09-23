// Which keys the Calendar shows. Owner ruling R1, 23 Sep 2026: the key ALWAYS
// shows every kind, so a person learns it once rather than per month (this
// replaced plan C6's "only the states this month has"). The one exception is
// "open" — a request waiting on YOU — which means nothing to someone who
// approves nothing: it shows for an approver, or whenever the server sent one.
export function legendFor(legend, { flags = {}, approver = false } = {}) {
	const hasOpen = Object.values(flags || {}).some((day) => day?.includes("open"))
	const keys = legend.filter((key) => key.state !== "open" || approver || hasOpen)
	console.info("[calendarLegend] keys shown", keys.length, "of", legend.length)
	return keys
}
