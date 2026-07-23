import frappeUIPreset from "frappe-ui/src/tailwind/preset"
export default {
	presets: [frappeUIPreset],
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
			colors: {
				ink: {
					100: "#f8f4f4",
					200: "#eae7e7",
					300: "#d7d3d3",
					400: "#bab6b6",
					500: "#9b9797",
					600: "#7d7979",
					700: "#605d5d",
					800: "#444141",
					900: "#2d2b2b",
				},
				accent: {
					DEFAULT: "#0B313A",
					100: "#eafaf2",
					200: "#A1EEC9",
					300: "#7fdcb2",
					400: "#4cc492",
					500: "#1a9a74",
					600: "#164a56",
					700: "#0B313A",
					800: "#08242c",
					900: "#05181e",
				},
				ground: "#f3f2f2",
				surface: "#eae9e9",
				inkbase: "#201e1d",
				divider: "rgba(32,30,29,0.4)",
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
