// Measure the SHIPPED PWA at the reference viewport (390x844): per route, the
// scrollable content height, the fold left after the tab bar, the overflow past
// it, and where the first primary action sits. The 2.0 plan's scroll budget
// compares these numbers with e2e/prototype-measure.mjs.
//   cd frontend && set -a && . ../.env && set +a && node e2e/app-measure.mjs > ../docs/glass/audit/2026-09-09-app-measure.json
import { chromium } from "playwright"
import { BASE, login, screens, settle } from "./screens.mjs"

const W = Number(process.env.W || 390), H = Number(process.env.H || 844)
const browser = await chromium.launch()
const state = await login(browser)
const ctx = await browser.newContext({ storageState: state, viewport: { width: W, height: H }, deviceScaleFactor: 1, colorScheme: "light" })
const page = await ctx.newPage()
const list = await screens(ctx.request)
const out = { viewport: { W, H }, base: BASE, screens: [] }
for (const s of list) {
	if (s.anon) continue
	try {
		await page.goto(`${BASE}/hrms${s.path}`, { waitUntil: "domcontentloaded", timeout: 35000 })
		await settle(page)
		await page.waitForTimeout(400)
		const m = await page.evaluate(() => {
			const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" }
			// tallest scroll container actually in use
			let content = document.scrollingElement.scrollHeight, scroller = "document"
			const cands = [...document.querySelectorAll("*")].filter((e) => { const o = getComputedStyle(e).overflowY; return (o === "auto" || o === "scroll") && e.clientHeight > 100 && vis(e) })
			for (const e of cands) if (e.scrollHeight > content) { content = e.scrollHeight; scroller = (e.tagName + (e.className ? "." + String(e.className).split(" ")[0] : "")).slice(0, 40) }
			for (const ic of document.querySelectorAll("ion-content")) { const inner = ic.shadowRoot?.querySelector(".inner-scroll"); if (inner && inner.scrollHeight > content) { content = inner.scrollHeight; scroller = "ion-content" } }
			const tab = [...document.querySelectorAll("nav, [role=tablist], ion-tab-bar")].find((e) => vis(e) && e.getBoundingClientRect().bottom >= innerHeight - 2)
			const tabH = tab ? Math.round(innerHeight - tab.getBoundingClientRect().top) : 0
			const header = [...document.querySelectorAll("header, ion-header, [class*=hdr], [class*=header]")].find(vis)
			const headerH = header ? Math.round(header.getBoundingClientRect().height) : 0
			const h1 = document.querySelector("h1, h2")
			const buttons = [...document.querySelectorAll("button, a, [role=button]")].filter(vis)
			const primary = buttons.find((b) => /primary|cta|accent|solid|is-primary|g-button--primary|bg-accent/i.test(b.className) || /^(check in|check out|apply|submit|save|claim|new|approve|request)/i.test((b.textContent || "").trim()))
			const primaryY = primary ? Math.round(primary.getBoundingClientRect().top + (scroller === "document" ? scrollY : 0)) : null
			const fold = innerHeight - tabH
			return { content: Math.round(content), scroller, tabH, headerH, fold, overflow: Math.max(0, Math.round(content) - fold), title: (h1?.textContent || document.title).trim().slice(0, 40), tappables: buttons.length, primary: primary ? (primary.textContent || "").trim().slice(0, 30) : null, primaryY }
		})
		out.screens.push({ slug: s.slug, path: s.path, ...m })
	} catch (e) {
		out.screens.push({ slug: s.slug, path: s.path, error: String(e.message || e).slice(0, 120) })
	}
}
console.log(JSON.stringify(out, null, 1))
await browser.close()
