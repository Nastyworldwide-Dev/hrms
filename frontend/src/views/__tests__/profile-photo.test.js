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

test("avatar is a Change profile photo button; file input takes images", () => {
	assert.match(profile, /:aria-label="__\('Change profile photo'\)"/)
	assert.match(profile, /accept="image\/\*"/)
	assert.match(profile, /capture="user"/)
})

test("5 MB and not-image messages are role=alert, and return before the crop sheet", () => {
	assert.match(profile, /This photo is over 5 MB\. Pick a smaller one\./)
	assert.match(profile, /That file isn't a photo\. Pick a JPEG or PNG\./)
	assert.match(profile, /class="g-account__error" role="alert"/)
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

test("reduced motion stops the spinner and sheet transitions; saving says so", () => {
	assert.match(
		profile,
		/@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.g-account__spinner[\s\S]*?animation: none/
	)
	assert.match(sheet, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?transition: none/)
	assert.match(profile, /Saving your photo…/)
	assert.match(profile, /:aria-describedby="photoUploadBusy \? .photo-saving. : undefined"/)
})

test("busy avatar tap returns early", () => {
	assert.match(profile, /function openPhotoActions\(\) \{\s*if \(photoUploadBusy\.value\) return/)
})

test("a new pick and Remove clear the stale retry", () => {
	assert.match(
		profile,
		/photoError\.value = ""\s*photoRetry\.value = ""\s*\n?\s*\/\/ Check file size/
	)
	assert.match(profile, /async function removePhoto\(\) \{[\s\S]*?photoRetry\.value = ""/)
})

test("undecodable image emits error; Profile shows not-a-photo and closes", () => {
	assert.match(sheet, /newImg\.onerror = \(\) => \{[\s\S]*?emit\("error"\)/)
	assert.match(profile, /@error="onPhotoUndecodable"/)
	assert.match(sheet, /if \(props\.saving\) return/)
})

test("error is role=alert in the danger ink token, no hard-coded fallbacks", () => {
	assert.match(profile, /class="g-account__error" role="alert"/)
	assert.match(profile, /var\(--g-danger-ink\)/)
	assert.doesNotMatch(profile, /#b3261e/)
	assert.doesNotMatch(profile, /var\(--g-bg, #fff\)/)
})

test("action rows carry icons; company footer", () => {
	assert.match(profile, /icon: ImageIcon/)
	assert.match(profile, /icon: Trash2/)
	assert.match(profile, /Your photo is seen by people in/)
})
