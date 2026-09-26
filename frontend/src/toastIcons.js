// The six glyphs frappe-ui's Toast draws, and nothing else (alpha.12 C4).
// vite.config.js points the toast's own icon import (the Toast icon component inside
// frappe-ui) here: the original pulled the whole icon library (157 KB) into
// every first download for a toast that only ever shows these. Same props and
// SVG output as the component it replaces.
import { h, mergeProps } from "vue"

const ICONS = {
	"check-circle": "<path d=\"M22 11.08V12a10 10 0 1 1-5.93-9.14\"></path><polyline points=\"22 4 12 14.01 9 11.01\"></polyline>",
	"alert-circle": "<circle cx=\"12\" cy=\"12\" r=\"10\"></circle><line x1=\"12\" y1=\"8\" x2=\"12\" y2=\"12\"></line><line x1=\"12\" y1=\"16\" x2=\"12.01\" y2=\"16\"></line>",
	"alert-triangle": "<path d=\"M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z\"></path><line x1=\"12\" y1=\"9\" x2=\"12\" y2=\"13\"></line><line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"></line>",
	"info": "<circle cx=\"12\" cy=\"12\" r=\"10\"></circle><line x1=\"12\" y1=\"16\" x2=\"12\" y2=\"12\"></line><line x1=\"12\" y1=\"8\" x2=\"12.01\" y2=\"8\"></line>",
	"x": "<line x1=\"18\" y1=\"6\" x2=\"6\" y2=\"18\"></line><line x1=\"6\" y1=\"6\" x2=\"18\" y2=\"18\"></line>",
	"circle": "<circle cx=\"12\" cy=\"12\" r=\"10\"></circle>"
}

export default {
	props: {
		name: { type: String, required: true },
		color: { type: String, default: null },
		strokeWidth: { type: Number, default: 1.5 },
	},
	render() {
		if (!ICONS[this.name]) console.info("[toastIcons] no icon", this.name, "- drawing a circle")
		const contents = ICONS[this.name] ?? ICONS.circle
		return h(
			"svg",
			mergeProps(
				{
					xmlns: "http://www.w3.org/2000/svg",
					viewBox: "0 0 24 24",
					fill: "none",
					stroke: "currentColor",
					color: this.color,
					"stroke-linecap": "round",
					"stroke-linejoin": "round",
					"stroke-width": this.strokeWidth,
					class: ["feather", `feather-${this.name}`, "shrink-0"],
					innerHTML: contents,
				},
				this.$attrs,
			),
		)
	},
}
