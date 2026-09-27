// alpha.14 S1. The installed app keeps a copy of the /hrms page for offline
// use (public/sw.js, cache "nadi-pages", alpha.12). Frappe renders that page
// PER USER — it carries the signed-in person's boot data. Nothing deleted it,
// so on a shared phone the next person, offline, could open the last one's.
// It goes when someone logs out AND when someone logs in (a login that merely
// expired never passed through logout).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { clearCachedPages, PAGE_CACHE } from "../cachedPages.js"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("the page copy is deleted, and only it", async () => {
	const deleted = []
	await clearCachedPages({ delete: async (name) => (deleted.push(name), true) })
	assert.deepEqual(deleted, [PAGE_CACHE])
})

test("it names the cache the service worker writes", () => {
	assert.match(read("../../../public/sw.js"), new RegExp(`cacheName: "${PAGE_CACHE}"`))
})

test("no Cache Storage, or a refusing one, never blocks logging in or out", async () => {
	await clearCachedPages(undefined)
	await clearCachedPages({ delete: () => Promise.reject(new Error("blocked")) })
})

test("logging out and logging in both clear it", () => {
	const session = read("../../data/session.js")
	const login = session.slice(session.indexOf("function handleLogin"), session.indexOf("export const session"))
	const logout = session.slice(session.indexOf("logout: createResource"))
	assert.match(login, /await clearCachedPages\(\)[\s\S]*window\.location\.replace/)
	assert.match(logout, /await clearCachedPages\(\)[\s\S]*window\.location\.reload/)
})
