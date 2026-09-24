// alpha.6 whole-app audit against the Apple checklist (docs/glass/plan/alpha6-standard.md).
// Every route × persona × theme on a phone, plus desktop for staff. Writes one
// JSON line per screen and a full-page screenshot per staff/approver phone view.
//   cd frontend && set -a && . ../.env && set +a && node e2e/alpha6-audit.mjs
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs"
import { chromium, webkit } from "playwright"

//: ENGINE=webkit runs the same checks in Safari's engine (alpha.7). The phone
//: contexts then identify as an iPhone, as the owner's Safari does, so iOS-only
//: code paths (install prompt, date pills) are exercised.
const ENGINE = process.env.ENGINE === "webkit" ? webkit : chromium
const IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
import { BASE, PW, screens, settle } from "./screens.mjs"

const OUT = process.env.OUT || "/tmp/alpha6/shots"
mkdirSync(OUT, { recursive: true })
const LOG = `${OUT}/audit.jsonl`
writeFileSync(LOG, "")

const PERSONAS = [
	["staff", process.env.HRMS_E2E_USER || "nurul.aisyah@nastyworldwide.com"],
	["approver", "nadi.w0.approver@example.invalid"],
].filter(([w]) => !process.env.WHO || process.env.WHO.split(",").includes(w))
const RUNS = [
	["phone", 390, 844, "dark"],
	["phone", 390, 844, "light"],
	["desktop", 1280, 800, "dark"],
]
const EXTRA = [
	["help", "/support"],
	["approvals", "/approvals"],
	["team-roster", "/team/roster"],
	["announcements", "/announcements"],
	["helpdesk-new", "/helpdesk/new"],
]

async function loginAs(browser, usr) {
	const ctx = await browser.newContext()
	const res = await ctx.request.post(`${BASE}/api/method/login`, { form: { usr, pwd: PW } })
	const state = res.status() === 200 ? await ctx.storageState() : null
	await ctx.close()
	return state
}

// Runs in the page. Each key is one checklist item (alpha6-standard.md §).
function audit() {
	const ROUND = (n) => Math.round(n * 10) / 10
	const vis = (e) => {
		const r = e.getBoundingClientRect()
		const cs = getComputedStyle(e)
		return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && cs.opacity !== "0"
	}
	const resolve = (tok) => {
		const s = document.createElement("span")
		s.style.color = `var(${tok})`
		document.body.appendChild(s)
		const v = getComputedStyle(s).color
		s.remove()
		return v
	}
	const BRAND = resolve("--g-brand")
	const INK = resolve("--g-accent-ink")
	const all = [...document.querySelectorAll("body *")].filter(vis)
	const ownText = (e) =>
		[...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join(" ").trim()
	const texts = all.filter((e) => ownText(e))
	const hist = (arr) => arr.reduce((m, k) => ((m[k] = (m[k] || 0) + 1), m), {})

	// L1 — a vertical page must not pan sideways. On iOS any overflow other than
	// visible on ONE axis makes the other axis scrollable too (CSS overflow rule),
	// so a scroller that does not clip x is a latent sideways drag.
	const scrollers = all.filter((e) => /(auto|scroll)/.test(getComputedStyle(e).overflowY))
	const panX = scrollers
		.filter((e) => e.scrollWidth > e.clientWidth + 1 && !/hidden|clip/.test(getComputedStyle(e).overflowX))
		.map((e) => `${e.tagName.toLowerCase()}.${String(e.className).split(" ")[0]} ${e.scrollWidth}>${e.clientWidth}`)
	const unclipped = scrollers.filter((e) => !/hidden|clip/.test(getComputedStyle(e).overflowX)).length
	const tooWide = all
		.filter((e) => e.getBoundingClientRect().right > innerWidth + 1 && !e.closest("[class*=scroll-x], .hide-scrollbar"))
		.slice(0, 3)
		.map((e) => `${e.tagName.toLowerCase()}.${String(e.className).split(" ")[0]}`)

	// T — type. Apple's iOS ramp at default size, in px (1pt = 1px in CSS).
	const RAMP = [11, 12, 13, 15, 16, 17, 20, 22, 28, 34]
	const sizes = texts.map((e) => ROUND(parseFloat(getComputedStyle(e).fontSize)))
	const weights = texts.map((e) => getComputedStyle(e).fontWeight)
	const offRamp = hist(sizes.filter((s) => !RAMP.includes(Math.round(s))))
	const heavy = texts.filter((e) => +getComputedStyle(e).fontWeight >= 800).map((e) => ownText(e).slice(0, 24))
	const under11 = texts.filter((e) => parseFloat(getComputedStyle(e).fontSize) < 11).map((e) => ownText(e).slice(0, 20))
	const uppercase = texts
		.filter((e) => getComputedStyle(e).textTransform === "uppercase")
		.map((e) => ownText(e).slice(0, 20))

	// C — colour. Tint (brand fill) only on THE primary action; brand-coloured
	// TEXT that is not a control is tint used as decoration.
	const tinted = all.filter((e) => {
		const bg = getComputedStyle(e).backgroundColor
		return (bg === BRAND || bg === INK) && e.getBoundingClientRect().width > 60
	})
	const tintText = texts
		.filter((e) => {
			const c = getComputedStyle(e).color
			return (c === BRAND || c === INK) && !e.closest("button, a, [role=button], [role=tab], .g-tabbar, ion-tab-bar")
		})
		.map((e) => ownText(e).slice(0, 24))

	// G — glass only on chrome.
	// frappe-ui toasts render in #frappeui-toast-root: chrome, not content.
	const CHROME = ".g-header, .g-tabbar, ion-tab-bar, .g-modal, ion-modal, .g-toast, .g-sidenav, [role=dialog], .g-tabbar-fade, #frappeui-toast-root"
	const glassOnContent = all
		.filter((e) => {
			const cs = getComputedStyle(e)
			const f = cs.backdropFilter || cs.webkitBackdropFilter
			return f && f !== "none" && !e.closest(CHROME)
		})
		.map((e) => `${e.tagName.toLowerCase()}.${String(e.className).split(" ")[0]}`)

	// K — controls.
	const ctlSel = "input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file]), textarea, select, .g-linkpick__trigger"
	const controls = [...document.querySelectorAll(ctlSel)].filter(vis).map((e) => {
		const cs = getComputedStyle(e)
		return `${Math.round(e.getBoundingClientRect().height)}h/${cs.borderRadius}`
	})
	const checkboxes = [...document.querySelectorAll("input[type=checkbox]")].filter(vis).length
	const switches = [...document.querySelectorAll("[role=switch]")].filter(vis).map((sw) => {
		const row = sw.closest(".g-row, .g-switch-row, label, li") || sw.parentElement
		const label = row && [...row.querySelectorAll("*")].find((x) => x !== sw && !sw.contains(x) && ownText(x))
		const leading = label ? sw.getBoundingClientRect().left < label.getBoundingClientRect().left : null
		return { leading, inGroup: !!sw.closest(".g-rows, .g-list-panel, .g-card, ul") }
	})
	const tappables = [...document.querySelectorAll("button, a[href], [role=button], [role=switch], select, input")].filter(vis)
	const under44 = tappables
		.filter((e) => {
			const r = e.getBoundingClientRect()
			// .g-seclink / .g-touch-area draw an invisible 44px ::before around
			// small text links; that IS the target (WCAG 2.5.8 counts it).
			const ex = getComputedStyle(e, "::before")
			const expanded = ex.content !== "none" && parseFloat(ex.height) >= 44 && parseFloat(ex.width) >= 44
			return (r.width < 44 || r.height < 44) && !expanded && !e.closest(".g-cal") && e.type !== "hidden"
		})
		.map((e) => (e.getAttribute("aria-label") || e.textContent || e.tagName).trim().slice(0, 20))
	const radii = hist(
		all
			.filter((e) => {
				const cs = getComputedStyle(e)
				return cs.borderRadius !== "0px" && (cs.backgroundColor !== "rgba(0, 0, 0, 0)" || cs.borderTopWidth !== "0px")
			})
			.map((e) => getComputedStyle(e).borderTopLeftRadius)
	)
	const buttonHeights = hist(
		[...document.querySelectorAll("button, .g-btn")].filter(vis).filter((b) => !b.closest(".g-row, .g-form-row, .g-sheet__action, ion-tab-bar, .g-tabbar, .g-cal") && (ownText(b) || b.querySelector("span"))).map((b) => Math.round(b.getBoundingClientRect().height))
	)

	// W — words.
	// The words gate (alpha.6 C1). Every one of these was on a live screen;
	// utils/plainLabel.js replaced them. E1 requires 0 on every screen.
	const BANNED = /\b(posting date|explanation|ot date|claimed hours|approver|submit(ted)?|draft|document|mandatory|invalid|leave type|shift type|employee|designation|accounting|exchange gain|advance|sanctioned|reimbursed|naming series|amended|docstatus|cancelled|hr can see this|overtime pay|you claim|compensat)/i
	const pageText = texts.map((e) => ownText(e))
	const jargon = [...new Set(pageText.filter((t) => BANNED.test(t)).map((t) => t.slice(0, 40)))]
	const emails = [...new Set(pageText.filter((t) => /[\w.]+@[\w.]+\.\w+/.test(t)).map((t) => t.slice(0, 40)))]
	const saveButtons = [...document.querySelectorAll("button")].filter(vis).map((b) => b.textContent.trim()).filter((t) => /^(save|submit|ok|done)$/i.test(t))

	// F — forms: a section heading with nothing under it before the next one.
	const heads = [...document.querySelectorAll("h2.g-eyebrow, .g-eyebrow")].filter(vis)
	const emptySections = heads
		.filter((h, i) => {
			const next = heads[i + 1]
			const top = h.getBoundingClientRect().bottom
			const bottom = next ? next.getBoundingClientRect().top : Infinity
			return !all.some((e) => {
				const r = e.getBoundingClientRect()
				return r.top >= top && r.bottom <= bottom && (e.matches("input, textarea, select, button, table, .g-row") || (ownText(e) && !e.matches("h2, .g-eyebrow")))
			})
		})
		.map((h) => ownText(h))

	const title = (document.querySelector("h1")?.textContent || "").trim()
	return {
		title,
		titleLong: title.length > 15,
		docH: document.scrollingElement.scrollHeight,
		panX,
		unclipped,
		tooWide,
		sizes: hist(sizes.map(Math.round)),
		weights: hist(weights),
		offRamp,
		heavy: heavy.slice(0, 8),
		under11: under11.slice(0, 6),
		uppercase: uppercase.slice(0, 6),
		tinted: tinted.length,
		tintedLabels: tinted.map((e) => (e.textContent || "").trim().slice(0, 20)).slice(0, 6),
		tintText: tintText.slice(0, 8),
		glassOnContent,
		controls: hist(controls),
		checkboxes,
		switches,
		under44: under44.slice(0, 8),
		under44Count: under44.length,
		radii,
		buttonHeights,
		jargon: jargon.slice(0, 12),
		emails: emails.slice(0, 3),
		saveButtons,
		emptySections,
	}
}

const browser = await ENGINE.launch()
let n = 0
for (const [who, usr] of PERSONAS) {
	const state = await loginAs(browser, usr)
	if (!state) {
		appendFileSync(LOG, JSON.stringify({ who, error: "login failed" }) + "\n")
		continue
	}
	for (const [vp, W, H, theme] of RUNS) {
		if (vp === "desktop" && who !== "staff") continue
		const ctx = await browser.newContext({ storageState: state, viewport: { width: W, height: H }, colorScheme: theme, deviceScaleFactor: 1, isMobile: vp === "phone" && ENGINE === chromium, hasTouch: vp === "phone", ...(ENGINE === webkit && vp === "phone" ? { userAgent: IPHONE_UA } : {}) })
		await ctx.addInitScript((t) => localStorage.setItem("hrms:theme", t), theme)
		const page = await ctx.newPage()
		const errors = []
		page.on("pageerror", (e) => errors.push(String(e).slice(0, 120)))
		const list = (await screens(ctx.request)).filter((s) => !s.anon && s.path).map((s) => [s.slug, s.path])
		for (const [slug, path] of [...list, ...EXTRA]) {
			errors.length = 0
			const row = { who, vp, theme, slug, path }
			try {
				await page.goto(`${BASE}/hrms${path}`, { waitUntil: "domcontentloaded", timeout: 35000 })
				await settle(page)
				await page.waitForTimeout(600)
				Object.assign(row, { url: page.url().replace(BASE, ""), errors: [...errors] }, await page.evaluate(audit))
				if (vp === "phone" && theme === "dark") {
					row.file = `${who}-${slug}.png`
					await page.screenshot({ path: `${OUT}/${row.file}`, fullPage: true })
				}
			} catch (e) {
				row.error = String(e).slice(0, 160)
			}
			appendFileSync(LOG, JSON.stringify(row) + "\n")
			n++
		}
		await ctx.close()
	}
}
await browser.close()
console.log(`audited ${n} views → ${LOG}`)
