// "3 days", "1 day" — never "day(s)" (audit P2-3). English only needs one or
// many; pass the plural when it is not the singular plus "s". Kept free of Vue
// imports so node tests can load it.
export function countOf(n, one, many = `${one}s`) {
	return `${n} ${Number(n) === 1 ? one : many}`
}

//: A duration in days as words (alpha.7 A16/B4): "Half day", "1 day",
//: "1½ days", "3 days". Nothing to say is "" — not "0 days".
export function daysWords(n) {
	const d = Number(n)
	if (!Number.isFinite(d) || d <= 0) return ""
	if (d === 0.5) return "Half day"
	const whole = Math.floor(d)
	const half = d - whole >= 0.5 ? "½" : ""
	const shown = `${whole || ""}${half}`
	return `${shown} ${d === 1 ? "day" : "days"}`
}
