// Frappe stores a Datetime as "YYYY-MM-DD HH:mm:ss"; the native
// <input type="datetime-local"> speaks "YYYY-MM-DDTHH:mm" (seconds optional).
// These two turn one into the other so GDateTimePicker can use the phone's own
// date/time wheel without the form ever seeing the browser's format.

const FRAPPE = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/
const LOCAL = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/

/** "2026-09-23 14:05:30" -> "2026-09-23T14:05:30" (the input has step=1, so
 * seconds survive an edit; dropping them zeroed the stored value on re-save).
 * Microseconds are dropped. Anything unreadable -> "". */
export function toDatetimeLocal(value) {
	const m = FRAPPE.exec(String(value ?? "").trim())
	if (!m) {
		if (value) console.warn("[datetimeInput] unreadable Frappe datetime", value)
		return ""
	}
	return `${m[1]}T${m[2]}:${m[3]}:${m[4] ?? "00"}`
}

/** "2026-09-23T14:05" -> "2026-09-23 14:05:00". Cleared input -> "". */
export function fromDatetimeLocal(value) {
	const m = LOCAL.exec(String(value ?? "").trim())
	if (!m) {
		if (value) console.warn("[datetimeInput] unreadable datetime-local", value)
		return ""
	}
	return `${m[1]} ${m[2]}:${m[3]}:${m[4] ?? "00"}`
}

/** Date fields: the ISO day of whatever Frappe sent ("2026-09-23 00:00:00" -> "2026-09-23"). */
export function toDateInput(value) {
	const m = /^(\d{4}-\d{2}-\d{2})/.exec(String(value ?? "").trim())
	return m ? m[1] : ""
}
