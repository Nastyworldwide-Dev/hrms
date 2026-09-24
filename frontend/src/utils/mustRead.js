// The must-read flow (alpha.7 plan 4.4/4.5). Pure, so the rules are testable.

//: The next notice to open full screen: the server's order (urgent first, then
//: oldest), skipping ones put off this session. Urgent ones cannot be put off.
export function nextMustRead(queue, snoozed) {
	return (queue || []).find((n) => Number(n.urgent) || !snoozed.has(n.name)) || null
}

//: The confirm button stays focusable before the end is reached (a disabled
//: button hides the reason from VoiceOver); it says why and scrolls on tap.
export function confirmState({ reachedEnd, pending }) {
	if (pending) return { ready: false, label: "Recording…" }
	if (!reachedEnd) return { ready: false, label: "Read to the end to confirm" }
	return { ready: true, label: "I have read this" }
}
