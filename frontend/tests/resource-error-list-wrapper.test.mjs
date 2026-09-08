// A failed list fetch must show its error, and an unconfirmed page must not
// read as "all caught up".
//
// N05 (8 Sep 2026 notifications audit, part 2): screens hand ResourceError the
// createListResource WRAPPER, but a list's request — and so its error and
// loading — lives on `.list`; `wrapper.error` is always undefined. A failed
// notifications/tickets/issues fetch therefore drew nothing, and the feed's
// empty state, gated on `data && !data.length`, showed "You are all caught
// up" over a cached empty page while the reload was failing or still running.
// Executes ResourceError's real <script setup> in a VM (the way the calendar
// and ticket tests do) and pins the feed's empty-state gate at source.
//   node --test tests/resource-error-list-wrapper.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { computed, reactive, ref } from "vue"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const script = (path) => read(path).split("<script setup>")[1].split("</script>")[0]
const executable = (text) =>
	text.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "").replace(/export /g, "")

function errorComponent(resource) {
	const context = vm.createContext({
		computed,
		reactive,
		ref,
		console: { info() {} },
		useRouter: () => ({}),
		inject: () => (s) => s,
		defineProps: (def) => ({ resource, what: "", back: false }),
	})
	vm.runInContext(executable(script("../src/components/ResourceError.vue")), context)
	return {
		failed: () => vm.runInContext("failed.value", context),
		loading: () => vm.runInContext("loading.value", context),
	}
}

test("a list wrapper whose request failed shows the error and its loading state", () => {
	const wrapper = reactive({ data: [], list: { error: new Error("403"), loading: false }, reload() {} })
	const c = errorComponent(wrapper)
	assert.equal(c.failed(), true, "the error lives on .list, not on the wrapper")
	wrapper.list.loading = true
	assert.equal(c.loading(), true)
})

test("a healthy list wrapper and a plain resource still behave", () => {
	assert.equal(errorComponent({ data: [], list: { error: null, loading: false } }).failed(), false)
	assert.equal(errorComponent({ error: "boom", loading: false, reload() {} }).failed(), true)
	assert.equal(errorComponent(undefined).failed(), false, "a missing resource never throws")
})

test("the feed says 'all caught up' only after its own request answered empty", () => {
	const view = read("../src/views/Notifications.vue")
	assert.match(view, /<GEmptyState\s+v-if="feedIsEmpty"/, "the empty state is gated on feedIsEmpty")
	const gate = view.match(/const feedIsEmpty = computed\(([\s\S]*?)\)\n/)?.[1] || ""
	for (const term of ["notifications.list.fetched", "!notifications.list.loading", "!notifications.list.error"]) {
		assert.ok(gate.includes(term), `feedIsEmpty must require ${term}`)
	}
})
