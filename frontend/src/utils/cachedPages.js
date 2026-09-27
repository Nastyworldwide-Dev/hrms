// The offline copy of the /hrms page (public/sw.js). Frappe renders that page
// per user, so it belongs to whoever was signed in: it goes when anyone logs
// in or out, or the next person on a shared phone could open it offline.
export const PAGE_CACHE = "nadi-pages"

export async function clearCachedPages(store = globalThis.caches) {
	if (!store) return
	try {
		const gone = await store.delete(PAGE_CACHE)
		console.info("[cachedPages] offline page copy cleared", gone)
	} catch {
		// a blocked Cache Storage must not stop anyone logging in or out
		console.warn("[cachedPages] offline page copy could not be cleared")
	}
}
