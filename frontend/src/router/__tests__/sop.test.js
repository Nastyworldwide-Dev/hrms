// SOP routes (owner, 27 Oct 2026): a folder has its own page, and its path
// is matched before /sop/:id, so "folder" is never read as an SOP name.
import { test } from "node:test"
import assert from "node:assert/strict"
import { createMemoryHistory, createRouter } from "vue-router"

import routes from "../sop.js"

test("/sop/folder/<name> opens the folder page, /sop/<id> the SOP", () => {
	const router = createRouter({ history: createMemoryHistory(), routes })
	const folder = router.resolve("/sop/folder/Safety")
	assert.equal(folder.name, "SopFolderView")
	assert.equal(folder.params.folder, "Safety")
	assert.equal(router.resolve("/sop/HR-SOP-00002").name, "SopDetailView")
})
