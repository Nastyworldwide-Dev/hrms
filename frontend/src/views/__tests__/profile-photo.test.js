// Profile photo UI: pins the wiring a later edit could silently break.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const dir = join(import.meta.dirname, "..")
const profile = readFileSync(join(dir, "Profile.vue"), "utf8")
const sheet = readFileSync(join(dir, "..", "components", "PhotoSheet.vue"), "utf8")

test("Profile posts to set_photo and remove_photo", () => {
	assert.match(profile, /url: "hrms\.api\.profile_photo\.set_photo"/)
	assert.match(profile, /url: "hrms\.api\.profile_photo\.remove_photo"/)
	assert.match(profile, /submit\(\{ image: dataUrl \}\)/)
})

test("avatar is a Change photo button; file input takes images", () => {
	assert.match(profile, /:aria-label="__\('Change photo'\)"/)
	assert.match(profile, /accept="image\/\*"/)
	assert.match(profile, /capture="user"/)
})

test("5 MB and not-image messages are role=status, and return before the crop sheet", () => {
	assert.match(profile, /This photo is over 5 MB\. Pick a smaller one\./)
	assert.match(profile, /That file isn't a photo\. Pick a JPEG or PNG\./)
	assert.match(profile, /class="g-account__error" role="status"/)
})

test("remove asks first; Reports to links to OrgChart only with reports_to", () => {
	assert.match(profile, /<GConfirm[\s\S]*?Remove your photo\?/)
	assert.match(profile, /v-else-if="employeeDoc\.doc\?\.reports_to"/)
	assert.match(profile, /name: 'OrgChart', query: \{ employee: employeeDoc\.doc\.reports_to \}/)
})

test("PhotoSheet: Zoom slider, locks while saving, 512 JPEG 0.85", () => {
	assert.match(sheet, /:aria-label="__\('Zoom'\)"/)
	assert.match(sheet, /:dismissible="!saving"/)
	assert.match(sheet, /toDataURL\("image\/jpeg", 0\.85\)/)
	assert.match(sheet, /out\.width = out\.height = 512/)
})
