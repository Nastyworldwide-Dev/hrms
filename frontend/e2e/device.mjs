// alpha.14: the installed iPhone, as close as a desktop WebKit can get.
//
// Why: every gate before this ran a 402x874 window with NO safe areas and no
// standalone mode, so the owner's phone showed defects no gate could see —
// the tab bar in the home-indicator zone, the gap above every page, the bar's
// title doubling the large one after a tab switch (owner, 27 Sep 2026).
//
// WebKit on Linux has no notch, so the insets are written into the page's CSS
// as it is served, and the standalone media query matches, as it does for an
// app opened from the Home Screen.
//
// The numbers are the iPhone 16 Pro in portrait (402x874; status bar 62,
// home indicator 34) AS NADI IS INSTALLED. index.html sets
// apple-mobile-web-app-status-bar-style "default": Apple's Safari Web Content
// Guide — only "black-translucent" lays the page under the status bar; with
// "default" the page starts BELOW it. So the page is 874 - 62 = 812 tall,
// its top inset is 0, and only the home indicator (34) is inside it.
// The first run of this audit assumed a 62 top inset and blamed the app for
// a gap the phone never has; the screenshot showed it.
export const IPHONE = { width: 402, height: 812, top: 0, bottom: 34, statusBar: 62 }

const INSET = { top: IPHONE.top, bottom: IPHONE.bottom, left: 0, right: 0 }
// the index.html setting the numbers above depend on; device.test.mjs pins it
export const STATUS_BAR_STYLE = "default"

export function asInstalled(css) {
	return css
		.replace(/(?:env|constant)\(\s*safe-area-inset-(top|bottom|left|right)\s*(?:,[^()]*(?:\([^()]*\))?[^()]*)?\)/g, (_m, side) => `${INSET[side]}px`)
		.replace(/\(\s*display-mode\s*:\s*standalone\s*\)/g, "(min-width: 0px)")
}

/** A browser context that behaves like Nadi opened from the iPhone Home Screen. */
export async function installedContext(browser, { scheme = "light" } = {}) {
	const ctx = await browser.newContext({
		viewport: { width: IPHONE.width, height: IPHONE.height },
		hasTouch: true,
		isMobile: false,
		colorScheme: scheme,
		serviceWorkers: "block",
	})
	await ctx.route(/\.css(\?|$)/, async (route) => {
		const res = await route.fetch()
		route.fulfill({ response: res, body: asInstalled(await res.text()) })
	})
	await ctx.addInitScript(() => {
		localStorage.setItem("hrms:install-prompt-dismissed", String(Date.now()))
		const real = window.matchMedia.bind(window)
		window.matchMedia = (q) => (/display-mode:\s*standalone/.test(q) ? { ...real("(min-width: 0px)"), media: q } : real(q))
		Object.defineProperty(navigator, "standalone", { value: true })
		// inline <style> blocks (Vue SFC styles in dev, index.html) get the same insets
		new MutationObserver((records) => {
			for (const r of records)
				for (const n of r.addedNodes)
					if (n.nodeName === "STYLE" && /safe-area-inset|display-mode/.test(n.textContent)) n.textContent = window.__asInstalled(n.textContent)
		}).observe(document, { childList: true, subtree: true })
	})
	await ctx.addInitScript(`window.__asInstalled = ${asInstalled.toString()}; const INSET = ${JSON.stringify(INSET)};`)
	return ctx
}
