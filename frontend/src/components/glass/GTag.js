import { h } from "vue"

/**
 * GTag — render a NATIVE element whose tag is decided at runtime.
 *
 * THE TRAP THIS EXISTS TO AVOID (8.2). Vue's `<component :is="'button'">`
 * resolves the string against registered components BEFORE treating it as an
 * HTML tag — `resolveDynamicComponent` tries the name, its camelCase form and
 * its capitalised form. `main.js` does `app.component("Button", Button)`, so
 * `'button'` found frappe-ui's Button and every Glass row, card and panel
 * rendered as a frappe-ui button instead of a `<button>`.
 *
 * What that cost: frappe-ui's own classes (`inline-flex justify-center h-7
 * px-2 rounded bg-surface-gray-2`) landed on top of the Glass class and won —
 * `justify-center` centred the label, `h-7` fought the 44px min-height, `px-2`
 * replaced --g-pad-row — and frappe-ui wrapped every slot in a single <span>,
 * so the icon well, body and chevron stopped being flex children of the row
 * and stacked instead. That is the whole "icons misaligned everywhere" defect.
 *
 * `h()` takes a string as a tag name directly and never consults the registry,
 * so this always renders the real element. Use it anywhere the tag is dynamic.
 *
 * Props:
 *   as  string, required — the tag to render, e.g. "button" or "div"
 * Everything else (class, type, listeners) falls through to the element.
 */
export default {
	name: "GTag",
	// attrs are applied by hand below; without this they would land twice
	inheritAttrs: false,
	props: {
		as: { type: String, required: true },
	},
	setup(props, { slots, attrs }) {
		return () => h(props.as, attrs, slots.default?.())
	},
}
