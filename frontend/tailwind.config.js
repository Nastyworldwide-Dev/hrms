import frappeUIPreset from "frappe-ui/src/tailwind/preset"

// Palette values in extend.colors mirror src/theme/modernist.css (the
// canonical palette) — change them there first, then here.
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
			sans: ["Archivo", "system-ui", "sans-serif"],
		},
		extend: {
			// Values resolve through the --m-* RGB triplets in theme/modernist.css
			// (:root light / .dark dark) so every utility follows the theme switch.
			colors: {
				ink: {
					100: "rgb(var(--m-ink-100) / <alpha-value>)",
					200: "rgb(var(--m-ink-200) / <alpha-value>)",
					300: "rgb(var(--m-ink-300) / <alpha-value>)",
					400: "rgb(var(--m-ink-400) / <alpha-value>)",
					500: "rgb(var(--m-ink-500) / <alpha-value>)",
					600: "rgb(var(--m-ink-600) / <alpha-value>)",
					700: "rgb(var(--m-ink-700) / <alpha-value>)",
					800: "rgb(var(--m-ink-800) / <alpha-value>)",
					900: "rgb(var(--m-ink-900) / <alpha-value>)",
				},
				accent: {
					DEFAULT: "rgb(var(--m-accent) / <alpha-value>)",
					100: "rgb(var(--m-accent-100) / <alpha-value>)",
					200: "rgb(var(--m-accent-200) / <alpha-value>)",
					300: "rgb(var(--m-accent-300) / <alpha-value>)",
					400: "rgb(var(--m-accent-400) / <alpha-value>)",
					500: "rgb(var(--m-accent-500) / <alpha-value>)",
					600: "rgb(var(--m-accent-600) / <alpha-value>)",
					700: "rgb(var(--m-accent-700) / <alpha-value>)",
					800: "rgb(var(--m-accent-800) / <alpha-value>)",
					900: "rgb(var(--m-accent-900) / <alpha-value>)",
				},
				ground: "rgb(var(--m-ground) / <alpha-value>)",
				surface: "rgb(var(--m-surface) / <alpha-value>)",
				inkbase: "rgb(var(--m-inkbase) / <alpha-value>)",
				divider: "var(--m-divider-color)",
			},
			screens: {
				standalone: {
					raw: "(display-mode: standalone)",
				},
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
