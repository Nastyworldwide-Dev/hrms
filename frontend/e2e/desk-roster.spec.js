// S11, the Desk roster month view, live (7 Oct 2026). The unit tests in roster/src/components/__tests__ read the
// Vue source; this drives the real page at /hr/roster as HR and asserts what HR sees:
//   1. a day marked Off Day / Rest Day / Public Holiday (a Roster Day, no shift) shows its marker in the month grid
//      (the grid prints the full word, in the shift's own Day Type style, not the letters O / R / PH), and a day
//      with no marker shows none;
//   2. a real drag of one shift onto another swaps them and each shift keeps its own Day Type.
//
// Real data. Setup seeds three Roster Days and two submitted Shift Assignments (each with a Day Type) for three
// employees of the test company that hold none, through the bench; teardown removes everything those employees
// hold (and the Version / Deleted Document rows the swap leaves), also after a crashed run.
import { test, expect } from "@playwright/test"
import { BASE } from "./screens.mjs"
import { bench, isLocal } from "./bench.mjs"

const HR_USER = process.env.HR_USER
const HR_PW = process.env.HR_PW
const COMPANY = "Nadi W0 A"
const MARKED = "HR-EMP-00007" // W0 approver: three Roster Days
const SWAP_A = "HR-EMP-00010" // W0 hr: Day Shift, Off Day, on the 15th
const SWAP_B = "HR-EMP-00011" // W0 ceo: Afternoon, Public Holiday, on the 16th
const EMPLOYEES = [MARKED, SWAP_A, SWAP_B]
const NAME_A = "E2E-S11-A"
const NAME_B = "E2E-S11-B"

// the month the page opens on is the browser's own current month
const now = new Date()
const MONTH = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
const iso = (day) => `${MONTH}-${String(day).padStart(2, "0")}`

const CLEAN = `
emps = ${JSON.stringify(EMPLOYEES)}
names = frappe.get_all("Shift Assignment", filters={"employee": ("in", emps)}, pluck="name") + ["${NAME_A}", "${NAME_B}"]
frappe.db.delete("Shift Assignment", {"employee": ("in", emps)})
frappe.db.delete("Roster Day", {"employee": ("in", emps)})
frappe.db.delete("Version", {"ref_doctype": "Shift Assignment", "docname": ("in", names)})
frappe.db.delete("Deleted Document", {"deleted_doctype": "Shift Assignment", "deleted_name": ("in", names)})
`

function seed() {
	bench(`
emps = ${JSON.stringify(EMPLOYEES)}
held = frappe.db.count("Shift Assignment", {"employee": ("in", emps)}) + frappe.db.count("Roster Day", {"employee": ("in", emps)})
if held:
	raise Exception("refusing to seed: these employees already hold %d roster rows" % held)
for day, kind in ((20, "Off Day"), (21, "Rest Day"), (22, "Public Holiday")):
	frappe.get_doc({"doctype": "Roster Day", "employee": "${MARKED}", "date": "${MONTH}-%02d" % day, "day_type": kind}).insert()
def shift(name, employee, shift_type, day, day_type):
	doc = frappe.get_doc({
		"doctype": "Shift Assignment", "employee": employee, "company": "${COMPANY}", "shift_type": shift_type,
		"start_date": "${MONTH}-%02d" % day, "end_date": "${MONTH}-%02d" % day, "status": "Active",
		"day_type": day_type, "docstatus": 1,
	})
	doc.set_user_and_timestamp()
	doc.name = name
	doc.db_insert()  # straight in: no submit hooks, so no background re-stamp job for seed rows
shift("${NAME_A}", "${SWAP_A}", "Day Shift", 15, "Off Day")
shift("${NAME_B}", "${SWAP_B}", "Afternoon", 16, "Public Holiday")
`)
}

const cleanup = () => bench(CLEAN)

async function loginAsHr(browser) {
	const ctx = await browser.newContext()
	const res = await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: HR_USER, pwd: HR_PW } })
	if (res.status() !== 200) throw new Error(`HR login failed: ${res.status()}`)
	const state = await ctx.storageState()
	await ctx.close()
	return state
}

async function openRoster(browser) {
	const ctx = await browser.newContext({ storageState: await loginAsHr(browser), viewport: { width: 1600, height: 900 } })
	const page = await ctx.newPage()
	const swaps = []
	page.on("request", (req) => {
		if (req.method() === "POST" && req.url().includes("hrms.api.roster.swap_shift")) swaps.push(req.postDataJSON())
	})
	await page.goto(`${BASE}/hr/roster`, { waitUntil: "domcontentloaded" })
	// HR sees many companies, so none is preselected: pick the test company in the header
	const company = page.getByRole("button", { name: "Company" })
	await expect(company).toBeEnabled({ timeout: 20000 })
	await company.click()
	await page.getByRole("option", { name: COMPANY, exact: true }).click()
	await expect(page.getByText("Please select a company.")).toHaveCount(0)
	await expect(rowOf(page, MARKED)).toBeVisible({ timeout: 20000 })
	await expect(page.locator("table").first()).not.toHaveClass(/animate-pulse/)
	return { ctx, page, swaps }
}

const rowOf = (page, employee) => page.locator("tbody tr").filter({ hasText: employee === MARKED ? "W0 approver" : employee === SWAP_A ? "W0 hr" : "W0 ceo" })
// the first td is the employee; the day's cell is the td at index = day of month
const cellOf = (page, employee, day) => rowOf(page, employee).locator("td").nth(day)

// A real hand drag, not locator.dragTo(). dragTo jumps the pointer straight onto the target BEFORE the browser starts
// the drag, so the grid's own mouseenter handler (hoveredCell) records the TARGET's shift as the one being held and the
// drop is then refused as "same shift". A person's pointer leaves the source first; native drags fire no mouseenter.
async function dragInSteps(page, source, target) {
	await source.scrollIntoViewIfNeeded()
	await target.scrollIntoViewIfNeeded() // neighbouring days: both stay on screen
	const s = await source.boundingBox()
	const t = await target.boundingBox()
	const from = { x: s.x + s.width / 2, y: s.y + s.height / 2 }
	await page.mouse.move(from.x, from.y)
	await page.mouse.down()
	await page.mouse.move(from.x + 12, from.y + 12, { steps: 4 }) // past the drag threshold: dragstart on the source
	await page.mouse.move(t.x + t.width / 2, t.y + t.height / 2, { steps: 15 })
	await page.mouse.up()
}

test.describe("desk roster month view, live", () => {
	test.skip(!isLocal(BASE), "seeds through the local bench, so the site under test must be the bench site")
	test.skip(!HR_USER || !HR_PW, "set HR_USER and HR_PW (the repo .env) to sign in as HR")

	test.beforeEach(() => {
		cleanup()
		seed()
	})
	test.afterEach(() => {
		cleanup()
	})

	test("a day marked Off / Rest / Public Holiday shows its marker in the month grid", async ({ browser }) => {
		const { ctx, page } = await openRoster(browser)
		await expect(cellOf(page, MARKED, 20)).toHaveText("Off Day")
		await expect(cellOf(page, MARKED, 21)).toHaveText("Rest Day")
		await expect(cellOf(page, MARKED, 22)).toHaveText("Public Holiday")
		// a day with no marker and no shift shows none
		await expect(cellOf(page, MARKED, 23)).not.toContainText(/Off Day|Rest Day|Public Holiday/)
		// the seeded shifts carry their Day Type in the grid too
		await expect(cellOf(page, SWAP_A, 15)).toContainText("Day Shift")
		await expect(cellOf(page, SWAP_A, 15)).toContainText("Off Day")
		await expect(cellOf(page, SWAP_B, 16)).toContainText("Afternoon")
		await expect(cellOf(page, SWAP_B, 16)).toContainText("Public Holiday")
		await ctx.close()
	})

	test("dragging one shift onto another swaps them and each keeps its own Day Type", async ({ browser }) => {
		const { ctx, page, swaps } = await openRoster(browser)
		const source = cellOf(page, SWAP_A, 15).locator("[draggable=true]")
		const target = cellOf(page, SWAP_B, 16).locator("[draggable=true]")
		await expect(source).toContainText("Day Shift")
		await expect(target).toContainText("Afternoon")

		await dragInSteps(page, source, target)

		await expect.poll(() => swaps.length, { timeout: 15000 }).toBe(1)
		expect(swaps[0]).toMatchObject({
			src_shift: NAME_A,
			src_date: iso(15),
			tgt_employee: SWAP_B,
			tgt_date: iso(16),
			tgt_shift: NAME_B,
		})
		// the grid: each employee now holds the other's shift on their own day, each with ITS Day Type
		await expect(cellOf(page, SWAP_B, 16)).toContainText("Day Shift", { timeout: 15000 })
		await expect(cellOf(page, SWAP_B, 16)).toContainText("Off Day")
		await expect(cellOf(page, SWAP_B, 16)).not.toContainText("Public Holiday")
		await expect(cellOf(page, SWAP_A, 15)).toContainText("Afternoon")
		await expect(cellOf(page, SWAP_A, 15)).toContainText("Public Holiday")
		await expect(cellOf(page, SWAP_A, 15)).not.toContainText("Off Day")

		// and the records: the submitted assignments say the same
		const rows = bench(
			`
rows = frappe.get_all("Shift Assignment", filters={"employee": ("in", ${JSON.stringify([SWAP_A, SWAP_B])}), "docstatus": 1},
	fields=["employee", "shift_type", "day_type", "start_date"], order_by="employee")
emit([[r.employee, r.shift_type, r.day_type, str(r.start_date)] for r in rows])
`
		)
		expect(rows).toEqual([
			[SWAP_A, "Afternoon", "Public Holiday", iso(15)],
			[SWAP_B, "Day Shift", "Off Day", iso(16)],
		])
		await ctx.close()
	})
})
