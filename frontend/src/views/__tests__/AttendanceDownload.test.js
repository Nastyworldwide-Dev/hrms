// The Shift Attendance download screen is reached from More > Apps, inside the
// PWA (router push), and downloads through a plain GET of the server method.
// The pieces live in four files; these assertions keep them pointing at each
// other. A route name or a method path that rots fails here, not on a phone.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const view = code(read("views/attendance/AttendanceDownload.vue"))
const router = code(read("router/index.js"))
const more = code(read("views/More.vue"))
const appLinks = code(read("data/appLinks.js"))

test("the route exists, lazy-loads the view, and matches the app row", () => {
	assert.match(router, /path:\s*"\/attendance-download"/)
	assert.match(router, /name:\s*"AttendanceDownload"/)
	assert.match(router, /import\("@\/views\/attendance\/AttendanceDownload\.vue"\)/)
	assert.match(appLinks, /route:\s*"\/attendance-download"/)
})

test("the app row offers the screen under the key the server offers", () => {
	assert.match(appLinks, /key:\s*"attendance"/)
	assert.match(appLinks, /title:\s*"Shift Attendance"/)
	const server = readFileSync(join(SRC, "../../hrms/api/app_links.py"), "utf8")
	assert.match(server, /"attendance":\s*\("Attendance Report Viewer",\)/)
})

test("the view downloads through downloadUrl and asks my_company who it is for", () => {
	assert.match(view, /downloadUrl\(/)
	assert.match(view, /hrms\.api\.attendance_download\.my_company/)
	assert.match(view, /fetch\(downloadUrl\(/)
	// the address is built once, in the helper
	assert.doesNotMatch(view, /attendance_download\.download/)
	// my_company is GET-only on the server; frappe-ui's default is POST
	assert.match(view, /my_company",\s*method:\s*"GET"/)
})

test("the button waits for the company and for the network", () => {
	assert.match(view, /useOnline/)
	assert.match(view, /!online/)
	assert.match(view, /company\.loading/)
})

test("someone without the role gets a plain line and no button", () => {
	assert.match(view, /Attendance Report Viewer role/)
	assert.match(view, /v-if="[^"]*noAccess[^"]*"/)
})

test("the Desk report link goes to Shift Attendance", () => {
	assert.match(view, /\/desk\/query-report\/Shift%20Attendance/)
})

test("More routes an app row that has a route, and keeps the full navigation for the rest", () => {
	const body = more.match(/const openApp = \(item\) => \{([\s\S]*?)\n\}/)
	assert.ok(body, "openApp not found in More.vue")
	const fn = body[1]
	const push = fn.indexOf("router.push(item.route)")
	const guard = fn.indexOf("isSameOriginPath(item.href)")
	const assign = fn.indexOf("window.location.assign(item.href)")
	assert.ok(push >= 0, "openApp must router.push(item.route) for an in-app row")
	assert.ok(guard >= 0 && assign > guard, "the same-origin guard stays in front of the full navigation")
	assert.ok(push < assign, "a row with a route is routed before the full navigation is reached")
	assert.match(fn, /if \(item\.route\)/)
})

// Review: on a computer the side menu opened the row in a new tab, outside Nadi.
test("the desktop side menu keeps a row with its own screen inside Nadi", () => {
	const side = readFileSync(fileURLToPath(new URL("../../components/SideNav.vue", import.meta.url)), "utf8")
	assert.match(side, /:is="item\.route \? 'router-link' : 'a'"/)
	assert.match(side, /item\.route \? \{ to: item\.route \}/)
})

// Reviews of 399090a5a: a failed download left Nadi for a raw JSON page, and a
// tap said nothing. It is fetched now; the result is a line on this screen.
test("the download stays in Nadi and says what happened", () => {
	const view = readFileSync(fileURLToPath(new URL("../attendance/AttendanceDownload.vue", import.meta.url)), "utf8")
	assert.doesNotMatch(view, /window\.location\.assign\(downloadUrl/)
	assert.match(view, /await fetch\(downloadUrl\(month\.value\)/)
	assert.match(view, /role="status"><span aria-hidden="true">✓<\/span> \{\{ saved \}\}/)
	// review of cddd5c784: no Python class path, and "started" (iPhone previews)
	assert.match(view, /split\(": "\)\.pop\(\)/)
	assert.match(view, /Download started: \{0\}/)
	assert.doesNotMatch(view, /v-html/)
	assert.match(view, /role="alert">\{\{ failed \}\}/)
})
