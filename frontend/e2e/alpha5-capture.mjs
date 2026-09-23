// alpha.5 whole-app audit: every route × persona × viewport × theme.
// Screenshots go to OUT (never committed); one JSON of measurements per run.
//   cd frontend && set -a && . ../.env && set +a && node e2e/alpha5-capture.mjs
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs"
import { chromium } from "playwright"
import { BASE, PW, screens, settle } from "./screens.mjs"

const OUT = process.env.OUT || "/tmp/alpha5-shots"
mkdirSync(OUT, { recursive: true })

const ALL_PERSONAS = [
	["staff", process.env.HRMS_E2E_USER || "nurul.aisyah@nastyworldwide.com"],
	["approver", "nadi.w0.approver@example.invalid"],
	["manager", "nadi.w0.manager@example.invalid"],
]
const PERSONAS = ALL_PERSONAS.filter(([w]) => !process.env.WHO || process.env.WHO.split(",").includes(w))
const SHOTS = process.env.SHOTS !== "0"
const LOG = `${OUT}/measure.jsonl`
const VIEWPORTS = [
	["phone", 390, 844],
	["desktop", 1280, 800],
]
const THEMES = (process.env.THEMES || "dark,light").split(",")

// Routes screens.mjs does not list (found by reading src/router/*).
const EXTRA = [
	["help", "/support"],
	["help-it", "/support?tab=it"],
	["approvals", "/approvals"],
	["team-roster", "/team/roster"],
	["announcements", "/announcements"],
	["helpdesk-new", "/helpdesk/new"],
]

async function loginAs(browser, usr) {
	const ctx = await browser.newContext()
	const res = await ctx.request.post(`${BASE}/api/method/login`, { form: { usr, pwd: PW } })
	if (res.status() !== 200) {
		await ctx.close()
		return null
	}
	const state = await ctx.storageState()
	await ctx.close()
	return state
}

function measure() {
	const vis = (e) => {
		const r = e.getBoundingClientRect()
		const cs = getComputedStyle(e)
		return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none"
	}
	const all = [...document.querySelectorAll("*")].filter(vis)
	const blur = all.filter((e) => {
		const cs = getComputedStyle(e)
		const f = cs.backdropFilter || cs.webkitBackdropFilter
		return f && f !== "none"
	})
	const tappables = [...document.querySelectorAll("button, a[href], [role=button], ion-button, ion-item[button]")].filter(vis)
	const small = tappables.filter((e) => {
		const r = e.getBoundingClientRect()
		return r.width < 44 || r.height < 44
	})
	const texts = all.filter((e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
	const minFont = texts.reduce((m, e) => Math.min(m, parseFloat(getComputedStyle(e).fontSize)), 99)
	const rawIds = texts
		.map((e) => e.textContent.trim())
		.filter((t) => /\b(HR-[A-Z]{2,4}-\d|[A-Z]{2,5}-\d{4}-\d{3,})/.test(t))
		.slice(0, 5)
	const rows = [...document.querySelectorAll(".g-row, [class*=list-row], li")].filter(vis)
	const tallRows = rows.filter((r) => r.getBoundingClientRect().height > 88).length
	return {
		title: (document.querySelector("h1")?.textContent || "").trim().slice(0, 40),
		glassHeader: !!document.querySelector(".g-header"),
		legacyHeader: !!document.querySelector("header.border-b-2, ion-header, .border-b-2"),
		blurCount: blur.length,
		blurOn: [...new Set(blur.map((e) => (e.tagName.toLowerCase() + "." + String(e.className).split(" ")[0]).slice(0, 40)))],
		hScroll: document.documentElement.scrollWidth > innerWidth + 1,
		tappables: tappables.length,
		under44: small.length,
		minFont,
		rawIds,
		rows: rows.length,
		tallRows,
		frappeUi: document.querySelectorAll("button[class*='focus-visible:ring'], .form-control").length,
	}
}

const browser = await chromium.launch()
const out = []
for (const [who, usr] of PERSONAS) {
	const state = await loginAs(browser, usr)
	if (!state) {
		out.push({ who, error: "login failed" })
		continue
	}
	for (const theme of THEMES) {
		for (const [vp, W, H] of VIEWPORTS) {
			const ctx = await browser.newContext({ storageState: state, viewport: { width: W, height: H }, colorScheme: theme, deviceScaleFactor: 1 })
			const page = await ctx.newPage()
			const errors = []
			page.on("pageerror", (e) => errors.push(String(e).slice(0, 120)))
			const list = (await screens(ctx.request)).filter((s) => !s.anon).map((s) => [s.slug, s.path])
			for (const [slug, path] of [...list, ...EXTRA]) {
				errors.length = 0
				try {
					await page.goto(`${BASE}/hrms${path}`, { waitUntil: "domcontentloaded", timeout: 35000 })
					await settle(page)
					await page.waitForTimeout(500)
					const m = await page.evaluate(measure)
					const file = `${who}-${theme}-${vp}-${slug}.png`
					// Full page only for the staff dark set; the rest viewport-only.
					if (SHOTS) await page.screenshot({ path: `${OUT}/${file}`, fullPage: who === "staff" && theme === "dark" })
					const row = { who, theme, vp, slug, path, url: page.url().replace(BASE, ""), errors: [...errors], ...m, file }
					out.push(row)
					appendFileSync(LOG, JSON.stringify(row) + "\n")
				} catch (e) {
					out.push({ who, theme, vp, slug, path, error: String(e).slice(0, 160) })
				}
			}
			await ctx.close()
		}
	}
}
await browser.close()
writeFileSync(`${OUT}/measure.json`, JSON.stringify(out, null, 1))
console.log(`captured ${out.length} → ${OUT}`)
