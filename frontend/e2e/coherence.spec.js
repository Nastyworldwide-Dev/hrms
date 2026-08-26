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
						return (
							cs.display !== "none" && cs.visibility !== "hidden" && r.width > 2 && r.height > 2
						)
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
								fill: paint.includes(BRAND)
									? "brand"
									: paint.includes(INK)
									? "accent-ink"
									: "other",
								isGButton: isG,
							})
						}
					}

					const back = [...document.querySelectorAll("button, a[href]")].find(
						(e) => vis(e) && /^back$/i.test((e.getAttribute("aria-label") || "").trim())
					)

					// Small uppercase text runs, CLASSIFIED — not counted.
					//
					// Reporting "225 uppercase runs, 225 not using .g-eyebrow" asserts
					// nothing: uppercase is also how this app draws chips, badges, tab
					// labels and button text, so most of that number is correct and the
					// rule it was gesturing at ("a SECTION HEADER uses .g-eyebrow") was
					// never actually tested. A gate that reports a number instead of
					// asserting a rule is the shape that lets a defect read green.
					//
					// The category is derived HERE, from the DOM, on every run — not
					// stored as a list of 225 approved strings, which would freeze at
					// the moment it was written and rot from the next component onward.
					// Anything that is not one of the known non-header roles is a
					// section header and must carry .g-eyebrow.
					// A role is DECLARED, never inferred from the words. Each entry is a
					// structural container or a role class the app already owns, so
					// adding one is a deliberate, reviewable edit here — the gate cannot
					// be quieted by sprinkling arbitrary classes on the markup.
					//
					// Order matters: a chip inside a button is a chip.
					const ROLES = [
						["tabbar", "ion-tab-bar, .g-tabbar"],
						["segmented", ".g-seg, ion-segment, .g-seg__option"],
						[
							"chip",
							".g-tag, .g-status-chip, .g-badge, [class*='chip'], [class*='badge'], [class*='status']",
						],
						// labels ONE control, not a group — §10's eyebrow is the group treatment
						["field-label", ".g-field__label"],
						// labels ONE number. g-poster__label is the poster variant of the
						// same role — "Total Claimed" over the RM figure — added with
						// .g-poster and never declared, so the gate filed it as an
						// undeclared section header.
						["stat-label", ".g-stat__label, .g-balance__label, .g-poster__label"],
						// labels a COLUMN
						["column-head", ".g-cal__dow, th, thead, [role='columnheader']"],
						// the label inside a date stepper — a control, not a heading
						["nav-label", ".g-datenav__label"],
						["interactive", "button, [role='button'], a[href], summary, label, .g-btn"],
						["header-meta", ".g-header__kicker, .g-header, ion-header"],
					]
					const classify = (e) => {
						for (const [role, sel] of ROLES) {
							if (e.closest(sel)) return role
						}
						return "section"
					}

					const eyebrows = [...document.querySelectorAll("*")]
						.filter((e) => {
							if (!vis(e)) return false
							const own = [...e.childNodes]
								.filter((n) => n.nodeType === 3)
								.map((n) => n.textContent.trim())
								.join("")
							if (!own || own.length > 40) return false
							const cs = getComputedStyle(e)
							return cs.textTransform === "uppercase" && parseFloat(cs.fontSize) <= 13
						})
						.map((e) => {
							const cs = getComputedStyle(e)
							const own = [...e.childNodes]
								.filter((n) => n.nodeType === 3)
								.map((n) => n.textContent.trim())
								.join(" ")
							return {
								text: own.slice(0, 40),
								tag: e.tagName.toLowerCase(),
								cls: (e.className || "").toString().slice(0, 80),
								category: classify(e),
								usesClass: (e.className || "").toString().split(/\s+/).includes("g-eyebrow"),
								color: cs.color,
								size: cs.fontSize,
							}
						})

					// AVATARS (RC18). Detected by SHAPE, not by class name, so a form
					// that calls itself something else is still found: a small square
					// box holding either an image or one-to-two initials.
					// Declared non-avatars: square marks that are not people. Same
					// discipline as ROLES — an exclusion is a visible edit here, not a
					// class someone can sprinkle on markup to silence the gate.
					const NOT_AVATAR = ".g-logo, [class*='logo'], svg, [data-icon]"
					const isAvatarish = (e) => {
						if (e.closest(NOT_AVATAR)) return false
						const r = e.getBoundingClientRect()
						if (r.width < 18 || r.width > 96) return false
						if (Math.abs(r.width - r.height) > 2) return false
						const cls = (e.className || "").toString()
						if (/avatar/i.test(cls)) return true
						const img = e.tagName === "IMG" || e.querySelector(":scope > img")
						const own = [...e.childNodes]
							.filter((n) => n.nodeType === 3)
							.map((n) => n.textContent.trim())
							.join("")
						return !!img || (own.length > 0 && own.length <= 2)
					}
					const avatars = [...document.querySelectorAll("img, span, div")]
						.filter((e) => vis(e) && isAvatarish(e))
						.map((e) => {
							const cs = getComputedStyle(e)
							const r = e.getBoundingClientRect()
							const own = [...e.childNodes]
								.filter((n) => n.nodeType === 3)
								.map((n) => n.textContent.trim())
								.join("")
							return {
								tag: e.tagName.toLowerCase(),
								cls: (e.className || "").toString().slice(0, 70),
								w: Math.round(r.width),
								h: Math.round(r.height),
								radius: cs.borderRadius,
								bg: cs.backgroundColor,
								color: cs.color,
								fontSize: cs.fontSize,
								kind: e.tagName === "IMG" ? "image" : own ? "initials" : "empty",
								grayscale:
									/grayscale/.test((e.parentElement?.className || "").toString()) ||
									cs.filter.includes("grayscale"),
								// which form owns it — the question RC18 asks
								form: /\bg-avatar\b/.test((e.className || "").toString())
									? "GAvatar"
									: /g-header__avatar\b/.test((e.className || "").toString())
									? "g-header__avatar"
									: "other",
							}
						})

					return {
						filled,
						avatars,
						hasBack: !!back,
						adHocEmpty:
							!document.querySelector(".g-empty") &&
							!![...document.querySelectorAll("div,p")].find(
								(e) =>
									vis(e) &&
									/nothing|no .*(yet|found|added)|all caught up/i.test(
										(e.textContent || "").slice(0, 80)
									)
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
