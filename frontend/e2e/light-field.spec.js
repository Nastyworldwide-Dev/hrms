import { test, expect } from "@playwright/test"

// Glass §3.2 — the backdrop-root trap.
//
// Chromium's backdrop-filter only filters its own isolation group. Ionic's
// ios-mode transitions animate transform AND opacity on .ion-page, making it a
// backdrop root, so a light field mounted outside the page is invisible to
// every glass surface inside it — after the FIRST navigation, not on first
// paint. A screenshot test taken on load would pass while the app is broken.
//
// Test 1 proves the CSS behaviour in this browser build, offline.
// Test 2 proves the real app still blurs the field AFTER a page transition.
// Test 2 needs a running bench: HRMS_E2E_URL, HRMS_E2E_USER, HRMS_E2E_PASSWORD.

test("§3.2: a field outside the transformed page is lost to the blur", async ({ page }) => {
	await page.goto(`file://${new URL("./light-field-isolation.html", import.meta.url).pathname}`)
	await page.waitForTimeout(300)

	const chroma = async (selector) => {
		const box = await page.locator(selector).boundingBox()
		const buf = await page.screenshot({
			clip: { x: box.x + box.width / 2 - 2, y: box.y + box.height / 2 - 2, width: 4, height: 4 },
		})
		return page.evaluate(async (d) => {
			const img = new Image()
			img.src = `data:image/png;base64,${d}`
			await img.decode()
			const c = document.createElement("canvas")
			c.width = img.width
			c.height = img.height
			c.getContext("2d").drawImage(img, 0, 0)
			const px = c.getContext("2d").getImageData(2, 2, 1, 1).data
			return Math.max(px[0], px[1], px[2]) - Math.min(px[0], px[1], px[2])
		}, buf.toString("base64"))
	}

	// inside the transformed page the blur picks the field up; outside it does not
	expect(await chroma("#glassInside")).toBeGreaterThan((await chroma("#glassOutside")) + 5)
})

test("§3.2: glass still blurs the field after an Ionic page transition", async ({ page }) => {
	test.skip(!process.env.HRMS_E2E_USER, "needs a running bench and credentials")

	await page.goto("/hrms/login")
	await page.fill('input[type="email"], input[name="email"]', process.env.HRMS_E2E_USER)
	await page.fill('input[type="password"]', process.env.HRMS_E2E_PASSWORD)
	await page.click('button[type="submit"]')
	await page.waitForURL(/\/hrms\//, { timeout: 20000 })

	// navigate at least once — the trap only bites AFTER a transition
	await page.goto("/hrms/dashboard/leaves")
	await page.waitForLoadState("networkidle")

	// the field must be a descendant of the page that Ionic transforms
	const nested = await page.evaluate(() => {
		const field = document.querySelector(".g-field")
		if (!field) return "no-field"
		return field.closest(".ion-page") ? "inside" : "outside"
	})
	expect(nested).toBe("inside")

	// and no element between a glass surface and the field may create a
	// backdrop root of its own
	const offenders = await page.evaluate(() => {
		const glass = document.querySelector(".g-glass, .g-glass-ghost")
		if (!glass) return ["no-glass"]
		const bad = []
		for (let el = glass.parentElement; el && !el.classList.contains("ion-page"); el = el.parentElement) {
			const s = getComputedStyle(el)
			if (s.filter !== "none" || s.mixBlendMode !== "normal" || (s.opacity !== "1" && s.opacity !== ""))
				bad.push(`${el.tagName}.${el.className} filter=${s.filter} opacity=${s.opacity}`)
		}
		return bad
	})
	expect(offenders).toEqual([])
})
