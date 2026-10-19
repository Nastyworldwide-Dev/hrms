// A time slip: the excuse for a late arrival, filed as an Attendance Request with
// reason "Time Slip" (owner, 14 Oct 2026). The check-in sheet offers it from the clock the
// moment the day would turn late; Today shows its status and offers it again afterwards.
//
// The pure rules live here with no frappe-ui import at load, so the node runner can test them.
// The server owns approval and the upload rules; this only says when to offer, in what words,
// and how to send. Saving the request IS sending it (status defaults to "Open"), as Fix a day.

export const TIME_SLIP_REASON = "Clinic Visit"

const plain = (text, args = []) => text.replace(/\{(\d+)\}/g, (_, i) => args[i])

/**
 * Whole minutes `now` is past `start` + `graceMin`; 0 when on time or the shift does not mark
 * late. The same line the server marks the day late by (now.py late_minutes), counted from the
 * clock on the device.
 *
 * A night shift (its `end` at or before its `start`, 22:00-06:00) owns the small hours before its
 * end: 00:30 is counted from last night's 22:00, as the shift gauge reads it (shiftGauge.js).
 * Without `end`, the same calendar day only, as before.
 */
const clockSec = (hhmm) => {
	const match = /^(\d{1,2}):(\d{2})/.exec(String(hhmm ?? "").trim())
	return match ? (Number(match[1]) * 60 + Number(match[2])) * 60 : null
}

export function lateMinutes(now, start, graceMin, markingOn, end) {
	if (!markingOn) return 0
	const startSec = clockSec(start)
	if (startSec === null) return 0
	let nowSec = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()
	const endSec = clockSec(end)
	// the small hours before a night shift's end belong to the shift that began last night
	if (endSec !== null && endSec <= startSec && nowSec < endSec) nowSec += 24 * 3600
	const over = (nowSec - startSec) / 60 - (Number(graceMin) || 0)
	return over > 0 ? Math.floor(over) : 0
}

/** "42 min after your 9:00 shift"; "1 h 5 min after your 9:00 shift" past an hour. */
export function slipLabel(minutes, start, __ = plain) {
	const [h, m] = String(start ?? "").split(":")
	const clock = `${Number(h)}:${m}`
	const hours = Math.floor(minutes / 60)
	const mins = minutes % 60
	if (hours && mins) return __("{0} h {1} min after your {2} shift", [hours, mins, clock])
	if (hours) return __("{0} h after your {1} shift", [hours, clock])
	return __("{0} min after your {1} shift", [mins, clock])
}

const STATUS_LINES = {
	Open: { text: "Waiting · your approver", tone: "warn" },
	Approved: { text: "Approved · not late", tone: "success" },
	Rejected: { text: "Not approved", tone: "danger" },
}

/** The slip's status as a line and a tone (warn / success / danger); null when there is none to say. */
export function slipStatusLine(status, __ = plain) {
	const line = STATUS_LINES[status]
	return line ? { text: __(line.text), tone: line.tone } : null
}

//: frappe-ui and the upload helper are pulled in when a slip is actually sent, never at load.
async function insertRequest(doc) {
	// the resources module only: a whole-package import also reaches frappe-ui's raw toast,
	// which renders text unescaped (no-unsanitised-html.test.js)
	const { createResource } = await import("frappe-ui/src/resources/index.js")
	return createResource({ url: "frappe.client.insert" }).submit({ doc })
}

async function uploadFile(file, name) {
	const { FileAttachment } = await import("@/composables")
	return new FileAttachment(file).upload("Attendance Request", name, "")
}

/**
 * Send the slip: insert the request for `day`, then upload the file to it. Returns the request's
 * name. A refused insert is thrown as it came and nothing is uploaded. A failed upload AFTER the
 * insert throws an Error saying the slip was saved without its file (`slipName` carries its name).
 * `deps` (insert, upload, __) are injectable so this is testable without a browser.
 */
//: What the server's upload takes (hrms.api.upload_base64_file): an iPhone's HEIC or a
//: WebP would be refused after the punch (review of c9a824c15).
export const SLIP_FILE_TYPES = "image/jpeg,image/png,application/pdf"

/** Attach the slip file to a slip already saved (Today's "Add the file"). */
export async function attachSlipFile(name, file, deps = {}) {
	const { upload = uploadFile } = deps
	await upload(file, name)
	console.info("[timeSlip] file added to", name)
	return name
}

export async function sendTimeSlip({ employee, day, file }, deps = {}) {
	const { insert = insertRequest, upload = uploadFile, __ = plain } = deps
	if (!file) throw new Error(__("Add the file for your time slip first."))
	const doc = await insert({
		doctype: "Attendance Request",
		employee,
		from_date: day,
		to_date: day,
		reason: "Time Slip",
		time_slip_reason: TIME_SLIP_REASON,
	})
	const name = doc?.name
	try {
		await upload(file, name)
	} catch (cause) {
		console.warn("[timeSlip] saved", name, "but its file did not upload", cause)
		const error = new Error(
			__("Your time slip was saved without its file. Add it from Today: Add the file to your time slip.")
		)
		error.slipName = name
		error.cause = cause
		throw error
	}
	console.info("[timeSlip] sent", name, "for", day)
	return name
}
