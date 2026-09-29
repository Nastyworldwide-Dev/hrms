// Requests withdrawn a moment ago and still inside their Undo window (owner,
// 29 Sep 2026, alpha.21). The lists leave them out so the screen shows the
// result at once; Undo puts them back. Nothing here reaches the server.
import { reactive } from "vue"

const hidden = reactive(new Set())

export function hideRequest(name) {
	hidden.add(name)
}

export function unhideRequest(name) {
	hidden.delete(name)
}

export function isHidden(name) {
	return hidden.has(name)
}
