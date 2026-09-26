// alpha.12: what every screen shows while it loads, when the server fails,
// and when the phone is offline — forced, not waited for. Apple (loading):
// "Show something as soon as possible"; a blank screen "can make people think
// your app is frozen". Each screen is opened three ways:
//   slow   — every /api/ answer held 2.5 s; shot at 700 ms. Pass = a skeleton
//            or placeholder is on screen (not blank, not a lone spinner).
//   error  — every /api/ answer is a 500. Pass = an alert with "Try again".
//   offline— the page loads, then the network drops and it reloads its data.
//            Pass = the offline banner shows.
//   cd frontend && set -a && . ../.env && set +a && node e2e/states-audit.mjs
import { writeFileSync, mkdirSync } from "node:fs"
import { webkit } from "playwright"
import { BASE, PW, screens } from "./screens.mjs"

const OUT = process.env.OUT || "/tmp/a12/states"
mkdirSync(OUT, { recursive: true })
const b = await webkit.launch()
const ctx = await b.newContext({ viewport: { width: 402, height: 874 }, hasTouch: true })
await ctx.addInitScript(() => localStorage.setItem("hrms:install-prompt-dismissed", String(Date.now())))
await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: process.env.WHO_USER || "nadi.w0.approver@example.invalid", pwd: PW } })
const list = [...new Map((await screens(ctx.request)).filter((s) => !s.anon && s.path).map((s) => [s.path, s])).values()]

const look = () => {
	const page = document.querySelector(".ion-page:not(.ion-page-hidden)") || document.body
	const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && !e.closest(".ion-page-hidden") }
	const inBody = (e) => !e.closest(".g-header, ion-tab-bar, .g-tabbar, .g-sidenav")
	const skeleton = [...page.querySelectorAll(".g-skeleton, [class*=skeleton], [aria-busy=true]")].filter(vis).filter(inBody).length
	const spinner = [...page.querySelectorAll("ion-spinner, .g-spinner, [class*=spinner], .animate-spin")].filter(vis).filter(inBody).length
	const text = [...page.querySelectorAll("*")].filter((e) => vis(e) && inBody(e) && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())).map((e) => e.textContent.trim()).join(" | ").slice(0, 160)
	const alert = [...page.querySelectorAll("[role=alert]")].filter(vis).map((e) => e.textContent.trim().replace(/\s+/g, " ").slice(0, 80))
	const retry = [...page.querySelectorAll("button")].filter(vis).some((e) => /try again|retry/i.test(e.textContent))
	const banner = [...document.querySelectorAll(".g-offline, [class*=offline]")].filter(vis).map((e) => e.textContent.trim().slice(0, 60))
	return { skeleton, spinner, text, alert, retry, banner }
}

const rows = []
for (const s of list) {
	const row = { path: s.path }
	// slow
	let p = await ctx.newPage()
	await p.route("**/api/**", async (route) => { await new Promise((r) => setTimeout(r, 2500)); await route.continue().catch(() => {}) })
	await p.goto(`${BASE}/hrms${s.path}`, { waitUntil: "commit" }).catch(() => {})
	await p.waitForTimeout(700)
	row.slow = await p.evaluate(look).catch((e) => ({ err: String(e).slice(0, 60) }))
	await p.screenshot({ path: `${OUT}/slow${s.path.replaceAll("/", "_")}.png` }).catch(() => {})
	await p.close()
	// error
	p = await ctx.newPage()
	await p.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle" }).catch(() => {})
	await p.route("**/api/method/**", (route) => {
		const u = route.request().url()
		if (/frappe\.auth|get_logged_user|boot|csrf|translations|get_context/.test(u)) return route.continue()
		return route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ exc_type: "Exception", _server_messages: "[]" }) })
	})
	await p.reload({ waitUntil: "networkidle" }).catch(() => {})
	await p.waitForTimeout(900)
	row.error = await p.evaluate(look).catch((e) => ({ err: String(e).slice(0, 60) }))
	await p.screenshot({ path: `${OUT}/error${s.path.replaceAll("/", "_")}.png` }).catch(() => {})
	await p.close()
	// offline
	p = await ctx.newPage()
	await p.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle" }).catch(() => {})
	await ctx.setOffline(true)
	await p.waitForTimeout(900)
	row.offline = await p.evaluate(look).catch((e) => ({ err: String(e).slice(0, 60) }))
	await ctx.setOffline(false)
	await p.close()
	const verdict = []
	if (!row.slow.skeleton && !row.slow.err) verdict.push(row.slow.spinner ? "D1 spinner, no skeleton" : row.slow.text ? "D1 no skeleton (content words only)" : "D1 blank while loading")
	if (!row.error.retry) verdict.push(row.error.alert?.length ? "O2 error without Try again" : "O1 error not shown")
	if (!row.offline.banner?.length) verdict.push("O3 no offline banner")
	row.verdict = verdict
	rows.push(row)
	console.log(s.path, "|", verdict.join(" || ") || "ok")
}
writeFileSync(`${OUT}/states.json`, JSON.stringify(rows, null, 1))
const counts = {}
for (const r of rows) for (const v of r.verdict) counts[v.split(" ")[0]] = (counts[v.split(" ")[0]] || 0) + 1
console.log(Object.entries(counts).map(([k, n]) => `${n}\t${k}`).join("\n"))
console.log(`GATE_COUNT ${rows.filter((r) => r.verdict.length).length}`)
await b.close()
process.exit(0)
