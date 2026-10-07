// "Your last 5" merges several request lists. When rows are on screen but one list failed, the
// list is incomplete and the page says so (alpha.41 S7). A list being retried after failing still
// counts as failed until the retry settles: frappe-ui clears `error` the moment a fetch starts, so
// without `retrying` the line vanished on the tap and blinked back on a second failure.
//
// rows   — how many rows the merged list shows
// lists  — the lists; each { error, loading, retrying? }
export function partlyLoaded(rows, lists) {
	if (!rows) return false
	return lists.some((list) => list.error || (list.retrying && list.loading))
}
