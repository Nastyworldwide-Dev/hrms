// alpha.9 D25: the iOS rules the page audit (ios-consistency-audit.mjs)
// applies, applied INSIDE every sheet a person reaches by tapping. The page
// audit skips ion-modal on purpose; this is the other half.
// The check-in clock (GClock) is the sheet's one hero figure, like a large
// title, not a line of loose text.
//   cd frontend && set -a && . ../.env && set +a && node e2e/sheet-consistency-audit.mjs
import { webkit } from "playwright"
import { BASE, PW } from "./screens.mjs"

const SHEETS = [
	["staff", "/requests", /^new request$/i, "New request"],
	["staff", "/requests", /leave left|all balances/i, "All balances"],
	["staff", "/requests", /^see all$/i, "All your requests"],
	["staff", "/home", /^check in$/i, "Check in"],
	["staff", "/dashboard/attendance", /what the colours mean/i, "Colours"],
	["staff", "/more", /public holidays/i, "Public holidays"],
	["staff", "/profile", /your details/i, "Your details"],
	["staff", "/support", /who to ask/i, "Who to ask"],
	["staff", "/expense-claims/new", /add an expense/i, "New expense item"],
	["approver", "/approvals", /already answered/i, "Answered"],
]
const who = { staff: "nadi.w0.employee@example.invalid", approver: "nadi.w0.approver@example.invalid" }

const browser = await webkit.launch()
const ctxs = {}
let bad = 0
for (const [persona, path, opener, name] of SHEETS) {
	if (!ctxs[persona]) {
		ctxs[persona] = await browser.newContext({ viewport: { width: 402, height: 874 }, hasTouch: true })
		await ctxs[persona].addInitScript(() => localStorage.setItem("hrms:install-prompt-dismissed", String(Date.now())))
		await ctxs[persona].request.post(`${BASE}/api/method/login`, { form: { usr: who[persona], pwd: PW } })
	}
	const page = await ctxs[persona].newPage()
	try {
		await page.goto(`${BASE}/hrms${path}`, { waitUntil: "networkidle", timeout: 35000 })
		await page.waitForTimeout(800)
		const target = page.getByRole("button", { name: opener }).or(page.getByRole("link", { name: opener })).first()
		if (!(await target.count())) { console.log(name, "| no opener"); await page.close(); continue }
		await target.click()
		await page.waitForTimeout(1200)
		const issues = await page.evaluate(() => {
			const sheet = [...document.querySelectorAll("ion-modal.show-modal")].pop()
			if (!sheet) return ["did not open"]
			const box = sheet.querySelector(".g-sheet") || sheet
			const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && !e.closest(".sr-only") }
			const R = (n) => Math.round(n)
			const uniq = (a) => [...new Set(a)]
			const out = []
			const sheetBox = box.getBoundingClientRect()
			const groups = [...box.querySelectorAll(".g-form-group, .g-list")].filter(vis)
			const edges = uniq(groups.map((g) => { const r = g.getBoundingClientRect(); return `${R(r.left - sheetBox.left)}-${R(sheetBox.right - r.right)}` }))
			if (edges.length > 1) out.push(`group side margins differ: ${edges}`)
			const radii = uniq(groups.map((g) => getComputedStyle(g).borderTopLeftRadius))
			if (radii.length > 1) out.push(`group radii differ: ${radii}`)
			const RAMP = [11, 12, 13, 15, 16, 17, 20, 22, 28, 34]
			const texts = [...box.querySelectorAll("*")].filter((e) => vis(e) && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) && !e.closest(".g-avatar"))
			const offRamp = uniq(texts.map((e) => R(parseFloat(getComputedStyle(e).fontSize))).filter((s) => !RAMP.includes(s)))
			if (offRamp.length) out.push(`type off the ramp: ${offRamp}px (${texts.filter((e) => !RAMP.includes(R(parseFloat(getComputedStyle(e).fontSize)))).slice(0, 2).map((e) => JSON.stringify(e.textContent.trim().slice(0, 20))).join(", ")})`)
			const heads = [...box.querySelectorAll(".g-form-section__title, .g-eyebrow")].filter(vis)
			const hx = uniq(heads.map((h) => R(h.getBoundingClientRect().left + parseFloat(getComputedStyle(h).paddingLeft) - sheetBox.left)))
			if (hx.length > 1) out.push(`section headers start at different x: ${hx}`)
			const loose = [...box.querySelectorAll("p, span")].filter(vis).filter((e) => !e.closest(".g-form-group, .g-list, .g-glass, .g-form-footer, .g-form-section__title, .g-eyebrow, .g-empty, button, a, .g-sheet__head, .g-sheet__bar, label, .g-chips, .g-segmented, .g-searchbar, .g-clock") && e.textContent.trim().length > 3 && e.children.length === 0)
			if (loose.length) out.push(`loose text: ${loose.length} (${loose.slice(0, 2).map((e) => JSON.stringify(e.textContent.trim().slice(0, 28))).join(", ")})`)
			const btns = uniq([...box.querySelectorAll(".g-btn")].filter(vis).map((x) => R(x.getBoundingClientRect().height)))
			if (btns.length > 1) out.push(`button heights differ: ${btns}`)
			return out
		})
		if (issues.length) bad++
		console.log(name, "|", issues.length ? issues.join(" || ") : "ok")
	} catch (e) {
		console.log(name, "| ERR", String(e).split("\n")[0].slice(0, 120))
	}
	await page.close()
}
console.log("sheets", SHEETS.length, "with issues", bad)
const FAILED = bad
console.log(`GATE_COUNT ${FAILED}`)
await browser.close()
process.exit(FAILED ? 1 : 0)
