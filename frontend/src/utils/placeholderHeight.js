// How tall a block was the last time it answered, so its loading placeholder can hold that space
// and the content under it does not jump when the answer lands (iOS gate scroll-and-shift,
// 27 Oct 2026: Approvals 208 pt, Home Needs you 54 pt, on every visit). frappe-ui reads its own
// cache back after the first paint, so the cache alone never prevented the jump.
// Per person and per block: a height says how much work someone has, nothing to share.
// A min-height only, never a fixed height: a shorter answer still collapses (once).

const KEY = (block, user) => `hrms:ph:${block}:${user}`

export function rememberHeight(block, user, px) {
	if (!user || !(px > 0)) return
	try {
		localStorage.setItem(KEY(block, user), String(Math.round(px)))
	} catch {
		// private mode or storage blocked: the placeholder falls back to its own size
	}
}

export function rememberedHeight(block, user) {
	if (!user) return 0
	try {
		const px = Number(localStorage.getItem(KEY(block, user)))
		return Number.isFinite(px) && px > 0 ? px : 0
	} catch {
		return 0
	}
}

//: An empty answer removes the block, so there is nothing to measure: without this, the old
//: tall height was held on the next load and the page jumped up (review of bcfbeaa8e).
export function forgetHeight(block, user) {
	if (!user) return
	try {
		localStorage.removeItem(KEY(block, user))
	} catch {
		// storage blocked: nothing was stored either
	}
}

//: Logout: the keys carry the person's email, so a shared phone keeps none of them.
export function forgetAllHeights() {
	try {
		const ours = []
		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i)
			if (key?.startsWith("hrms:ph:")) ours.push(key)
		}
		for (const key of ours) localStorage.removeItem(key)
	} catch {
		// storage blocked: nothing was stored either
	}
}
