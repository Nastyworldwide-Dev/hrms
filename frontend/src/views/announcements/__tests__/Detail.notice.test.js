// The notice (owner-approved mockup, 27 Oct 2026): eyebrow, title, ONE meta line, the summary as a
// lead paragraph, the cover, an Event's "When" row, then the body. The must-read block is pinned
// elsewhere (must-read-tickbox.test.js) and is not touched here.
// Source-asserted because the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const raw = readFileSync(fileURLToPath(new URL("../Detail.vue", import.meta.url)), "utf8")
const src = raw.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
const at = (needle) => {
	const i = src.indexOf(needle)
	assert.ok(i >= 0, `${needle} is on the page`)
	return i
}

test("one meta caption: 'Posted D MMM · Shown until D MMM', from the shared rule", () => {
	assert.match(src, /import \{ noticeDates \} from "@\/utils\/announcementRow"/)
	assert.match(
		src,
		/noticeDates\(doc\.value, __, \(date\) => \$dayjs\(date\)\.format\("D MMM"\)\)/
	)
	assert.match(src, /<p v-if="dates" class="-mt-2 text-caption text-ink-700">\{\{ dates \}\}<\/p>/)
	assert.doesNotMatch(src, /D MMM YYYY/, "the old posted-only line is gone")
})

test("the summary is a lead paragraph, only when HR wrote one", () => {
	assert.match(src, /<p v-if="doc\.summary" class="g-ann-lead">\{\{ doc\.summary \}\}<\/p>/)
})

test("the lead is the one new class: larger than the body, secondary ink, in rem", () => {
	const css = readFileSync(
		fileURLToPath(new URL("../../../theme/glass-components.css", import.meta.url)),
		"utf8"
	)
	const rule = css.match(/\.g-ann-lead \{([^}]*)\}/)?.[1] ?? ""
	assert.match(rule, /font-size:\s*1\.125rem/)
	assert.match(rule, /color:\s*var\(--g-ink2\)/)
	assert.match(rule, /overflow-wrap:\s*anywhere/)
})

test("the cover is full width, rounded by a Glass token, 16:9, cropped to fit, decorative", () => {
	assert.match(
		src,
		/<img\s+v-if="doc\.cover_image"\s+:src="doc\.cover_image"\s+alt=""\s+class="w-full aspect-video rounded-card object-cover bg-icon-bg"\s*\/>/
	)
})

test("an Event shows a read-only 'When' row with its day", () => {
	assert.match(src, /<GListPanel v-if="doc\.category === 'Event' && doc\.event_date">/)
	assert.match(src, /<GListRow :label="__\('When'\)" :amount="eventDay" :tappable="false" \/>/)
	assert.match(src, /\$dayjs\(doc\.value\.event_date\)\.format\("ddd D MMM"\)/)
	assert.match(src, /import GListPanel from "@\/components\/glass\/GListPanel\.vue"/)
	assert.match(src, /import GListRow from "@\/components\/glass\/GListRow\.vue"/)
})

test("the page reads top to bottom as the mockup: eyebrow, title, meta, lead, cover, when, body", () => {
	const order = [
		'class="g-eyebrow"',
		"text-screen-title",
		"{{ dates }}",
		"{{ doc.summary }}",
		':src="doc.cover_image"',
		"__('When')",
		'v-html="safeHtml(doc.body)"',
		'ref="endMarker"',
	].map(at)
	assert.deepEqual(
		order,
		[...order].sort((a, b) => a - b)
	)
})

test("the body, the end marker and the must-read gate are as they were", () => {
	assert.match(src, /<div class="prose-sm text-inkbase" v-html="safeHtml\(doc\.body\)" \/>/)
	assert.match(src, /<div ref="endMarker" class="g-mustread__end" aria-hidden="true" \/>/)
	assert.match(src, /v-else-if="doc\.acknowledge_required && !preview && doc\.live !== false"/)
	assert.match(src, /<GBanner v-if="acknowledged" variant="info">/)
})
