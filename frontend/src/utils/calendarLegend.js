// Which legend keys a month shows (approved Calendar plan, C6). Listing all
// five states every month is load with no use (Hick's law; Nielsen 8): a
// month with no half days needs no "Half day" key. The order stays the
// legend's own, so a key never moves between months.
export function legendFor(legend, days) {
	const present = new Set(days.map((day) => day.state))
	const keys = legend.filter((key) => present.has(key.state))
	console.debug("[calendarLegend] keys shown", keys.length, "of", legend.length)
	return keys
}
