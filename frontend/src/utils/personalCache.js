import { keys, delMany } from "idb-keyval"

const PRIVATE_CACHE = "hrms:private:v1"
const SESSION_EPOCH = "hrms:session-epoch"
const pageUser = sessionUser()
const pageEpoch = readSessionEpoch()
let invalidated = false

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
	invalidated = true
	console.info("[personalCache] session changed; discarding this page's resources")
	document.documentElement.style.visibility = "hidden"
	window.location.reload()
	return false
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
