// The Shift Attendance download screen (Nadi, More > Apps). The helpers are
// pure so the month list, the date line and the download address are checked
// without a browser. The server side is hrms/api/attendance_download.py.
import { test } from "node:test"
import assert from "node:assert/strict"

import { downloadUrl, monthDates, monthOptions } from "../attendanceDownload.js"

test("monthOptions lists the current month and the 11 before it, newest first", () => {
	const options = monthOptions(new Date(2026, 9, 15))
	assert.equal(options.length, 12)
	assert.deepEqual(options[0], { value: "2026-10", label: "October 2026" })
	assert.deepEqual(options[1], { value: "2026-09", label: "September 2026" })
	assert.deepEqual(options[11], { value: "2025-11", label: "November 2025" })
})

test("monthOptions rolls the year over (January looks back to December)", () => {
	const options = monthOptions(new Date(2026, 0, 31))
	assert.deepEqual(options[0], { value: "2026-01", label: "January 2026" })
	assert.deepEqual(options[1], { value: "2025-12", label: "December 2025" })
	assert.deepEqual(options[11], { value: "2025-02", label: "February 2025" })
})

test("monthOptions honours a different count", () => {
	assert.deepEqual(
		monthOptions(new Date(2026, 9, 1), 2).map((o) => o.value),
		["2026-10", "2026-09"]
	)
})

test("monthDates names the first and last day, leap years included", () => {
	assert.equal(monthDates("2026-10"), "1 – 31 Oct 2026")
	assert.equal(monthDates("2026-02"), "1 – 28 Feb 2026")
	assert.equal(monthDates("2028-02"), "1 – 29 Feb 2028") // leap year
	assert.equal(monthDates("2100-02"), "1 – 28 Feb 2100") // century, not a leap year
	assert.equal(monthDates("2026-12"), "1 – 31 Dec 2026")
	assert.equal(monthDates("2026-04"), "1 – 30 Apr 2026")
})

test("monthDates says nothing for a value that is not a month", () => {
	for (const bad of ["", "2026", "2026-13", "2026-00", "October", undefined, null]) {
		assert.equal(monthDates(bad), "", String(bad))
	}
})

test("downloadUrl is the server method with the month in the query", () => {
	assert.equal(
		downloadUrl("2026-10"),
		"/api/method/hrms.api.attendance_download.download?month=2026-10"
	)
})

test("downloadUrl encodes the month, so a value cannot add a parameter", () => {
	assert.equal(
		downloadUrl("2026-10&x=1"),
		"/api/method/hrms.api.attendance_download.download?month=2026-10%26x%3D1"
	)
})
