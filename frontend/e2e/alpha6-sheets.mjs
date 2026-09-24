// alpha.6 E3: open every sheet a person can reach by tapping, and measure it
// against the rulebook (docs/glass/plan/alpha6-standard.md §8): Close on the
// leading edge, a title, nothing wider than the screen, no jargon, no email,
// and it closes again with Close. The first audit never opened a sheet.
//   cd frontend && set -a && . ../.env && set +a && node e2e/alpha6-sheets.mjs
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs"
import { chromium } from "playwright"
import { BASE, PW } from "./screens.mjs"

const OUT = process.env.OUT || "/tmp/alpha6/sheets"
mkdirSync(OUT, { recursive: true })
const LOG = `${OUT}/sheets.jsonl`
writeFileSync(LOG, "")

const BANNED = /\b(posting date|explanation|ot date|claimed hours|approver|sanctioned|leave type|shift type|expense claim type|docstatus|naming series)\b/i

//: [who, page, how to open (a button's accessible name), what it is]
const SHEETS = [
	["staff", "/requests", /^new request$/i, "New request"],
	["staff", "/requests", /all balances/i, "All balances"],
	["staff", "/home", /^check in$/i, "Check in"],
	["staff", "/dashboard/attendance", /^\d{1,2}$/, "Day (calendar)"],
	["staff", "/more", /public holidays/i, "Public holidays"],
	["staff", "/profile", /your details/i, "Your details"],
	["staff", "/support", /who to ask/i, "Who to ask"],
	["staff", "/expense-claims/new", /add an expense/i, "New expense item"],
	["staff", "/leave-applications/new", /kind of leave|leave type/i, "(picker is native; skipped)"],
	["approver", "/approvals", /W0 employee · \d+ request/i, "Approval"],
	["approver", "/approvals", /already answered/i, "Answered"],
]

async function session(browser, usr) {
	const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
	const res = await ctx.request.post(`${BASE}/api/method/login`, { form: { usr, pwd: PW } })
	if (res.status() !== 200) throw new Error(`login ${usr}: ${res.status()}`)
	return ctx
}

function measure(banned) {
	// The topmost PRESENTED sheet (ion-modal gets .show-modal while open).
	const sheet = [...document.querySelectorAll("ion-modal.show-modal")].pop()
	if (!sheet) return { open: false }
	const R = new RegExp(banned, "i")
	const box = sheet.querySelector(".g-sheet") || sheet
	const close = box.querySelector(".g-sheet__close")
	const title = (box.querySelector(".g-sheet__title")?.textContent || "").trim()
	const bar = box.querySelector(".g-sheet__bar")?.getBoundingClientRect()
	const texts = [...box.querySelectorAll("*")].filter((e) => e.children.length === 0 && e.getBoundingClientRect().height > 0).map((e) => (e.textContent || "").trim()).filter(Boolean)
	return {
		open: true,
		title,
		closeLeading: close && bar ? close.getBoundingClientRect().left - bar.left < 60 : false,
		tooWide: [...box.querySelectorAll("*")].some((e) => e.getBoundingClientRect().right > innerWidth + 1),
		jargon: [...new Set(texts.filter((t) => R.test(t)))].slice(0, 5),
		emails: texts.filter((t) => /[\w.]+@[\w.]+\.\w+/.test(t)).slice(0, 3),
		heavy: texts.length ? [...box.querySelectorAll("*")].filter((e) => e.children.length === 0 && +getComputedStyle(e).fontWeight >= 800).length : 0,
	}
}

const browser = await chromium.launch()
const who = { staff: "nadi.w0.employee@example.invalid", approver: "nadi.w0.approver@example.invalid" }
const ctxs = {}
let n = 0
for (const [persona, path, opener, name] of SHEETS) {
	if (name.includes("skipped")) continue
	ctxs[persona] ||= await session(browser, who[persona])
	const page = await ctxs[persona].newPage()
	const row = { persona, path, name }
	try {
		await page.goto(`${BASE}/hrms${path}`, { waitUntil: "networkidle", timeout: 35000 })
		await page.waitForTimeout(900)
		const target = page.getByRole("button", { name: opener }).or(page.getByRole("link", { name: opener })).first()
		if (!(await target.count())) {
			row.result = "no opener on this page for this person"
		} else {
			await target.click()
			await page.waitForTimeout(1000)
			Object.assign(row, await page.evaluate(measure, BANNED.source))
			await page.screenshot({ path: `${OUT}/${String(++n).padStart(2, "0")}-${name.replace(/\W+/g, "-")}.png` })
			const closeBtn = page.locator("ion-modal .g-sheet__close").last()
			if (await closeBtn.count()) {
				await closeBtn.click()
				await page.waitForTimeout(900)
				row.closes = !(await page.evaluate(() => [...document.querySelectorAll("ion-modal")].some((m) => m.classList.contains("show-modal"))))
			}
		}
	} catch (e) {
		row.error = String(e).split("\n")[0].slice(0, 140)
	}
	appendFileSync(LOG, JSON.stringify(row) + "\n")
	console.info(JSON.stringify(row))
	await page.close()
}
await browser.close()
