// A failure turned into words: plain text, never markup. The ONE reader of a server refusal,
// shared with the forms (loudRequest.js re-exports it, so its callers import from one place).
// Split out of loudRequest.js (alpha.41 S12): most of that file's churn was this one concern,
// patched a case at a time (tags, line breaks, unclosed tags, offline wording).
//
// A request that never got a server answer: the browser says "Failed to fetch"
// (Chrome), "NetworkError ..." (Firefox) or "Load failed" (Safari). That is the
// phone being offline OR the server being down/restarting, so the words depend
// on navigator.onLine (owner ruling R4, 6 Oct 2026: a clear failure, no queue;
// review: "offline" was wrong for a server that was simply unreachable).
export function noServerAnswer(error) {
	if (!error || error.exc_type || error.messages?.length) return false
	return /failed to fetch|networkerror|network request failed|load failed/i.test(
		String(error.message || "")
	)
}

export function phoneOffline() {
	return typeof navigator !== "undefined" && navigator.onLine === false
}

/** A form's save failed: what to say after "Could not save this …". Only form-save
 *  sites use it, because only there is something typed still on screen. A request
 *  can leave before the connection drops, so it says "may not have been sent". */
export function saveFailedSentence(error, fallback) {
	if (!noServerAnswer(error)) return firstMessage(error, fallback)
	return phoneOffline()
		? "You are offline, so it may not have been sent. What you typed is still here."
		: "The server could not be reached, so it may not have been sent. What you typed is still here."
}

// Shared with the forms: a refused create/update must show the server's reason
// ("Insufficient leave balance", "outside leave allocation period"), not a
// generic "Error creating X" — which is what an employee reported as "unknown
// error" when their leave application was refused (15 Sep 2026).
// The toast renders `text` with v-html, and server refusals carry Desk links
// and <strong> markup: plain text only, so an employee never sees a live
// link to a Desk page they cannot open.
// `fallback` is the caller's own wording for a failure that carries no
// server message at all (a network drop, a thrown TypeError).
export function firstMessage(error, fallback = "Request failed") {
	if (noServerAnswer(error))
		return phoneOffline() ? "No connection." : "Could not reach the server."
	const message = error?.messages?.[0] || error?.message || fallback
	return (
		String(message)
			// a break between parts stays a space ("Line one<br>Line two"); inline tags just go.
			// Only a real tag — "<" then a tag name, a closing "/", or a comment — is stripped, so a
			// comparison ("must be < 8", "a<b and c>d", "x <= 5") stays as written. Making the text
			// safe for the v-html toast is the toast's job (glass/toast.js escapes it), not this one's.
			.replace(/<br\s*\/?>|<\/(p|li|div)>/gi, " ")
			.replace(/<!--[\s\S]*?(-->|$)/g, "")
			.replace(/<\/?[a-z][a-z0-9-]*(\s[^<>]*)?\/?>/gi, "")
			.replace(/\s+/g, " ")
			.trim()
	)
}
