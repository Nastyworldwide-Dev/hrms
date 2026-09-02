// The PWA install prompt is a bottom sheet that overlays the home content and
// the tab bar. `beforeinstallprompt` fires on every load while the app is
// installable, so without a memory of the user's dismissal the sheet re-covered
// the navigation on every cold start and route back to home. InstallPrompt.vue
// records a dismissal timestamp and stays quiet for a cooldown; this is the pure
// predicate that decides "quiet or not", split out so it is unit-testable
// without a DOM (the component itself owns the localStorage read/write).

export const INSTALL_DISMISS_KEY = "hrms:install-prompt-dismissed"
export const INSTALL_COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000 // 30 days

/**
 * @param {string|number|null} stored - the raw stored dismissal timestamp (ms)
 * @param {number} now - current time in ms
 * @param {number} cooldownMs - how long a dismissal stays in effect
 * @returns {boolean} true when a dismissal is still within its cooldown
 */
export function isWithinCooldown(stored, now, cooldownMs = INSTALL_COOLDOWN_MS) {
	const at = Number(stored)
	// Not-a-number, empty, 0, or a future/stale value all mean "not suppressed".
	if (!Number.isFinite(at) || at <= 0) return false
	const elapsed = now - at
	return elapsed >= 0 && elapsed < cooldownMs
}
