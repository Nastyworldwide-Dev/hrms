// Every sheet is one kind of sheet (owner, 23 Sep; Apple HIG Sheets):
// a pinned bar with a grabber, the title centred and a Close X on the
// trailing edge. Raw <ion-modal> sites drew their own head (or none, or a
// text "Close"), so sheets looked different from screen to screen. GModal is
// the only door to ion-modal, and every GModal says what it is.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs"
import { join, relative } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../../", import.meta.url))
const read = (p) => readFileSync(p, "utf8")

function vueFiles(dir) {
	return readdirSync(dir).flatMap((name) => {
		const path = join(dir, name)
		if (statSync(path).isDirectory()) return name === "__tests__" ? [] : vueFiles(path)
		return name.endsWith(".vue") ? [path] : []
	})
}
const files = vueFiles(SRC).map((path) => ({ rel: relative(SRC, path), src: read(path) }))

//: Justified exceptions, one line each.
const RAW_MODAL_ALLOWED = new Set([
	// the one door
	"components/glass/GModal.vue",
])
const UNTITLED_ALLOWED = new Set([
	// the check-in sheet: the title IS the live clock + next action, drawn
	// by the sheet's own content
	"components/CheckInPanel.vue",
])
//: A sheet that only wraps one of these is exempt: they build their own head
//: from the record they show (kind of request + open-form link; who + when),
//: so a static title would say it twice. Follow-up: lift those heads into
//: GModal's title and drop this list.
const SELF_HEADED = /^\s*<(RequestActionSheet|CheckinDecisionSheet)\b/

test("no raw <ion-modal> outside GModal", () => {
	const offenders = files
		.filter((f) => /<ion-modal[\s>]/.test(f.src) && !RAW_MODAL_ALLOWED.has(f.rel))
		.map((f) => f.rel)
	assert.deepEqual(offenders, [])
})

test("CustomIonModal is gone", () => {
	assert.equal(existsSync(join(SRC, "components/CustomIonModal.vue")), false)
})

test("every <GModal> passes a title", () => {
	const offenders = []
	for (const f of files) {
		if (f.rel === "components/glass/GModal.vue" || UNTITLED_ALLOWED.has(f.rel)) continue
		for (const m of f.src.matchAll(/<GModal\b[^>]*>/g)) {
			const tag = m[0]
			if (/\s:?title=/.test(tag)) continue
			if (SELF_HEADED.test(f.src.slice(m.index + tag.length))) continue
			offenders.push(`${f.rel}: ${tag.replace(/\s+/g, " ")}`)
		}
	}
	assert.deepEqual(offenders, [])
})

const modal = read(join(SRC, "components/glass/GModal.vue"))

test("the head is a pinned bar: grabber, Close X (leading), centred title, confirm slot", () => {
	assert.match(
		modal,
		/<div class="g-sheet__head">\s*<span class="g-sheet__grabber" aria-hidden="true"/
	)
	assert.match(modal, /g-sheet__close[\s\S]*g-sheet__title[\s\S]*g-sheet__trail/)
	const css = read(join(SRC, "theme/glass-components.css"))
	assert.match(css, /\.g-sheet__head \{[^}]*position: sticky[^}]*top: 0/)
	assert.match(css, /\.g-sheet__bar \{[^}]*grid-template-columns: 44px 1fr 44px/)
	assert.match(css, /\.g-sheet__title \{[^}]*text-align: center/)
})

test("every sheet opens full height with the focus-trap breakpoints intact", () => {
	// A medium detent was tried (alpha.5) and opened with only the bar on
	// screen; the breakpoints are load-bearing for the focus-trap fix.
	assert.match(modal, /:initial-breakpoint="1"/)
	assert.match(modal, /:breakpoints="\[0, 1\]"/)
	assert.match(modal, /:backdrop-breakpoint="1"/)
})

test("More's holiday sheet is titled", () => {
	const more = read(join(SRC, "views/More.vue"))
	assert.match(more, /<GModal[^>]*:title="__\('Public holidays'\)"/)
})

test("the holiday list is flat and marks the next one", () => {
	const list = read(join(SRC, "components/HolidayList.vue"))
	assert.doesNotMatch(list, /<GListPanel v-else-if="upcoming/)
	assert.doesNotMatch(list, /<h2/)
	assert.match(list, /<GStatusChip[^>]*v-if="index === 0"/)
})
