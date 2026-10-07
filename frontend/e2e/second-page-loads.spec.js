// S10, the second page loads (7 Oct 2026). list-scroll.spec.js proves the scroll LISTENER is reached; this proves
// what the listener is for: on a list longer than one page, a real scroll to the bottom makes the client ask for
// page two and the rows on screen grow.
//
// REAL data, no route fake. The page size and the paging parameter are read from ListView.vue: page_length is 50 and
// the next page is asked for with `start` = the page length on frappe.desk.reportview.get. The test site's employee
// holds 40 Leave Applications, which is one page, so setup adds 20 more through the bench and teardown removes
// exactly those (name prefix E2E-S10-), also after a crashed run.
import { test, expect, devices } from "@playwright/test"
import { BASE, login } from "./screens.mjs"
import { bench, isLocal } from "./bench.mjs"

const PAGE_LENGTH = 50 // ListView.vue: listOptions.page_length
const SEEDED = 20
const OWNER = process.env.HRMS_E2E_USER || "nurul.aisyah@nastyworldwide.com"

const REMOVE = `frappe.db.delete("Leave Application", {"name": ("like", "E2E-S10-%")})`

function seedLeaves() {
	return bench(
		`
${REMOVE}
user, count = args[0], int(args[1])
emp = frappe.db.get_value("Employee", {"user_id": user}, ["name", "company"], as_dict=True)
for i in range(count):
	doc = frappe.get_doc({
		"doctype": "Leave Application", "employee": emp.name, "company": emp.company,
		"leave_type": "Casual Leave", "status": "Open", "docstatus": 0,
		"from_date": "2027-03-%02d" % (i + 1), "to_date": "2027-03-%02d" % (i + 1),
		"posting_date": "2026-10-07", "description": "E2E S10 second page, delete me",
	})
	doc.set_user_and_timestamp()
	doc.name = "E2E-S10-%04d" % i
	doc.db_insert()
emit(frappe.db.count("Leave Application", {"employee": emp.name, "docstatus": ("!=", 2)}))
`,
		[OWNER, String(SEEDED)]
	)
}

test.describe("list paging, live", () => {
	test.skip(!isLocal(BASE), "seeds through the local bench, so the site under test must be the bench site")

	test.afterEach(() => {
		bench(REMOVE)
	})

	test("a real scroll to the bottom asks for page two (start = page length) and the rows grow", async ({ browser }) => {
		const total = seedLeaves()
		expect(total, "the list must be longer than one page and shorter than two for this proof").toBeGreaterThan(PAGE_LENGTH)
		expect(total).toBeLessThanOrEqual(2 * PAGE_LENGTH)

		const ctx = await browser.newContext({ ...devices["iPhone 13"], storageState: await login(browser) })
		const page = await ctx.newPage()
		const asked = []
		page.on("request", (req) => {
			if (req.method() === "POST" && req.url().includes("frappe.desk.reportview.get")) {
				const body = req.postDataJSON()
				if (body?.doctype === "Leave Application") asked.push({ start: body.start, page_length: body.page_length })
			}
		})
		const rows = page.locator(".g-listview__row")

		await page.goto(`${BASE}/hrms/leave-applications`, { waitUntil: "domcontentloaded" })
		await expect(rows).toHaveCount(PAGE_LENGTH, { timeout: 20000 })
		expect(asked, "opening the list asks for page one only").toEqual([{ start: 0, page_length: PAGE_LENGTH }])

		// a real wheel scroll on the list, down to the bottom, until the next page is asked for
		const box = await page.locator("ion-content").boundingBox()
		await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
		await expect
			.poll(
				async () => {
					await page.mouse.wheel(0, 1500)
					return asked.length
				},
				{ timeout: 20000, intervals: [300] }
			)
			.toBeGreaterThan(1)

		expect(asked[1], "page two is asked for with start = the page length").toEqual({
			start: PAGE_LENGTH,
			page_length: PAGE_LENGTH,
		})
		await expect(rows).toHaveCount(total, { timeout: 20000 })

		// the last page was short, so scrolling on must not ask again
		for (let i = 0; i < 5; i++) {
			await page.mouse.wheel(0, 1500)
			await page.waitForTimeout(300)
		}
		await page.waitForTimeout(800)
		expect(asked, "a short last page ends the paging").toHaveLength(2)
		await ctx.close()
	})
})
