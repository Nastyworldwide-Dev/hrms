// A build's identity, from what it precaches (28 Sep 2026). The service worker
// is served at one fixed URL (/hrms/sw.js) since alpha.12, so the URL no longer
// tells builds apart; the precache list does — a changed file changes its
// revision or its hashed name. Pure, and imported by public/sw.js, which
// answers "GET_BUILD_ID" with it so the page can remember a dismissal per build.

//: FNV-1a, 32-bit: small, stable, no crypto needed — this names a build, it
//: does not protect anything.
function fnv1a(text) {
	let hash = 0x811c9dc5
	for (let i = 0; i < text.length; i++) {
		hash ^= text.charCodeAt(i)
		hash = Math.imul(hash, 0x01000193) >>> 0
	}
	return hash.toString(16).padStart(8, "0")
}

export function buildIdOf(entries) {
	if (!Array.isArray(entries) || !entries.length) return null
	const lines = entries
		.map((entry) => (typeof entry === "string" ? entry : `${entry.url}|${entry.revision ?? ""}`))
		.sort()
	return fnv1a(lines.join("\n"))
}
