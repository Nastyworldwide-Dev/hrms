import { getCurrentInstance, onBeforeUnmount, reactive } from "vue"

const subscribed = reactive({})
// Sockets already wired with the reconnect handler (normally one for the app's
// lifetime; a WeakSet so a replaced socket isn't pinned alive).
const reconnectWired = new WeakSet()
// Sockets that have connected at least once: the "connect" after that is a
// RECONNECT, and events emitted in between were lost for good.
const everConnected = new WeakSet()

// Reload hooks for the moments realtime may have missed events: a socket
// reconnect (the server replays nothing) and a tab that was hidden long enough
// for the browser to have frozen the socket. The socket is a bonus, never the
// guarantee (A-C1, 21 Sep 2026).
const gapHooks = new Set()
const LONG_HIDDEN_MS = 60_000
let hiddenAt = null
let resumeWired = false

// Listens for list_update events for one doctype. Detaches itself on component
// unmount — the previous version never called socket.off, so every remount of a
// caller (ListView, RequestPanel registers six) stacked another permanent
// handler and each event reloaded every list once per historical mount.
// Callers created outside a component context get the detach function back.
export function useListUpdate(socket, doctype, callback) {
	if (!socket) return () => {}
	subscribe(socket, doctype)
	const handler = (data) => {
		if (data.doctype == doctype) {
			callback(data.name)
		}
	}
	socket.on("list_update", handler)
	const off = () => socket.off("list_update", handler)
	if (getCurrentInstance()) onBeforeUnmount(off)
	return off
}

function subscribe(socket, doctype) {
	wireReconnect(socket)
	if (subscribed[doctype]) return

	socket.emit("doctype_subscribe", doctype)
	subscribed[doctype] = true
	console.info("[realtime] subscribed to", doctype)
}

// The socketio server drops EVERY room membership on a new connection, and on a
// mobile PWA reconnects are routine (screen sleep/wake, network blips). Without
// this the module `subscribed` flag stayed true across a reconnect, subscribe()
// early-returned, the room was never rejoined, and list_update events silently
// stopped arriving until a full page reload — the whole realtime layer dead but
// invisible. Re-join every subscribed room on each (re)connect. socket.io fires
// "connect" on the initial connect and on every reconnect; only the latter
// runs the gap hooks (the initial connect has nothing to catch up on).
function wireReconnect(socket) {
	if (reconnectWired.has(socket)) return
	reconnectWired.add(socket)
	socket.on("connect", () => {
		const rooms = Object.keys(subscribed)
		console.info("[realtime] (re)connected — rejoining rooms:", rooms)
		for (const doctype of rooms) {
			socket.emit("doctype_subscribe", doctype)
		}
		if (everConnected.has(socket)) runGapHooks("reconnect")
		everConnected.add(socket)
	})
}

// Registers `fn(why)` to run after a reconnect and after a long-hidden tab
// becomes visible again. Detaches on component unmount; returns the detach.
export function useReloadOnGap(fn) {
	gapHooks.add(fn)
	wireResume()
	console.info("[realtime] gap reload hook registered:", gapHooks.size)
	const detach = () => gapHooks.delete(fn)
	if (getCurrentInstance()) onBeforeUnmount(detach)
	return detach
}

function runGapHooks(why) {
	console.info(
		"[realtime] events may have been missed (%s) — reloading %d hook(s)",
		why,
		gapHooks.size
	)
	for (const fn of gapHooks) fn(why)
}

// Exposed for tests: the visibility listener is installed once per document.
// Returns whether the hooks ran.
export function onVisibilityChange(visibilityState, now = Date.now()) {
	if (visibilityState === "hidden") {
		hiddenAt = now
		return false
	}
	const hiddenFor = hiddenAt === null ? 0 : now - hiddenAt
	hiddenAt = null
	if (hiddenFor <= LONG_HIDDEN_MS) {
		console.info("[realtime] visible after a short hide, no reload:", hiddenFor)
		return false
	}
	runGapHooks(`visible after ${Math.round(hiddenFor / 1000)} s hidden`)
	return true
}

function wireResume() {
	if (resumeWired || typeof document === "undefined") return
	resumeWired = true
	document.addEventListener("visibilitychange", () => onVisibilityChange(document.visibilityState))
}
