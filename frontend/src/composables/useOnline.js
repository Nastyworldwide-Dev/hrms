// Is the device online, as one fact (pre-2.0 R3).
//
// Nothing in the app read `navigator.onLine` before this. A phone that lost
// signal mid-shift looked exactly like a server that was slow — taps did
// nothing, a spinner sat there, and the employee pressed the button again.
//
// ONE module-level ref, not one per caller. Three components each holding
// their own listener is three answers that can disagree, and three listeners
// to leak; the checklist's own state rule is one source of truth. The
// listeners are attached once, on first use, and every caller reads the same
// ref.
//
// WHAT `navigator.onLine` ACTUALLY MEANS, because it is weaker than it reads:
// false is reliable — the OS says there is no network interface, so nothing
// will reach the server. true only means an interface exists. A phone on a
// captive-portal wifi, or one with a bar of signal and no throughput, reports
// true and still cannot talk to Frappe. So this is used to explain a failure
// the employee is already looking at, never to decide whether a request is
// worth attempting: a request that fails while `online` is true is a server
// problem and says so, and the same failure while false gets the banner.
import { onScopeDispose, readonly, ref } from "vue"

// `navigator` is absent under SSR and in the node test runner; assume online
// there, because a build-time "you are offline" banner would be a lie.
const online = ref(typeof navigator === "undefined" ? true : navigator.onLine !== false)

let wired = false

function wire() {
	if (wired || typeof window === "undefined") return
	wired = true
	const set = (value) => () => {
		if (online.value === value) return
		online.value = value
		console.info("[useOnline] the device went", value ? "online" : "offline")
	}
	window.addEventListener("online", set(true))
	window.addEventListener("offline", set(false))
	// Deliberately not removed: this pair lives for the app's lifetime, one
	// listener each, and tearing them down when the last component unmounts
	// would leave the next one reading a stale ref. `useOnline` below removes
	// what IT adds; see there.
}

/**
 * A readonly ref: true when the device has a network interface.
 * Read it to EXPLAIN a failure, not to pre-empt a request — see the note above.
 */
export function useOnline() {
	wire()
	return readonly(online)
}

/**
 * Run `handler` each time connectivity changes, for the life of the calling
 * component. Unlike the shared ref above, this one owns its listeners and
 * removes them on unmount — a handler that outlives its component is the leak
 * the checklist's §15 names (clean up listeners, timers, observers).
 */
export function onConnectivityChange(handler) {
	if (typeof window === "undefined") return
	const up = () => handler(true)
	const down = () => handler(false)
	window.addEventListener("online", up)
	window.addEventListener("offline", down)
	onScopeDispose(() => {
		window.removeEventListener("online", up)
		window.removeEventListener("offline", down)
	})
}
