// The dim area behind an open sheet (GModal). Built by hand, not by Vue:
// Ionic moves ion-modal to ion-app when it presents, so a Vue <Teleport>
// beside it loses its anchor and the render throws (nextSibling of null).
//
// Placed immediately before the presented ion-modal, in the same parent, so
// it shares the sheet's stacking context and sits under it (scrim z 10000,
// Ionic's sheet 20000+). Not in the page: the page is inert while a sheet is
// open, so a tap there did nothing. Not in <body>: there it covered the sheet.
export function mountScrim(sheetEl, onTap) {
	if (!sheetEl?.ownerDocument) return null
	const scrim = sheetEl.ownerDocument.createElement("div")
	scrim.className = "g-scrim"
	scrim.setAttribute("aria-hidden", "true")
	scrim.addEventListener("click", onTap)
	sheetEl.before(scrim)
	console.info("[sheetScrim] scrim placed before the sheet")
	return scrim
}
