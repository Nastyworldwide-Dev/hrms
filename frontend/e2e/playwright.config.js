import { defineConfig, devices } from "@playwright/test"

// The project's first end-to-end tests. Everything else that guards this app is
// static or unit-level: those prove SHAPES are right — that an endpoint declares
// the argument its caller sends, that a mirrored row never fires on_submit — and
// not one of them can answer "does an employee see their leave balance".
//
// Until now the only thing answering that question was a person opening the app
// and taking a screenshot. That is why faults survived for a week: verification
// was manual, so confidence decayed the moment anyone stopped looking.
//
// Deliberately configurable rather than pinned to a site. The same specs run
// against a local bench, a staging site, or verifica-live:
//
//   HRMS_E2E_URL=https://verifica-live.s.frappe.cloud \
//   HRMS_E2E_USER=someone@nastyworldwide.com \
//   HRMS_E2E_PASSWORD=... \
//   npx playwright test
//
// First run needs the browser binary: `npx playwright install chromium`.
export default defineConfig({
	testDir: ".",
	// One retry, because a real site over a real network is allowed one blip
	// before a failure is called a failure. More would start hiding flakiness.
	retries: process.env.CI ? 1 : 0,
	// Serial by default: these sign in as one user, and parallel logins against a
	// shared site invalidate each other's sessions.
	workers: 1,
	reporter: [["list"]],
	use: {
		baseURL: process.env.HRMS_E2E_URL || "http://localhost:8000",
		// Kept only for failures — a trace per passing run is noise nobody opens.
		trace: "retain-on-failure",
		screenshot: "only-on-failure",
		...devices["Desktop Chrome"],
	},
})
