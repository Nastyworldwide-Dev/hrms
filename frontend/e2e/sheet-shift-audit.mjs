// alpha.8 r3 (owner, 25 Sep 2026: "jumpy stuff on certain pages AND SHEETS …
// every bit measured"). Opens every sheet a person reaches by tapping (the
// alpha6-sheets list), in Safari's engine at 402×874, and per sheet reports:
//   settleMs   when the sheet stopped moving (its slide-up)
//   shifts     content that moved AFTER the sheet had settled — a jump
//   extra      how far the sheet's own scroller runs past its content
//   cd frontend && set -a && . ../.env && set +a && node e2e/sheet-shift-audit.mjs
import { webkit } from "playwright"
import { BASE, PW } from "./screens.mjs"

const SHEETS = [
	["staff", "/requests", /^new request$/i, "New request"],
	["staff", "/requests", /all balances|leave left/i, "All balances"],
	["staff", "/requests", /^see all$/i, "All your requests"],
	["staff", "/home", /^check in$/i, "Check in"],
	["staff", "/dashboard/attendance", /^\d{1,2} \w+, /, "Day (calendar)"],
	["staff", "/dashboard/attendance", /what the colours mean/i, "Colours"],
	["staff", "/more", /public holidays/i, "Public holidays"],
	["staff", "/profile", /your details/i, "Your details"],
	["staff", "/support", /who to ask/i, "Who to ask"],
	["staff", "/expense-claims/new", /add an expense/i, "New expense item"],
	["approver", "/approvals", /W0 employee · \d+ request/i, "Approval"],
	["approver", "/approvals", /already answered/i, "Answered"],
]
const who = { staff: "nadi.w0.employee@example.invalid", approver: "nadi.w0.approver@example.invalid" }

const browser = await webkit.launch()
const ctxs = {}
let bad = 0
for (const [persona, path, opener, name] of SHEETS) {
	if (!ctxs[persona]) {
		ctxs[persona] = await browser.newContext({ viewport: { width: 402, height: 874 }, hasTouch: true, colorScheme: "dark" })
		await ctxs[persona].addInitScript(() => localStorage.setItem("hrms:install-prompt-dismissed", String(Date.now())))
		await ctxs[persona].request.post(`${BASE}/api/method/login`, { form: { usr: who[persona], pwd: PW } })
	}
	const page = await ctxs[persona].newPage()
	const row = { name }
	try {
		await page.goto(`${BASE}/hrms${path}`, { waitUntil: "networkidle", timeout: 35000 })
		await page.waitForTimeout(800)
		const target = page.getByRole("button", { name: opener }).or(page.getByRole("link", { name: opener })).first()
		if (!(await target.count())) { row.result = "no opener"; console.log(JSON.stringify(row)); await page.close(); continue }
		await page.evaluate(() => {
			window.__f = []
			// One id per ELEMENT: keyed by tag+text, every unnamed <svg> in a
			// sheet was one key and different icons were compared as one.
			const ids = new WeakMap()
			let nextId = 0
			const t0 = performance.now()
			const tick = () => {
				const m = [...document.querySelectorAll("ion-modal.show-modal")].pop()
				if (m) {
					const wrap = m.shadowRoot?.querySelector(".modal-wrapper")
					const wr = wrap?.getBoundingClientRect()
					const kids = [...m.querySelectorAll(".g-sheet *")].filter((e) => e.children.length <= 3 && e.getBoundingClientRect().height >= 8)
					window.__f.push({ t: Math.round(performance.now() - t0), sheetTop: wr ? Math.round(wr.top) : null, sheetH: wr ? Math.round(wr.height) : null, pos: kids.map((e) => { if (!ids.has(e)) ids.set(e, `${nextId++}:${e.tagName.toLowerCase()}.${String(e.className).split(" ")[0]} ${(e.textContent || "").trim().slice(0, 18)}`); return [ids.get(e), Math.round(e.getBoundingClientRect().top - (wr?.top || 0))] }) })
				}
				if (performance.now() - t0 < 3000) requestAnimationFrame(tick)
			}
			requestAnimationFrame(tick)
		})
		await target.click()
		await page.waitForTimeout(3200)
		Object.assign(row, await page.evaluate(async () => {
			const f = window.__f
			if (!f.length) return { open: false }
			// settled = the sheet's top stops changing for good
			let settle = f.length - 1
			while (settle > 0 && f[settle - 1].sheetTop === f.at(-1).sheetTop && f[settle - 1].sheetH === f.at(-1).sheetH) settle--
			const after = f.slice(settle)
			const moved = new Map()
			for (let i = 1; i < after.length; i++) {
				const prev = new Map(after[i - 1].pos)
				for (const [k, top] of after[i].pos) if (prev.has(k) && Math.abs(prev.get(k) - top) > 2) moved.set(k, `${top - prev.get(k)}@${after[i].t}ms`)
			}
			const heights = new Set(f.slice(settle).map((x) => x.sheetH))
			const m = [...document.querySelectorAll("ion-modal.show-modal")].pop()
			// A sheet scrolls in .g-sheet (GModal), not in an ion-content.
			const sc = m?.querySelector(".g-sheet")
			let extra = null, overscroll = null
			if (sc) {
				let bottom = 0
				for (const e of sc.querySelectorAll("*")) { const r = e.getBoundingClientRect(); if (r.height > 0 && getComputedStyle(e).position !== "sticky") bottom = Math.max(bottom, r.bottom + sc.scrollTop) }
				const pad = parseFloat(getComputedStyle(sc).paddingBottom) || 0
				const contentH = bottom + pad - sc.getBoundingClientRect().top
				// runs past its content: scrollable though everything fits
				extra = contentH <= sc.clientHeight + 1 ? Math.round(sc.scrollHeight - sc.clientHeight) : 0
				overscroll = getComputedStyle(sc).overscrollBehaviorY
			}
			return { open: true, settleMs: f[settle].t, sheetH: f.at(-1).sheetH, resized: heights.size > 1, overscroll, shifts: [...moved].slice(0, 5).map(([k, v]) => `${k} ${v}`), extra }
		}))
		if (row.shifts?.length || row.resized || row.extra > 2 || (row.open && row.overscroll !== "contain")) bad++
	} catch (e) {
		row.error = String(e).split("\n")[0].slice(0, 140)
	}
	console.log(JSON.stringify(row))
	await page.close()
}
console.log("sheets", SHEETS.length, "moving", bad)
await browser.close()
