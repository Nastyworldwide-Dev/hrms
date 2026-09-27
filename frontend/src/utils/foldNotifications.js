// Fold a day's notifications (alpha.13 slice 3, owner ruling R6): the same
// person asking for the same kind of thing becomes one entry with its members,
// the newest leading. Input is newest first (the list's order); a fold keeps
// the place of its newest member, so the day still reads top to bottom.

//: [{ key, lead, members, unread }]; `unread` is how many members are unread.
export function foldNotifications(items) {
	const folds = new Map()
	for (const item of items || []) {
		const key = `${item.from_user || ""}|${item.reference_document_type || ""}`
		let fold = folds.get(key)
		if (!fold) {
			fold = { key, lead: item, members: [], unread: 0 }
			folds.set(key, fold)
		}
		fold.members.push(item)
		if (!item.read) fold.unread += 1
	}
	return [...folds.values()]
}
