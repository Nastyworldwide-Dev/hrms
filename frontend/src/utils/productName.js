/**
 * The product name, and the two places a Translation record could not reach.
 *
 * §16.6 makes copy a data concern: label changes ship as Frappe Translation
 * records, zero code change. `index.html` is static, so `<title>` and
 * `apple-mobile-web-app-title` were the one exception — they shipped the vendor
 * string "Frappe HR" to every tenant, in the browser tab and as the name the
 * PWA installs under, and no record could touch them.
 *
 * Re-setting them from the SAME translated string the app header uses puts them
 * back under §16.6: one record now covers the header, the tab and the install
 * name together.
 *
 * @param {(s: string) => string} [translate] the app's `__`; when absent or it
 *   returns nothing, the document keeps whatever index.html shipped
 * @param {Document} [doc]
 * @returns {string} the name applied
 */
export function applyProductName(translate, doc = globalThis.document) {
	const SOURCE = "Frappe HR"
	const name = (typeof translate === "function" && translate(SOURCE)) || doc?.title || SOURCE

	if (doc) {
		doc.title = name
		doc.querySelector?.('meta[name="apple-mobile-web-app-title"]')?.setAttribute("content", name)
	}
	return name
}
