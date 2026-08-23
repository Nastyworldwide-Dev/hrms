import { test, chromium } from "@playwright/test"
import { writeFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

import { BASE, login, screens, settle } from "./screens.mjs"

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))))
const REPORT = join(ROOT, "design", "gates", ".coherence-report.json")

// Gate 8 — CROSS-SCREEN INVARIANTS (spec §16.5.3).
//
// Every other gate asks "is this screen right?" once per screen. None compares
// screen A to screen B, which is how the app ended up with six section-header
// treatments, a back control on 26 screens and not 12 with no rule connecting
// them, and one role rendered as a chartreuse GButton on dashboards and a white
// frappe-ui pill on lists.
//
// Collects a profile per screen; design/gates/coherence.mjs asserts the
// invariants over the whole set, so the rules live with the other gates.
//
// Runs in LIGHT theme deliberately. --accent-ink equals --brand in dark, so a
// brand/ink swap renders correctly there — the defect that started this was
// invisible to every dark-theme screenshot ever taken of this app.
test("coherence: profile every screen", async () => {
	test.setTimeout(20 * 60 * 1000)

	const browser = await chromium.launch()
	const state = await login(browser)
	const probe = await browser.newContext({ storageState: state })
	const list = await screens(probe.request)
	await probe.close()

	const profile = {}
	for (const anon of [false, true]) {
		const batch = list.filter((s) => !!s.anon === anon)
		if (!batch.length) continue
		const ctx = await browser.newContext({
			viewport: { width: 390, height: 844 },
			storageState: anon ? undefined : state,
			reducedMotion: "reduce",
		})
		await ctx.addInitScript(() => {
			localStorage.setItem("hrms:theme", "light")
			localStorage.setItem("hrms:reduce-transparency", "0")
		})
		const page = await ctx.newPage()

		for (const s of batch) {
			try {
				await page.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle", timeout: 35000 })
				await settle(page)
				profile[s.slug] = await page.evaluate(() => {
					// Resolve tokens THROUGH the engine — they are hex, and parsing
					// digits out of "#3F5C00" yields [3,5,0], which matches every
					// transparent element. That mistake produced a screenful of false
					// findings once already.
					const resolve = (tok) => {
						const el = document.createElement("span")
						el.style.color = `var(${tok})`
						document.body.appendChild(el)
						const v = getComputedStyle(el).color
						el.remove()
						return v
					}
					const BRAND = resolve("--g-brand")
					const INK = resolve("--g-accent-ink")
					const vis = (e) => {
						const cs = getComputedStyle(e)
						const r = e.getBoundingClientRect()
						return cs.display !== "none" && cs.visibility !== "hidden" && r.width > 2 && r.height > 2
					}

					const filled = []
					for (const e of document.querySelectorAll("button, a[href], [role=button], .g-btn")) {
						if (!vis(e)) continue
						const cs = getComputedStyle(e)
						const paint = cs.backgroundColor + " " + cs.backgroundImage
						const cls = (e.className || "").toString()
						const isG = cls.includes("g-btn")
						if (paint.includes(BRAND) || paint.includes(INK) || isG) {
							filled.push({
								label: (e.textContent || "").trim().slice(0, 30),
								fill: paint.includes(BRAND) ? "brand" : paint.includes(INK) ? "accent-ink" : "other",
								isGButton: isG,
							})
						}
					}

					const back = [...document.querySelectorAll("button, a[href]")].find(
						(e) => vis(e) && /^back$/i.test((e.getAttribute("aria-label") || "").trim())
					)

					// section headers: anything uppercase and small enough to read as one
					const eyebrows = [...document.querySelectorAll("*")]
						.filter((e) => {
							if (!vis(e)) return false
							const own = [...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join("")
							if (!own || own.length > 40) return false
							const cs = getComputedStyle(e)
							return cs.textTransform === "uppercase" && parseFloat(cs.fontSize) <= 13
						})
						.map((e) => ({
							usesClass: (e.className || "").toString().includes("g-eyebrow"),
							color: getComputedStyle(e).color,
							size: getComputedStyle(e).fontSize,
						}))

					return {
						filled,
						hasBack: !!back,
						adHocEmpty:
							!document.querySelector(".g-empty") &&
							!![...document.querySelectorAll("div,p")].find(
								(e) => vis(e) && /nothing|no .*(yet|found|added)|all caught up/i.test((e.textContent || "").slice(0, 80))
							),
						eyebrows,
					}
				})
			} catch (e) {
				profile[s.slug] = { error: String(e).split("\n")[0].slice(0, 120) }
			}
			console.info(`[coherence] ${s.slug}`)
		}
		await ctx.close()
	}

	await browser.close()
	mkdirSync(dirname(REPORT), { recursive: true })
	writeFileSync(REPORT, JSON.stringify(profile, null, 2))
	console.info(`[coherence] profiled ${Object.keys(profile).length} screens`)
})
