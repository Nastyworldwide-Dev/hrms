import frappeUIPreset from "frappe-ui/src/tailwind/preset"
import glassTheme from "./src/theme/glass.tailwind.cjs"

// Glass fragment is generated from design/tokens.json (yarn tokens).
// colors.ink collides with the ink shade map below, so it is split out and
// re-nested as ink.DEFAULT: text-ink and text-ink-100…900 both resolve.
const { colors: glassColors, ...glassExtend } = glassTheme
const { ink: glassInk, ...glassOtherColors } = glassColors
export default {
	presets: [frappeUIPreset],
	darkMode: "class",
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
		"../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		borderRadius: {
			none: "0",
			sm: "0",
			DEFAULT: "0",
			md: "0",
			lg: "0",
			xl: "0",
			"2xl": "0",
			"3xl": "0",
			full: "9999px",
		},
		fontFamily: {
			// self-hosted Inter via theme/fonts.css; -apple-system leads (spec §4.1)
			sans: "var(--g-font-ui)",
		},
		extend: {
			// Glass semantic scales: backdropBlur, borderRadius (panel/action/…,
			// additive — the zeroed scale above is untouched), boxShadow.lift,
			// fontFamily, fontSize, opacity, spacing, transitionDuration/-TimingFunction
			...glassExtend,
			// Repointed off Modernist onto Glass tokens (phase 3.4). The nine-step
			// ink and accent ramps collapse onto Glass's four ink levels and its
			// single accent ink — Glass has no nine-step ramp and §2.4 forbids brand
			// setting type on light, so accent-* resolves to --accent-ink, not --brand.
			backgroundColor: {
				surface: { DEFAULT: "rgb(var(--g-track-solid-rgb) / <alpha-value>)" },
			},
			colors: {
				...glassOtherColors,
				ink: {
					DEFAULT: glassInk,
					100: "rgb(var(--g-track-solid-rgb) / <alpha-value>)",
					200: "rgb(var(--g-track-solid-rgb) / <alpha-value>)",
					300: "rgb(var(--g-ink3-rgb) / <alpha-value>)",
					400: "rgb(var(--g-ink3-rgb) / <alpha-value>)",
					500: "rgb(var(--g-ink3-rgb) / <alpha-value>)",
					600: "rgb(var(--g-ink-muted-rgb) / <alpha-value>)",
					700: "rgb(var(--g-ink2-rgb) / <alpha-value>)",
					800: "rgb(var(--g-ink-rgb) / <alpha-value>)",
					900: "rgb(var(--g-ink-rgb) / <alpha-value>)",
				},
				accent: {
					DEFAULT: "rgb(var(--g-accent-ink-rgb) / <alpha-value>)",
					100: "rgb(var(--g-brand-rgb) / <alpha-value>)",
					200: "rgb(var(--g-brand-rgb) / <alpha-value>)",
					300: "rgb(var(--g-brand-2-rgb) / <alpha-value>)",
					400: "rgb(var(--g-brand-2-rgb) / <alpha-value>)",
					500: "rgb(var(--g-accent-ink-rgb) / <alpha-value>)",
					600: "rgb(var(--g-accent-ink-rgb) / <alpha-value>)",
					700: "rgb(var(--g-accent-ink-rgb) / <alpha-value>)",
					800: "rgb(var(--g-accent-ink-rgb) / <alpha-value>)",
					900: "rgb(var(--g-accent-ink-rgb) / <alpha-value>)",
				},
				ground: "rgb(var(--g-bg-rgb) / <alpha-value>)",
				surface: "rgb(var(--g-track-solid-rgb) / <alpha-value>)",
				// ^ colors.surface alone never reaches bg-surface: the frappe-ui plugin
				// extends backgroundColor.surface with its own shade map and no DEFAULT,
				// which shadows this for bg-* utilities. The backgroundColor extend
				// above restores the bare utility while keeping the plugin's shades.
				inkbase: "rgb(var(--g-ink-rgb) / <alpha-value>)",
				divider: "var(--g-hair)",
			},
			screens: {
				standalone: {
					raw: "(display-mode: standalone)",
				},
			},
			// Promoted from arbitrary values in phase 3.2. Not design tokens —
			// they carry no theme meaning — so they are named here rather than in
			// design/tokens.json. The z-index scale IS a token (--g-layer-*) and
			// arrives through the generated fragment above.
			textUnderlineOffset: {
				link: "3px",
			},
			maxHeight: {
				// bottom-sheet ceiling; GModal owns this shape (spec §10.3 #25).
				// Reads the token so the utility and glass-components.css cannot drift.
				sheet: "var(--g-sheet-max-height)",
			},
			padding: {
				"safe-top": "env(safe-area-inset-top)",
				"safe-right": "env(safe-area-inset-right)",
				"safe-bottom": "env(safe-area-inset-bottom)",
				"safe-left": "env(safe-area-inset-left)",
			},
		},
	},
	plugins: [],
}
