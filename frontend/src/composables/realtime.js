import { getCurrentInstance, onBeforeUnmount, reactive } from "vue"

const subscribed = reactive({})

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
	if (subscribed[doctype]) return

	socket.emit("doctype_subscribe", doctype)
	subscribed[doctype] = true
}
