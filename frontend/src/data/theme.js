import { reactive } from "vue"

// Theme mode store — light / dark / system, persisted, applied as `.dark` on
// <html>. Mirrors the HandaPOS Android ThemeMode (LIGHT / DARK / SYSTEM)
// settings pattern; switching animates via a circular view-transition reveal
// from the tapped control.

const STORAGE_KEY = "hrms:theme"
const TRANSPARENCY_KEY = "hrms:reduce-transparency"
const systemDark = window.matchMedia("(prefers-color-scheme: dark)")

export const THEME_MODES = ["light", "dark", "system"]

export const theme = reactive({
	mode: THEME_MODES.includes(localStorage.getItem(STORAGE_KEY))
		? localStorage.getItem(STORAGE_KEY)
		: "system",
})

export function resolvedTheme(mode = theme.mode) {
	return mode === "system" ? (systemDark.matches ? "dark" : "light") : mode
}

function applyTheme() {
	const dark = resolvedTheme() === "dark"
	// .dark drives Modernist + Tailwind dark:, data-theme drives glass.css;
	// both stay until Modernist is retired in phase 3
	document.documentElement.classList.toggle("dark", dark)
	document.documentElement.setAttribute("data-theme", dark ? "dark" : "light")
	document
		.querySelector('meta[name="theme-color"]')
		?.setAttribute("content", dark ? "#191817" : "#f3f2f2")
}

export function setTheme(mode, event) {
	const from = resolvedTheme()
	theme.mode = mode
	localStorage.setItem(STORAGE_KEY, mode)
	console.info("[Theme] Mode change:", { mode, resolved: resolvedTheme() })

	if (from === resolvedTheme() || !document.startViewTransition) {
		return applyTheme()
	}

	// Circular reveal from the tap point (falls back to instant swap above).
	const x = event?.clientX ?? window.innerWidth / 2
	const y = event?.clientY ?? window.innerHeight / 2
	const radius = Math.hypot(
		Math.max(x, window.innerWidth - x),
		Math.max(y, window.innerHeight - y)
	)
	const transition = document.startViewTransition(applyTheme)
	transition.ready
		.then(() => {
			document.documentElement.animate(
				{
					clipPath: [
						`circle(0px at ${x}px ${y}px)`,
						`circle(${radius}px at ${x}px ${y}px)`,
					],
				},
				{
					duration: 450,
					easing: "ease-in-out",
					pseudoElement: "::view-transition-new(root)",
				}
			)
		})
		.catch(() => {})
}

// Reduce-transparency (glass spec §6.2) — persisted manual override on top of
// the prefers-reduced-transparency media query, which CSS honours directly.
// html[data-transparency="reduce"] swaps every .g-glass to the fallback fill.
export const transparency = reactive({
	reduce: localStorage.getItem(TRANSPARENCY_KEY) === "1",
})

export function setTransparency(reduce) {
	transparency.reduce = reduce
	localStorage.setItem(TRANSPARENCY_KEY, reduce ? "1" : "0")
	applyTransparency()
}

function applyTransparency() {
	const mode = transparency.reduce ? "reduce" : "full"
	console.info("[Theme] Transparency:", { mode })
	document.documentElement.setAttribute("data-transparency", mode)
}

systemDark.addEventListener("change", () => {
	if (theme.mode === "system") applyTheme()
})

applyTheme()
applyTransparency()
