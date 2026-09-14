// Hotfix 14 Sep 2026: a reports_to-only manager saw no Cancel on an approved
// request. For an approved request the PWA now asks the server
// (hrms.api.approval.can_cancel_approved) — once per request revision — instead
// of guessing from roles and the approver field.
// Run: cd frontend && node --experimental-test-module-mocks --test tests/approved-cancel.test.mjs
import test, { mock } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { nextTick, reactive, ref } from "vue"

const created = []
mock.module("frappe-ui", {
	namedExports: {
		// frappe-ui resources are reactive: data arriving updates computeds.
		createResource(options) {
			const resource = reactive({ options, data: null, fetches: 0 })
			resource.fetch = () => {
				resource.fetches += 1
				return Promise.resolve()
			}
			created.push(resource)
			return resource
		},
	},
})
const { default: useApprovedCancel } = await import(
	"../src/composables/approvedCancel.js"
)

test("asks the server once per revision and shows Cancel only when it says yes", async () => {
	created.length = 0
	const target = ref({ doctype: "OT Request", name: "OT-1", modified: "m1" })
	const allowed = useApprovedCancel(() => target.value)
	assert.equal(created.length, 1)
	assert.equal(created[0].options.url, "hrms.api.approval.can_cancel_approved")
	assert.deepEqual(created[0].options.params, {
		doctype: "OT Request",
		name: "OT-1",
	})
	assert.equal(created[0].fetches, 1)
	assert.equal(allowed.value, false, "nothing shown before the answer")

	created[0].data = { can_cancel: true, reason: null }
	assert.equal(allowed.value, true)

	target.value = { ...target.value } // same revision: no second request
	await nextTick()
	assert.equal(created.length, 1)

	target.value = { doctype: "OT Request", name: "OT-1", modified: "m2" }
	await nextTick()
	assert.equal(created.length, 2, "a new revision is asked again")
	assert.equal(allowed.value, false, "the old answer does not carry over")
	created[1].data = {
		can_cancel: false,
		reason: "Only HR or the approver can cancel an approved request.",
	}
	assert.equal(allowed.value, false)
})

test("no target (not an approved request) means no request and no Cancel", async () => {
	created.length = 0
	const target = ref(null)
	const allowed = useApprovedCancel(() => target.value)
	assert.equal(created.length, 0)
	assert.equal(allowed.value, false)
})

test("both Cancel buttons use the server answer for approved requests", () => {
	const read = (p) =>
		readFileSync(new URL(p, import.meta.url), "utf8").replaceAll("'", '"')
	const offer =
		/\(cancelOffer === "approved" && approvedCancel(\.value)?\) \|\|\s*\(cancelOffer === "own" && hasPermission\("cancel"\)\)/
	for (const path of [
		"../src/components/RequestActionSheet.vue",
		"../src/components/FormView.vue",
	]) {
		const src = read(path)
		assert.match(
			src,
			/import useApprovedCancel from "@\/composables\/approvedCancel"/,
			path
		)
		assert.match(src, /useApprovedCancel\(/, path)
		assert.match(src, offer, path)
		assert.match(
			src,
			/url: "hrms\.api\.approval\.finalize"/,
			`${path} cancels through finalize`
		)
	}
})
