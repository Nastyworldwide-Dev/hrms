import { keys, delMany } from "idb-keyval"
import { clearCachedPages } from "./cachedPages.js"

const PRIVATE_CACHE = "hrms:private:v1"
const SESSION_EPOCH = "hrms:session-epoch"
const pageUser = sessionUser()
const pageEpoch = readSessionEpoch()
let invalidated = false
let loggingOut = false
const SIGNED_OUT = "hrms:signed-out"
const RELOADED_FOR = "hrms:session-ended-reload"
// ceiling: 2 s wait for Cache Storage before the reload; upgrade: raise it if a slow phone ever keeps the old page copy
const CLEAR_CAP_MS = 2000

// Read identity without importing reactive session/resources: these keys are
// needed while that import graph is still being initialized.
export function sessionUser() {
	if (typeof document === "undefined") return null
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	const user = cookies.get("user_id")
	return user && user !== "Guest" ? user : null
}

export function personalCacheKey(key) {
	return sessionIsCurrent() && pageUser
		? [PRIVATE_CACHE, window.location.origin, pageUser, key]
		: null
}

function readSessionEpoch() {
	try {
		return localStorage.getItem(SESSION_EPOCH)
	} catch {
		console.warn("[personalCache] session change storage unavailable")
		return null
	}
}

export function announceSessionChange() {
	try {
		localStorage.setItem(SESSION_EPOCH, crypto.randomUUID())
		console.info("[personalCache] announced session change")
	} catch {
		console.warn("[personalCache] session change broadcast unavailable")
	}
}

// The entire resource graph belongs to the login that created the page.
// Hiding immediately matters: navigation can wait on network while the old
// account's in-memory rows would otherwise still be visible to the new user.
export function sessionIsCurrent() {
	if (invalidated) return false
	if (sessionUser() === pageUser && readSessionEpoch() === pageEpoch) return true
	// Only a session that ended on its own is "signed out": not another person signing in.
	if (pageUser && !sessionUser()) sessionEnded()
	else leavePage()
	return false
}

// The ONE owner of "the session ended" (R1, alpha.37; docs/glass/tickets/2026-10-06-session-identity-hotspot.md).
// Everything that learns the server ended this login calls this and nothing routes to Login on its own:
// the cookie watcher above, the user and employee reads, the navigation guard. Each of those used to
// do some of the steps (the mark, the offline page copy, the reload) and forget the rest.
// Once per page, however many of them notice at the same moment. A page that never had a user has no
// session to end: nothing is reloaded and it answers false, so the router can send that page to Login.
// Returns true when the page is on its way to Login.
export function sessionEnded() {
	if (invalidated) return true
	if (!pageUser) {
		console.info("[personalCache] no session on this page; nothing ended")
		return false
	}
	// A refusal while the cookie still names this person is not an expiry the reload can fix: the
	// reloaded page would get the same refusal and reload again. One reload per cookie, then stay.
	// (A real expiry turns the cookie to Guest, so the next page has no user and cannot loop.)
	const stillSignedIn = sessionUser() === pageUser
	if (stillSignedIn && readOnce(RELOADED_FOR) === pageUser) {
		console.warn("[personalCache] refused again with the same login; not reloading in a loop")
		return false
	}
	if (stillSignedIn) writeOnce(RELOADED_FOR, pageUser)
	// The reload lands on Login, so a message on this page is never seen (AU-2); Login reads the mark.
	// Not for Log out, which is the person's own act.
	if (!loggingOut) {
		try {
			sessionStorage.setItem(SIGNED_OUT, "1")
		} catch {
			console.warn("[personalCache] signed-out notice storage unavailable")
		}
	}
	// the last person's offline copy of the page (a session that only expired never passed through
	// Log out). The page is hidden at once; the reload waits for the clear, capped, so a stuck Cache
	// Storage cannot keep the old page alive (review of R1: an unawaited clear could lose the race).
	leavePage(Promise.race([clearCachedPages(), new Promise((r) => setTimeout(r, CLEAR_CAP_MS))]))
	return true
}

function leavePage(before = null) {
	invalidated = true
	console.info("[personalCache] session changed; discarding this page's resources")
	document.documentElement.style.visibility = "hidden"
	// Nothing to wait for (another person signed in on this phone): reload at once,
	// as before alpha.37. Waiting for the page-copy clear only when there is one.
	if (!before) return window.location.reload()
	before.finally(() => window.location.reload())
}

function readOnce(key) {
	try {
		return sessionStorage.getItem(key)
	} catch {
		return null
	}
}

function writeOnce(key, value) {
	try {
		sessionStorage.setItem(key, value)
	} catch {
		console.warn("[personalCache] reload guard storage unavailable")
	}
}

export function markLoggingOut() {
	loggingOut = true
}

// A Log out that failed leaves the person signed in on this page: a later session end is not theirs.
export function clearLoggingOut() {
	loggingOut = false
}

// Read once by the Login page: true when the last page lost its session.
export function takeSignedOutNotice() {
	try {
		const signedOut = sessionStorage.getItem(SIGNED_OUT) === "1"
		sessionStorage.removeItem(SIGNED_OUT)
		return signedOut
	} catch {
		return false
	}
}

// Which browser-store keys a logout removes. frappe-ui uses the default
// idb-keyval store with JSON-array keys:
//   * our private keys   [PRIVATE_CACHE, origin, user, key] — this user's only
//   * our old shared keys ["hrms:…"] / ["nsty:…"]
//   * frappe-ui's document cache [doctype, name]. createDocumentResource saves
//     every document it loads there (Profile's Employee record: name, date of
//     birth, contacts), and until 23 Sep logout left it behind for the next
//     person on the device (audit P0-5, OWASP ASVS V8.2).
// Other apps' keys and other identities' private keys are left intact.
export function isClearedAtLogout(key, user) {
	let parts
	try {
		parts = JSON.parse(key)
	} catch {
		return false
	}
	if (!Array.isArray(parts)) return false
	if (parts[0] === PRIVATE_CACHE) {
		return Boolean(user && parts[1] === window.location.origin && parts[2] === user)
	}
	if (/^(hrms:|nsty:(remote-checkin-|hr-contacts$|reporting-manager$))/.test(parts[0])) return true
	return isDocumentKey(parts)
}

//: frappe-ui's document cache key: exactly [doctype, name]. A doctype is a
//: capitalised name ("Employee", "Leave Application"), which is what keeps this
//: from matching some other app's two-part key.
function isDocumentKey(parts) {
	return (
		parts.length === 2 &&
		typeof parts[0] === "string" &&
		/^[A-Z][A-Za-z ]+$/.test(parts[0]) &&
		(typeof parts[1] === "string" || typeof parts[1] === "number")
	)
}

export async function clearPersonalCaches(user = null) {
	if (typeof indexedDB === "undefined") return
	try {
		const obsolete = (await keys()).filter((key) => isClearedAtLogout(key, user))
		await delMany(obsolete)
		console.info("[personalCache] cleared obsolete resource entries", obsolete.length)
	} catch {
		// A blocked/full/unavailable browser store must not prevent logout.
		console.warn("[personalCache] browser resource cleanup unavailable")
	}
}
clearPersonalCaches()

if (typeof window !== "undefined") {
	window.addEventListener("focus", sessionIsCurrent)
	window.addEventListener("storage", (event) => {
		if (event.key === SESSION_EPOCH) sessionIsCurrent()
	})
	document.addEventListener("visibilitychange", () => {
		if (document.visibilityState !== "hidden") sessionIsCurrent()
	})
}
