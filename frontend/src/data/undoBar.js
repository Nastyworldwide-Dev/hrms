// The one Undo bar (owner, 29 Sep 2026, alpha.21): what just happened, and a
// way to take it back for a few seconds. UndoBar.vue renders it; callers use
// showUndo with an undoable() handle.
import { reactive } from "vue"

import { UNDO_MS } from "@/utils/undoable"

export const undoBar = reactive({ open: false, message: "", pending: null, onUndo: null, timer: null })

export function showUndo(message, pending, onUndo = null) {
	if (undoBar.pending && undoBar.pending !== pending) undoBar.pending.flush()
	clearTimeout(undoBar.timer)
	Object.assign(undoBar, { open: true, message, pending, onUndo })
	undoBar.timer = setTimeout(closeUndo, UNDO_MS)
}

export function closeUndo() {
	clearTimeout(undoBar.timer)
	Object.assign(undoBar, { open: false, message: "", pending: null, onUndo: null, timer: null })
}
