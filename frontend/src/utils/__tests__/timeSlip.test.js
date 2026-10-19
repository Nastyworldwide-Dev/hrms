// A time slip: the clinic-visit excuse for a late arrival (owner, 14 Oct 2026).
//
// The check-in sheet offers it from the clock the moment the day would turn late, and Today
// shows its status afterwards. These are the pure rules behind both screens: how late, the
// words for it, the words for its status, and the send (insert the request, then its file).
// Run: cd frontend && node --test src/utils/__tests__/timeSlip.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { lateMinutes, slipLabel, slipStatusLine, sendTimeSlip } from "../timeSlip.js"

const at = (h, m, s = 0) => new Date(2026, 9, 14, h, m, s)

test("on time, or inside the grace, is not late", () => {
	assert.equal(lateMinutes(at(8, 55), "09:00", 15, true), 0)
	assert.equal(lateMinutes(at(9, 0), "09:00", 15, true), 0)
	assert.equal(lateMinutes(at(9, 15), "09:00", 15, true), 0)
})

test("late is the whole minutes past the start plus the grace", () => {
	assert.equal(lateMinutes(at(9, 42), "09:00", 15, true), 27)
	assert.equal(lateMinutes(at(9, 16), "09:00", 15, true), 1)
	assert.equal(lateMinutes(at(10, 5), "09:00", 0, true), 65)
})

test("a part minute is not counted, as the server counts it", () => {
	assert.equal(lateMinutes(at(9, 15, 59), "09:00", 15, true), 0)
	assert.equal(lateMinutes(at(9, 16, 59), "09:00", 15, true), 1)
})

test("a shift that does not mark late never offers a slip", () => {
	assert.equal(lateMinutes(at(11, 0), "09:00", 15, false), 0)
	assert.equal(lateMinutes(at(11, 0), "09:00", 15, 0), 0)
})

test("no shift start, or an unreadable one, is not late", () => {
	assert.equal(lateMinutes(at(11, 0), "", 15, true), 0)
	assert.equal(lateMinutes(at(11, 0), null, 15, true), 0)
	assert.equal(lateMinutes(at(11, 0), "soon", 15, true), 0)
})

test("a missing grace counts as none", () => {
	assert.equal(lateMinutes(at(9, 10), "09:00", undefined, true), 10)
	assert.equal(lateMinutes(at(9, 10), "09:00:00", null, true), 10)
})

test("the label says how long after the shift start", () => {
	assert.equal(slipLabel(42, "09:00"), "42 min after your 9:00 shift")
	assert.equal(slipLabel(59, "09:00"), "59 min after your 9:00 shift")
})

test("past an hour the label says hours and minutes", () => {
	assert.equal(slipLabel(65, "09:00"), "1 h 5 min after your 9:00 shift")
	assert.equal(slipLabel(120, "08:30"), "2 h after your 8:30 shift")
})

test("the label goes through the translator it is given", () => {
	const seen = []
	const __ = (text, args = []) => {
		seen.push(text)
		return text.replace(/\{(\d+)\}/g, (_, i) => args[i])
	}
	assert.equal(slipLabel(7, "09:00", __), "7 min after your 9:00 shift")
	assert.ok(seen.includes("{0} min after your {1} shift"))
})

test("Open waits on the approver, in a warning tone", () => {
	assert.deepEqual(slipStatusLine("Open"), { text: "Waiting · your approver", tone: "warn" })
})

test("Approved says the day is not late, in a success tone", () => {
	assert.deepEqual(slipStatusLine("Approved"), { text: "Approved · not late", tone: "success" })
})

test("Rejected says so, in a danger tone", () => {
	assert.deepEqual(slipStatusLine("Rejected"), { text: "Not approved", tone: "danger" })
})

test("no slip, or any other status, has no line", () => {
	assert.equal(slipStatusLine(null), null)
	assert.equal(slipStatusLine(undefined), null)
	assert.equal(slipStatusLine(""), null)
	assert.equal(slipStatusLine("Cancelled"), null)
})

const FILE = { name: "clinic.pdf" }

test("send inserts the request for that day, then uploads the file to it, and returns the name", async () => {
	const calls = []
	const name = await sendTimeSlip(
		{ employee: "HR-EMP-1", day: "2026-10-14", file: FILE },
		{
			insert: async (doc) => {
				calls.push(["insert", doc])
				return { name: "HR-ATR-9" }
			},
			upload: async (file, requestName) => {
				calls.push(["upload", file, requestName])
			},
		}
	)
	assert.equal(name, "HR-ATR-9")
	assert.deepEqual(calls, [
		[
			"insert",
			{
				doctype: "Attendance Request",
				employee: "HR-EMP-1",
				from_date: "2026-10-14",
				to_date: "2026-10-14",
				reason: "Time Slip",
				time_slip_reason: "Clinic Visit",
			},
		],
		["upload", FILE, "HR-ATR-9"],
	])
})

test("a refused insert is thrown as it came and nothing is uploaded", async () => {
	const refusal = Object.assign(new Error("refused"), { messages: ["Not yours"] })
	let uploaded = false
	await assert.rejects(
		sendTimeSlip(
			{ employee: "HR-EMP-1", day: "2026-10-14", file: FILE },
			{
				insert: async () => {
					throw refusal
				},
				upload: async () => {
					uploaded = true
				},
			}
		),
		(error) => error === refusal
	)
	assert.equal(uploaded, false)
})

test("a failed upload after the insert says the slip was saved without its file", async () => {
	await assert.rejects(
		sendTimeSlip(
			{ employee: "HR-EMP-1", day: "2026-10-14", file: FILE },
			{
				insert: async () => ({ name: "HR-ATR-9" }),
				upload: async () => {
					throw new Error("network")
				},
			}
		),
		(error) => {
			assert.match(error.message, /saved without its file/i)
			assert.match(error.message, /from Today/)
			assert.equal(error.slipName, "HR-ATR-9")
			return true
		}
	)
})

test("no file means nothing is saved", async () => {
	let inserted = false
	await assert.rejects(
		sendTimeSlip(
			{ employee: "HR-EMP-1", day: "2026-10-14", file: null },
			{
				insert: async () => {
					inserted = true
					return { name: "HR-ATR-9" }
				},
				upload: async () => {},
			}
		),
		/file/i
	)
	assert.equal(inserted, false)
})

test("a file added later goes to the slip already saved", async () => {
	const { attachSlipFile } = await import("../timeSlip.js")
	const uploaded = []
	const name = await attachSlipFile("HR-ARQ-1", { name: "slip.jpg" }, { upload: async (f, n) => uploaded.push([f.name, n]) })
	assert.equal(name, "HR-ARQ-1")
	assert.deepEqual(uploaded, [["slip.jpg", "HR-ARQ-1"]])
})

// alpha.48 "Later" (the ceiling on lateMinutes): a night shift checked in after midnight. The
// small hours before its end belong to the shift that began last night, as the shift gauge reads
// them, so 00:30 on a 22:00-06:00 shift is 2 h 30 min late, not "not late".
test("a night shift checked in after midnight is late from last night's start", () => {
	assert.equal(lateMinutes(at(0, 30), "22:00", 15, true, "06:00"), 135)
	assert.equal(lateMinutes(at(22, 10), "22:00", 15, true, "06:00"), 0)
	assert.equal(lateMinutes(at(23, 0), "22:00", 15, true, "06:00"), 45)
})

test("after a night shift has ended, the clock is not counted against it", () => {
	// 07:00 is past the 06:00 end: not a late check-in for last night (nor tonight's, not begun)
	assert.equal(lateMinutes(at(7, 0), "22:00", 15, true, "06:00"), 0)
})

test("a day shift is unchanged by its end", () => {
	assert.equal(lateMinutes(at(9, 42), "09:00", 15, true, "18:00"), 27)
	assert.equal(lateMinutes(at(8, 0), "09:00", 15, true, "18:00"), 0)
})
