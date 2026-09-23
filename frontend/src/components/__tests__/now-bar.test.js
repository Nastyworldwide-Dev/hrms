// The line at the top of Home (revamp §2, slice D1).
//
// What it replaces: "Last check-out was at 08:17 pm". True, and it made the
// reader do the rest of the work — am I on shift, how long have I been in,
// does today's shift start yet. Somebody standing at a door with a phone in
// one hand should not be doing arithmetic.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const api = readFileSync(join(SRC, "../../hrms/api/now.py"), "utf8").replace(
	/(^|\n)(\s*)#[^\n]*/g,
	(m, nl, indent) => nl + indent
)

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const bar = code(read("components/NowBar.vue"))

test("the elapsed time is derived from the start, never accumulated", () => {
	// A counter that adds a minute per tick drifts, and drifts most while the
	// phone is asleep — which is exactly when nobody is watching it.
	assert.match(bar, /Date\.now\(\) - started\.valueOf\(\)/)
	assert.doesNotMatch(bar, /minutes\s*\+=|minutes\.value\s*\+\+/, "nothing accumulates")
})

test("the timer ticks once a minute and is cleaned up", () => {
	// A session that says "6h 12m" and then stops reads as the app having lost
	// track. A per-second interval re-renders Home sixty times for a digit
	// nobody is watching.
	assert.match(bar, /const TICK_MS = 60_000/)
	assert.match(bar, /onBeforeUnmount\(\(\) => clearInterval\(timer\)\)/)
})

test("an unparseable timestamp renders nothing, not NaN", () => {
	// Safari parses "2026-09-22 19:00:00" as Invalid Date — the exact defect
	// CheckInPanel already carries a note about — and "Working · NaNm" at the
	// top of Home is worse than no line.
	// siteTime parses "YYYY-MM-DD HH:mm:ss" on the SITE clock (dayjs.tz, no
	// Safari Date parsing) and returns an invalid instant for junk.
	assert.match(bar, /const started = siteTime\(session\.value\.since\)/, "parsed on the site clock")
	assert.match(bar, /if \(!started\.isValid\(\)\) return ""/, "and a bad value is refused")
})

test("the bar ALWAYS renders", () => {
	// THIS ASSERTION IS INVERTED FROM WHAT IT WAS, and the inversion is the
	// fix. It used to require `v-if="hasAnything"` — the bar hiding itself
	// when it had no shift and no open session — which is precisely the defect
	// that deployed on 23 September: an employee with neither got an empty
	// space and Home opened on the same "Last check-out was at 08:17 pm" it
	// always had.
	//
	// A status line whose whole job is to say what is true right now does not
	// get to say nothing. "No shift today" is an answer; blank is a screen
	// that looks like it failed to load.
	assert.doesNotMatch(bar, /v-if="hasAnything"/, "the bar may not hide itself")
	const root = bar.slice(bar.indexOf("<template>"), bar.indexOf("</template>"))
	const opening = root.slice(root.indexOf("<div"), root.indexOf(">", root.indexOf("<div")))
	assert.doesNotMatch(opening, /v-if=/, "its root element is unconditional")
})

test("a missing state still reads as a state", () => {
	// While the payload is in flight, and on a site where the read fails
	// outright, the bar falls back to "off" rather than to nothing — so Home
	// does not jump when it lands, which is a layout shift on the first screen
	// of the app.
	assert.match(bar, /data\.value\.state\?\.key \|\| "off"/)
	assert.match(bar, /__\("No shift today"\)/, "and it says something")
})

test("the detail line disappears, but the state never does", () => {
	// The shift window is genuinely optional — an employee with no shift
	// assigned should not read "Shift: none". The STATE is not.
	assert.match(bar, /v-if="detail"/)
})

test("a forgotten punch is not a running session", () => {
	// The check-in button gives up on an open IN after 16 hours and offers IN
	// again. A live timer beside it would be the screen contradicting itself.
	assert.match(api, /MAX_OPEN_SESSION_HOURS = 16/)
	assert.match(api, /if hours > MAX_OPEN_SESSION_HOURS/)
	const panel = code(read("components/CheckInPanel.vue"))
	assert.match(panel, /MAX_OPEN_SHIFT_HOURS = 16/, "the two agree on the number")
})

test("the shift window survives a single-digit hour", () => {
	// A timedelta stringifies "6:00:00", and slicing five characters gives
	// "6:00:" — a trailing colon on the top line of Home. Found on the bench
	// against a real 22:00 to 6:00 night shift.
	assert.match(api, /def _hhmm\(value\)/)
	assert.doesNotMatch(api, /str\(start\)\[:5\]/, "a fixed slice is the bug")
	assert.match(api, /f"\{int\(hours\):02d\}/, "the hour is padded")
})

test("the clock is the employee's own", () => {
	// A site in another timezone put the wrong DAY at the top of Home near
	// midnight.
	assert.match(api, /employee_now\(employee\)/)
	assert.doesNotMatch(api, /nowdate\(\)|now_datetime\(\)/, "not the server's clock")
})

test("it is above the check-in button", () => {
	// The button underneath is a decision; the line above it is what the
	// decision is based on.
	const home = code(read("views/Home.vue"))
	assert.ok(home.indexOf("<NowBar") < home.indexOf("<CheckInPanel"), "facts, then the action")
})
