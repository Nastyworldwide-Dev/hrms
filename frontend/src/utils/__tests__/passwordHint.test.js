// alpha.14 N (27 Sep 2026 sweep): Change password showed three "Required"
// rows and said nothing about what a new password needs until the server
// refused it. The rule is the site's own (System Settings: password policy
// and minimum score), judged by Frappe's test_password_strength, so the
// screen asks that as the person types and shows its words under the field.
// No policy on the site: nothing is shown — the app never invents a rule.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { passwordHint } from "../passwordHint.js"

test("no policy on the site: no hint", () => {
	assert.deepEqual(passwordHint({}), { text: "", ok: true })
	assert.deepEqual(passwordHint(null), { text: "", ok: true })
})

test("a weak password: Frappe's own warning and first suggestion", () => {
	const r = { score: 1, feedback: { password_policy_validation_passed: false, warning: "This is a top-10 common password.", suggestions: ["Add another word or two."] } }
	assert.deepEqual(passwordHint(r), { text: "This is a top-10 common password. Add another word or two.", ok: false })
})

test("a weak password with no words from Frappe still says it is too weak", () => {
	assert.deepEqual(passwordHint({ score: 0, feedback: { password_policy_validation_passed: false, warning: "", suggestions: [] } }), { text: "Too easy to guess. Try a longer one.", ok: false })
})

test("a strong enough password says so", () => {
	assert.deepEqual(passwordHint({ score: 4, feedback: { password_policy_validation_passed: true } }), { text: "Strong enough.", ok: true })
})

test("the screen asks Frappe as the person types, and shows the hint under the group", () => {
	const view = readFileSync(fileURLToPath(new URL("../../views/ChangePassword.vue", import.meta.url)), "utf8")
	assert.match(view, /frappe\.core\.doctype\.user\.user\.test_password_strength/)
	assert.match(view, /<p v-if="hint\.text" class="g-form-footer"[^>]*>/)
})
