// alpha.10 A3-A4 (owner, 25 Sep 2026: "another old frappe design … many look
// badly hand-rolled"). These screens were rebuilt on the Glass kit; this keeps
// hand-drawn controls from coming back: no raw <textarea> or <select>, no
// Tailwind-painted buttons, no lime surfaces.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const template = (src) => src.slice(src.indexOf("<template>"), src.indexOf("<script"))

const REBUILT = [
	"../RemoteCheckinDialog.vue",
	"../LateCheckoutDialog.vue",
	"../PushNotificationPrompt.vue",
	"../../views/sop/SopList.vue",
	"../../views/sop/SopFormSheet.vue",
	"../../views/issues/HRIssueBoard.vue",
]

for (const file of REBUILT) {
	test(`${file} is built from the kit`, () => {
		const t = template(read(file))
		assert.doesNotMatch(t, /<textarea\b/, "a raw textarea")
		assert.doesNotMatch(t, /<select\b/, "a raw select")
		assert.doesNotMatch(t, /<button[^>]*class="[^"]*\b(px-3\.5|py-3|border-accent-ink|bg-accent-ink|bg-brand)\b/, "a hand-painted button")
		assert.doesNotMatch(t, /\bbg-brand\/15\b|\bbg-accent-ink\b/, "lime used as a surface")
	})
}
