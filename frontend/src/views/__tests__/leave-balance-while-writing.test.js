// alpha.14 M (27 Sep 2026 sweep): a sent leave request showed "Days left
// before this  19" — the balance as it stood when it was written, which reads
// as a live figure the employee cannot act on. The balance helps while
// choosing dates; once sent, Requests' balance card is the answer. Shown
// only on a new request, as "Days left".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { plainLabel } from "../../utils/plainLabel.js"

const form = readFileSync(fileURLToPath(new URL("../leave/Form.vue", import.meta.url)), "utf8")
const list = (name) => form.slice(form.indexOf(`const ${name} = [`), form.indexOf("]", form.indexOf(`const ${name} = [`)))

test("the balance is asked of a new request only", () => {
	assert.doesNotMatch(list("FIELDS"), /"leave_balance"/)
	assert.match(list("FIELDS_ON_NEW"), /"leave_balance"/)
	assert.match(form, /props\.id \? \[\.\.\.FIELDS, \.\.\.FIELDS_ON_EXISTING\] : \[\.\.\.FIELDS, \.\.\.FIELDS_ON_NEW\]/)
})

test("it reads Days left", () => {
	assert.equal(plainLabel("Leave Balance Before Application"), "Days left")
})
