// A page stops at its edges, as a native screen does (owner, 25 Sep 2026:
// "scrolling to max top or bottom still pulls its own content"). On iOS Ionic
// turns ion-content's forceOverscroll ON by default (ion-content.js,
// shouldForceOverscroll: mode ios + platform ios), rubber-banding the page past
// both ends. The property exists per element only, not in the Ionic config,
// so it is set once here for every ion-content the app ever mounts, instead of
// on 19 templates a new page could forget.
// Pull-to-refresh is not affected: GPullRefresh drives its own gesture.
export function noOverscroll(root = globalThis.document) {
	if (!root?.addEventListener || typeof MutationObserver === "undefined") return null
	const settle = (el) => {
		if (el.forceOverscroll !== false) el.forceOverscroll = false
	}
	root.querySelectorAll?.("ion-content").forEach(settle)
	const observer = new MutationObserver((records) => {
		for (const record of records) {
			for (const node of record.addedNodes) {
				if (node.nodeType !== 1) continue
				if (node.tagName === "ION-CONTENT") settle(node)
				node.querySelectorAll?.("ion-content").forEach(settle)
			}
		}
	})
	observer.observe(root.documentElement || root, { childList: true, subtree: true })
	console.info("[noOverscroll] pages stop at their edges")
	return observer
}
