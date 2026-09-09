// Measure the 2.0 prototype at the reference viewport (390x844, CSS px).
// For every screen: content height, overflow past the fold (with the 78px tab
// bar and the sticky header), and the height of each top-level block, so the
// plan's scroll budget rests on numbers rather than on eyeballing.
//   cd frontend && node e2e/prototype-measure.mjs > ../docs/glass/audit/2026-09-09-prototype-measure.json
import { chromium } from "playwright"
import { pathToFileURL } from "node:url"
import path from "node:path"

const FILE = path.resolve(process.env.PROTOTYPE || "../Nadi PWA UI UX 2.0/nadi-prototype.html")
const W = 390, H = 844
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
await page.goto(pathToFileURL(FILE).href)
await page.waitForTimeout(300)

const screens = await page.$$eval("section.screen", (els) => els.map((e) => e.id))
const out = { viewport: { W, H }, screens: [], sheets: [] }
for (const id of screens) {
	await page.evaluate((id) => {
		// approver view so "Needs you" and Approvals are populated
		if (typeof ROLE !== "undefined" && ROLE !== "approver") toggleRole()
		if (id === "s-approvals") { curTab = "s-home" }
		show(id)
		window.scrollTo(0, 0)
	}, id)
	await page.waitForTimeout(80)
	const m = await page.evaluate(() => {
		const sec = document.querySelector("section.screen.on")
		const tabs = document.getElementById("tabs")
		const tabsShown = tabs && getComputedStyle(tabs).display !== "none"
		const tabH = tabsShown ? tabs.getBoundingClientRect().height : 0
		const blocks = [...sec.children].map((c) => {
			const r = c.getBoundingClientRect()
			const label = (c.className || c.tagName).toString().split(" ")[0] + (c.id ? "#" + c.id : "")
			const text = (c.textContent || "").trim().replace(/\s+/g, " ").slice(0, 40)
			return { block: label, top: Math.round(r.top + window.scrollY), height: Math.round(r.height), text }
		})
		const content = Math.round(sec.getBoundingClientRect().height)
		const fold = innerHeight - tabH
		return { content, tabH, fold, overflow: Math.max(0, content - fold), blocks, title: (sec.querySelector("h1")?.textContent || "").trim() }
	})
	out.screens.push({ id, ...m })
}
// sheets: open each and measure its height
for (const sid of ["sheet-new", "sheet-day", "sheet-cat", "sheet-rej", "sheet-wd"]) {
	await page.evaluate((sid) => { closeSheets(); if (sid === "sheet-day") { home("s-attend"); dayTap(2) } else openSheet(sid) }, sid)
	await page.waitForTimeout(350)
	const h = await page.$eval("#" + sid, (e) => Math.round(e.getBoundingClientRect().height))
	out.sheets.push({ id: sid, height: h, overFold: Math.max(0, h - Math.round(H * 0.86)) })
}
// the type and spacing scale actually used, read off computed styles
out.styles = await page.evaluate(() => {
	const pick = (sel) => { const e = document.querySelector(sel); if (!e) return null; const s = getComputedStyle(e); return { font: s.fontSize, weight: s.fontWeight, lh: s.lineHeight, pad: s.padding, radius: s.borderRadius, minH: s.minHeight, h: Math.round(e.getBoundingClientRect().height) } }
	return { hdrH1: pick(".hdr h1"), hdr: pick(".hdr"), card: pick(".card"), lrow: pick(".lrow"), cta: pick(".cta"), ghost: pick(".ghost"), mini: pick(".mini"), chip: pick(".chip"), tile: pick(".tile"), control: pick(".control"), big: pick(".big"), ttl: pick(".ttl"), sub: pick(".sub"), lbl: pick(".lbl"), sect: pick(".sect"), pill: pick(".pill"), tabs: pick(".tabs"), tabBtn: pick(".tabs button"), calDay: pick(".cal .d"), stats: pick(".stats div"), field: pick(".field"), summary: pick(".summary"), tgridBtn: pick(".tgrid button"), sheetH2: pick(".sheet h2"), srow: pick(".srow"), ecard: pick(".ecard") }
})
console.log(JSON.stringify(out, null, 1))
await browser.close()
