import pkg from "/home/nabil/nz-version-16/frontend/node_modules/playwright/index.js"
import fs from "node:fs"
import { BASE, login, screens, settle } from "../../../frontend/e2e/screens.mjs"
const { chromium } = pkg


const OUT = "/home/nabil/nz-version-16/docs/glass/audit/screens"
fs.mkdirSync(OUT, { recursive: true })

const VIEWPORTS = [
	{ w: 390, h: 844, dsf: 2, tag: "390" },
	{ w: 768, h: 1024, dsf: 1, tag: "768" },
	{ w: 1440, h: 900, dsf: 1, tag: "1440" },
]

const browser = await chromium.launch()

// ---- session -------------------------------------------------------------
const state = await login(browser)

// ---- screens ------------------------------------------------------------
// The list is shared with the a11y and visual gates (frontend/e2e/screens.mjs).
// One list: a route added there is audited AND gated, with no second edit.
const api = await browser.newContext({ storageState: state })
const ALL = await screens(api.request)
await api.close()
console.log(`SCREENS ${ALL.length}`)

const ONLY = process.env.ONLY ? process.env.ONLY.split(",") : null
const SCREENS = ALL.filter((s) => !ONLY || ONLY.includes(s.slug))

// ---- variants ------------------------------------------------------------
// 390 is the reference — both themes, plus bottom-of-scroll and reduce-transparency.
// 768/1440 get one shot per theme; the desktop column is what matters there.
const VARIANTS = [
	{ vp: "390", theme: "dark", rt: false, bottom: true },
	{ vp: "390", theme: "light", rt: false, bottom: true },
	{ vp: "390", theme: "dark", rt: true, bottom: false },
	{ vp: "768", theme: "dark", rt: false, bottom: false },
	{ vp: "768", theme: "light", rt: false, bottom: false },
	{ vp: "1440", theme: "dark", rt: false, bottom: false },
	{ vp: "1440", theme: "light", rt: false, bottom: false },
]


// A per-screen deadline. `goto` has its own timeout, but nothing else here did:
// a page that never settles could block `evaluate`, `waitForTimeout` or
// `screenshot` indefinitely and take the whole run with it — 38 screens x 7
// variants is a long time to discover one wedged page. Whatever happens, the
// run logs it and moves to the next screen.
const SCREEN_DEADLINE_MS = Number(process.env.SCREEN_DEADLINE_MS || 90000)

function withDeadline(promise, ms, label) {
	let timer
	const deadline = new Promise((_, reject) => {
		timer = setTimeout(() => reject(new Error(`deadline ${ms}ms exceeded: ${label}`)), ms)
	})
	return Promise.race([promise, deadline]).finally(() => clearTimeout(timer))
}

const manifest = []

for (const v of VARIANTS) {
	const vp = VIEWPORTS.find((x) => x.tag === v.vp)
	for (const anon of [false, true]) {
		const screens = SCREENS.filter((s) => s.path && !!s.anon === anon)
		if (!screens.length) continue
		const ctx = await browser.newContext({
			viewport: { width: vp.w, height: vp.h },
			deviceScaleFactor: vp.dsf,
			storageState: anon ? undefined : state,
			reducedMotion: "reduce",
		})
		await ctx.addInitScript(
			([theme, rt]) => {
				localStorage.setItem("hrms:theme", theme)
				localStorage.setItem("hrms:reduce-transparency", rt ? "1" : "0")
			},
			[v.theme, v.rt]
		)
		let page = await ctx.newPage()
		const errs = []
		page.on("console", (m) => { if (m.type() === "error") errs.push(m.text().slice(0, 300)) })
		page.on("pageerror", (e) => errs.push("PAGEERROR " + String(e).slice(0, 300)))

		for (const s of screens) {
			const suffix = `${v.vp}-${v.theme}${v.rt ? "-rt" : ""}`
			// single dash, not "__": Playwright sanitises a double underscore to a
			// dash when it resolves a snapshot path, so `__` names could never be
			// the visual gate's baselines — it silently built a parallel set.
			const base = `${s.slug}-${suffix}`
			errs.length = 0
			let note = "ok"
			const started = Date.now()
			try {
				await withDeadline((async () => {
				await page.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle", timeout: 35000 })
				await page.waitForTimeout(2200)
				const landed = new URL(page.url()).pathname.replace("/hrms", "") || "/"
				if (landed !== s.path && !s.path.includes(landed)) note = `redirected to ${landed}`
				await page.screenshot({ path: `${OUT}/${base}.png` })
				if (v.bottom) {
					// Scroll EVERY scrollable box, not just ion-content. Ionic
					// scrolls inside ion-content, but FormView and ListView each
					// own an inner `overflow-y-auto` div — scrolling only the
					// outer one left every form and detail screen looking like it
					// could not scroll at all, and the first audit pass recorded
					// that as a defect when it was an artifact of this function.
					await page.evaluate(async () => {
						const c = document.querySelector("ion-content")
						if (c?.scrollToBottom) await c.scrollToBottom(0)
						for (const el of document.querySelectorAll("*")) {
							const cs = getComputedStyle(el)
							if (/(auto|scroll)/.test(cs.overflowY) && el.scrollHeight > el.clientHeight + 4) {
								el.scrollTop = el.scrollHeight
							}
						}
						window.scrollTo(0, document.body.scrollHeight)
					})
					await page.waitForTimeout(900)
					await page.screenshot({ path: `${OUT}/${base}-bottom.png` })
				}
				})(), SCREEN_DEADLINE_MS, base)
			} catch (e) {
				note = "CAPTURE FAIL " + String(e).split("\n")[0].slice(0, 140)
				// A wedged page can leave the tab unusable for the next screen,
				// so give the context a fresh one rather than cascading failures.
				try {
					await page.close({ runBeforeUnload: false })
				} catch {}
				page = await ctx.newPage()
				page.on("console", (m) => { if (m.type() === "error") errs.push(m.text().slice(0, 300)) })
				page.on("pageerror", (err) => errs.push("PAGEERROR " + String(err).slice(0, 300)))
			}
			const took = Date.now() - started
			manifest.push({ file: base, slug: s.slug, path: s.path, ...v, note, ms: took, errors: [...new Set(errs)] })
			console.log(
				`${base}  ${note}` +
					(took > 15000 ? `  [SLOW ${Math.round(took / 1000)}s]` : "") +
					(errs.length ? `  [${errs.length} console errors]` : "")
			)
		}
		await ctx.close()
	}
}

fs.writeFileSync(`${OUT}/../manifest.json`, JSON.stringify(manifest, null, 2))
console.log("DONE " + manifest.length + " captures")
await browser.close()
