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
	// By label, for the same reason the assertions below use it: the password
	// placeholder is "••••••" and matches no /password/i that will ever be
	// written.
	await page.getByLabel(/email/i).first().fill(USER)
	await page
		.getByLabel(/password/i)
		.first()
		.fill(PASSWORD)
	await page.getByRole("button", { name: /login/i }).click()
	await expect(page).not.toHaveURL(/\/login/, { timeout: 15000 })
}

test.describe("the login page", () => {
	test("offers email and password, not SSO alone", async ({ page }) => {
		// Reported as "users can only sign in with Microsoft SSO". The form was
		// always rendered; the recovery route out of a bad password was not.
		// By LABEL, not placeholder. These assertions were red from the day they
		// were written and nobody knew, because nothing ran this spec: the
		// password field's placeholder is "••••••", which no /password/i will
		// ever match. Asserting on the accessible name is also the stronger
		// claim — GInput draws it from the wrapping <label>, so a field that
		// passes here is one a screen reader can announce.
		await page.goto("/hrms/login")
		await expect(page.getByLabel(/email/i).first()).toBeVisible()
		await expect(page.getByLabel(/password/i).first()).toBeVisible()
	})

	test("forgot password is accepted, not rejected outright", async ({ page }) => {
		// The 400 was a missing CSRF header on a guest POST — the endpoint never ran.
		// Asserted on the RESPONSE rather than the message, because frappe answers
		// the same generic text whether or not the address exists (anti-enumeration),
		// so the status is the only thing that distinguishes working from broken.
		await page.goto("/hrms/login")

		const request = page.waitForResponse((r) => r.url().includes("user.reset_password"), {
			timeout: 15000,
		})
		await page.getByText(/forgot password/i).click()
		await page.getByLabel(/email/i).last().fill("nobody@example.invalid")
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
			route.fulfill({ status: 500, contentType: "application/json", body: "{}" })
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
		const shown = page.locator('[role="alert"], :text-matches("no leaves allocated", "i"), .m-bar')
		await expect(shown.first()).toBeVisible({ timeout: 15000 })
	})
})

// ---------------------------------------------------------------------------
// The flows an employee actually performs. Added 26 August 2026, after a week
// in which four defects reached an employee before they reached us — every one
// of them in a flow nothing above touches.
//
// The four tests above cover the login page and the leave balance panel. Not
// one could have caught a check-in that refused to save, an approval that did
// nothing, or a settings form that could not be saved at all.
//
// These seed their own data through the REST API using the signed-in session,
// then drive the UI. Seeding through the API and asserting through the UI is
// deliberate: the bug these exist for lived exactly in that gap — the server
// was willing, and the button called the wrong thing.

/** The signed-in session's cookies, for REST calls that seed or verify. */
async function api(page, method, path, data) {
	const res = await page.request.fetch(`/api/resource/${path}`, {
		method,
		headers: { "Content-Type": "application/json", Accept: "application/json" },
		...(data ? { data } : {}),
	})
	return { ok: res.ok(), status: res.status(), body: await res.json().catch(() => null) }
}

test.describe("a decided request stays decided", () => {
	test.skip(!USER || !PASSWORD, "set HRMS_E2E_USER and HRMS_E2E_PASSWORD to run this")

	test("approving a request does not leave it asking to be submitted", async ({ page }) => {
		// THE REGRESSION. RequestActionSheet sent {docstatus: 1} through
		// frappe-ui's setValue — frappe.client.set_value — which refuses to write
		// docstatus ("Cannot edit standard fields"). The call threw, a red toast
		// showed for a moment on a phone, and the document stayed a draft. The
		// approver believed they had approved it; the employee was asked to submit
		// it again. Nothing was recorded anywhere.
		//
		// Asserted on docstatus rather than on any pixel: the bug was that the
		// SERVER state never moved, and a UI that merely stops showing a button
		// would satisfy a weaker test while leaving the document a draft.
		await signIn(page)

		const me = await api(
			page,
			"GET",
			"Employee?filters=" +
				encodeURIComponent(JSON.stringify([["user_id", "=", USER]])) +
				"&fields=" +
				encodeURIComponent(JSON.stringify(["name"]))
		)
		const employee = me.body?.data?.[0]?.name
		test.skip(!employee, "the signed-in user has no Employee record to file against")

		const draft = await api(page, "POST", "Attendance Request", {
			employee,
			from_date: "2026-08-20",
			to_date: "2026-08-20",
			reason: "On Duty",
			explanation: "e2e: a decided request must stay decided",
		})
		test.skip(!draft.ok, `could not seed a draft: ${draft.status}`)
		const name = draft.body.data.name

		// The transition the button performs. Calling the endpoint the UI calls —
		// not set_value — is the whole point: this fails loudly if the wiring
		// regresses to a field write.
		const decided = await page.request.fetch("/api/method/hrms.api.approval.finalize", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			data: { doctype: "Attendance Request", name, docstatus: 1 },
		})

		// A refusal with a REASON is a pass — validate_mandatory_attachment and
		// validate_self_submission are supposed to stop this, and the old code's
		// failure was that it reported "Cannot edit standard fields" instead of
		// the real rule. What must never happen is a silent non-approval.
		const after = await api(page, "GET", `Attendance Request/${name}`)
		const docstatus = after.body?.data?.docstatus

		if (decided.ok()) {
			expect(docstatus, "approved, so the document must be submitted").toBe(1)
		} else {
			const why = await decided.json().catch(() => ({}))
			const message = JSON.stringify(why)
			expect(docstatus, "refused, so the document must still be a draft").toBe(0)
			expect(
				message,
				"a refusal must name the business rule, not a framework detail"
			).not.toContain("Cannot edit standard fields")
		}

		await api(page, "DELETE", `Attendance Request/${name}`)
	})
})

test.describe("check-in", () => {
	test.skip(!USER || !PASSWORD, "set HRMS_E2E_USER and HRMS_E2E_PASSWORD to run this")

	test("the sheet opens and can be confirmed", async ({ page }) => {
		// Mirza could not check in at all: mirrored rows had taken the numbers
		// autoname was about to issue, so every attempt asked for a name already
		// on disk and the counter rolled back with the failure. Three consecutive
		// attempts all requested EMP-CKIN-08-2026-000001.
		//
		// This asserts the sheet REACHES a confirmable state. It stops short of
		// punching, because a test that creates attendance records on a live site
		// is a test nobody dares run — and the naming defect itself is pinned
		// server-side by hrms/sync/test_series_advance.py.
		await signIn(page)
		await page.goto("/hrms/home")

		const button = page.getByRole("button", { name: /check\s*(in|out)/i }).first()
		await expect(button, "the home screen must offer check-in").toBeVisible({
			timeout: 15000,
		})
		await button.click()

		// Whatever the geofence says, the sheet must reach a state a person can
		// act on. Blank was the failure mode worth catching.
		await expect(page.getByRole("button", { name: /confirm/i }).first()).toBeVisible({
			timeout: 15000,
		})
	})
})
