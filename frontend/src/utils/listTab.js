// Which tab a list opens on. Home's "Waiting on you" rows send the approver to
// a list with ?tab=team; without honouring it the list opened on the person's
// OWN requests, empty, with the thing to decide behind a second tab (audit
// P0-9). The team tab is always the second one, and only exists for an
// approver, so "team" is honoured only when there is a second tab.
export function initialListTab(tabs, requested) {
	if (!tabs?.length) return undefined
	const keys = tabs.map((tab) => tab?.key ?? tab)
	if (requested === "team" && keys.length > 1) {
		console.info("[listTab] opening on the team tab", keys[1])
		return keys[1]
	}
	return keys[0]
}
