// A deploy publishes new hashed chunks and the service worker purges the old
// ones (cleanupOutdatedCaches). A tab left open on the previous build then
// lazy-loads a chunk hash that no longer exists — the dynamic import rejects
// mid-navigation and the route renders a broken/half-old state. The three
// wordings below are how Chromium, Firefox and webpack-era bundlers phrase that
// same "the chunk I asked for is gone" failure.
//
// Kept in its own DOM-free, import-free module so it can be unit-tested under
// `node --test` (index.js pulls in ionic/router deps that need a browser).
export function isStaleChunkError(message) {
	return /dynamically imported module|Importing a module script failed|ChunkLoadError/i.test(
		message || ""
	)
}
