import { getCurrentInstance, onBeforeUnmount, reactive } from "vue"

const subscribed = reactive({})
// Sockets already wired with the reconnect handler (normally one for the app's
// lifetime; a WeakSet so a replaced socket isn't pinned alive).
const reconnectWired = new WeakSet()

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
// "connect" on the initial connect and on every reconnect.
function wireReconnect(socket) {
	if (reconnectWired.has(socket)) return
	reconnectWired.add(socket)
	socket.on("connect", () => {
		const rooms = Object.keys(subscribed)
		console.info("[realtime] (re)connected — rejoining rooms:", rooms)
		for (const doctype of rooms) {
			socket.emit("doctype_subscribe", doctype)
		}
	})
}
