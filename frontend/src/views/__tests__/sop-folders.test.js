// SOP folders (owner, 27 Oct 2026; mockups/mockup-sop-folders.html).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

test("the SOP page lists folders before General, and HR gets Manage folders", () => {
	const list = read("views/sop/SopList.vue")
	const folders = list.indexOf('__("Folders")')
	assert.ok(folders > 0 && folders < list.indexOf('v-for="section in sections"'))
	assert.match(list, /name: "SopFolderView"/)
	assert.match(list, /v-if="isHR"\s+:label="__\('Manage folders'\)"/)
	assert.match(list, /sop\.folderName \|\| scopeLabel\(sop\)/)
})

test("a folder opens its own page that reads the list's answer", () => {
	assert.match(read("router/sop.js"), /name: "SopFolderView",\s+path: "\/sop\/folder\/:folder"/)
	const page = read("views/sop/SopFolder.vue")
	assert.match(page, /personalCacheKey\("hrms:sops"\)/)
	assert.match(page, /No SOPs in this folder yet/)
})

test("the SOP sheet picks a folder, or makes a new one with a Create that says why it is dimmed", () => {
	const sheet = read("views/sop/SopFormSheet.vue")
	assert.match(sheet, /__\("No folder"\)/)
	assert.match(sheet, /__\("New folder…"\)/)
	assert.match(sheet, /folder: form\.folder \|\| ""/)
	assert.match(sheet, /:disabled="!newFolderName\.trim\(\) \|\| createFolder\.loading"/)
	assert.match(sheet, /:aria-describedby="newFolderName\.trim\(\) \? undefined : newFolderHintId"/)
	assert.match(sheet, /:id="newFolderHintId"[^>]*>\s*\{\{ __\("Name the folder"\) \}\}/)
	assert.match(sheet, /url: "hrms\.api\.sop\.save_folder"/)
})

test("Manage folders moves and renames every folder, deletes only an empty one", () => {
	const sheet = read("views/sop/SopManageFolders.vue")
	assert.match(sheet, /__\('Move \{0\} up', \[folder\.folder_name\]\)/)
	assert.match(sheet, /__\('Move \{0\} down', \[folder\.folder_name\]\)/)
	assert.match(sheet, /v-if="folder\.count === 0"[\s\S]*?__\("Delete"\)/)
	assert.match(sheet, /A folder with SOPs in it cannot be deleted\. Move its SOPs first\./)
	assert.match(sheet, /await props\.sops\.reload\(\)/)
})
