// One short line per notification, built from what the row refers to — never
// the stored sentence. The server writes "Your <b>Leave Application</b>
// HR-LAP-2026-02733 has been <b>Approved</b> by <b>Hafiz Salim</b> on
// 23-09-2026 18:31:03": a table name, a raw id and a timestamp with seconds,
// three lines on a phone (owner: "drowned with information", 23 Sep 2026).
// Stored rows are not rewritten (no data repair); this reads them.
// Evidence: Apple HIG Notifications — "Prefer brief titles that people can
// read at a glance"; Teams activity feed — actor + what, then the time.
import { REQUEST_KIND } from "./requestKind.js"

const STATUS_WORD = {
	Approved: "approved",
	Rejected: "not approved",
	Cancelled: "cancelled",
	Open: "opened",
	"In Progress": "in progress",
	Completed: "completed",
	Resolved: "resolved",
	Closed: "closed",
}

// The kind as a sentence subject: "Time off approved", "Overtime approved".
const SUBJECT = {
	...REQUEST_KIND,
	"Leave Application": "Time off",
	"Employee Issue": "Issue",
	"HD Ticket": "Ticket",
}

// The entities frappe.utils.escape_html writes. Decoded in ONE pass, `&amp;` last, so "&amp;lt;" reads
// as the text "&lt;" and not "<". The text is shown as text (never HTML), so decoding is safe.
const ENTITIES = {
	"&lt;": "<",
	"&gt;": ">",
	"&quot;": '"',
	"&#x27;": "'",
	"&#39;": "'",
	"&nbsp;": " ",
	"&amp;": "&",
}
const decode = (s) => s.replace(/&(?:lt|gt|quot|#x27|#39|nbsp|amp);/g, (e) => ENTITIES[e])

const text = (html) =>
	decode(String(html || "").replace(/<[^>]*>/g, " "))
		.replace(/\s+/g, " ")
		.trim()

// A rejection carries the approver's reason after the status sentence (hrms/mixins/pwa_notifications.py:
// ". Reason: <escaped text>"). It is split off BEFORE the sentence is matched, or it leaks into "who".
// (the tags are already gone by now, and removing <strong>Reason</strong> leaves a space before the colon)
const REASON_MARK = /\.\s+Reason\s*:\s*/
function splitReason(body) {
	const found = REASON_MARK.exec(body)
	if (!found) return { sentence: body, reason: "" }
	return {
		sentence: body.slice(0, found.index),
		reason: body.slice(found.index + found[0].length).trim(),
	}
}

/**
 * @param {object} item  a PWA Notification row
 * @param {object} opts  { t: translate, remoteStatus: status of a Remote Checkin Request }
 * @returns {{ title: string, who: string, reason: string }}  title: "Time off approved"; who: a
 *   name the sentence carried ("Hafiz Salim"), or "" — the caller adds the time.
 */
function lineFor(item, { t = (s, a) => fill(s, a), remoteStatus } = {}) {
	const { sentence: body, reason } = splitReason(text(item?.message))
	const doctype = item?.reference_document_type || ""
	const subject = SUBJECT[doctype] || ""

	// "Your <kind> <id> has been <Status> by <Name> [on <datetime>]"
	let m = body.match(/^Your .+? has been (\w[\w ]*?) by (.+?)(?: on [\d-]+ [\d:]+)?$/)
	if (m) {
		const word = STATUS_WORD[m[1]] || m[1].toLowerCase()
		// only a REJECTION carries one; an approval never does
		return {
			title: t("{0} {1}", [t(subject || "Request"), t(word)]),
			who: m[2],
			reason: m[1] === "Rejected" ? reason : "",
		}
	}
	// "<Name> raised a new <Doctype> for approval: <id>"
	m = body.match(/^(.+?) raised a new .+? for approval/)
	if (m)
		return {
			title: t("{0} asked for {1}", [m[1], t(subject || "a request").toLowerCase()]),
			who: "",
		}
	// "<Name> reported a new <type> issue: <id>"
	m = body.match(/^(.+?) reported a new (.+?) issue/)
	if (m) return { title: t("{0} reported an issue", [m[1]]), who: m[2] }
	// "Your issue <id> is now <Status>"
	m = body.match(/^Your issue \S+ is now (.+)$/)
	if (m) return { title: t("Issue {0}", [t(STATUS_WORD[m[1]] || m[1].toLowerCase())]), who: "" }

	if (doctype === "Remote Checkin Request") {
		if (remoteStatus === "Pending")
			return { title: t("Check-in outside the area to decide"), who: "" }
		if (remoteStatus === "Approved")
			return { title: t("Check-in outside the area approved"), who: "" }
		if (remoteStatus === "Rejected")
			return { title: t("Check-in outside the area not approved"), who: "" }
	}
	// Anything else (reminders, remote check-in text) is already written for
	// people: keep it, minus any raw document id it carries.
	const clean = body
		.replace(/\b[A-Z]{2,5}(?:-[A-Z]{2,4})?-\d{2,4}-\d{2}-?\d{2,6}\b/g, "")
		.replace(/\s{2,}/g, " ")
		.trim()
	return { title: clean || t(subject ? "{0} update" : "Update", [t(subject)]), who: "" }
}

export function notificationLine(item, options) {
	return { reason: "", ...lineFor(item, options) }
}

function fill(s, args = []) {
	return String(s).replace(/\{(\d+)\}/g, (_, i) => args[i] ?? "")
}

/** "Today" / "Yesterday" / "Earlier" for a site-clock dayjs instant. */
export function dayGroup(when, now) {
	if (!when?.isValid?.()) return "Earlier"
	const days = now.startOf("day").diff(when.startOf("day"), "day")
	if (days <= 0) return "Today"
	if (days === 1) return "Yesterday"
	return "Earlier"
}
