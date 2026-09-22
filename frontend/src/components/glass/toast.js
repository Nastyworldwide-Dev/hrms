import { toast } from "frappe-ui"

import { announce } from "./announce.js"

// GToast (spec §10.3 #27) — WRAPS frappe-ui's toast, does not replace it.
//
// Why wrap: the mechanism is sound and none of it is design. frappe-ui owns
// the queue, the teleport into #frappeui-toast-root, positioning and
// auto-dismiss; only the skin was wrong, and the toast root is plain DOM (not
// shadow), so glass-components.css reaches it. Replacing would mean rewriting
// the six existing `toast({...})` call sites in phase 5 for no user-visible
// gain, and rebuilding queue logic we would then own.
//
// What this adds over calling toast() directly: §11.3's copy rules in one
// place. A variant maps to frappe-ui's type/icon so call sites stop passing
// iconClasses and colour names, and errors stop being spelled six ways.

const VARIANTS = {
	success: { type: "success", icon: "check-circle" },
	error: { type: "error", icon: "alert-circle" },
	warning: { type: "warning", icon: "alert-triangle" },
	info: { type: "info", icon: "info" },
}

/**
 * @param {object} options
 * @param {string} options.title   what happened, in plain language (§11.3)
 * @param {string} [options.text]  what to do about it
 * @param {"success"|"error"|"warning"|"info"} [options.variant]
 * @param {string} [options.position] frappe-ui position, default bottom-center
 */
export function gToast({ title, text = "", variant = "info", position = "bottom-center" }) {
	const mapped = VARIANTS[variant] ?? VARIANTS.info
	console.info("[GToast]", { variant, title })
	// frappe-ui's Toast.vue carries no role and no aria-live, and a toast takes
	// no focus — so every confirmation and every failure this app has shown has
	// been silent to a screen reader. Announced through our own region rather
	// than by patching the vendor component, which a dependency bump undoes.
	// An error interrupts; a success waits its turn.
	announce([title, text].filter(Boolean).join(". "), variant === "error" ? "assertive" : "polite")
	return toast({ title, text, position, ...mapped })
}
