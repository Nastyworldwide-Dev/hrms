// Do it now, with Undo, instead of asking "Are you sure?" (owner, 29 Sep 2026,
// alpha.21; Apple: prefer undo to confirmation). The screen shows the result
// at once; the real action waits until the undo window closes, so pressing
// Undo only cancels a timer — there is never anything to restore on the server.
// Leaving the page (flush) runs it immediately, so a withdraw is never lost.

export const UNDO_MS = 5000

export function undoable(action, { ms = UNDO_MS, timers = globalThis } = {}) {
	let state = "waiting"
	const run = () => {
		if (state !== "waiting") return
		state = "done"
		console.info("[undoable] running the action")
		action()
	}
	const timer = timers.setTimeout(run, ms)
	return {
		undo() {
			if (state !== "waiting") return false
			state = "undone"
			timers.clearTimeout(timer)
			console.info("[undoable] undone")
			return true
		},
		flush() {
			timers.clearTimeout(timer)
			run()
		},
	}
}
