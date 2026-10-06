// Logging out hands the phone back: the person leaving stops getting their pushes here, and the next
// person to sign in subscribes fresh (auth hunt AU-1, 5 Oct 2026).
//
// Logout used to leave the push token registered to the leaving person and in localStorage. The next
// person on a shared phone found the SAME token, skipped subscribing (enableNotification only
// subscribes when the token changed), and the first person's approval and overtime pushes, titles
// and bodies included, kept arriving on a phone someone else was holding.
//
// Best effort, bounded: a relay that is down or hangs must never keep anyone from logging out. When
// the server cannot be told, the token is still forgotten on THIS phone so the next sign-in
// subscribes a fresh one; the old registration is the relay's to expire.

//: How long logout waits for the relay before it goes ahead without it.
const HAND_BACK_MS = 3000

const forgetHere = (push, storage) => {
	try {
		storage?.removeItem?.(`firebase_token_${push.projectName || "hrms"}`)
		push.token = null
	} catch (error) {
		console.warn("[handBackPhone] could not forget the token here", error)
	}
}

export async function handBackPhone(
	push,
	waitMs = HAND_BACK_MS,
	storage = globalThis.localStorage
) {
	if (!push || typeof push.disableNotification !== "function") return
	let told = false
	try {
		const attempt = push.disableNotification().then(() => (told = true))
		const patience = new Promise((resolve) => setTimeout(resolve, waitMs))
		await Promise.race([attempt, patience])
	} catch (error) {
		console.warn("[handBackPhone] the relay was not told", error)
	}
	if (!told) forgetHere(push, storage)
}
