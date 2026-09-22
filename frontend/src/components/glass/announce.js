// The app's single live region (revamp slice A7, WCAG 2.2 SC 4.1.3).
//
// THE DEFECT. Every confirmation and every failure in this app is delivered by
// a toast, and frappe-ui's Toast.vue carries no `role` and no `aria-live` —
// checked, not assumed. A toast appears without taking focus, so a screen
// reader has no reason to look at it: "Leave request submitted" and "Could not
// check you in" were both simply never spoken. Sixteen call sites, silent.
//
// WHY A SEPARATE REGION rather than patching the vendor component. The toast
// root is created imperatively by frappe-ui and teleported into; adding
// attributes to it means patch-package and re-patching on every upgrade. A
// region we own is ours, works the same for toasts and for anything else that
// needs to announce, and cannot be undone by a dependency bump.
//
// ONE region, not one per screen. A live region must exist in the DOM BEFORE
// the text lands in it — a region created and filled in the same tick is
// frequently missed, because assistive technology watches existing nodes for
// mutations rather than re-scanning the document. So this is created once at
// module load and only its text ever changes.
//
// POLITE by default. `assertive` interrupts whatever is being read mid-word,
// which is right for "your session expired" and wrong for "saved". The APG's
// guidance is that assertive is for things that need attention NOW; everything
// else waits its turn.

let region = null
let assertiveRegion = null

//: Screen-reader-only positioning, inline rather than a class: this element is
//: created before any stylesheet is guaranteed to have applied, and a visible
//: flash of announcement text would be worse than the silence it replaces.
const SR_ONLY = {
	position: "absolute",
	width: "1px",
	height: "1px",
	margin: "-1px",
	padding: "0",
	overflow: "hidden",
	clipPath: "inset(50%)",
	whiteSpace: "nowrap",
	border: "0",
}

function makeRegion(politeness) {
	if (typeof document === "undefined") return null
	const el = document.createElement("div")
	el.setAttribute("aria-live", politeness)
	// An announcement is a whole sentence. Without atomic, a reader may speak
	// only the words that CHANGED between two messages, which turns "Leave
	// approved" followed by "Leave rejected" into the single word "rejected".
	el.setAttribute("aria-atomic", "true")
	el.setAttribute("role", politeness === "assertive" ? "alert" : "status")
	Object.assign(el.style, SR_ONLY)
	document.body.appendChild(el)
	return el
}

/**
 * Speak `message` to assistive technology. Visual users are unaffected.
 *
 * @param {string} message      a whole sentence, in the same plain language
 *                              the visible copy uses (§11.3)
 * @param {"polite"|"assertive"} [politeness]
 */
export function announce(message, politeness = "polite") {
	if (!message) return
	if (typeof document === "undefined") return

	if (politeness === "assertive") {
		assertiveRegion = assertiveRegion || makeRegion("assertive")
	} else {
		region = region || makeRegion("polite")
	}
	const target = politeness === "assertive" ? assertiveRegion : region
	if (!target) return

	// Clearing first is what makes a REPEATED message speak twice. Setting the
	// same string produces no mutation, so a second failed save would be
	// silent — which is precisely the moment somebody needs to be told again.
	target.textContent = ""
	// A microtask is enough for the mutation observer to see two changes; a
	// timeout would risk landing after the next announcement.
	Promise.resolve().then(() => {
		target.textContent = message
	})
}

//: Test seam. Nothing in the app calls this; it exists so a test can assert on
//: a fresh region instead of one another test already wrote into.
export function __resetAnnouncer() {
	region?.remove()
	assertiveRegion?.remove()
	region = null
	assertiveRegion = null
}
