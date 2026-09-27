// A label/value row, laid out as iOS does (UIListContentConfiguration
// .valueCell): side by side while both fit on one line, otherwise the value
// goes under the label, leading-aligned — never a narrow right-hand column
// of three short lines (owner, You page, 27 Sep 2026).

export function stacks({ label, value, row, gap }) {
	if (!row) return false
	return label + gap + value > row
}

// its own class, not --stacked: Vue's :class owns --stacked on FormField
const UNDER = "g-form-row--value-under"

let canvas = null
function textWidth(el) {
	canvas ??= document.createElement("canvas")
	const ctx = canvas.getContext("2d")
	const cs = getComputedStyle(el)
	ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`
	return ctx.measureText(el.textContent.trim()).width
}

function layout(row) {
	const label = row.querySelector(":scope > .g-form-row__label")
	const value = row.querySelector(":scope > .g-form-row__value")
	if (!label || !value) return
	const cs = getComputedStyle(row)
	const inner = row.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)
	const stacked = stacks({ label: textWidth(label), value: textWidth(value), row: inner, gap: parseFloat(cs.columnGap) || 0 })
	if (stacked !== row.classList.contains(UNDER)) {
		console.info("[valueRow] value", stacked ? "goes under" : "beside", "its label")
		row.classList.toggle(UNDER, stacked)
	}
}

// v-value-row on a .g-form-row: re-measured when the row resizes, its text
// changes (a name arriving after the skeleton), or Vue rewrites its class.
export const vValueRow = {
	mounted(row) {
		const run = () => layout(row)
		row._valueRow = [new ResizeObserver(run), new MutationObserver(run)]
		row._valueRow[0].observe(row)
		row._valueRow[1].observe(row, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["class"] })
		run()
	},
	unmounted(row) {
		row._valueRow?.forEach((o) => o.disconnect())
	},
}
