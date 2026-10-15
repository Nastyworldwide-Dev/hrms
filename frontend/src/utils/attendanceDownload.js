// Pure helpers for the Shift Attendance download screen (Nadi, More > Apps).
// The server side is hrms/api/attendance_download.py: one GET that answers
// with an .xlsx for a month ("YYYY-MM"). Fixed English month names, not Intl,
// so the label never depends on the phone's locale data.
const MONTHS = [
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December",
]

const DOWNLOAD_METHOD = "/api/method/hrms.api.attendance_download.download"

const pad = (n) => String(n).padStart(2, "0")

// The current month and the `n - 1` before it, newest first.
export function monthOptions(today, n = 12) {
	const options = []
	for (let i = 0; i < n; i++) {
		const d = new Date(today.getFullYear(), today.getMonth() - i, 1)
		options.push({
			value: `${d.getFullYear()}-${pad(d.getMonth() + 1)}`,
			label: `${MONTHS[d.getMonth()]} ${d.getFullYear()}`,
		})
	}
	return options
}

// "2026-10" -> "1 – 31 Oct 2026"; "" for anything that is not a month.
export function monthDates(value) {
	const match = typeof value === "string" ? /^(\d{4})-(\d{2})$/.exec(value) : null
	if (!match) return ""
	const year = Number(match[1])
	const month = Number(match[2])
	if (month < 1 || month > 12) return ""
	const lastDay = new Date(year, month, 0).getDate()
	return `1 – ${lastDay} ${MONTHS[month - 1].slice(0, 3)} ${year}`
}

export function downloadUrl(value) {
	return `${DOWNLOAD_METHOD}?month=${encodeURIComponent(value)}`
}
