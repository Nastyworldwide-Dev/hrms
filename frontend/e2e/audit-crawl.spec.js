import { expect, test } from "@playwright/test"
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

import { BASE, PW, USER } from "./screens.mjs"

// Runtime crawl of every router route, per persona, REPORT-ONLY.
//
// For each persona x route it records: 4xx/5xx from /api, console errors and
// unhandled rejections, Ionic's "does not have the required <ion-page>"
// warning, blank content, error toasts, dead buttons (a safe button whose click
// produced no navigation, no request and no DOM change in 1.5 s), BACK
// behaviour (the in-app Back control when the page has one, else browser
// back — must land on the previous route within 2 s), phone-width overflow,
// and content a persona should not see (HR-only surfaces, other people's rows).
//
// Navigation is IN-APP (router.push through the mounted Vue app) the way a
// user moves, so Ionic's page stack and history are the real ones; a hard
// reload happens only after an uncaught error, so one crash cannot poison
// every later route.
//
// It never presses a persistence verb: submit / approve / reject / cancel /
// delete / save / check-in ... are excluded by accessible name (DANGER below)
// and by type=submit, so the crawl is safe against a fixture site.
//
// Personas come from CRAWL_PERSONAS_FILE, a JSON object
//   { "<label>": { "user": "...", "pw": "...", "employee": "HR-EMP-..." } }
// plus the audit user (AUDIT_PW / HRMS_E2E_PW) as "audit-employee". With no
// credentials at all, or with no server on BASE, every test skips.
// CRAWL_NAMES_FILE (optional): [{employee_name, company, user_id}] for the
// other-people's-rows check. CRAWL_ONLY=<regex> narrows the route list.
//
// Output: CRAWL_OUT (default frontend/e2e/.audit-crawl.json) — the raw log —
// and a route x persona table on stdout. Findings never fail the run unless
// CRAWL_STRICT=1, in which case any 5xx or uncaught error does.

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = process.env.CRAWL_OUT || join(HERE, ".audit-crawl.json")
const PHONE = { width: 400, height: 844 }
const CLICK_BUDGET = Number(process.env.CRAWL_CLICKS || 10)
const DEAD_MS = 1500
const BACK_MS = 2000

// Verbs that persist, decide or destroy. A button whose accessible name matches
// is never clicked. Deliberately broad: a missed safe button costs coverage, a
// missed dangerous one changes the site.
const DANGER =
	/submit|approv|reject|cancel|delete|remove|save|send|apply|check[\s-]?in|check[\s-]?out|punch|confirm|^yes|sign ?out|log ?out|mark|resolve|assign|reply|post|upload|publish|withdraw|revoke|accept|decline|grant|update|reset|clear|discard|start|stop|finish|claim|request access|resend|share|export|download|print|escalate|reopen|archive|attach|switch|enable|disable|allow|subscribe|turn on|turn off|proceed|continue|done|^ok$|^back$/i

// Console noise that is not a finding on the dev bundle.
const IGNORED_CONSOLE = [
	/frappe\.boot = \{\{ boot \}\}/, // raw dev index.html still carries the Jinja line
	/Unexpected token '\{'/, // same SyntaxError, as Chromium phrases it
	/\[vite\]/,
	/socket\.io|:9000\//i, // realtime socket is not part of the crawl
	/Download the Vue Devtools/,
]

const NOT_FOUND_TEXT =
	/isn.t here|not found|no such|doesn.t exist|could not|unable|missing|not permitted|no permission|no longer|removed/i

function loadPersonas() {
	const personas = {}
	const file = process.env.CRAWL_PERSONAS_FILE
	if (file && existsSync(file)) {
		const raw = JSON.parse(readFileSync(file, "utf8"))
		for (const [label, v] of Object.entries(raw)) {
			if (v && v.user && v.pw) personas[label] = { user: v.user, pw: v.pw, employee: v.employee }
		}
	}
	if (PW) personas["audit-employee"] = { user: USER, pw: PW }
	return personas
}

function loadNames() {
	const file = process.env.CRAWL_NAMES_FILE
	if (!file || !existsSync(file)) return []
	return JSON.parse(readFileSync(file, "utf8"))
}

const PERSONAS = loadPersonas()
const NAMES = loadNames()

/** Static route table, mirrored from src/router/*.js. `expect` = final path. */
function routeList(id) {
	const R = (path, extra = {}) => ({ path, ...extra })
	return [
		R("/", { expect: "/hrms/home" }),
		R("/form", { expect: "/hrms/home" }),
		R("/home"),
		R("/dashboard/attendance"),
		R("/dashboard/leaves"),
		R("/dashboard/expense-claims"),
		R("/dashboard/kpi"),
		R("/support"),
		R("/support?tab=hr"),
		R("/support?tab=it"),
		R("/issues", { expect: "/hrms/support?tab=hr" }),
		R("/hr/issues", { expect: "/hrms/support?tab=hr" }),
		R("/helpdesk", { expect: "/hrms/support?tab=it" }),
		R("/sop"),
		R("/sop/SOP-DOES-NOT-EXIST", { missing: true }),
		R("/team"),
		R("/team/roster"),
		R("/more"),
		R("/profile"),
		R("/notifications"),
		R("/settings"),
		R("/change-password"),
		R("/hr-contacts"),
		R("/remote-approvals"),
		// both open a full-screen "Login failed" sheet that is NOT dismissed when
		// the route is left, so the crawl hard-reloads after them — otherwise the
		// sheet covers every later route and reads as a blank page
		R("/invalid-employee", { reloadAfter: true }),
		R("/login", { reloadAfter: true }),
		R("/attendance-requests"),
		R("/attendance-requests/new"),
		R(id.attReq && `/attendance-requests/${id.attReq}`),
		R("/shift-requests"),
		R("/shift-requests/new"),
		R(id.shiftReq && `/shift-requests/${id.shiftReq}`),
		R("/shift-assignments"),
		R(id.shiftAssign && `/shift-assignments/${id.shiftAssign}`),
		R("/employee-checkins"),
		R("/ot-requests"),
		R("/ot-requests/new"),
		R(id.ot && `/ot-requests/${id.ot}`),
		R("/leave-applications"),
		R("/leave-applications/new"),
		R(id.leave && `/leave-applications/${id.leave}`),
		R("/leave-applications/HR-LAP-DOES-NOT-EXIST", { missing: true }),
		R("/expense-claims"),
		R("/expense-claims/new"),
		R(id.claim && `/expense-claims/${id.claim}`),
		R("/issues/new"),
		R(id.issue && `/issues/${id.issue}`),
		R("/helpdesk/new"),
		R("/helpdesk/HD-DOES-NOT-EXIST", { missing: true }),
		R("/design"),
		R("/no-such-route-crawl", { notFound: true }),
	]
		.filter((r) => r.path)
		.filter((r) => !process.env.CRAWL_ONLY || new RegExp(process.env.CRAWL_ONLY).test(r.path))
}

async function api(request, method, params = {}) {
	const qs = new URLSearchParams(params).toString()
	const r = await request.get(`${BASE}/api/method/${method}${qs ? `?${qs}` : ""}`)
	let body = null
	try {
		body = await r.json()
	} catch {
		body = null
	}
	return { status: r.status(), message: body?.message }
}

async function firstId(request, doctype) {
	const r = await api(request, "frappe.client.get_list", {
		doctype,
		limit_page_length: "1",
		order_by: "modified desc",
	})
	return r.message?.[0]?.name ?? null
}

async function login(browser, user, pw) {
	const ctx = await browser.newContext()
	const res = await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: user, pwd: pw } })
	const state = res.status() === 200 ? await ctx.storageState() : null
	await ctx.close()
	return state
}

async function serverUp() {
	try {
		return (await fetch(`${BASE}/api/method/ping`)).ok
	} catch {
		return false
	}
}

const ignorable = (text) => IGNORED_CONSOLE.some((re) => re.test(text))

/** Wire collectors onto a page; returns { drain, requests }. */
function collect(page) {
	const bag = { http: [], console: [], pageerror: [], ionPage: [], requests: 0 }
	page.on("request", () => (bag.requests += 1))
	page.on("response", (r) => {
		const url = r.url()
		if (r.status() >= 400 && !/socket\.io/.test(url)) {
			bag.http.push(`${r.status()} ${r.request().method()} ${url.replace(BASE, "")}`)
		}
	})
	page.on("console", (m) => {
		const text = m.text()
		if (/does not have the required <ion-page>/.test(text)) {
			bag.ionPage.push(text.split("\n")[0])
			return
		}
		if (m.type() !== "error" || ignorable(text)) return
		const loc = m.location()?.url
		// "Failed to load resource" carries its URL only in location()
		if (/Failed to load resource/.test(text) && loc) {
			if (ignorable(loc)) return
			bag.console.push(`${text.slice(0, 120)} <${loc.replace(BASE, "")}>`)
			return
		}
		bag.console.push(text.slice(0, 300))
	})
	page.on("pageerror", (e) => {
		if (!ignorable(e.message)) bag.pageerror.push(e.message.slice(0, 300))
	})
	return {
		drain: () => ({
			http: bag.http.splice(0),
			console: bag.console.splice(0),
			pageerror: bag.pageerror.splice(0),
			ionPage: bag.ionPage.splice(0),
		}),
		requests: () => bag.requests,
	}
}

/** In-app navigation via the mounted Vue router; falls back to a hard goto. */
async function navigate(page, path) {
	const pushed = await page
		.evaluate(async (p) => {
			const router = document.querySelector("#app")?.__vue_app__?.config?.globalProperties?.$router
			if (!router) return false
			await router.push(p).catch(() => {})
			return true
		}, path)
		.catch(() => false)
	if (!pushed) await page.goto(`${BASE}/hrms${path}`, { waitUntil: "networkidle", timeout: 25000 })
	await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {})
	await settleIonic(page)
}

/**
 * Ionic transitions the new page in after the route resolves; wait until
 * nothing is mid-transition (ion-page-invisible) and the page set has held
 * still for a moment.
 */
async function settleIonic(page) {
	await page
		.waitForFunction(
			() => {
				if (document.querySelector(".ion-page-invisible")) return false
				const key = [...document.querySelectorAll(".ion-page")].map((p) => p.className).join("|")
				if (window.__crawlPageKey !== key) {
					window.__crawlPageKey = key
					window.__crawlPageAt = Date.now()
					return false
				}
				return Date.now() - window.__crawlPageAt > 300
			},
			null,
			{ timeout: 5000 }
		)
		.catch(() => {})
}

/**
 * Mark the page the user actually sees with data-crawl-top. Ionic keeps every
 * visited page mounted and DOM order does not say which is on top (the tab
 * shell and the form shell are siblings, re-created in either order), so this
 * HIT-TESTS a grid of points and takes the innermost .ion-page most of them
 * land in.
 */
const TOP_PAGE = () => {
	for (const el of document.querySelectorAll("[data-crawl-top]"))
		el.removeAttribute("data-crawl-top")
	const votes = new Map()
	const W = window.innerWidth
	const H = window.innerHeight
	for (const fx of [0.2, 0.5, 0.8]) {
		for (const fy of [0.15, 0.3, 0.45, 0.6, 0.75]) {
			const hit = document.elementFromPoint(W * fx, H * fy)
			const pg = hit?.closest?.(".ion-page")
			if (pg) votes.set(pg, (votes.get(pg) || 0) + 1)
		}
	}
	let top = null
	let best = 0
	for (const [pg, n] of votes) {
		if (n > best) {
			best = n
			top = pg
		}
	}
	if (top) top.setAttribute("data-crawl-top", "1")
	return top ? top.className : null
}

const PAGE_PROBE = () => {
	const clipped = (el) => {
		for (let a = el.parentElement; a; a = a.parentElement) {
			const cs = getComputedStyle(a)
			if (/hidden|clip/.test(cs.overflowX) || /hidden|clip/.test(cs.overflow)) return true
		}
		return false
	}
	const visible = (el) => {
		const r = el.getBoundingClientRect()
		if (!r.width || !r.height) return false
		const cs = getComputedStyle(el)
		return (
			cs.visibility !== "hidden" &&
			cs.display !== "none" &&
			!el.closest(".ion-page-hidden, [aria-hidden='true']")
		)
	}
	// The main region: Ionic keeps every visited page mounted, so there can be
	// several ion-content elements; the shown one is the visible one with the
	// most text (a hidden page is aria-hidden / .ion-page-hidden).
	const count = (root) => {
		const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
		let textNodes = 0
		const texts = []
		while (walker.nextNode()) {
			const n = walker.currentNode
			if (!n.textContent.trim()) continue
			const p = n.parentElement
			if (!p || !visible(p)) continue
			textNodes += 1
			if (texts.length < 12) texts.push(n.textContent.trim().slice(0, 50))
		}
		return { textNodes, texts }
	}
	// Ionic appends each new page after the ones beneath it, and a page under
	// a full-screen one can stay laid out for a moment — so the SHOWN page is
	// the LAST visible ion-content in DOM order, not the one with most text.
	const topPage = document.querySelector("[data-crawl-top]")
	const mainEl = topPage?.querySelector("ion-content, main") || topPage || null
	const { textNodes, texts } = count(mainEl || document.body)
	const activePage = mainEl?.closest(".ion-page") || document.body
	const bodyText = activePage.innerText || ""
	const W = window.innerWidth
	const overflow = []
	if (document.documentElement.scrollWidth > W + 1)
		overflow.push(`document scrollWidth ${document.documentElement.scrollWidth} > ${W}`)
	for (const el of document.querySelectorAll("body *")) {
		if (overflow.length >= 4) break
		if (!visible(el) || clipped(el)) continue
		const r = el.getBoundingClientRect()
		if (r.right > W + 1 && r.left < W && r.width > 8) {
			const id = el.id ? `#${el.id}` : ""
			const cls =
				typeof el.className === "string" && el.className
					? `.${el.className.trim().split(/\s+/).slice(0, 2).join(".")}`
					: ""
			overflow.push(`${el.tagName.toLowerCase()}${id}${cls} right=${Math.round(r.right)}`)
		}
	}
	const toasts = []
	for (const el of document.querySelectorAll(
		'ion-toast, [role="alert"], [id*="toast" i], [class*="toast" i]'
	)) {
		const t = (el.innerText || el.textContent || "").trim()
		if (t && visible(el)) toasts.push(t.slice(0, 200))
	}
	return { textNodes, texts, bodyText: bodyText.slice(0, 20000), overflow, toasts }
}

/** Enumerate clickable candidates on the active page, safe ones only. */
const CANDIDATES = (dangerSrc) => {
	const DANGER = new RegExp(dangerSrc, "i")
	const out = []
	const skip = (el) =>
		!!el.closest(
			".ion-page-hidden, ion-tab-bar, nav, aside, [aria-hidden='true'], [role='dialog'], ion-modal, form"
		)
	const name = (el) => {
		const aria = el.getAttribute("aria-label")
		if (aria) return aria.trim()
		return (el.innerText || el.textContent || "").trim().replace(/\s+/g, " ")
	}
	// only the TOPMOST page, as marked by TOP_PAGE (hit-tested)
	const top = document.querySelector("[data-crawl-top]") || document.body
	let i = 0
	for (const el of document.querySelectorAll("button, [role=button], a[href], [role=tab]")) {
		i += 1
		if (!top.contains(el) || skip(el)) continue
		const r = el.getBoundingClientRect()
		if (!r.width || !r.height || r.bottom < 0 || r.top > window.innerHeight * 3) continue
		if (el.disabled || el.getAttribute("aria-disabled") === "true") continue
		// the tab already selected does nothing when tapped again, by design
		if (el.getAttribute("aria-selected") === "true" || el.getAttribute("aria-current")) continue
		if (el.getAttribute("type") === "submit") continue
		const n = name(el).slice(0, 60)
		if (!n || DANGER.test(n)) continue
		const href = el.getAttribute("href")
		if (href && !href.startsWith("/hrms") && !href.startsWith("#")) continue
		el.setAttribute("data-crawl-idx", String(i))
		out.push({ idx: i, name: n, tag: el.tagName.toLowerCase() })
	}
	return out
}

const OVERLAY =
	'ion-modal:not(.overlay-hidden), [role="dialog"], ion-action-sheet, ion-alert, ion-popover'

async function closeOverlays(page) {
	for (let i = 0; i < 2; i++) {
		if (!(await page.evaluate((s) => !!document.querySelector(s), OVERLAY))) return
		await page.keyboard.press("Escape").catch(() => {})
		await page.waitForTimeout(300)
		const close = page
			.locator(
				'[role="dialog"] [aria-label*="close" i], ion-modal [aria-label*="close" i], ion-modal button:has-text("Close")'
			)
			.first()
		if (await close.isVisible().catch(() => false))
			await close.click({ timeout: 1000 }).catch(() => {})
		await page.waitForTimeout(300)
	}
}

async function probeButtons(page, collector, path, log) {
	const dead = []
	const clicked = []
	await page.evaluate(TOP_PAGE).catch(() => {})
	const cands = await page.evaluate(CANDIDATES, DANGER.source).catch(() => [])
	const seen = new Set()
	let budget = CLICK_BUDGET
	for (const c of cands) {
		if (budget <= 0) break
		const key = `${c.tag}:${c.name}`
		if (seen.has(key)) continue
		seen.add(key)
		const el = page.locator(`[data-crawl-idx="${c.idx}"]`).first()
		if (!(await el.isVisible().catch(() => false))) continue
		budget -= 1
		const before = { url: page.url(), req: collector.requests() }
		await page.evaluate((idx) => {
			const target = document.querySelector(`[data-crawl-idx="${idx}"]`)
			window.__crawlMut = 0
			window.__crawlObs?.disconnect()
			window.__crawlObs = new MutationObserver((muts) => {
				for (const m of muts) {
					const t = m.target.nodeType === 1 ? m.target : m.target.parentElement
					// the control's own focus/active class flips are not a response
					if (target && t && (t === target || target.contains(t)) && m.type === "attributes")
						continue
					window.__crawlMut += 1
				}
			})
			window.__crawlObs.observe(document.body, {
				subtree: true,
				childList: true,
				attributes: true,
				characterData: true,
			})
		}, c.idx)
		const t0 = Date.now()
		const ok = await el
			.click({ timeout: 2000, noWaitAfter: true })
			.then(() => true)
			.catch(() => false)
		if (!ok) continue
		let alive = null
		while (Date.now() - t0 < DEAD_MS) {
			await page.waitForTimeout(100)
			if (page.url() !== before.url) {
				alive = "navigated"
				break
			}
			if (collector.requests() > before.req) {
				alive = "request"
				break
			}
			if ((await page.evaluate(() => window.__crawlMut || 0).catch(() => 0)) > 0) {
				alive = "dom"
				break
			}
		}
		clicked.push({ name: c.name, tag: c.tag, alive })
		if (!alive) dead.push(`${c.tag} "${c.name}"`)
		if (page.url() !== before.url) {
			await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {})
			const tb = Date.now()
			await page.goBack({ waitUntil: "commit", timeout: 5000 }).catch(() => {})
			const restored = await page
				.waitForURL((u) => u.toString() === before.url, { timeout: BACK_MS })
				.then(() => true)
				.catch(() => false)
			;(log.backFromClick ||= []).push({ button: c.name, ms: Date.now() - tb, restored })
			if (!restored) await navigate(page, path)
			else await settleIonic(page)
			await page.waitForTimeout(300)
			await page.evaluate(TOP_PAGE).catch(() => {})
			await page.evaluate(CANDIDATES, DANGER.source).catch(() => {})
		}
		await closeOverlays(page)
	}
	return { dead, clicked, candidates: cands.length }
}

function personaExpectations(info, employee) {
	const own = new Set()
	if (info?.name) own.add(info.name)
	const ownRow = NAMES.find((n) => n.user_id === info?.name)
	if (ownRow) own.add(ownRow.employee_name)
	return {
		isHR: !!info?.is_hr,
		roles: new Set(info?.roles || []),
		own,
		employee: ownRow || employee,
	}
}

function leakCheck(label, exp, bodyText, route) {
	const findings = []
	if (!exp.isHR) {
		for (const t of ["Issue Board", "Manage SOPs", "Draft SOPs"]) {
			if (bodyText.includes(t)) findings.push(`HR-only text "${t}" visible to non-HR`)
		}
	}
	if (!NAMES.length) return findings
	// lists and boards are where other people's rows would leak; forms show approvers legitimately
	const listy =
		/^\/(leave-applications|attendance-requests|shift-requests|shift-assignments|employee-checkins|expense-claims|ot-requests|replacement-leave|support|issues|hr\/issues|helpdesk|team|notifications|remote-approvals|sop)(\?|\/roster|$)/.test(
			route
		)
	if (!listy) return findings
	const ownCompany = exp.employee?.company
	for (const n of NAMES) {
		if (!n.employee_name || exp.own.has(n.employee_name) || !bodyText.includes(n.employee_name))
			continue
		if (exp.isHR) {
			if (ownCompany && n.company !== ownCompany && exp.roles.has("HR Manager"))
				findings.push(
					`other-company employee "${n.employee_name}" (${n.company}) visible to fenced HR Manager`
				)
			continue
		}
		if (label === "approver" && /Crawl Report/.test(n.employee_name)) continue // their own report
		findings.push(`other employee "${n.employee_name}" visible on a list`)
	}
	return findings
}

test.describe("audit crawl", () => {
	test.describe.configure({ mode: "parallel" })
	const labels = Object.keys(PERSONAS)
	test.skip(labels.length === 0, "set CRAWL_PERSONAS_FILE and/or AUDIT_PW to run the crawl")

	for (const label of labels) {
		test(`persona ${label}`, async ({ browser }) => {
			test.setTimeout(45 * 60 * 1000)
			test.skip(!(await serverUp()), `no server at ${BASE}`)
			const persona = PERSONAS[label]
			const state = await login(browser, persona.user, persona.pw)
			test.skip(!state, `login failed for ${label}`)

			const ctx = await browser.newContext({
				storageState: state,
				viewport: PHONE,
				reducedMotion: "reduce",
			})
			const probe = ctx.request
			const info = (await api(probe, "hrms.api.get_current_user_info")).message
			const ids = {
				leave: await firstId(probe, "Leave Application"),
				attReq: await firstId(probe, "Attendance Request"),
				shiftReq: await firstId(probe, "Shift Request"),
				shiftAssign: await firstId(probe, "Shift Assignment"),
				claim: await firstId(probe, "Expense Claim"),
				issue: await firstId(probe, "Employee Issue"),
				ot: await firstId(probe, "OT Request"),
				rlc: await firstId(probe, "Replacement Leave Claim"),
			}
			const exp = personaExpectations(info, persona.employee)
			const routes = routeList(ids)

			const page = await ctx.newPage()
			// the dev bundle boots from get_context_for_dev, which a site outside
			// developer_mode refuses; the production bundle never calls it
			await page.route("**/hrms.www.hrms.get_context_for_dev", (route) =>
				route.fulfill({
					status: 200,
					contentType: "application/json",
					body: JSON.stringify({
						message: {
							site_name: "site",
							socketio_port: 9000,
							default_route: "/hrms",
							__messages: {},
						},
					}),
				})
			)
			const collector = collect(page)
			const results = []

			await page
				.goto(`${BASE}/hrms/home`, { waitUntil: "networkidle", timeout: 30000 })
				.catch(() => {})
			await page.waitForTimeout(800)
			const boot = collector.drain()
			let prevPath = "/hrms/home"
			let needReload = false

			for (const r of routes) {
				const log = { persona: label, route: r.path, findings: [] }
				if (needReload) {
					await page
						.goto(`${BASE}/hrms/home`, { waitUntil: "networkidle", timeout: 30000 })
						.catch(() => {})
					await page.waitForTimeout(500)
					prevPath = "/hrms/home"
					needReload = false
				}
				collector.drain()
				const t0 = Date.now()
				await navigate(page, r.path).catch((e) =>
					log.findings.push(`navigate: ${e.message.split("\n")[0]}`)
				)
				await page.waitForTimeout(700)
				log.loadMs = Date.now() - t0
				log.finalUrl = page.url().replace(BASE, "")
				if (r.expect && log.finalUrl !== r.expect)
					log.findings.push(`redirect: landed on ${log.finalUrl}, expected ${r.expect}`)

				log.topPage = await page.evaluate(TOP_PAGE).catch(() => null)
				// CRAWL_SHOTS=<dir>: one PNG per persona x route, for reading a finding
				if (process.env.CRAWL_SHOTS) {
					mkdirSync(process.env.CRAWL_SHOTS, { recursive: true })
					const slug = r.path.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") || "root"
					log.shot = join(process.env.CRAWL_SHOTS, `${label}--${slug}.png`)
					await page.screenshot({ path: log.shot }).catch(() => {})
				}
				const p = await page.evaluate(PAGE_PROBE).catch(() => null)
				if (p) {
					log.textNodes = p.textNodes
					if (p.textNodes < 6) log.texts = p.texts
					if (p.textNodes < 2) log.findings.push(`blank: ${p.textNodes} visible text nodes`)
					if (p.overflow.length) log.findings.push(`overflow@400: ${p.overflow.join(" | ")}`)
					if (p.toasts.length) log.findings.push(`toast: ${p.toasts.join(" | ")}`)
					if (r.notFound && !NOT_FOUND_TEXT.test(p.bodyText))
						log.findings.push("notfound: catch-all did not render a not-found message")
					if (r.missing && !NOT_FOUND_TEXT.test(p.bodyText))
						log.findings.push(
							`missing-doc: no error / not-found message for a missing id (${p.textNodes} text nodes)`
						)
					for (const f of leakCheck(label, exp, p.bodyText, r.path))
						log.findings.push(`gated: ${f}`)
				}

				if (!r.notFound && !r.missing) {
					const b = await probeButtons(page, collector, r.path, log)
					log.buttons = { candidates: b.candidates, clicked: b.clicked.length }
					if (b.dead.length) log.findings.push(`dead: ${b.dead.join(", ")}`)
				}

				// BACK: the in-app control when the page has one, else browser back;
				// must land on the previous route within 2 s. Runs LAST on a route, after
				// the button probe, so the next route is pushed from wherever back
				// landed — no synthetic return trip that would stack duplicate pages
				if (log.finalUrl === prevPath) {
					// a redirect onto the route we were already on pushes no history
					// entry, so there is nothing to go back from
					log.backVia = "same-url"
				} else {
					// the header Back control of the TOPMOST visible page (the last
					// visible .ion-page in DOM order), never a stale one underneath
					await page.evaluate(TOP_PAGE).catch(() => {})
					const inApp = page.locator('[data-crawl-top] [aria-label="Back"]:visible').first()
					const useInApp = await inApp.isVisible().catch(() => false)
					const tb = Date.now()
					if (useInApp) await inApp.click({ timeout: 2000, noWaitAfter: true }).catch(() => {})
					else await page.goBack({ waitUntil: "commit", timeout: 5000 }).catch(() => {})
					const ok = await page
						.waitForURL((u) => u.toString().replace(BASE, "") === prevPath, { timeout: BACK_MS })
						.then(() => true)
						.catch(() => false)
					log.backMs = Date.now() - tb
					log.backVia = useInApp ? "in-app" : "browser"
					if (!ok)
						log.findings.push(
							`back(${log.backVia}): landed on ${page.url().replace(BASE, "")} after ${
								log.backMs
							} ms, expected ${prevPath}`
						)
				}

				// let the back transition finish before the next push: a push that
				// lands mid-transition leaves the outgoing page painted on top
				// (reproduced on KPI — see the report), and the crawl measures
				// each route on its own, not that race
				await settleIonic(page)
				await page.waitForTimeout(600)
				prevPath = page.url().replace(BASE, "")
				const d = collector.drain()
				for (const h of d.http) log.findings.push(`http: ${h}`)
				for (const c of d.console) log.findings.push(`console: ${c}`)
				for (const e of d.pageerror) log.findings.push(`pageerror: ${e}`)
				for (const w of d.ionPage) log.findings.push(`ion-page: ${w}`)
				// an overlay still presented after the route is done leaks onto the
				// next route; record it, and start the next route clean
				const overlayLeft = await page
					.evaluate(() => {
						const m = document.querySelector("ion-modal:not(.overlay-hidden)")
						return m ? (m.innerText || "").trim().replace(/\s+/g, " ").slice(0, 80) : null
					})
					.catch(() => null)
				if (overlayLeft) log.findings.push(`overlay: still open after the route: "${overlayLeft}"`)
				if (d.pageerror.length || r.reloadAfter || overlayLeft) needReload = true
				log.findings = [...new Set(log.findings)]
				results.push(log)
			}
			await ctx.close()

			mkdirSync(dirname(OUT), { recursive: true })
			let all = {}
			try {
				all = existsSync(OUT) ? JSON.parse(readFileSync(OUT, "utf8")) : {}
			} catch {
				all = {}
			}
			all[label] = {
				user: persona.user,
				info: { name: info?.name, is_hr: info?.is_hr, roles: info?.roles },
				ids,
				boot,
				results,
				at: new Date().toISOString(),
			}
			writeFileSync(OUT, JSON.stringify(all, null, 1))
			const rows = results.map(
				(x) => `| ${x.route} | ${label} | ${x.findings.length ? x.findings.join("<br>") : "OK"} |`
			)
			console.log(`\n| route | persona | result |\n|---|---|---|\n${rows.join("\n")}\n`)

			expect(results.length, "crawled at least one route").toBeGreaterThan(0)
			if (process.env.CRAWL_STRICT) {
				const hard = results.flatMap((x) =>
					x.findings.filter((f) => /^http: 5|^pageerror/.test(f)).map((f) => `${x.route}: ${f}`)
				)
				expect(hard, "no 5xx and no uncaught error").toEqual([])
			}
		})
	}
})
