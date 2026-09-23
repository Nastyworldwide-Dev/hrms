// The announcement resources (revamp slice B2).
//
// Three decisions live in this module and each has a failure mode that only
// shows up on somebody else's phone:
//
//   the boards are cached PER PERSON, because the board is audience-filtered
//   and a shared key serves one employee's department notices to the next
//   person who signs in on the same device — routine on a shared factory
//   phone;
//
//   the detail is NOT cached, because fetching it is what records the read,
//   and a cached response never reaches the server;
//
//   both boards reload together, because acknowledging changes Home's block
//   AND the badge on the full list.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = fileURLToPath(new URL(".", import.meta.url))
const source = readFileSync(join(HERE, "../announcements.js"), "utf8")

const code = source
	.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
	.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

//: Each resource's own block, so an assertion about one cannot pass because
//: of another. Keyed by the export name, sliced to the next export.
function resource(name) {
	const start = code.indexOf(`export const ${name} = createResource(`)
	assert.ok(start >= 0, `${name} is exported`)
	const end = code.indexOf("export ", start + 10)
	return code.slice(start, end === -1 ? undefined : end)
}

test("the boards are cached per person", () => {
	for (const name of ["homeAnnouncements", "allAnnouncements"]) {
		assert.match(resource(name), /personalCacheKey\(/, `${name} is personally keyed`)
	}
})

test("the detail is not cached, because fetching it records the read", () => {
	const detail = resource("announcementDetail")
	assert.doesNotMatch(detail, /cache:/, "a cached detail never reaches the server")
	assert.match(detail, /get_announcement/, "and it is the endpoint that marks it read")
})

test("nothing fetches on import", () => {
	// A module-level auto-fetch runs on every screen that imports it, including
	// the login screen, where it 403s and logs noise.
	for (const name of [
		"homeAnnouncements",
		"allAnnouncements",
		"announcementDetail",
		"acknowledgeAnnouncement",
	]) {
		assert.match(resource(name), /auto: false/, `${name} waits to be asked`)
	}
})

test("a reload refreshes both boards", () => {
	const fn = code.slice(code.indexOf("export async function reloadAnnouncements"))
	assert.match(fn, /homeAnnouncements\.fetch\(\)/)
	assert.match(fn, /allAnnouncements\.fetch\(\)/)
	// One failing board must not stop the other refreshing: they are
	// independent reads, and leaving one stale is the bug this function exists
	// to prevent.
	// `?.catch?.`: fetch() can return nothing when frappe-ui skips a request.
	assert.equal((fn.match(/\?\.catch\?\.\(\(\) => \{\}\)/g) || []).length, 2, "each is independent")
})

test("every endpoint is under the announcements API", () => {
	// A resource pointed at the wrong module fails at runtime on the screen
	// that uses it, never at build.
	const urls = [...code.matchAll(/url: "([^"]+)"/g)].map((m) => m[1])
	assert.equal(urls.length, 4, "four endpoints")
	for (const url of urls) {
		assert.match(url, /^hrms\.api\.announcements\./, `${url} is not in this module`)
	}
})
