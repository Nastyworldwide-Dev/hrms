import pkg from "/home/nabil/nz-version-16/frontend/node_modules/playwright/index.js"
import fs from "node:fs"
const { chromium } = pkg

const BASE = "http://localhost:8080"
const USER = "nurul.aisyah@nastyworldwide.com"
const PW = process.env.AUDIT_PW
const OUT = "/home/nabil/nz-version-16/docs/glass/audit/screens"
fs.mkdirSync(OUT, { recursive: true })

// Which slice to run — lets the capture be resumed / split.
const ONLY = process.env.ONLY ? process.env.ONLY.split(",") : null

const VIEWPORTS = [
	{ w: 390, h: 844, dsf: 2, tag: "390" },
	{ w: 768, h: 1024, dsf: 1, tag: "768" },
	{ w: 1440, h: 900, dsf: 1, tag: "1440" },
]

const browser = await chromium.launch()

// ---- session -------------------------------------------------------------
const auth = await browser.newContext()
const login = await auth.request.post(`${BASE}/api/method/login`, { form: { usr: USER, pwd: PW } })
if (login.status() !== 200) throw new Error("login failed: " + login.status())
const state = await auth.storageState()
await auth.close()

// ---- real document ids ---------------------------------------------------
const api = await browser.newContext({ storageState: state })
async function firstId(doctype, extra = {}) {
	try {
		const r = await api.request.get(
			`${BASE}/api/method/frappe.client.get_list?doctype=${encodeURIComponent(doctype)}&limit_page_length=1&order_by=modified%20desc`
		)
		const j = await r.json()
		return j?.message?.[0]?.name ?? null
	} catch { return null }
}
const ids = {
	leave: await firstId("Leave Application"),
	attReq: await firstId("Attendance Request"),
	shiftReq: await firstId("Shift Request"),
	shiftAssign: await firstId("Shift Assignment"),
	claim: await firstId("Expense Claim"),
	issue: await firstId("Employee Issue"),
	ot: await firstId("OT Request"),
	rlc: await firstId("Replacement Leave Claim"),
	sop: await firstId("SOP Document"),
}
await api.close()
console.log("IDS " + JSON.stringify(ids))

// ---- screens -------------------------------------------------------------
const S = (slug, path, opts = {}) => ({ slug, path, ...opts })
const SCREENS = [
	S("login", "/login", { anon: true }),
	S("forgot-password", "/forgot-password", { anon: true }),
	S("home", "/home"),
	S("dash-attendance", "/dashboard/attendance"),
	S("dash-leaves", "/dashboard/leaves"),
	S("dash-expense-claims", "/dashboard/expense-claims"),
	S("dash-kpi", "/dashboard/kpi"),
	S("issues", "/issues"),
	S("issues-new", "/issues/new"),
	S("issues-detail", ids.issue ? `/issues/${ids.issue}` : null),
	S("hr-issue-board", "/hr/issues"),
	S("sop", "/sop"),
	S("sop-detail", ids.sop ? `/sop/${ids.sop}` : null),
	S("team", "/team"),
	S("more", "/more"),
	S("profile", "/profile"),
	S("notifications", "/notifications"),
	S("settings", "/settings"),
	S("change-password", "/change-password"),
	S("hr-contacts", "/hr-contacts"),
	S("remote-approvals", "/remote-approvals"),
	S("invalid-employee", "/invalid-employee"),
	S("design-specimen", "/design"),
	S("attendance-requests", "/attendance-requests"),
	S("attendance-requests-new", "/attendance-requests/new"),
	S("attendance-requests-detail", ids.attReq ? `/attendance-requests/${ids.attReq}` : null),
	S("shift-requests", "/shift-requests"),
	S("shift-requests-new", "/shift-requests/new"),
	S("shift-requests-detail", ids.shiftReq ? `/shift-requests/${ids.shiftReq}` : null),
	S("shift-assignments", "/shift-assignments"),
	S("shift-assignments-detail", ids.shiftAssign ? `/shift-assignments/${ids.shiftAssign}` : null),
	S("employee-checkins", "/employee-checkins"),
	S("expense-claims", "/expense-claims"),
	S("expense-claims-new", "/expense-claims/new"),
	S("expense-claims-detail", ids.claim ? `/expense-claims/${ids.claim}` : null),
	S("leave-applications", "/leave-applications"),
	S("leave-applications-new", "/leave-applications/new"),
	S("leave-applications-detail", ids.leave ? `/leave-applications/${ids.leave}` : null),
	S("ot-requests", "/ot-requests"),
	S("ot-requests-new", "/ot-requests/new"),
	S("ot-requests-detail", ids.ot ? `/ot-requests/${ids.ot}` : null),
	S("replacement-leave", "/replacement-leave"),
	S("replacement-leave-new", "/replacement-leave/claims/new"),
	S("replacement-leave-detail", ids.rlc ? `/replacement-leave/claims/${ids.rlc}` : null),
].filter((s) => !ONLY || ONLY.includes(s.slug))

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
		const page = await ctx.newPage()
		const errs = []
		page.on("console", (m) => { if (m.type() === "error") errs.push(m.text().slice(0, 300)) })
		page.on("pageerror", (e) => errs.push("PAGEERROR " + String(e).slice(0, 300)))

		for (const s of screens) {
			const suffix = `${v.vp}-${v.theme}${v.rt ? "-rt" : ""}`
			const base = `${s.slug}__${suffix}`
			errs.length = 0
			let note = "ok"
			try {
				await page.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle", timeout: 35000 })
				await page.waitForTimeout(2200)
				const landed = new URL(page.url()).pathname.replace("/hrms", "") || "/"
				if (landed !== s.path && !s.path.includes(landed)) note = `redirected to ${landed}`
				await page.screenshot({ path: `${OUT}/${base}.png` })
				if (v.bottom) {
					// Ionic scrolls inside ion-content, not the window
					await page.evaluate(async () => {
						const c = document.querySelector("ion-content")
						if (c?.scrollToBottom) await c.scrollToBottom(0)
						else window.scrollTo(0, document.body.scrollHeight)
					})
					await page.waitForTimeout(900)
					await page.screenshot({ path: `${OUT}/${base}__bottom.png` })
				}
			} catch (e) {
				note = "CAPTURE FAIL " + String(e).split("\n")[0].slice(0, 140)
			}
			manifest.push({ file: base, slug: s.slug, path: s.path, ...v, note, errors: [...new Set(errs)] })
			console.log(`${base}  ${note}${errs.length ? "  [" + errs.length + " console errors]" : ""}`)
		}
		await ctx.close()
	}
}

fs.writeFileSync(`${OUT}/../manifest.json`, JSON.stringify(manifest, null, 2))
console.log("DONE " + manifest.length + " captures")
await browser.close()
