// Who to ask (alpha.5): your manager first, then HR, as plain rows with Call
// and Email links. Help opens it as a sheet; /hr-contacts renders the same
// component. The empty copy used to tell an EMPLOYEE to "ask your
// administrator to assign the HR Manager or HR User role" — a Desk job.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { parse } from "@vue/compiler-sfc"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const who = parse(read("../WhoToAsk.vue")).descriptor
const markup = who.template.content
const script = who.scriptSetup.content

test("the empty HR list says so plainly, never 'assign roles'", () => {
	// The words live in the script since alpha.9 D4 (a row label; the
	// apostrophe cannot sit in a single-quoted template attribute).
	assert.match(script, /__\("HR hasn't listed contacts yet\."\)/)
	for (const file of ["../WhoToAsk.vue", "../../views/HRContacts.vue"]) {
		assert.doesNotMatch(read(file), /administrator|assign the HR/i, file)
	}
})

test("your manager comes first, then HR, as rows with call and email links", () => {
	assert.match(script, /hrms\.api\.hr_contacts\.get_reporting_manager/)
	assert.match(script, /hrContactsResource/)
	assert.ok(markup.indexOf(`__("Your manager")`) < markup.indexOf(`__("HR")`))
	assert.match(markup, /<ContactCard v-if="manager\.data"/)
	assert.match(markup, /<ContactCard v-for="contact in hrContacts\.data/)
	const card = read("../ContactCard.vue")
	assert.match(card, /<GListRow/)
	assert.match(card, /:href="`tel:\$\{contact\.phone\}`"/)
	assert.match(card, /:href="`mailto:\$\{contact\.email\}`"/)
})

test("Help opens it as a sheet; /hr-contacts renders the same component", () => {
	const hub = read("../../views/helpdesk/HelpdeskHub.vue")
	assert.match(hub, /<GModal[^>]*:title="__\('Who to ask'\)"[\s\S]*?<WhoToAsk \/>/)
	assert.doesNotMatch(hub, /name: 'HRContacts'/, "no longer routes away")
	assert.match(read("../../views/HRContacts.vue"), /<WhoToAsk\b/)
})
