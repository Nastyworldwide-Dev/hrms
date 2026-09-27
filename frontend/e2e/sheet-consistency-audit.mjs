// alpha.9 D25: the iOS rules the page audit (ios-consistency-audit.mjs)
// applies, applied INSIDE every sheet a person reaches by tapping. The page
// audit skips ion-modal on purpose; this is the other half.
// The check-in clock (GClock) is the sheet's one hero figure, like a large
// title, not a line of loose text.
//   cd frontend && set -a && . ../.env && set +a && node e2e/sheet-consistency-audit.mjs
import { webkit } from "playwright"
import { BASE, PW } from "./screens.mjs"
import { withPendingLeave } from "./pendingRequest.mjs"

const SHEETS = [
	["staff", "/requests", /^new request$/i, "New request"],
	["staff", "/requests", /leave left|all balances/i, "All balances"],
	["staff", "/requests", /^see all$/i, "All your requests"],
	["staff", "/home", /^check in$/i, "Check in"],
	["staff", "/dashboard/attendance", /what the colours mean/i, "Colours"],
	["staff", "/dashboard/attendance", /^\d{1,2} \w+ \d{4}, /, "Day (calendar)"],
	["staff", "/more", /public holidays/i, "Public holidays"],
	["staff", "/profile", /your details/i, "Your details"],
	["staff", "/support", /who to ask/i, "Who to ask"],
	["staff", "/expense-claims/new", /add an expense/i, "New expense item"],
	["approver", "/approvals", /already answered/i, "Answered"],
	["approver", "/approvals", /W0 employee/i, "Approval"],
	// the sheet a sent request opens (owner screenshot, 27 Sep): Requests' last five
	["staff", "/requests", /^(overtime|time off|expense|shift change|fix a day) · /i, "Your request"],
	["staff", "/dashboard/leaves", /nadi w0 annual/i, "Request from Time off"],
	["staff", "/employee-checkins", /^(in|out)\b/i, "Check-in"],
]
const who = { staff: "nadi.w0.employee@example.invalid", approver: "nadi.w0.approver@example.invalid" }

const browser = await webkit.launch()
const ctxs = {}
let bad = 0
await withPendingLeave(browser, async () => {
for (const [persona, path, opener, name] of SHEETS) {
	if (!ctxs[persona]) {
		// alpha.14: the owner's phone is in dark mode, where the page colour and
		// the sheet colour differ; in light they are the same grey and a page-
		// coloured box inside a sheet cannot be seen. SCHEME picks one.
		ctxs[persona] = await browser.newContext({ viewport: { width: 402, height: 874 }, hasTouch: true, colorScheme: process.env.SCHEME || "dark" })
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
			// alpha.14 (owner screenshot, 27 Sep): the request sheet drew a black
			// page-coloured box inside the sheet, 12 px grey labels, a value cut at
			// the right edge and a text field inside a row. iOS: a sheet is the
			// grouped background; groups sit on it; nothing is a box in a box.
			const sheetBg = getComputedStyle(sheet).getPropertyValue("--background").trim()
			const bgOf = (e) => getComputedStyle(e).backgroundColor
			const opaque = (c) => c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent"
			const boxes = [...box.querySelectorAll("div, section")].filter(vis).filter((e) => {
				if (e.closest(".g-form-group, .g-list, .g-sheet__group, .g-sheet__head, .g-btn, .g-chips, .g-segmented, .g-cal, .g-clock, .g-selfie, .g-toast, .g-attachment, img, .g-map")) return false
				const r = e.getBoundingClientRect()
				// the sheet's own colour (its --background) is the sheet, not a box
				const probe = document.createElement("i")
				probe.style.color = sheetBg
				document.body.append(probe)
				const sheetRgb = getComputedStyle(probe).color
				probe.remove()
				return opaque(bgOf(e)) && r.width > sheetBox.width * 0.6 && r.height > 60 && bgOf(e) !== sheetRgb && !e.classList.contains("g-sheet")
			})
			if (boxes.length) out.push(`a box inside the sheet: ${boxes.slice(0, 2).map((e) => `${String(e.className).split(" ").slice(0, 3).join(".")} ${bgOf(e)}`).join(", ")}`)
			// every row reads at body size: a label beside a value, in any list
			// markup (the request sheet drew 12 pt labels in hand-made rows)
			const rowsLike = [...box.querySelectorAll("*")].filter((e) => vis(e) && e.children.length >= 2 && getComputedStyle(e).display === "flex" && getComputedStyle(e).flexDirection === "row" && e.getBoundingClientRect().height >= 36 && e.getBoundingClientRect().height <= 80 && !e.closest(".g-btn, .g-sheet__head, .g-chips, .g-segmented, .g-seg, .g-cal, .g-request-sheet__bar, .g-attachment, .g-exp-head"))
			const tinyLabels = rowsLike.map((r) => [...r.children].find((c) => vis(c) && c.textContent.trim())).filter((c) => c && !c.querySelector("svg, img, .g-avatar") && R(parseFloat(getComputedStyle(c).fontSize)) < 15)
			if (tinyLabels.length) out.push(`row labels under body size: ${tinyLabels.length} (${tinyLabels.slice(0, 2).map((e) => JSON.stringify(e.textContent.trim().slice(0, 18))).join(", ")})`)
			const cut = texts.filter((e) => { const r = e.getBoundingClientRect(); return r.right > sheetBox.right - 8 || r.left < sheetBox.left + 8 })
			if (cut.length) out.push(`text at the sheet edge: ${cut.length} (${cut.slice(0, 2).map((e) => JSON.stringify(e.textContent.trim().slice(0, 18))).join(", ")})`)
			return out
		})
		if (issues.length) bad++
		console.log(name, "|", issues.length ? issues.join(" || ") : "ok")
	} catch (e) {
		console.log(name, "| ERR", String(e).split("\n")[0].slice(0, 120))
	}
	await page.close()
}
})
console.log("sheets", SHEETS.length, "with issues", bad)
const FAILED = bad
console.log(`GATE_COUNT ${FAILED}`)
await browser.close()
process.exit(FAILED ? 1 : 0)
