// The pull gate (6 Oct 2026). Pull-to-refresh "never reloaded anything" TWICE: on 28 Sep the template
// binding was replaced by a raw listener, and four source-reading tests pinned that, but they only read the
// file. A real pull on the running app still did nothing, because the browser's element fires "ion-refresh"
// (Ionic's Vue wrapper renames every event to kebab-case) while the component listened for "ionRefresh".
// This test drags with real touch events and asserts what a person would see: data requests go out.
import { test, expect, devices } from "@playwright/test"
import { BASE, login } from "./screens.mjs"

// screens that carry a pull-down, and one request the pull must make
const SCREENS = [
	{ path: "/home", expect: /api\.now\.get_now|get_home_week|needs_you/ },
	{ path: "/requests", expect: /get_list|request_counts|get_leave|get_expense|get_ot|get_shift|get_attendance/ },
	{ path: "/approvals", expect: /approvals_list|get_approvals|remote_checkin/ },
	{ path: "/announcements", expect: /announcements/ },
]

async function pullDown(page, ctx) {
	const cdp = await ctx.newCDPSession(page)
	await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: 195, y: 200, id: 1 }] })
	for (let i = 1; i <= 24; i++) {
		await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: 195, y: 200 + i * 15, id: 1 }] })
		await page.waitForTimeout(30)
	}
	await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] })
}

for (const s of SCREENS) {
	test(`a real pull-down on ${s.path} reloads its data`, async ({ browser }) => {
		// a real phone context: the config's desktop default plus touch delivers the gesture twice (touch and emulated mouse)
		const ctx = await browser.newContext({ ...devices["iPhone 13"], storageState: await login(browser) })
		const page = await ctx.newPage()
		const calls = []
		page.on("request", (r) => { const u = r.url(); if (u.includes("/api/")) calls.push(u.split("/api/")[1].split("?")[0]) })
		const logs = []
		page.on("console", (m) => { if (/\[GPullRefresh\] refresh started/.test(m.text())) logs.push(m.text()) })
		await page.goto(`${BASE}/hrms${s.path}`, { waitUntil: "domcontentloaded" })
		await page.waitForTimeout(3500)
		calls.length = 0
		await pullDown(page, ctx)
		await page.waitForTimeout(3500)
		expect(logs, "the component's own handler must run").toHaveLength(1)
		expect(calls.join(" "), "the pull must make the screen's data requests").toMatch(s.expect)
	})
}
