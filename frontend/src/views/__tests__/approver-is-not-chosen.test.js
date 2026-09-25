// Nobody chooses their approver (owner, 25 Sep 2026: "never to the director,
// only their own approver; nobody is supposed to choose"). Each request form
// shows ONE approver, read-only: the person's own. The server sets it anyway
// (hrms.hr.utils.validate_staff_approver), so the form cannot route elsewhere.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

for (const [file, field] of [
	["../leave/Form.vue", "leave_approver"],
	["../expense_claim/Form.vue", "expense_approver"],
	["../attendance/ShiftRequestForm.vue", "approver"],
]) {
	test(`${file}: the approver is their own, read-only`, () => {
		const src = read(file)
		assert.match(src, /approverOptions\([^)]*\)\.slice\(0, 1\)/, "only their own approver is offered")
		assert.match(src, new RegExp(`${field === "approver" ? "approver" : field}\\.read_only = 1`), "and it cannot be changed")
	})
}

test("the check-in toast names the approver, never their login", () => {
	const panel = read("../../components/CheckInPanel.vue")
	assert.match(panel, /approverName: doc\.approver_name \|\| ""/)
	assert.doesNotMatch(panel, /approverName: req\.approver/)
})

test("the banner keeps to two lines and clears the status bar", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /#frappeui-toast-root p \+ p \{[^}]*-webkit-line-clamp: 2;/)
	assert.match(css, /#frappeui-toast-root \{\s*padding-top: env\(safe-area-inset-top, 0px\);/)
})
