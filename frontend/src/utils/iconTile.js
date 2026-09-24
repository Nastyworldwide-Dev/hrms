// The coloured icon tile per kind (alpha.7 plan §7, owner Q2): iOS Settings
// style, one colour per kind, reused wherever that kind appears. Colours are
// Apple's iOS system colours (dark variants). The white glyph is decorative
// (aria-hidden; the row's words carry the meaning), so it is not held to
// WCAG 1.4.11's 3:1, and some tiles (green, teal) do not reach it, as in iOS.
export const TILE = {
	leave: "#30D158",
	overtime: "#FF9230",
	expense: "#0091FF",
	shift: "#6D7CFF",
	fix: "#40C8E0",
	help: "#0091FF",
	sop: "#B78A66",
	announcement: "#FF4245",
	holiday: "#FF4245",
	team: "#6D7CFF",
	checkin: "#30D158",
	neutral: "#8E8E93",
}

const BY_KEY = {
	"Leave Application": "leave",
	"Compensatory Leave Request": "leave",
	"Replacement Leave Claim": "leave",
	"OT Request": "overtime",
	"Expense Claim": "expense",
	"Shift Request": "shift",
	"Attendance Request": "fix",
	"Remote Checkin Request": "checkin",
	"HR Announcement": "announcement",
	"SOP": "sop",
}

export function tileFor(kind) {
	return TILE[BY_KEY[kind] || kind] || TILE.neutral
}
