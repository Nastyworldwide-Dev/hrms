// The service worker's address, the same every launch for the same settings
// (owner, 28 Sep 2026: the update bar kept coming back on real phones).
//
// The browser treats a different worker URL as a new worker. The URL carries
// the push settings (the worker reads them from ?config=), which main.js
// fetches from the relay on every launch. Two ways that changed the address
// with no deploy: the settings came back with their keys in another order,
// and a slow or failed fetch registered the plain address one launch and the
// full one the next. Keys are sorted, and a failed fetch reuses the settings
// that last worked (main.js keeps them), so only a real change in the
// settings — or a real new build — makes a new worker.

function sorted(value) {
	if (Array.isArray(value)) return value.map(sorted)
	if (value && typeof value === "object") {
		return Object.fromEntries(
			Object.keys(value)
				.sort()
				.map((key) => [key, sorted(value[key])])
		)
	}
	return value
}

export function workerURL(base, fresh, stored) {
	const config = fresh || stored
	if (!config) return base
	return `${base}?config=${encodeURIComponent(JSON.stringify(sorted(config)))}`
}
