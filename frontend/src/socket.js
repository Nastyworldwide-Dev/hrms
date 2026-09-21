import { io } from "socket.io-client"

import { getCachedListResource } from "frappe-ui/src/resources/listResource"
import { getCachedResource } from "frappe-ui/src/resources/resources"
import { personalCacheKey } from "@/utils/personalCache"

export function initSocket() {
	let host = window.location.hostname
	let siteName = window.site_name
	let socketio_port = window.frappe?.boot?.socketio_port || 9000
	let port = window.location.port ? `:${socketio_port}` : ""
	let protocol = port ? "http" : "https"
	let url = `${protocol}://${host}${port}/${siteName}`
	// No `reconnectionAttempts`: the default is forever. The inherited cap of 5
	// gave up after ~20 s of bad signal and nothing ever called connect() again,
	// so every realtime feature was dead until a full reload — invisibly. A
	// mobile PWA lives for days; the backoff ceiling is the only guard needed.
	let socket = io(url, {
		withCredentials: true,
		reconnectionDelayMax: 30000,
	})
	console.info("[socket] connecting to", url)

	socket.on("hrms:refetch_resource", (data) => {
		if (data.cache_key) {
			const key = personalCacheKey(data.cache_key)
			let resource = getCachedResource(key) || getCachedListResource(key)

			if (resource) {
				resource.reload()
			}
		}
	})

	wakeSocket(socket)

	return socket
}

// Belt and braces for the transport: if the manager ever does give up
// (`reconnect_failed`, only possible with a finite attempt cap), or the tab
// comes back to the foreground while the socket is down (the browser pauses
// timers in a backgrounded tab, so the backoff clock may not have run), start
// a fresh connection attempt instead of waiting on a dead backoff.
function wakeSocket(socket) {
	const connectIfDown = (why) => {
		if (socket.connected) return
		console.info("[socket] reconnecting:", why)
		socket.connect()
	}
	socket.io?.on?.("reconnect_failed", () => connectIfDown("reconnect_failed"))
	document.addEventListener("visibilitychange", () => {
		if (document.visibilityState === "visible") connectIfDown("visible")
	})
}
