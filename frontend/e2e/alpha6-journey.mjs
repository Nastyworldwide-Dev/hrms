// alpha.6 screen journeys: the employee files each request through the real
// forms; the approver decides each through the real Approvals screen. Asserted
// on SERVER state after each tap, plus a screenshot of every step.
//   cd frontend && set -a && . ../.env && set +a && node e2e/alpha6-journey.mjs
// Local test site only (W0 fixture); every request it creates is deleted.
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs"
import { chromium } from "playwright"
import { BASE, PW } from "./screens.mjs"

const OUT = process.env.OUT || "/tmp/alpha6/journey"
mkdirSync(OUT, { recursive: true })
const LOG = `${OUT}/journey.jsonl`
writeFileSync(LOG, "")

const STAFF = "nadi.w0.employee@example.invalid"
const APPROVER = "nadi.w0.approver@example.invalid"
const results = []
let shot = 0

function record(kind, step, ok, detail = "") {
	const row = { kind, step, ok, detail: String(detail).slice(0, 200) }
	results.push(row)
	appendFileSync(LOG, JSON.stringify(row) + "\n")
	console.info(`${ok ? "PASS" : "FAIL"}  ${kind.padEnd(14)} ${step.padEnd(44)} ${row.detail}`)
}

async function session(browser, usr) {
	const ctx = await browser.newContext({
		viewport: { width: 390, height: 844 },
		isMobile: true,
		hasTouch: true,
		colorScheme: "dark",
	})
	const res = await ctx.request.post(`${BASE}/api/method/login`, { form: { usr, pwd: PW } })
	if (res.status() !== 200) throw new Error(`login ${usr}: ${res.status()}`)
	await ctx.addInitScript(() => localStorage.setItem("hrms:theme", "dark"))
	const page = await ctx.newPage()
	const errors = []
	page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)))
	page.on("response", async (r) => {
		if (r.url().includes("/api/") && r.status() >= 400) {
			let body = ""
			try {
				body = (await r.text()).slice(0, 300)
			} catch {}
			errors.push(`${r.status()} ${r.url().split("/api/")[1].slice(0, 60)} ${body}`)
		}
	})
	return { ctx, page, errors }
}

async function snap(page, name) {
	shot++
	await page.screenshot({ path: `${OUT}/${String(shot).padStart(2, "0")}-${name}.png` })
}

async function api(page, method, path, data) {
	const r = await page.request.fetch(`${BASE}/api/${path}`, {
		method,
		headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": await csrf(page) },
		...(data ? { data } : {}),
	})
	return r.json().catch(() => ({}))
}

async function csrf(page) {
	return page.evaluate(() => window.csrf_token || window.frappe?.csrf_token || "").catch(() => "")
}

async function newest(page, doctype, since) {
	const f = encodeURIComponent(JSON.stringify([["owner", "=", STAFF], ["creation", ">=", since]]))
	const r = await api(page, "GET", `resource/${encodeURIComponent(doctype)}?filters=${f}&order_by=creation%20desc&limit_page_length=1`)
	return r?.data?.[0]?.name || null
}

async function settle(page) {
	await page.waitForLoadState("networkidle").catch(() => {})
	await page.waitForTimeout(700)
}

// ---- field helpers: find controls by their accessible name, as a screen reader does
function control(scope, label) {
	return scope.getByLabel(label, { exact: false }).first()
}
async function pickSelect(scope, label, optionMatch) {
	const el = control(scope, label)
	const tag = await el.evaluate((e) => e.tagName)
	if (tag === "SELECT") {
		const opts = await el.locator("option").allTextContents()
		const want = opts.find((o) => optionMatch.test(o)) || opts.find((o) => o.trim())
		await el.selectOption({ label: want })
		return want
	}
	await el.click()
	await scope.page?.().waitForTimeout?.(500)
	const opt = scope.getByRole("option").filter({ hasText: optionMatch }).first()
	const txt = await opt.textContent()
	await opt.click()
	return txt
}
async function fillDate(scope, label, value) {
	const el = control(scope, label)
	await el.fill(value)
	await el.dispatchEvent("change")
}
async function fillText(scope, label, text) {
	const byName = control(scope, label)
	if (await byName.count()) return byName.fill(text)
	// A textarea without a name: the one after the visible label text.
	const lab = scope.getByText(label, { exact: true }).first()
	return lab.locator("xpath=following::textarea[1]").fill(text)
}
async function tapSave(page) {
	const btn = page.getByRole("button", { name: /^(save|submit|send.*)$/i }).last()
	await btn.click()
	await settle(page)
}

const iso = (d) => d.toISOString().slice(0, 10)
const ago = (n) => iso(new Date(Date.now() - n * 864e5))
const ahead = (n) => iso(new Date(Date.now() + n * 864e5))

// ---- the journeys -------------------------------------------------------------
const JOURNEYS = [
	{
		kind: "Time off",
		doctype: "Leave Application",
		path: "/leave-applications/new",
		async fill(page) {
			await pickSelect(page, "Leave type", /Annual/)
			await fillDate(page, "From date", ahead(20))
			await fillDate(page, "To date", ahead(20))
			await fillText(page, "Reason", "screen journey")
		},
	},
	{
		kind: "Fix a day",
		doctype: "Attendance Request",
		path: "/attendance-requests/new",
		async fill(page) {
			await fillDate(page, "From date", ago(6))
			await fillDate(page, "To date", ago(6))
			await pickSelect(page, "Reason", /On Duty/)
			await fillText(page, "Explanation", "screen journey")
		},
	},
	{
		kind: "Shift change",
		doctype: "Shift Request",
		path: "/shift-requests/new",
		async fill(page) {
			await pickSelect(page, "Shift type", /Night/)
			await pickSelect(page, "Approver", /approver/i)
			await fillDate(page, "From date", ahead(25))
			await fillDate(page, "To date", ahead(25))
		},
	},
	{
		kind: "Expense",
		doctype: "Expense Claim",
		path: "/expense-claims/new",
		async fill(page) {
			await page.getByRole("button", { name: /add an expense|add/i }).first().click()
			await page.waitForTimeout(600)
			await snap(page, "expense-item-sheet")
			const sheet = page.locator("ion-modal").last()
			await sheet.getByLabel("Expense claim type").selectOption({ label: "Travel" })
			await sheet.getByLabel("Expense date").fill(ago(3))
			await sheet.getByLabel(/^Amount/).fill("12.50")
			await sheet.getByRole("button", { name: /^add expense$/i }).click()
			await page.waitForTimeout(500)
		},
	},
]

async function staffFiles(browser) {
	const { ctx, page, errors } = await session(browser, STAFF)
	const filed = []
	for (const j of JOURNEYS) {
		errors.length = 0
		const since = new Date(Date.now() - 5000).toISOString().replace("T", " ").slice(0, 19)
		try {
			await page.goto(`${BASE}/hrms${j.path}`, { waitUntil: "domcontentloaded" })
			await settle(page)
			await j.fill(page)
			await snap(page, `${j.kind}-filled`)
			await tapSave(page)
			await snap(page, `${j.kind}-after-save`)
			const name = await newest(page, j.doctype, since)
			record(j.kind, "staff files it through the form", !!name, name || errors.join(" | ") || "no record created")
			if (name) filed.push({ ...j, name })
		} catch (e) {
			await snap(page, `${j.kind}-error`).catch(() => {})
			record(j.kind, "staff files it through the form", false, `${String(e).split("\n")[0]} ${errors.join(" | ")}`)
		}
	}
	await ctx.close()
	return filed
}

async function approverDecides(browser, filed) {
	const { ctx, page, errors } = await session(browser, APPROVER)
	await page.goto(`${BASE}/hrms/approvals`, { waitUntil: "domcontentloaded" })
	await settle(page)
	await snap(page, "approvals-queue")
	for (const [i, f] of filed.entries()) {
		errors.length = 0
		const decision = i % 2 === 0 ? "Approved" : "Rejected"
		try {
			await page.goto(`${BASE}/hrms/approvals`, { waitUntil: "domcontentloaded" })
			await settle(page)
			// Open THIS request: the queue groups by type, then person; a person
			// with several requests opens their list, and the list row is chosen
			// by the request's own date line.
			// The row that follows this request type's caption ("Time off · 1").
			const caption = page.locator("p.g-approvals__kind").filter({ hasText: new RegExp(`^\\s*${f.kind}\\s*·`) }).first()
			await caption.locator("xpath=following-sibling::*[contains(@class,'g-row') or self::button][1]").click()
			await page.waitForTimeout(700)
			const dialogRows = page.locator("ion-modal .g-row, ion-modal button.g-row, [role=dialog] .g-row")
			if (await dialogRows.count()) {
				// the newest is ours (oldest-first list)
				await dialogRows.last().click()
				await page.waitForTimeout(800)
			}
			const sheetName = await page.evaluate(() => location.href)
			void sheetName
			await snap(page, `${f.kind}-approver-sheet`)
			if (decision === "Approved") {
				await page.getByRole("button", { name: /^approve$/i }).last().click()
			} else {
				await page.getByRole("button", { name: /^reject$/i }).last().click()
				await page.waitForTimeout(400)
				await page.locator("textarea").last().fill("screen journey decline")
				await page.getByRole("button", { name: /^reject$/i }).last().click()
			}
			await settle(page)
			await snap(page, `${f.kind}-after-${decision}`)
			// Wait for the server, not a fixed sleep: poll until the decision lands.
			let doc = {}
			for (let t = 0; t < 10; t++) {
				doc = (await api(page, "GET", `resource/${encodeURIComponent(f.doctype)}/${f.name}`))?.data || {}
				if (doc.docstatus === 1) break
				await page.waitForTimeout(500)
			}
			const toast = await page.locator(".g-toast, [role=status], [role=alert]").allTextContents().catch(() => [])
			const field = f.doctype === "Expense Claim" ? "approval_status" : "status"
			const ok = doc.docstatus === 1 && doc[field] === decision
			record(f.kind, `approver taps ${decision === "Approved" ? "Approve" : "Reject"}`, ok, `${doc[field]} docstatus=${doc.docstatus} toast="${toast.join(" ").trim().slice(0, 60)}" ${errors.join(" | ")}`)
		} catch (e) {
			await snap(page, `${f.kind}-approver-error`).catch(() => {})
			record(f.kind, `approver decides (${decision})`, false, `${String(e).split("\n")[0]} ${errors.join(" | ")}`)
		}
	}
	await ctx.close()
}

async function cleanup(browser, filed) {
	// Remove what this run created (decided docs are cancelled first).
	const ctx = await browser.newContext()
	await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: "Administrator", pwd: process.env.ADMIN_PW || "admin" } })
	for (const f of filed) {
		const r = await ctx.request.post(`${BASE}/api/method/frappe.client.cancel`, { form: { doctype: f.doctype, name: f.name } })
		await ctx.request.post(`${BASE}/api/method/frappe.client.delete`, { form: { doctype: f.doctype, name: f.name } })
		void r
	}
	await ctx.close()
}

const browser = await chromium.launch()
const filed = await staffFiles(browser)
await approverDecides(browser, filed)
if (!process.env.KEEP) await cleanup(browser, filed)
await browser.close()
const fails = results.filter((r) => !r.ok).length
console.info(`\n${results.length} steps, ${fails} fail → ${OUT}`)
