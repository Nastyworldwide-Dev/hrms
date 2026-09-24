// The coloured icon tile per kind (alpha.7 plan §7, owner Q2): iOS Settings
// style, one colour per kind, reused wherever that kind appears. The colours
// are tokens (design/tokens.json, tile-*): Apple's iOS system colours. The
// white glyph is decorative (aria-hidden; the row's words carry the meaning).
const tile = (name) => `var(--g-tile-${name})`

export const TILE = {
	leave: tile("leave"),
	overtime: tile("overtime"),
	expense: tile("expense"),
	shift: tile("shift"),
	fix: tile("fix"),
	help: tile("expense"),
	sop: tile("sop"),
	announcement: tile("announcement"),
	holiday: tile("announcement"),
	team: tile("shift"),
	checkin: tile("leave"),
	neutral: tile("neutral"),
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
