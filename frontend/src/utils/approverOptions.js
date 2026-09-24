// Approver picker options: the person's name as the label, their login as the
// value. The pickers showed "email : Name", with the name cut off on a phone
// (owner, 24 Sep 2026). The value is unchanged, so what the server receives and
// validates is exactly what it did before.

const handle = (login) => String(login || "").split("@")[0]

export function approverOptions(approvers) {
	const list = approvers || []
	const count = {}
	for (const a of list) count[a.full_name] = (count[a.full_name] || 0) + 1
	return list.map((a) => ({
		// Two people with one name need telling apart; the handle does that
		// without printing a whole address.
		label: !a.full_name
			? handle(a.name)
			: count[a.full_name] > 1
			? `${a.full_name} (${handle(a.name)})`
			: a.full_name,
		value: a.name,
	}))
}
