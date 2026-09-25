// The half-day AM | PM choice, in the person's own words (owner, 25 Sep 2026).
// `hints` comes from hrms.api.half_day.get_half_day_hints: what each half means
// in the caller's shift on that date. The option is SHORT so a picked value
// fits the row ("AM · start 13:30"); the full sentence is the line under it.
// Without a shift that day the choice still reads plainly; nothing is guessed.
const PLAIN = { AM: "Off in the morning.", PM: "Off in the afternoon." }

export function sessionOptions(hints, __) {
	return ["AM", "PM"].map((value) => {
		const short = hints?.[`${value}_short`]
		return { value, label: short ? `${value} · ${__(short)}` : value }
	})
}

//: The sentence under the choice: what the picked half means, or what to pick.
export function sessionGuidance(hints, session, __) {
	if (session === "AM" || session === "PM") return __(hints?.[session] || PLAIN[session])
	return __("AM if you are off in the morning, PM if you leave at mid-shift.")
}
