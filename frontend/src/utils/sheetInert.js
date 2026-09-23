// The page behind an open sheet cannot take focus (WAI-ARIA dialog pattern,
// audit P0-4). GModal keeps Ionic's own focus trap OFF on purpose (Ionic
// #24646 breaks portalled pickers inside it), so the page is made `inert`
// instead: it drops out of the tab order and the accessibility tree, and the
// sheet, presented at the app root outside it, is all that is left.
//
// Counted PER PAGE, because sheets stack (a picker over a form sheet), and a
// sheet must free the exact page it froze: re-finding "the visible page" at
// release freed the wrong one after a route change and left the old page
// inert — untappable the next time anyone went back to it (review of
// 76367b0fd).
const holds = new Map()

//: Freeze the page `findPage` returns and hand it back; pass the SAME value to
//: releasePageInert. Returns null when there is no page.
export function holdPageInert(findPage) {
	const page = findPage()
	if (!page) return null
	holds.set(page, (holds.get(page) || 0) + 1)
	page.inert = true
	console.info("[sheetInert] page inert, sheets on it:", holds.get(page))
	return page
}

export function releasePageInert(page) {
	if (!page || !holds.has(page)) return
	const left = holds.get(page) - 1
	if (left > 0) {
		holds.set(page, left)
	} else {
		holds.delete(page)
		page.inert = false
	}
	console.info("[sheetInert] released, sheets left on that page:", Math.max(0, left))
}

export function _resetForTest() {
	holds.clear()
}
