// GENERATED FROM design/tokens.json BY design/build-tokens.mjs — DO NOT EDIT BY HAND.
// Regenerate: yarn tokens  (in frontend/)
// Merge into tailwind.config.js theme.extend (prompt 1.3).
// rgba()-based tokens (accent-glow, glass, glass-fallback, rim, hair, icon-bg, rim-hi, rim-lo, sheen)
// are plain var() references and do not support Tailwind opacity modifiers.
module.exports = {
	backdropBlur: {
		ghost: "var(--g-blur-ghost)",
		panel: "var(--g-blur-panel)",
	},
	borderRadius: {
		action: "var(--g-radius-action)",
		banner: "var(--g-radius-banner)",
		card: "var(--g-radius-card)",
		input: "var(--g-radius-input)",
		panel: "var(--g-radius-panel)",
		pill: "var(--g-radius-pill)",
		tabbar: "var(--g-radius-tabbar)",
		tile: "var(--g-radius-tile)",
		well: "var(--g-radius-well)",
	},
	boxShadow: {
		action: "var(--g-shadow-action)",
		lift: "var(--g-lift)",
	},
	colors: {
		"accent-glow": "var(--g-accent-glow)",
		"accent-ink": "rgb(var(--g-accent-ink-rgb) / <alpha-value>)",
		bg: "rgb(var(--g-bg-rgb) / <alpha-value>)",
		brand: "rgb(var(--g-brand-rgb) / <alpha-value>)",
		"brand-2": "rgb(var(--g-brand-2-rgb) / <alpha-value>)",
		danger: "rgb(var(--g-danger-rgb) / <alpha-value>)",
		"danger-ink": "rgb(var(--g-danger-ink-rgb) / <alpha-value>)",
		glass: "var(--g-glass-fill)",
		"glass-fallback": "var(--g-glass-fill-fallback)",
		hair: "var(--g-hair)",
		"icon-bg": "var(--g-icon-bg)",
		ink: "rgb(var(--g-ink-rgb) / <alpha-value>)",
		"ink-2": "rgb(var(--g-ink2-rgb) / <alpha-value>)",
		"ink-3": "rgb(var(--g-ink3-rgb) / <alpha-value>)",
		"ink-muted": "rgb(var(--g-ink-muted-rgb) / <alpha-value>)",
		leave: "rgb(var(--g-leave-rgb) / <alpha-value>)",
		"leave-ink": "rgb(var(--g-leave-ink-rgb) / <alpha-value>)",
		"neutral-dot": "rgb(var(--g-neutral-dot-rgb) / <alpha-value>)",
		"on-brand": "rgb(var(--g-on-brand-rgb) / <alpha-value>)",
		rest: "rgb(var(--g-rest-rgb) / <alpha-value>)",
		rim: "var(--g-glass-rim)",
		"rim-hi": "var(--g-rim-hi)",
		"rim-lo": "var(--g-rim-lo)",
		sheen: "var(--g-sheen)",
		success: "rgb(var(--g-success-rgb) / <alpha-value>)",
		"success-ink": "rgb(var(--g-success-ink-rgb) / <alpha-value>)",
		warn: "rgb(var(--g-warn-rgb) / <alpha-value>)",
		"warn-ink": "rgb(var(--g-warn-ink-rgb) / <alpha-value>)",
	},
	fontFamily: {
		display: "var(--g-font-display)",
		mono: "var(--g-font-mono)",
		ui: "var(--g-font-ui)",
	},
	fontSize: {
		badge: ["10px", {
			fontWeight: "700",
			letterSpacing: "0.09em",
			lineHeight: "1.2",
		}],
		"button-label": ["15.5px", {
			fontWeight: "800",
			letterSpacing: "-0.01em",
			lineHeight: "1.2",
		}],
		caption: ["10.5px", {
			fontWeight: "400",
			letterSpacing: "0.02em",
			lineHeight: "1.45",
		}],
		"card-title": ["12.5px", {
			fontWeight: "600",
			letterSpacing: "0",
			lineHeight: "1.4",
		}],
		clock: ["36px", {
			fontWeight: "800",
			letterSpacing: "-0.02em",
			lineHeight: "1",
		}],
		"data-system": ["10px", {
			fontWeight: "400",
			letterSpacing: "0",
			lineHeight: "1.5",
		}],
		"display-number": ["31px", {
			fontWeight: "800",
			letterSpacing: "-0.02em",
			lineHeight: "1",
		}],
		eyebrow: ["10.5px", {
			fontWeight: "600",
			letterSpacing: "0.13em",
			lineHeight: "1.3",
		}],
		"field-label": ["10px", {
			fontWeight: "600",
			letterSpacing: "0.14em",
			lineHeight: "1.3",
		}],
		"kra-label": ["11.5px", {
			fontWeight: "600",
			letterSpacing: "0",
			lineHeight: "1.4",
		}],
		"micro-label": ["10px", {
			fontWeight: "600",
			letterSpacing: "0.13em",
			lineHeight: "1.3",
		}],
		"panel-title": ["14.5px", {
			fontWeight: "800",
			letterSpacing: "-0.02em",
			lineHeight: "1.2",
		}],
		"ring-centre": ["25px", {
			fontWeight: "800",
			letterSpacing: "-0.02em",
			lineHeight: "1",
		}],
		"row-label": ["12.5px", {
			fontWeight: "500",
			letterSpacing: "0",
			lineHeight: "1.4",
		}],
		"screen-title": ["21.5px", {
			fontWeight: "800",
			letterSpacing: "-0.025em",
			lineHeight: "1.15",
		}],
		"stat-number": ["22px", {
			fontWeight: "800",
			letterSpacing: "-0.02em",
			lineHeight: "1",
		}],
		"tab-label": ["10px", {
			fontWeight: "600",
			letterSpacing: "0.07em",
			lineHeight: "1.2",
		}],
	},
	opacity: {
		blob: "var(--g-blob-opacity)",
	},
	spacing: {
		"screen-gutter": "var(--g-screen-gutter)",
		"stack-lg": "var(--g-stack-lg)",
		"stack-md": "var(--g-stack-md)",
		"stack-sm": "var(--g-stack-sm)",
	},
	transitionDuration: {
		"button-press": "var(--g-motion-button-press-duration)",
		"check-in-success": "var(--g-motion-check-in-success-duration)",
		"row-tap": "var(--g-motion-row-tap-duration)",
		"screen-push": "var(--g-motion-screen-push-duration)",
		"sheet-present": "var(--g-motion-sheet-present-duration)",
		"skeleton-shimmer": "var(--g-motion-skeleton-shimmer-duration)",
		"theme-change": "var(--g-motion-theme-change-duration)",
	},
	transitionTimingFunction: {
		"button-press": "var(--g-motion-button-press-easing)",
		"row-tap": "var(--g-motion-row-tap-easing)",
		"screen-push": "var(--g-motion-screen-push-easing)",
		"sheet-present": "var(--g-motion-sheet-present-easing)",
		"skeleton-shimmer": "var(--g-motion-skeleton-shimmer-easing)",
		"theme-change": "var(--g-motion-theme-change-easing)",
	},
};
