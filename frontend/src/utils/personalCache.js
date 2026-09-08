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

// frappe-ui uses the default idb-keyval store with JSON-array keys. Delete
// only our old shared keys or this origin/account's private keys; other apps,
// identities and stores remain intact. No database is cleared wholesale.
export async function clearPersonalCaches(user = null) {
	if (typeof indexedDB === "undefined") return
	try {
		const obsolete = (await keys()).filter((key) => {
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
			return /^(hrms:|nsty:(remote-checkin-|hr-contacts$|reporting-manager$))/.test(parts[0])
		})
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
