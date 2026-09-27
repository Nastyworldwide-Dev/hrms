// alpha.14 slice 0: the installed-iPhone journey (device.mjs). What a person
// does, not a URL typed cold: open Home, scroll, tap each tab, scroll it,
// switch away and back, pull to the top. Measured at every stop:
//   J1 the bar's small title and the large title are never both showing
//   J2 the large title sits directly under the bar's row (Apple "Layout":
//      status bar + 44 pt bar row), no extra band of chrome above it
//   J3 nothing interactive sits under the status bar or the home indicator
//   J4 the tab bar clears the home indicator
//   cd frontend && set -a && . ../.env && set +a && node e2e/device-journey-audit.mjs
import { mkdirSync, writeFileSync } from "node:fs"
import { webkit } from "playwright"
import { BASE, PW } from "./screens.mjs"
import { IPHONE, installedContext } from "./device.mjs"
import { TAB_ROUTES } from "./tabRoutes.mjs"

const OUT = process.env.OUT || "/tmp/a14/device"
const SHOTS = process.env.SHOTS === "1"
mkdirSync(OUT, { recursive: true })
const b = await webkit.launch()
const ctx = await installedContext(b, { scheme: process.env.SCHEME || "light" })
await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: process.env.WHO_USER || "nadi.w0.approver@example.invalid", pwd: PW } })
const p = await ctx.newPage()

const measure = () =>
	p.evaluate(({ top, bottom, height }) => {
		const page = document.querySelector("ion-router-outlet .ion-page:not(.ion-page-hidden) .ion-page:not(.ion-page-hidden)") ||
			[...document.querySelectorAll(".ion-page:not(.ion-page-hidden)")].pop()
		const box = (e) => e && e.getBoundingClientRect()
		const shown = (e) => {
			if (!e) return false
			const r = e.getBoundingClientRect()
			const cs = getComputedStyle(e)
			return r.width > 0 && r.height > 0 && Number(cs.opacity) > 0.5 && cs.visibility !== "hidden" && r.bottom > 0 && r.top < innerHeight
		}
		const large = page?.querySelector(".g-large-title")
		const mini = page?.querySelector(".g-header__mini")
		const header = page?.querySelector(".g-header")
		const tabbar = document.querySelector("ion-tab-bar")
		const scroller = page?.querySelector("ion-content")
		const lr = box(large)
		const hr = box(header)
		// visible part of the large title: below the bar's bottom edge
		const largeShown = shown(large) && lr.bottom > (hr ? hr.bottom : 0) + 4
		const issues = []
		if (largeShown && shown(mini)) issues.push("J1 small and large title both showing")
		const controls = [...(header?.querySelectorAll("button, a, [role=button]") || [])].filter(shown)
		const firstRowTop = controls.length ? Math.min(...controls.map((c) => box(c).top)) : hr ? hr.top : null
		if (firstRowTop !== null && firstRowTop < top - 0.5) issues.push(`J3 bar control under the status bar at y ${Math.round(firstRowTop)}`)
		// Apple: the large-title row starts under status bar + 44 pt bar row
		if (lr && shown(large)) {
			const expected = top + 44
			const gap = Math.round(lr.top - expected)
			if (gap > 12) issues.push(`J2 large title ${gap} pt lower than under the bar row (y ${Math.round(lr.top)} vs ${expected})`)
		}
		const tr = box(tabbar)
		if (tr && tr.height && tr.bottom > height - bottom + 0.5) issues.push(`J4 tab bar reaches y ${Math.round(tr.bottom)}, into the home indicator (starts ${height - bottom})`)
		return {
			issues,
			largeTop: lr && Math.round(lr.top),
			headerTop: hr && Math.round(hr.top),
			headerBottom: hr && Math.round(hr.bottom),
			firstRowTop: firstRowTop && Math.round(firstRowTop),
			tabBottom: tr && Math.round(tr.bottom),
			miniShown: shown(mini),
			largeShown,
			scrolled: scroller ? null : null,
		}
	}, { top: IPHONE.top, bottom: IPHONE.bottom, height: IPHONE.height })

async function scrollTo(y) {
	await p.evaluate(async (y) => {
		const c = [...document.querySelectorAll(".ion-page:not(.ion-page-hidden) ion-content")].pop()
		await c?.scrollToPoint?.(0, y, 0)
	}, y)
	await p.waitForTimeout(500)
}
async function tab(route) {
	await p.locator(`ion-tab-button[href$="${route}"], ion-tab-button[tab="${route}"]`).first().click({ timeout: 8000 }).catch(async () => {
		await p.goto(`${BASE}/hrms${route}`, { waitUntil: "networkidle" })
	})
	await p.waitForTimeout(900)
}

const stops = []
const stop = async (label) => {
	const m = await measure()
	stops.push({ stop: label, ...m })
	if (SHOTS) await p.screenshot({ path: `${OUT}/${String(stops.length).padStart(2, "0")}-${label.replace(/\W+/g, "_")}.png` })
}
await p.goto(`${BASE}/hrms/home`, { waitUntil: "networkidle", timeout: 40000 })
await p.waitForTimeout(1500)
await stop("home cold")
for (const route of TAB_ROUTES) {
	await tab(route)
	await stop(`${route} open`)
	await scrollTo(400)
	await stop(`${route} scrolled`)
	await tab(TAB_ROUTES[0] === route ? TAB_ROUTES[1] : TAB_ROUTES[0])
	await tab(route)
	await stop(`${route} back again`)
	await scrollTo(0)
	await stop(`${route} top`)
	// half the large title under the bar: the moment the two titles overlap
	await scrollTo(24)
	await stop(`${route} half scrolled`)
	await scrollTo(0)
	// a pushed screen and Back (the bell), then the tab again
	await p.locator(".ion-page:not(.ion-page-hidden) .g-header__action").first().click({ timeout: 5000 }).catch(() => {})
	await p.waitForTimeout(900)
	await p.goBack()
	await p.waitForTimeout(900)
	await stop(`${route} after a pushed screen`)
}
writeFileSync(`${OUT}/journey.json`, JSON.stringify(stops, null, 1))
const bad = stops.filter((s) => s.issues.length)
for (const s of bad) console.log(`${s.stop}: ${s.issues.join("; ")}`)
const n = bad.reduce((a, s) => a + s.issues.length, 0)
console.log(`${stops.length} stops`)
console.log(`GATE_COUNT ${n}`)
await b.close()
process.exit(n ? 1 : 0)
