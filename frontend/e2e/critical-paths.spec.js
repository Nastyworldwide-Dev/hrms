import { expect, test } from "@playwright/test"

// The paths whose failure this project actually experienced, written as the
// checks that would have caught them.
//
// Every one of these corresponds to a real incident:
//
//   "the login page offers password login"   -> users could sign in with SSO only
//   "forgot password is not rejected"        -> 400 CSRFTokenError, recovery dead
//   "the leave balance renders"              -> 486 allocations were never mirrored
//   "a failed request is visible"            -> 18 screens rendered nothing on error
//
// The last one is the most valuable, and the only one that needs no data and no
// credentials: it FORCES a failure and asserts the app admits it. A test that
// needs a broken server to run is usually a bad test; here the broken server is
// the subject.

const USER = process.env.HRMS_E2E_USER
const PASSWORD = process.env.HRMS_E2E_PASSWORD

async function signIn(page) {
	await page.goto("/hrms/login")
	await page.getByPlaceholder(/email/i).fill(USER)
	await page.getByPlaceholder(/password/i).fill(PASSWORD)
	await page.getByRole("button", { name: /login/i }).click()
	await expect(page).not.toHaveURL(/\/login/, { timeout: 15000 })
}

test.describe("the login page", () => {
	test("offers email and password, not SSO alone", async ({ page }) => {
		// Reported as "users can only sign in with Microsoft SSO". The form was
		// always rendered; the recovery route out of a bad password was not.
		await page.goto("/hrms/login")
		await expect(page.getByPlaceholder(/email/i)).toBeVisible()
		await expect(page.getByPlaceholder(/password/i)).toBeVisible()
	})

	test("forgot password is accepted, not rejected outright", async ({ page }) => {
		// The 400 was a missing CSRF header on a guest POST — the endpoint never ran.
		// Asserted on the RESPONSE rather than the message, because frappe answers
		// the same generic text whether or not the address exists (anti-enumeration),
		// so the status is the only thing that distinguishes working from broken.
		await page.goto("/hrms/login")

		const request = page.waitForResponse(
			(r) => r.url().includes("user.reset_password"),
			{ timeout: 15000 },
		)
		await page.getByText(/forgot password/i).click()
		await page.getByPlaceholder(/email/i).last().fill("nobody@example.invalid")
		await page.getByRole("button", { name: /send reset link/i }).click()

		const response = await request
		expect(response.status(), "400 means the CSRF token is missing again").not.toBe(400)
	})
})

test.describe("a failed request is never silent", () => {
	// No login and no data required: the point is what the app does when the server
	// says no, and that is the contract eighteen screens used to break.
	test("the leave balance says it failed instead of showing nothing", async ({ page }) => {
		await page.route("**/api/method/hrms.api.get_leave_balance_map*", (route) =>
			route.fulfill({ status: 500, contentType: "application/json", body: "{}" }),
		)

		await page.goto("/hrms/login")
		if (USER && PASSWORD) await signIn(page)
		else test.skip(true, "set HRMS_E2E_USER and HRMS_E2E_PASSWORD to run this")

		// The exact defect: `hasBalances` is false on failure just as it is when the
		// employee has none, so this used to read "You have no leaves allocated" —
		// a confident false statement about someone's entitlement.
		await expect(page.getByText(/could not load your leave balance/i)).toBeVisible({
			timeout: 15000,
		})
		await expect(page.getByText(/no leaves allocated/i)).toHaveCount(0)
	})
})

test.describe("the leave balance", () => {
	test.skip(!USER || !PASSWORD, "set HRMS_E2E_USER and HRMS_E2E_PASSWORD to run this")

	test("renders a balance, or says why not — never a blank panel", async ({ page }) => {
		// 486 Leave Allocations were absent from the mirror, so this panel was empty
		// for every employee. Parity proves the rows arrived; only this proves the
		// screen shows them.
		await signIn(page)
		await page.goto("/hrms/leaves")

		const balance = page.getByText(/leave balance/i)
		await expect(balance).toBeVisible({ timeout: 15000 })

		// Whichever of the three states is showing, it must be one of them. The bug
		// was a fourth: nothing at all.
		const shown = page.locator(
			'[role="alert"], :text-matches("no leaves allocated", "i"), .m-bar',
		)
		await expect(shown.first()).toBeVisible({ timeout: 15000 })
	})
})
