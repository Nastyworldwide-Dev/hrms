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
	// Visual-regression baselines live in design/baselines/ and are owned by
	// this gate alone.
	//
	// They used to BE the committed audit screens in docs/glass/audit/screens/,
	// deliberately: one set of images serving as both the evidence a finding
	// cites and the baseline a regression fails against, on the reasoning that a
	// second parallel set would drift the day someone re-shot only one of them.
	//
	// That reasoning held until this gate started masking. `visual.spec.js`
	// injects `[data-visual-mask]{visibility:hidden}` so relative timestamps stop
	// rotting the baselines — correct for a comparison, and it renders every
	// dynamic string INVISIBLE in the images the audit documents cite. On
	// `home-390-dark.png` the check-out banner's title and the date eyebrow are
	// both present in the DOM and both blank in the picture; two readers have now
	// filed them as defects.
	//
	// Two correct decisions, made months apart, combined into an artifact set
	// that silently misleads its reader. So the sets are split by role: this one
	// is masked and compared, docs/glass/audit/screens/ is unmasked and read.
	// capture.mjs owns the latter and does not mask.
	//
	// relative to this config's directory (frontend/e2e), so two levels up
	snapshotPathTemplate: "../../design/baselines/{arg}{ext}",
	expect: {
		toHaveScreenshot: {
			// An ABSOLUTE pixel count, not a ratio. The ratio was the fourth
			// instrument defect of this phase, and the reasoning behind it was never
			// measured — only assumed:
			//
			//   "Antialiasing and font hinting move a few pixels between runs on the
			//    same machine; a real layout regression moves thousands."
			//
			// Both halves are wrong here. MEASURED noise, twice and agreeing: a
			// reload-to-reload comparison of the same page reports **0** differing
			// pixels, and re-shooting every baseline across separate runs produces
			// byte-identical PNGs. pixelmatch already runs with includeAA:false, so
			// it discounts anti-aliased edges before counting. There is no noise to
			// budget for.
			//
			// And a real change does NOT move thousands. MEASURED signal, from the
			// RC18 avatar consolidation:
			//
			//   header avatar initial 11.5px -> 14px ............  34 px
			//   ten avatars, blank circle -> 9px box with "?" ...  74 px
			//   header avatar + a back control appearing ........ 648 px
			//   profile avatar, radius 0 -> 9px, 72px box ....... 4661 px
			//
			// The old budget was 0.002 x 329,160 = 658 px at 390x844, so the first
			// three passed — including `sop`, which was missing an entire back
			// control and came in ten pixels under the line.
			//
			// A ratio is the wrong measure for this failure. It scales the budget
			// with viewport AREA, while a UI element's pixel footprint is roughly
			// viewport-INDEPENDENT: the same avatar glyph is ~34px at 390x844 and
			// ~34px at 1440x900, but the budget quadruples to 2,592. The instrument
			// was least sensitive exactly where the screen was largest.
			//
			// 20 is an order of magnitude above the measured noise (0) and below the
			// smallest measured real change (34). Playwright takes Math.min() when
			// both limits are set, so this binds everywhere; the ratio is dropped
			// rather than kept as a decorative second bound that can never fire.
			//
			// If a browser upgrade ever makes this flaky, re-measure the noise floor
			// before raising it — do not raise it because a run went red.
			maxDiffPixels: 20,
			animations: "disabled",
			caret: "hide",
		},
	},
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
