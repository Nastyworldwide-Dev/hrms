// The Calendar key (owner ruling R1, 23 Sep 2026: "always show every kind").
// It used to list only the states a month had (plan C6), so the key changed
// month to month and had to be re-read each time; a fixed key is learned
// once, and every colour keeps its word (WCAG 1.4.1). `days` stays in the
// signature so callers need not change.
export function legendFor(legend, days) {
	console.debug("[calendarLegend] full key", legend.length, "kinds;", days?.length ?? 0, "days")
	return legend
}
