import { createDocumentResource } from "frappe-ui"

import dayjs from "@/utils/dayjs"

const settings = createDocumentResource({
	doctype: "System Settings",
	name: "System Settings",
	auto: false,
})

export const formatCurrency = (value, currency) => {
	if (!currency) return value

	// hack: if value contains a space, it is already formatted
	if (value?.toString().trim().includes(" ")) return value

	// A Currency amount is numeric and defaults to 0; an undefined/null/NaN here
	// (an uninitialised total, a sum taken before rows have loaded) must never
	// reach Intl.NumberFormat, which renders it as "NaN" — the "RMNaN" seen in
	// the expenses UI. Coerce to a finite number; 0 is the correct money zero.
	const num = Number(value)
	const amount = Number.isFinite(num) ? num : 0
	// Signal only a genuine anomaly — a non-empty value that is not a number —
	// so a malformed total is findable, without logging the ordinary empty case.
	if (value != null && value !== "" && !Number.isFinite(num))
		console.warn("[formatters] non-numeric currency value coerced to 0:", value)

	const locale = settings.doc?.country == "India" ? "en-IN" : settings.doc?.language

	const formatter = Intl.NumberFormat(locale, {
		style: "currency",
		currency: currency,
		trailingZeroDisplay: "stripIfInteger",
		currencyDisplay: "narrowSymbol",
	})
	return (
		formatter
			.format(amount)
			// add space between the digits and symbol
			.replace(/^(\D+)/, "$1 ")
			// remove extra spaces if any (added by some browsers)
			.replace(/\s+/, " ")
	)
}

export const formatLeaveDays = (value) => {
	// one decimal only when fractional: 10.5 (not 10.50), 11 (not 11.0)
	const rounded = Math.round((Number(value) || 0) * 10) / 10
	return rounded.toString()
}

export const formatTimestamp = (timestamp) => {
	const formattedTime = dayjs(timestamp).format("hh:mm a")

	if (dayjs(timestamp).isToday()) return formattedTime
	else if (dayjs(timestamp).isYesterday()) return `${formattedTime} yesterday`
	else if (dayjs(timestamp).isSame(dayjs(), "year"))
		return `${formattedTime} on ${dayjs(timestamp).format("D MMM")}`

	return `${formattedTime} on ${dayjs(timestamp).format("D MMM, YYYY")}`
}
