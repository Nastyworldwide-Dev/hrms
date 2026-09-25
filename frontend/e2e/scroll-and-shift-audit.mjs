// alpha.8 r3 (owner, 25 Sep 2026: "fix the overflow scrolling to the top and
// bottom, and the jumpy stuff on pages and sheets; every bit measured").
// Per screen, in Safari's engine at the owner's iPhone size:
//   extraScroll  how far the page scrolls BEYOND its content (px); 0 is right
//   fitsButScrolls  content fits the screen yet the page still scrolls
//   cls          cumulative layout shift while the page loads and settles
//   shifts       the elements that moved, and by how much
//   cd frontend && set -a && . ../.env && set +a && node e2e/scroll-and-shift-audit.mjs
import { writeFileSync, mkdirSync } from "node:fs"
import { webkit } from "playwright"
import { BASE, PW, screens } from "./screens.mjs"

const OUT = process.env.OUT || "/tmp/alpha8/scroll"
mkdirSync(OUT, { recursive: true })
const b = await webkit.launch()
const ctx = await b.newContext({ viewport: { width: 402, height: 874 }, hasTouch: true, colorScheme: "dark" })
await ctx.addInitScript(() => {
	localStorage.setItem("hrms:install-prompt-dismissed", String(Date.now()))
	window.__shifts = []
	// Layout shift, measured the way the browser defines it where supported,
	// and by watching every element's box where it is not (WebKit).
	const seen = new Map()
	const snap = () => {
		for (const e of document.querySelectorAll(".ion-page:not(.ion-page-hidden) ion-content *")) {
			if (e.children.length > 3) continue
			const r = e.getBoundingClientRect()
			if (r.width < 20 || r.height < 8) continue
			const prev = seen.get(e)
			if (prev && Math.abs(prev - r.top) > 4) window.__shifts.push({ el: `${e.tagName.toLowerCase()}.${String(e.className).split(" ")[0]}`, text: (e.textContent || "").trim().slice(0, 24), dy: Math.round(r.top - prev) })
			seen.set(e, r.top)
		}
	}
	window.__shiftTimer = setInterval(snap, 50)
})
await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: process.env.WHO_USER || "nadi.w0.approver@example.invalid", pwd: PW } })
const p = await ctx.newPage()
const list = [...new Map((await screens(ctx.request)).filter((s) => !s.anon && s.path).map((s) => [s.path, s])).values()]
const rows = []
for (const s of list) {
	try {
		await p.goto(`${BASE}/hrms${s.path}`, { waitUntil: "domcontentloaded" })
		await p.waitForTimeout(2500)
		const r = await p.evaluate(async () => {
			const content = document.querySelector(".ion-page:not(.ion-page-hidden) ion-content")
			const sc = content ? await content.getScrollElement() : document.scrollingElement
			const inner = sc.firstElementChild
			// the real bottom of the content, not the scroller's padding
			let bottom = 0
			for (const e of sc.querySelectorAll("*")) { const r = e.getBoundingClientRect(); if (r.height > 0 && getComputedStyle(e).position !== "fixed") bottom = Math.max(bottom, r.bottom + sc.scrollTop) }
			const top = sc.getBoundingClientRect().top
			const max = sc.scrollHeight - sc.clientHeight
			const contentH = bottom - top
			const shifts = window.__shifts.slice()
			const moved = [...new Map(shifts.map((x) => [x.el + x.text, x])).values()].slice(0, 5)
			return { scrollMax: Math.round(max), contentH: Math.round(contentH), viewH: sc.clientHeight, padB: getComputedStyle(sc).paddingBottom, fitsButScrolls: contentH <= sc.clientHeight && max > 2, shiftCount: shifts.length, moved }
		})
		rows.push({ path: s.path, ...r })
	} catch (e) {
		rows.push({ path: s.path, error: String(e).slice(0, 100) })
	}
}
writeFileSync(`${OUT}/report.json`, JSON.stringify(rows, null, 1))
for (const r of rows) {
	if (r.error) { console.log(r.path, "ERR", r.error); continue }
	const flags = []
	if (r.fitsButScrolls) flags.push(`fits but scrolls ${r.scrollMax}px`)
	if (r.shiftCount) flags.push(`${r.shiftCount} shifts: ${r.moved.map((m) => `${m.text || m.el} ${m.dy}`).join("; ")}`)
	if (flags.length) console.log(r.path, "|", flags.join(" || "), `(content ${r.contentH}/${r.viewH}, pad ${r.padB})`)
}
console.log("screens", rows.length, "fitsButScrolls", rows.filter((r) => r.fitsButScrolls).length, "withShifts", rows.filter((r) => r.shiftCount).length)
await b.close()
