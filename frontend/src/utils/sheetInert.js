// The page behind an open sheet cannot take focus (WAI-ARIA dialog pattern,
// audit P0-4). GModal keeps Ionic's own focus trap OFF on purpose (Ionic
// #24646 breaks portalled pickers inside it), so the page is made `inert`
// instead: it drops out of the tab order and the accessibility tree, and the
// sheet — presented at the app root, outside it — is all that is left.
//
// Counted, because sheets stack (a picker over a form sheet): the page is freed
// only when the last one closes.
let open = 0

export function holdPageInert(findPage) {
	open += 1
	const page = findPage()
	if (page) page.inert = true
	console.info("[sheetInert] page inert, open sheets:", open)
}

export function releasePageInert(findPage) {
	open = Math.max(0, open - 1)
	const page = findPage()
	if (page && open === 0) page.inert = false
	console.info("[sheetInert] released, open sheets:", open)
}

export function _resetForTest() {
	open = 0
}
