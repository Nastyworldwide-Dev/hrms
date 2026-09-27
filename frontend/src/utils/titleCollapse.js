// Whether a tab root's large title has scrolled under the bar (so the bar
// shows its small title). Read from one IntersectionObserver entry.
//
// Only a measured page decides. While a pushed screen is up, Ionic hides the
// tab page; its boxes read 0x0, which looks exactly like "the title went above
// the top edge" — the double title the owner saw after coming Back (27 Sep
// 2026). A hidden page keeps what it was.
export function titleCollapsed(entry, was) {
	const root = entry.rootBounds
	if (!root || root.height === 0 || entry.boundingClientRect.height === 0) return was
	return !entry.isIntersecting && entry.boundingClientRect.bottom <= root.top
}
