// The name a screen reader says when a sheet opens. Ionic 7.4 draws its own
// role=dialog wrapper in ion-modal's shadow root and copies aria-label to it
// once, at first load (inheritAttributes, which also strips it from the host).
// A title that is empty then, or changes later, never reached the dialog, so
// every sheet read as a bare "dialog". Called on each present, it names the
// wrapper with the title as it is now.
export function nameSheet(modalEl, title) {
	const wrapper = modalEl?.shadowRoot?.querySelector?.(".modal-wrapper")
	if (!wrapper) return
	if (title) wrapper.setAttribute("aria-label", title)
	else wrapper.removeAttribute("aria-label")
}
